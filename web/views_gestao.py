"""Painel da gestão (desktop). Toda consulta de creator passa por scoped_creators (1ª camada) e RLS (2ª)."""
import csv
import datetime as dt
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.access import (assign_manager, can_contact_creator, can_edit_creator, covers_creator, get_agency, scoped_creators,
                         staff_roles, unassign_manager, visible_creators)
from core.models import AgencySettings, AppEvent, AuditLog, Role
from crm import absence, first_access, referrals
from crm import models as C
from crm.timeline import timeline
from data import engine as E
from data import importer, phases, port, states
from data.models import ImportBatch, ImportTemplate, MonthlyResult
from engage import academy
from engage import battles as battle_rules
from engage import campaigns as campaign_rules
from engage import models as M
from engage import playbook
from engage.services import (creator_facts, creator_track, notify, outside_track, pick_variant, publish_announcement, render_message,
                             template_for, templates_by_code, whatsapp_link)

from . import services as S

User = get_user_model()


def staff_required(*roles):
    def deco(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            mine = staff_roles(request.user)
            if not mine or (roles and not mine & set(roles)):
                raise PermissionDenied
            request.agency = get_agency(request.user)
            request.roles = mine
            return view(request, *args, **kwargs)

        return wrapper

    return deco


def _creator(request, pk):
    """O criador, se este usuário pode abrir a ficha: o que é dele ou o que ele cobre hoje (ver core/access.py)."""
    c = visible_creators(request.user).filter(pk=pk).first()
    if c is None:
        raise Http404
    return c


def _require_edit(request, c):
    if not can_edit_creator(request.user, c):
        raise PermissionDenied


def _require_contact(request, c):
    """Registrar contato: quem edita o criador ou quem cobre a carteira dele hoje."""
    if not can_contact_creator(request.user, c):
        raise PermissionDenied


# O que quem cobre a carteira pode registrar na ficha. O resto (cadastro, saída, adiar, código de acesso) é de quem edita.
COVER_ACTIONS = {"note", "responded", "wrote"}


IMPORT_ROLES = {
    "backstage": {Role.ADMIN, Role.GESTORA},  # importação diária: gestão ou sócias
    "task": {Role.ADMIN, Role.FINANCEIRO},  # fechamento do mês
}


def _can_import(roles, kind):
    return bool(set(roles) & IMPORT_ROLES.get(kind, {Role.ADMIN}))


def _phone(c):
    p = getattr(c, "private", None)
    return p.whatsapp if p else ""


def _msg(request, body, c):
    """Mensagem pronta para o criador, com o endereço da tela de primeiro acesso deste app."""
    return render_message(body, c, link_app=request.build_absolute_uri(reverse("first_access")))


# ================================================================== dashboard
@staff_required()
def dashboard(request):
    creators = scoped_creators(request.user)
    queue = S.action_queue(creators, request.agency)
    nums = S.dashboard_numbers(creators, request.agency)
    shown = queue[:60]
    link_app = request.build_absolute_uri(reverse("first_access"))
    S.fill_queue_messages(shown, request.agency, link_app=link_app)
    from .panel import pending_by_creator  # manter ou encerrar: mostra "aguardando as sócias" (passo 4.1)

    pending = pending_by_creator([i.creator.pk for i in shown if i.asks_partners])
    for i in shown:
        i.approval = pending.get(i.creator.pk) if i.asks_partners else None
    # ausência: a gestora que avisou "Hoje não trabalho" vê o aviso no lugar da fila; quem cobre vê o que não pode esperar
    is_manager, is_admin = Role.GESTORA in request.roles, Role.ADMIN in request.roles
    away = absence.active(request.user) if is_manager else None
    coverage = S.coverage_blocks(request.user, request.agency, is_admin)
    for b in coverage:
        S.fill_queue_messages(b["items"], request.agency, link_app=link_app)
    ctx = {"nav": "dash", "queue": shown, "queue_total": len(queue), "n": nums, "q": queue,
           "cap": AgencySettings.objects.get(agency=request.agency).daily_message_cap,
           "can_import": _can_import(request.roles, "backstage"), "is_manager": is_manager, "away": away, "coverage": coverage}
    if is_manager:
        ctx["urgent_count"] = sum(1 for i in queue if i.urgent)
        ctx["cover_name"] = absence.name_of(away.cover if away else absence.default_cover(request.agency, request.user))
    return render(request, "gestao/dashboard.html", ctx)


@require_POST
@staff_required(Role.GESTORA)
def absence_toggle(request):
    """ "Hoje não trabalho" e "Voltei": a gestora marca ou desfaz a própria ausência de hoje."""
    if request.POST.get("a") == "cancel":
        a = absence.active(request.user)
        if a:
            absence.cancel(a, by=request.user)
            messages.success(request, "Ausência desfeita. A fila de hoje voltou para você.")
    else:
        try:
            a = absence.start(request.agency, request.user, by=request.user)
        except absence.AbsenceError as e:
            messages.error(request, str(e))
        else:
            who = absence.name_of(a.cover) or "as sócias"
            messages.success(request, f"Combinado: hoje você não trabalha. Os itens passam para amanhã, na mesma ordem. "
                                      f"O que não pode esperar foi para {who}.")
    return redirect("g_dashboard")


@require_POST
@staff_required(Role.ADMIN, Role.GESTORA)
def dismiss(request, pk, code):
    """Adiar um item da fila, com motivo. Ele volta no dia escolhido (amanhã, se nada for informado)."""
    c = _creator(request, pk)
    _require_edit(request, c)
    reason = request.POST.get("reason", "").strip()[:240]
    if not reason:
        return HttpResponse("Escreva o motivo do adiamento.", status=400)
    days = _int(request.POST.get("days"), 1, 14) or 1
    until = (timezone.localtime() + dt.timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    C.AlertDismissal.objects.create(creator=c, code=code[:40], reason=reason, until=until, by=request.user)
    return HttpResponse("")


# ================================================================== creators
@staff_required()
def creators(request):
    qs = scoped_creators(request.user).select_related("partner_group")
    f = request.GET
    if f.get("q"):
        qs = qs.filter(Q(username__icontains=f["q"]) | Q(display_name__icontains=f["q"]) | Q(tiktok_id=f["q"]) | Q(usernames__username__icontains=f["q"])).distinct()
    if f.get("status"):
        qs = qs.filter(status=f["status"])
    else:
        qs = qs.exclude(status__in=[C.CreatorStatus.SAIU, C.CreatorStatus.ANONIMIZADO])
    if f.get("tag"):
        qs = qs.filter(tags__tag=f["tag"])
    if f.get("manager"):
        qs = qs.filter(assignments__manager_id=f["manager"], assignments__valid_to__isnull=True)
    if f.get("partner"):
        qs = qs.filter(partner_group_id=f["partner"])
    if f.get("sem_gestora"):
        qs = qs.exclude(assignments__valid_to__isnull=True, assignments__isnull=False)
    rows = []
    today = E.tiktok_today()
    pm = E.prev_month(today)
    lm = {m.creator_id: m for m in MonthlyResult.objects.filter(creator__in=qs, month=pm)}
    st = AgencySettings.objects.get(agency=request.agency)
    contacted = set(C.Contact.objects.filter(creator__in=qs).values_list("creator_id", flat=True))
    for c in qs.prefetch_related("snapshots", "tags", "group_history", "assignments__manager")[:500]:
        ph = phases.phase_for(c, list(c.snapshots.all()), st, today, has_contact=c.pk in contacted)
        if f.get("fase") and ph.code != f["fase"]:
            continue
        snaps = [s for s in c.snapshots.all() if E.month_start(s.period_start) == E.month_start(today)]
        snap = snaps[-1] if snaps else None
        g = next((h for h in c.group_history.all() if h.until is None), None)
        mgr = next((a.manager for a in c.assignments.all() if a.valid_to is None), None)
        tier = lm[c.pk].tier if c.pk in lm else 1
        if f.get("tier") and str(tier) != f["tier"]:
            continue
        if f.get("group") and (g.group_name if g else "") != f["group"]:
            continue
        rows.append({"c": c, "snap": snap, "tier": tier, "group": g.group_name if g else "—", "manager": mgr, "phase": ph,
                     "tags": [t.get_tag_display() for t in c.tags.all()]})
    if f.get("export") == "csv":
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="creators.csv"'
        w = csv.writer(resp)
        w.writerow(["ID TikTok", "@", "Status", "Fase", "Tier", "Grupo", "Gestora", "Diamantes mês", "Horas mês", "Dias válidos mês"])
        for r in rows:
            s = r["snap"]
            w.writerow([r["c"].tiktok_id, r["c"].username, r["c"].get_status_display(), r["phase"].label, r["tier"], r["group"],
                        r["manager"].email if r["manager"] else "", s.diamonds if s else 0, round(s.hours, 1) if s else 0, s.valid_days if s else 0])
        return resp
    managers = User.objects.filter(memberships__agency=request.agency, memberships__role=Role.GESTORA).distinct()
    return render(request, "gestao/creators.html", {
        "nav": "creators", "rows": rows, "f": f, "tags": C.TAG_CHOICES, "statuses": C.CreatorStatus.choices,
        "managers": managers, "partners": request.agency.partner_groups.all(), "groups": ["Primeiro Mês", "Bronze", "Prata", "Ouro", "Diamante"],
        "phases": phases.PHASES,
        "tiers": range(1, 11),
    })


@staff_required()
def creator_detail(request, pk):
    c = _creator(request, pk)
    tab = request.GET.get("tab", "visao")
    today = E.tiktok_today()
    snaps = list(c.snapshots.all())
    snap = E.latest_in_month(c, E.month_start(today))
    settings_ = AgencySettings.objects.get(agency=c.agency)
    ctx = {"nav": "creators", "c": c, "tab": tab, "snap": snap, "can_edit": can_edit_creator(request.user, c),
           "manager": c.current_manager(), "facts": creator_facts(c), "phone": _phone(c),
           "group_url": getattr(getattr(c, "private", None), "whatsapp_group_url", "")}
    # quem cobre a carteira hoje ("Hoje não trabalho") só registra o contato: Enviei, Respondeu e nota
    ctx["covering"] = not ctx["can_edit"] and covers_creator(request.user, c)
    ctx["can_contact"] = ctx["can_edit"] or ctx["covering"]
    ctx["tier"], _ = E.official_tier(c, today)
    ctx["phase"] = phases.phase_for(c, snaps, settings_, today)
    if tab == "visao":
        ctx["radar"] = phases.graduation_radar_row(c, snaps, settings_, today)
        ctx["week"] = states.week_state(c, snaps, today)
        ctx["paces"] = E.month_paces(c, snap) if snap else {}
        ctx["months"] = list(MonthlyResult.objects.filter(creator=c).order_by("-month")[:8])
        ctx["intervals"] = list(reversed(E.weekly_intervals(snaps)))[:8]
        ctx["tags"] = list(c.tags.all())
        ctx["all_tags"] = C.TAG_CHOICES
        ctx["notes"] = c.notes.select_related("author")[:20]
        ctx["usernames"] = c.usernames.order_by("-last_seen")
        if ctx["can_edit"]:
            ctx["access_code"] = first_access.active_code(c)
            invite = template_for(c.agency, "CONVITE-APP", c)
            ctx["invite_text"] = _msg(request, invite.body, c) if invite and ctx["access_code"] else ""
            ctx["code_days"] = settings_.access_code_days
            ctx["test_lock"] = settings_.app_test_only_testers and not c.app_tester  # passo 3.7
        ctx["assign_history"] = c.assignments.select_related("manager", "assigned_by").order_by("-valid_from")
        ctx["managers"] = _active_managers(c.agency)
        ctx["onboarding"] = E.onboarding_status(c, snaps, settings_)
        ctx["timeline"] = timeline(c)
        ctx["reminders"] = c.reminders.filter(done_at__isnull=True)
        ctx["last_stop"] = c.stop_reasons.first()
        ctx["open_case"] = c.account_cases.filter(resolved_at__isnull=True).first()
        ctx["case_kinds"], ctx["visit_scores"] = C.AccountCase.KINDS, C.Visit.SCORES
        ctx["visits"] = c.visits.select_related("author")[:5]
        ctx["escalate_days"] = settings_.restriction_escalate_days
        ctx["recruiters"] = User.objects.filter(memberships__agency=c.agency, memberships__role=Role.RECRUTADORA, memberships__active=True).distinct()
        ctx["tracks"], ctx["stop_reasons"], ctx["stop_details"] = C.TRACKS, C.STOP_REASONS, C.STOP_DETAILS
        ctx["niches"], ctx["battles_choices"] = C.NICHES, C.BATTLES
        ctx["private"] = getattr(c, "private", None)
        ctx["referred_by"] = referrals.handle_of(c.referred_by_id)
        ctx["referred"] = referrals.referred_handles(c)
        ctx["today"] = timezone.localdate()
        ctx["campaigns"] = M.CampaignStanding.objects.filter(creator_id_ref=c.pk).select_related("campaign")
        ctx["lessons_done"] = M.LessonProgress.objects.filter(creator=c).select_related("lesson")
        # Hera Academy: o que abriu para o criador, o que a gestão liberou e a aula que aparece no app
        mods = academy.modules(c, include_hidden=True)
        ctx["academy_mods"] = mods
        ctx["academy_open"] = [m for m in mods if m.open and m.lessons]
        ctx["academy_auto"] = academy.recommended(c, mods=mods, snap=snap, today=today, counting=ctx["phase"].base in ("chegada", "novato"), use_pick=False)
        ctx["lesson_pick"] = M.LessonPick.objects.filter(creator=c).select_related("lesson", "picked_by").first()
        ctx["lessons_done_ids"] = {p.lesson_id for p in ctx["lessons_done"]}
        # campanha do momento (passo 3.4): a escolha da gestão vence a sugestão pelo encaixe
        facts = creator_facts(c)
        ctx["campaign_pick"] = M.CampaignPick.objects.filter(creator=c).select_related("campaign", "picked_by").first()
        visible = campaign_rules.creator_campaigns(c, facts, today, pick=ctx["campaign_pick"] or False)
        ctx["campaign_auto"] = campaign_rules.suggest(visible, campaign_rules.profile(snaps))
        ctx["campaign_options"] = campaign_rules.creator_campaigns(c, facts, today, pick=False, include_unfocused=True)
        ctx["dias_sem_live"] = E.days_without_live(snaps)
        # Meu plano (passo 3.6): a gestão lê o que o criador escolheu, sem editar
        from engage import plan as plan_rules

        ctx["creator_plan"] = plan_rules.for_creator(c)
        # sinais de risco dos criadores Diamante (passo 4.3): números e conversa
        from crm.one_on_one import diamond_min_tier

        from . import month_items

        ctx["risk"] = month_items.risk_for(c, ctx["week"], ctx["tier"], diamond_min_tier(c.agency))
        ctx["risk_kinds"] = C.RiskSignal.KINDS
        # resumo do mês no app: o que o criador vê e a dica da Hera escrita pela gestora
        from . import month_summary

        ctx["summary_month"] = E.prev_month(today)
        ctx["month_summary"] = month_summary.for_month(c, ctx["summary_month"], month_summary.extra_for(c, today))
    elif tab == "1a1":
        from crm import one_on_one

        ctx["items"] = c.one_on_ones.prefetch_related("actions").select_related("conducted_by", "manager")[:20]
        prev = c.one_on_ones.first()
        ctx["prev_actions"] = prev.actions.all() if prev else []
        ctx["b1_default"] = one_on_one.performance_text(c, today)  # bloco 1 preenchido pelo sistema (passo 4.2)
        ctx["today"] = timezone.localdate()
        ctx["channels"] = C.OneOnOne.CHANNELS
        ctx["conductors"] = User.objects.filter(memberships__agency=c.agency, memberships__active=True,
                                                memberships__role__in=[Role.ADMIN, Role.GESTORA]).distinct().order_by("first_name", "email")
    elif tab == "onboarding":
        ctx["ob"] = E.onboarding_status(c, snaps, settings_)
        E.update_onboarding(c, snaps, settings_) if ctx["can_edit"] else None
        ctx["items"] = C.CreatorOnboarding.objects.filter(creator=c).select_related("item").order_by("item__order")
    elif tab == "mensagens":
        # um modelo por código: a variação que vale para a trilha e o "faz batalha" deste criador
        groups = {}
        for rows in templates_by_code(c.agency).values():
            t = pick_variant(rows, c)
            groups.setdefault(t.stage, []).append({"t": t, "text": _msg(request, t.body, c), "outside": outside_track(t, c),
                                                   "variants": len(rows)})
        ctx["groups"] = groups
        ctx["cadence"] = getattr(c, "cadence", None)
        ctx["niche_guide"] = next((n for n in playbook.NICHE_GUIDE if n["code"] == c.niche), None)
        ctx["track_label"] = dict(C.TRACKS)[creator_track(c)]
        ctx["track_defined"] = bool(c.track)
    elif tab == "batalhas":
        ctx["records"] = c.battle_records.select_related("author")[:50]
        ctx["requests"] = c.battle_requests.all()[:20]
        ctx["results"] = C.BattleRecord.RESULTS
        ctx["today"] = timezone.localdate()
        vistas = [r for r in ctx["records"] if r.result != "nao_aconteceu"]
        ctx["placar"] = {"total": len(vistas), "venceu": sum(1 for r in vistas if r.result == "venceu"),
                         "perdeu": sum(1 for r in vistas if r.result == "perdeu"), "empate": sum(1 for r in vistas if r.result == "empate")}
    elif tab == "saida":
        ctx["exits"] = c.exits.all()
        ctx["days_in"] = c.days_in_agency()
        ctx["settings"] = settings_
        ctx["stop_reasons"] = C.STOP_REASONS
    return render(request, "gestao/creator.html", ctx)


def _date(text):
    try:
        return dt.date.fromisoformat((text or "").strip())
    except ValueError:
        return None


def _int(text, lo=None, hi=None):
    try:
        n = int(text)
    except (TypeError, ValueError):
        return None
    return n if (lo is None or n >= lo) and (hi is None or n <= hi) else None


def _save_profile(request, c):
    """Cadastro da ficha: trilha, nicho, recrutadora, quem indicou e aniversário. Cada troca vira uma nota na linha do tempo."""
    P = request.POST
    changes = []
    track = P.get("track", "")
    if track in dict(C.TRACKS) or track == "":
        if track != c.track:
            changes.append(f"Trilha: {c.get_track_display() or 'sem trilha'} → {dict(C.TRACKS).get(track, 'sem trilha')}")
            c.track = track
    niche = P.get("niche", "")
    if (niche in dict(C.NICHES) or niche == "") and niche != c.niche:
        changes.append(f"Nicho: {c.get_niche_display() or '—'} → {dict(C.NICHES).get(niche, '—')}")
        c.niche = niche
    battles = P.get("does_battles", c.does_battles)
    if battles in dict(C.BATTLES) and battles != c.does_battles:
        changes.append(f"Faz batalha: {c.get_does_battles_display()} → {dict(C.BATTLES)[battles]}")
        c.does_battles = battles
    rec = None
    if P.get("recruited_by"):
        rec = User.objects.filter(pk=_int(P["recruited_by"]), memberships__agency=c.agency, memberships__role=Role.RECRUTADORA).first()
        if rec is None:
            messages.error(request, "Recrutadora não encontrada. Confira em Configurações → Papéis.")
            return
    if (rec.pk if rec else None) != c.recruited_by_id:
        old = c.recruited_by
        changes.append(f"Recrutadora: {(old.first_name or old.email) if old else '—'} → {(rec.first_name or rec.email) if rec else '—'}")
        c.recruited_by = rec
    ref = None
    handle = P.get("referred_by", "").strip().lstrip("@")
    if handle:
        ref = referrals.find_by_handle(c.agency, handle, exclude_pk=c.pk)  # pode ser de outra carteira
        if ref is None:
            messages.error(request, f"Não achei o criador @{handle} na agência. Confira o @ de quem indicou.")
            return
    if (ref["pk"] if ref else None) != c.referred_by_id:
        old = referrals.handle_of(c.referred_by_id)
        changes.append(f"Indicado por: {('@' + old) if old else '—'} → {('@' + ref['username']) if ref else '—'}")
        c.referred_by_id = ref["pk"] if ref else None
    if "first_live_planned" in P:
        planned = _date(P.get("first_live_planned"))
        if planned != c.first_live_planned:
            changes.append(f"1ª LIVE combinada para {planned:%d/%m}" if planned else "Data da 1ª LIVE retirada")
            c.first_live_planned = planned
    c.save(update_fields=["track", "niche", "does_battles", "recruited_by", "referred_by", "first_live_planned"])
    day, month = P.get("birth_day", ""), P.get("birth_month", "")
    if day or month:
        d, m = _int(day, 1, 31), _int(month, 1, 12)
        if d is None or m is None:
            messages.error(request, "Aniversário: informe o dia (1 a 31) e o mês (1 a 12).")
            return
    else:
        d = m = None
    priv, _ = C.CreatorPrivate.objects.get_or_create(creator=c)
    if (priv.birth_day, priv.birth_month) != (d, m):
        priv.birth_day, priv.birth_month = d, m
        priv.save(update_fields=["birth_day", "birth_month"])
        changes.append("Aniversário atualizado")
    if changes:
        C.Note.objects.create(creator=c, author=request.user, body="Cadastro alterado. " + "; ".join(changes) + ".")
        messages.success(request, "Cadastro salvo.")


def _campaign_pick(request, c):
    """Campanha do momento na ficha: uma das campanhas em que o criador participa, "nenhuma", ou a sugestão do app."""
    v = request.POST.get("campaign", "")
    if v == "":
        if M.CampaignPick.objects.filter(creator=c).delete()[0]:
            C.Note.objects.create(creator=c, author=request.user, body="Campanha do momento volta a ser a sugestão do app.")
            messages.success(request, "O app volta a sugerir a campanha do momento sozinho.")
        return
    if v == "nenhuma":
        M.CampaignPick.objects.update_or_create(creator=c, defaults={"campaign": None, "picked_by": request.user, "picked_at": timezone.now()})
        C.Note.objects.create(creator=c, author=request.user, body="Campanha do momento: nenhuma por enquanto.")
        messages.success(request, "Sem campanha do momento para este criador.")
        return
    options = campaign_rules.creator_campaigns(c, creator_facts(c), E.tiktok_today(), pick=False, include_unfocused=True)
    camp = next((x["c"] for x in options if x["c"].pk == _int(v)), None)
    if camp is None:
        messages.error(request, "Essa campanha não vale para este criador agora (ele não se qualifica, já encerrou ou está como “não oferecer”).")
        return
    M.CampaignPick.objects.update_or_create(creator=c, defaults={"campaign": camp, "picked_by": request.user, "picked_at": timezone.now()})
    C.Note.objects.create(creator=c, author=request.user, body=f"Campanha do momento escolhida: “{camp.name}”.")
    if c.user_id:
        notify(user_id=c.user_id, kind="campanha", title="A Hera escolheu uma campanha para você", body=camp.name, url=reverse("campaigns"))
    messages.success(request, f"“{camp.name}” é a campanha do momento deste criador. Ela aparece no app no lugar da sugestão.")


def _academy_action(request, c, a):
    """Hera Academy na ficha: liberar um módulo antes da hora (ou desfazer) e escolher a aula que aparece no app.
    Cada mudança vira uma nota na linha do tempo; o criador recebe um aviso no app."""
    if a in ("module_release", "module_unrelease"):
        course = get_object_or_404(M.Course, pk=_int(request.POST.get("course")), agency=c.agency)
        if a == "module_release":
            _, created = M.ModuleRelease.objects.get_or_create(creator=c, course=course, defaults={"released_by": request.user})
            if created:
                C.Note.objects.create(creator=c, author=request.user, body=f"Hera Academy: módulo “{course.title}” liberado antes da hora.")
                if c.user_id:
                    notify(user_id=c.user_id, kind="academy", title="Um módulo novo abriu para você na Hera Academy",
                           body=course.title, url=reverse("academy"))
                messages.success(request, f"Módulo “{course.title}” liberado.")
        else:
            if M.ModuleRelease.objects.filter(creator=c, course=course).delete()[0]:
                C.Note.objects.create(creator=c, author=request.user, body=f"Hera Academy: liberação do módulo “{course.title}” desfeita.")
                messages.success(request, "Liberação desfeita. O módulo volta a abrir pela regra.")
        return
    # aula que aparece no app: só aulas que já abriram para este criador (vazio = sugestão automática)
    pk = _int(request.POST.get("lesson"))
    if pk is None:
        if M.LessonPick.objects.filter(creator=c).delete()[0]:
            C.Note.objects.create(creator=c, author=request.user, body="Hera Academy: aula recomendada volta a ser a sugestão automática.")
            messages.success(request, "O app volta a sugerir a aula sozinho.")
        return
    lesson = next((l for l in academy.open_lessons(academy.modules(c)) if l.pk == pk), None)
    if lesson is None:
        messages.error(request, "Essa aula ainda não abriu para este criador. Libere o módulo antes.")
        return
    pick = M.LessonPick.objects.filter(creator=c).first()
    if pick and pick.lesson_id == lesson.pk:
        return
    M.LessonPick.objects.update_or_create(creator=c, defaults={"lesson": lesson, "picked_by": request.user, "picked_at": timezone.now()})
    C.Note.objects.create(creator=c, author=request.user, body=f"Hera Academy: aula indicada no app: “{lesson.title}”.")
    if c.user_id:
        notify(user_id=c.user_id, kind="academy", title="A Hera escolheu uma aula para você", body=lesson.title,
               url=reverse("lesson", args=[lesson.pk]))
    messages.success(request, f"Aula “{lesson.title}” indicada. Ela aparece no app no lugar da sugestão automática.")


@require_POST
@staff_required()
def creator_action(request, pk):
    c = _creator(request, pk)
    a = request.POST.get("a")
    if a in COVER_ACTIONS:
        _require_contact(request, c)  # quem edita, ou quem cobre a carteira hoje
    else:
        _require_edit(request, c)
    back = request.POST.get("next") or reverse("g_creator", args=[c.pk])
    if back.startswith("?"):  # "?tab=..." volta para a aba da ficha (e não para o endereço da ação)
        back = reverse("g_creator", args=[c.pk]) + back
    if a == "note" and request.POST.get("body"):
        C.Note.objects.create(creator=c, author=request.user, body=request.POST["body"][:4000])
    elif a == "tag":
        tag = request.POST.get("tag")
        obj = C.CreatorTag.objects.filter(creator=c, tag=tag).first()
        if obj:
            obj.delete()
        elif tag in dict(C.TAG_CHOICES):
            C.CreatorTag.objects.create(creator=c, tag=tag, set_by=request.user)
    elif a == "assign":
        if Role.ADMIN not in request.roles:
            raise PermissionDenied
        mgr = get_object_or_404(User, pk=request.POST.get("manager"), memberships__agency=c.agency, memberships__role=Role.GESTORA,
                                memberships__active=True)
        assign_manager(c, mgr, by=request.user)
        messages.success(request, f"Carteira atualizada: {mgr.get_full_name() or mgr.email}. O histórico do criador foi junto.")
    elif a == "onboarding":
        co = get_object_or_404(C.CreatorOnboarding, pk=request.POST.get("item"), creator=c)
        co.done = not co.done
        co.auto = False
        co.done_at = timezone.now() if co.done else None
        co.done_by = request.user if co.done else None
        co.save()
        if request.headers.get("HX-Request"):
            return HttpResponse("✅" if co.done else "—")
    elif a == "cadence_start":
        C.CadenceState.objects.update_or_create(creator=c, defaults={"started_at": timezone.now(), "step": 1, "resolved_at": None})
        messages.success(request, "Cadência de não-resposta iniciada. O próximo passo aparece na fila em 24h.")
    elif a == "cadence_next":
        cs = get_object_or_404(C.CadenceState, creator=c)
        if cs.step < 4:
            cs.step += 1
            cs.save()
        else:
            cs.resolved_at = timezone.now()
            cs.save()
    elif a in ("responded", "wrote"):
        # "Respondeu" e "O criador me escreveu": sempre uma linha nova, nunca por cima do contato
        now = timezone.now()
        last = c.contacts.first() if a == "responded" else None
        C.Reply.objects.create(creator=c, kind="respondeu" if a == "responded" else "escreveu", contact=last,
                               note=request.POST.get("note", "")[:2000], author=request.user, created_at=now)
        C.CadenceState.objects.filter(creator=c, resolved_at__isnull=True).update(resolved_at=now)
        if last and last.responded_at is None:
            last.responded_at = now  # só a primeira resposta marca o contato; as seguintes ficam na linha do tempo
            last.save(update_fields=["responded_at"])
        messages.success(request, "Resposta registrada." if a == "responded" else "Registrado: o criador escreveu.")
    elif a == "profile":
        _save_profile(request, c)
    elif a in ("module_release", "module_unrelease", "lesson_pick"):
        _academy_action(request, c, a)
    elif a == "campaign_pick":
        _campaign_pick(request, c)
    elif a == "month_tip":  # dica da Hera no resumo do mês do app (vence a primeira dica automática)
        from engage.tom import verificar_tom

        month = E.prev_month(E.tiktok_today())
        text = request.POST.get("text", "").strip()[:240]
        problems = verificar_tom(text)
        if not text:
            M.MonthTip.objects.filter(creator=c, month=month).delete()
            messages.success(request, "Dica apagada. O resumo volta a mostrar só as dicas automáticas.")
        elif problems:
            messages.error(request, f"A dica não foi salva: o app do criador não usa {', '.join(problems)}.")
        else:
            M.MonthTip.objects.update_or_create(creator=c, month=month, defaults={"text": text, "author": request.user})
            messages.success(request, "Dica salva. Ela aparece no resumo do mês do criador, no app.")
    elif a == "risk_signal":  # sinal de risco pela conversa (Diamante, passo 4.3); vale 30 dias
        kind = request.POST.get("kind", "")
        if kind in dict(C.RiskSignal.KINDS):
            C.RiskSignal.objects.create(creator=c, kind=kind, note=request.POST.get("note", "").strip()[:240], author=request.user)
            messages.success(request, f"Sinal registrado: {dict(C.RiskSignal.KINDS)[kind].lower()}. Ele vale por {C.RiskSignal.VALID_DAYS} dias.")
        else:
            messages.error(request, "Escolha o sinal na lista.")
    elif a == "reminder_add":
        due, text = _date(request.POST.get("due_date")), request.POST.get("text", "").strip()[:240]
        if due and text:
            C.Reminder.objects.create(creator=c, text=text, due_date=due, author=request.user)
            messages.success(request, f"Lembrete criado para {due:%d/%m}. Ele entra na fila nesse dia.")
        else:
            messages.error(request, "Lembrete: escreva o texto e escolha a data.")
    elif a == "reminder_done":
        C.Reminder.objects.filter(creator=c, pk=_int(request.POST.get("reminder")), done_at__isnull=True).update(
            done_at=timezone.now(), done_by=request.user)
    elif a == "stop_reason":
        reason = request.POST.get("reason", "")
        detail = request.POST.get("detail", "") if reason == "desmotivou" else ""
        if reason not in dict(C.STOP_REASONS) or (detail and detail not in dict(C.STOP_DETAILS)):
            messages.error(request, "Escolha o motivo na lista.")
        else:
            C.StopReason.objects.create(creator=c, reason=reason, detail=detail, return_date=_date(request.POST.get("return_date")),
                                        note=request.POST.get("note", "")[:2000], author=request.user)
            messages.success(request, "Motivo registrado.")
    elif a == "visit":
        score, date = _int(request.POST.get("score"), 1, 3), _date(request.POST.get("date")) or timezone.localdate()
        if score is None:
            messages.error(request, "Visita: escolha a nota de 1 a 3.")
        else:
            C.Visit.objects.create(creator=c, date=date, score=score, note=request.POST.get("note", "")[:2000], author=request.user)
            messages.success(request, "Visita registrada. Mande o retorno no grupo individual.")
    elif a == "case_open":
        kind = request.POST.get("kind", "restricao")
        if kind in dict(C.AccountCase.KINDS) and not c.account_cases.filter(resolved_at__isnull=True).exists():
            C.AccountCase.objects.create(creator=c, kind=kind, opened_on=_date(request.POST.get("opened_on")) or timezone.localdate(),
                                         note=request.POST.get("note", "")[:2000], author=request.user)
            messages.success(request, "Caso aberto. Ele fica no topo da fila todo dia até ser resolvido.")
    elif a == "case_resolve":
        if C.AccountCase.objects.filter(creator=c, pk=_int(request.POST.get("case")), resolved_at__isnull=True).update(
                resolved_at=timezone.now(), resolved_by=request.user, resolution=request.POST.get("resolution", "")[:240]):
            # o aviso que o criador mandou pela Ajuda também fecha
            M.SupportTicket.objects.filter(creator=c, kind="restricao", status="aberto").update(status="respondido", answered_at=timezone.now())
        messages.success(request, "Caso encerrado.")
    elif a == "battle_record":
        P = request.POST
        date, result = _date(P.get("date")), P.get("result", "")
        if date is None or result not in dict(C.BattleRecord.RESULTS):
            messages.error(request, "Batalha: informe a data e o resultado.")
        else:
            req = c.battle_requests.filter(pk=_int(P.get("request"))).first() if P.get("request") else None
            C.BattleRecord.objects.create(
                creator=c, request=req, date=date, opponent=P.get("opponent", "").strip()[:120], rounds=_int(P.get("rounds"), 1, 9) or 1,
                result=result, diamonds=_int(P.get("diamonds"), 0), opponent_diamonds=_int(P.get("opponent_diamonds"), 0),
                note=P.get("note", "")[:2000], author=request.user)
            if req and result != "nao_aconteceu" and req.status != "realizada":
                req.status = "realizada"
                req.save(update_fields=["status"])
            messages.success(request, "Batalha registrada.")
    elif a == "exit":
        st = AgencySettings.objects.get(agency=c.agency)
        code = request.POST.get("reason_code", "")
        if code not in dict(C.STOP_REASONS):
            messages.error(request, "Saída não registrada: escolha o motivo na lista. O motivo de saída é obrigatório.")
            return redirect(reverse("g_creator", args=[c.pk]) + "?tab=saida")
        days = c.days_in_agency() or 0
        within = days <= st.free_exit_days
        req = _date(request.POST.get("requested_at")) or timezone.localdate()
        C.ExitRecord.objects.create(
            creator=c, requested_at=req, within_free_period=within, reason_code=code, reason=request.POST.get("reason", "")[:2000],
            action="excluida" if within else "aviso_previo", notice_ends_at=None if within else req + dt.timedelta(days=30),
            return_eligible_at=req if within else req + dt.timedelta(days=30 + st.return_wait_days),
            anonymize_at=req + dt.timedelta(days=st.anonymize_after_days), reviewed=True)
        c.status = C.CreatorStatus.SAIU if within else C.CreatorStatus.EM_SAIDA
        c.save(update_fields=["status"])
        messages.success(request, "Saída registrada. Campanhas e premiações do mês deixam de valer.")
    elif a == "group_link":
        url = request.POST.get("url", "").strip()
        if url and not url.startswith("https://"):
            messages.error(request, "Cole o link completo do grupo (começa com https://chat.whatsapp.com/).")
        else:
            priv, _ = C.CreatorPrivate.objects.get_or_create(creator=c)
            priv.whatsapp_group_url = url
            priv.save(update_fields=["whatsapp_group_url"])
            messages.success(request, "Link do grupo individual salvo. O streamer vê o botão \"Falar com a Hera\".")
    elif a == "ticket_done":
        M.SupportTicket.objects.filter(creator=c, pk=request.POST.get("ticket")).update(status="respondido", answered_at=timezone.now())
    return redirect(back)


def _group_url(c):
    return getattr(getattr(c, "private", None), "whatsapp_group_url", "")


@staff_required()
def open_chat(request, pk, code):
    """Abre o grupo individual do criador (link guardado na ficha). Sem link, abre o WhatsApp com o texto preenchido.

    Não registra contato: abrir não quer dizer que a mensagem saiu. O registro é feito só pelo "Enviei" (mark_sent)."""
    c = _creator(request, pk)
    _require_contact(request, c)
    t = template_for(c.agency, code, c)
    if t is None:
        raise Http404
    group = _group_url(c)
    if group:
        return redirect(group)  # link de grupo não leva texto: a gestora copia antes ("Copiar mensagem")
    body = t.body
    if code == "BAT-CONF" and request.GET.get("batalha", "").isdigit():  # confirmação já preenchida com a batalha
        b = get_object_or_404(M.BattleRequest, pk=int(request.GET["batalha"]), creator=c)
        body = battle_rules.fill_confirmation(body, b)
    return redirect(whatsapp_link(_phone(c), _msg(request, body, c)))


@require_POST
@staff_required()
def mark_sent(request, pk, code):
    """A gestora (ou quem cobre a carteira hoje) marca "Enviei": vira uma linha nova no histórico de contatos e avança
    a cadência de não-resposta."""
    c = _creator(request, pk)
    _require_contact(request, c)
    t = template_for(c.agency, code, c)
    if t is None:
        raise Http404
    text = request.POST.get("text") or _msg(request, t.body, c)
    C.Contact.objects.create(creator=c, user=request.user, template_code=code, body=text[:4000])
    if code.startswith("NR-") and code != "NR-5D":
        cs = getattr(c, "cadence", None)
        if cs and cs.resolved_at is None:
            step = {"NR-24H": 1, "NR-2D": 2, "NR-3D": 3}[code.removesuffix("-CASA")]  # a versão "da casa" é a mesma etapa
            if cs.step == step:
                cs.step = step + 1
                cs.save()
    if request.headers.get("HX-Request"):
        return HttpResponse('<span class="pill cyan">Enviei ✓ registrado</span>')
    messages.success(request, "Envio registrado.")
    return redirect(request.POST.get("next") or reverse("g_creator", args=[c.pk]) + "?tab=mensagens")


@staff_required()
def one_on_ones(request):
    """Agenda de 1:1 (passo 4.2): quem precisa de 1:1 todo mês, os marcados e os atrasados, na carteira de quem vê."""
    from crm import one_on_one

    qs = scoped_creators(request.user).exclude(status__in=[C.CreatorStatus.SAIU, C.CreatorStatus.ANONIMIZADO])
    ctx = one_on_one.agenda(qs, request.agency)
    ctx["nav"] = "1a1"
    return render(request, "gestao/one_on_ones.html", ctx)


@require_POST
@staff_required(Role.ADMIN, Role.GESTORA)
def one_on_one_new(request, pk):
    c = _creator(request, pk)
    _require_edit(request, c)
    P = request.POST
    conductor = User.objects.filter(pk=_int(P.get("conducted_by")) or 0, memberships__agency=c.agency, memberships__active=True,
                                    memberships__role__in=[Role.ADMIN, Role.GESTORA]).first() or request.user
    with transaction.atomic():
        o = C.OneOnOne.objects.create(
            creator=c, manager=request.user, conducted_by=conductor, date=_date(P.get("date")) or timezone.localdate(),
            tier_at=E.official_tier(c)[0], channel=P.get("channel") if P.get("channel") in dict(C.OneOnOne.CHANNELS) else "",
            print_saved=bool(P.get("print_saved")), notes=P.get("notes", "")[:5000],
            b1_performance=P.get("b1", ""), b2_constancia=P.get("b2", ""), b3_qualidade=P.get("b3", ""),
            b4_monetizacao=P.get("b4", ""), b5_dificuldades=P.get("b5", ""), b7_next_date=_date(P.get("b7")),
            reviewed_previous_plan=bool(P.get("reviewed")))
        for i in range(1, 4):
            if P.get(f"action{i}"):
                C.ActionItem.objects.create(one_on_one=o, creator=c, action=P[f"action{i}"][:240], owner=P.get(f"owner{i}", "")[:80] or "streamer",
                                            due_date=P.get(f"due{i}") or (timezone.localdate() + dt.timedelta(days=7)))
        for aid in P.getlist("prev_done"):
            C.ActionItem.objects.filter(pk=aid, creator=c).update(done=True)
    missing = o.missing
    messages.success(request, "1:1 registrado." + (f" Atenção: registro incompleto, falta {', '.join(missing)}. Sem registro completo, o 1:1 não conta."
                                                   if missing else ""))
    return redirect(reverse("g_creator", args=[c.pk]) + "?tab=1a1")


@require_POST
@staff_required(Role.ADMIN, Role.GESTORA)
def access_code_new(request, pk):
    """Gera o código de acesso ao app (primeiro acesso ou senha nova). A gestora envia no grupo individual."""
    c = _creator(request, pk)
    _require_edit(request, c)
    try:
        ac = first_access.new_code(c, by=request.user)
    except first_access.AccessError as e:
        messages.error(request, str(e))
    else:
        messages.success(request, f"Código de acesso gerado: {ac.display}. A mensagem pronta está no quadro “Acesso ao app”.")
    return redirect("g_creator", c.pk)


# ================================================================== onboarding
@staff_required()
def onboarding(request):
    today = E.tiktok_today()
    st = AgencySettings.objects.get(agency=request.agency)
    since = timezone.now() - dt.timedelta(days=st.first_month_days + 1)
    qs = scoped_creators(request.user).filter(joined_at__gte=since).exclude(status__in=[C.CreatorStatus.SAIU]).prefetch_related("snapshots")
    items = list(C.OnboardingItem.objects.filter(agency=request.agency))
    # próximo passo de cada um, pelo roteiro da fila (relógio de quem não abriu LIVE, conferências, cadência)
    nxt = {}
    for it in S.action_queue(scoped_creators(request.user).filter(joined_at__gte=since), request.agency, raw=True):
        if S.item_kind(it.code) in ("onboarding", "onboarding_risco", "cadencia"):
            nxt.setdefault(it.creator.pk, it)
    rows = []
    for c in qs:
        snaps = list(c.snapshots.all())
        if can_edit_creator(request.user, c):
            E.update_onboarding(c, snaps, st)
        done = {co.item_id: co for co in C.CreatorOnboarding.objects.filter(creator=c)}
        n_done = sum(1 for co in done.values() if co.done)
        rows.append({"c": c, "ob": E.onboarding_status(c, snaps, st), "done": done, "pct": n_done / len(items) if items else 0, "next": nxt.get(c.pk),
                     "cells": [done.get(it.pk) for it in items], "can_edit": can_edit_creator(request.user, c)})
    rows.sort(key=lambda r: (not (r["ob"] and r["ob"]["at_risk"]), r["c"].joined_at))
    return render(request, "gestao/onboarding.html", {"nav": "onb", "rows": rows, "items": items})


# ================================================================== carteiras
def _active_managers(agency):
    return (User.objects.filter(memberships__agency=agency, memberships__role=Role.GESTORA, memberships__active=True)
            .distinct().order_by("first_name", "email"))


def _move_creators(request, managers):
    """Passa os criadores marcados para outra carteira (ou deixa sem gestora). O histórico de cada um vai junto."""
    ag, target = request.agency, request.POST.get("target", "")
    mgr = None
    if target != "none":
        mgr = next((m for m in managers if str(m.pk) == target), None)
        if mgr is None:
            messages.error(request, "Escolha para qual carteira os criadores vão.")
            return
    ids = [n for n in (_int(x) for x in request.POST.getlist("creator")) if n]
    chosen = (C.Creator.objects.filter(agency=ag, pk__in=ids).exclude(status__in=[C.CreatorStatus.SAIU, C.CreatorStatus.ANONIMIZADO])
              .prefetch_related("assignments__manager"))
    moved, left = [], {}  # criadores que mudaram; de quem saíram (gestora anterior → quantos)
    with transaction.atomic():
        for c in chosen:
            prev = next((a.manager for a in c.assignments.all() if a.valid_to is None), None)
            if (prev.pk if prev else None) == (mgr.pk if mgr else None):
                continue
            if mgr is None:
                unassign_manager(c)
            else:
                assign_manager(c, mgr, by=request.user)
            moved.append(c)
            left.setdefault(prev, 0)
            left[prev] += 1
        if moved:
            dest = absence.name_of(mgr) or "sem gestora"
            AuditLog.objects.create(
                agency=ag, actor=request.user, action="carteira_troca", target=f"{len(moved)} criador(es) → {dest}"[:200],
                detail={"para": dest, "de": {absence.name_of(p) or "sem gestora": n for p, n in left.items()},
                        "criadores": [c.username for c in moved][:200]})
    if not moved:
        messages.error(request, "Nenhum criador mudou de carteira. Marque os criadores na lista e escolha o destino.")
        return
    n = len(moved)
    plural = "es" if n > 1 else ""
    if mgr is not None:
        notify(user=mgr, kind="carteira", url=reverse("g_creators"), title=f"{n} criador{plural} entr{'aram' if n > 1 else 'ou'} na sua carteira",
               body="O histórico de cada um (mensagens, respostas, notas e 1:1) veio junto.")
    for prev, k in left.items():
        if prev is not None:
            notify(user=prev, kind="carteira", url=reverse("g_creators"), title=f"{k} criador{'es' if k > 1 else ''} sa{'íram' if k > 1 else 'iu'} da sua carteira",
                   body=f"Agora {'estão' if k > 1 else 'está'} com {absence.name_of(mgr)}." if mgr else "Por enquanto, sem gestora (com as sócias).")
    messages.success(request, f"{n} criador{plural} {'passaram' if n > 1 else 'passou'} para "
                              f"{('a carteira de ' + absence.name_of(mgr)) if mgr else 'a lista “sem gestora”'}. O histórico foi junto.")


@staff_required(Role.ADMIN)
def partners_panel(request):
    """Painel das sócias (passo 4.1): os números da conta, a execução da gestão, as aprovações e o sorteio semanal."""
    from . import panel

    ag = request.agency
    if request.method == "POST":
        a = request.POST.get("a")
        try:
            if a == "decide":
                ap = get_object_or_404(C.ApprovalRequest, pk=_int(request.POST.get("approval")) or 0, agency=ag)
                panel.decide(ap, request.user, request.POST.get("decision", ""), request.POST.get("note", "").strip())
                messages.success(request, f"Decisão registrada: {ap.decision_label}. A gestora foi avisada e a decisão está na ficha.")
            elif a == "check":
                sc = get_object_or_404(C.SentCheck, pk=_int(request.POST.get("check")) or 0, agency=ag)
                panel.check_sent(sc, request.user, request.POST.get("result", ""), request.POST.get("note", "").strip())
                messages.success(request, "Conferência registrada.")
        except panel.PanelError as e:
            messages.error(request, str(e))
        anchor = {"decide": "#aprovacoes", "check": "#sorteio"}.get(a, "")
        return redirect(reverse("g_panel") + anchor)
    ctx = panel.overview(ag)
    ctx.update({"nav": "panel", "decisions": dict(C.ApprovalRequest.DECISIONS), "results_choices": C.SentCheck.RESULTS[1:]})
    return render(request, "gestao/panel.html", ctx)


@require_POST
@staff_required(Role.ADMIN, Role.GESTORA)
def approval_request(request, pk, code):
    """Na fila: "Pedir decisão às sócias" (manter ou encerrar). Quem pede é quem edita o criador."""
    from . import panel

    c = _creator(request, pk)
    _require_edit(request, c)
    ap, created = panel.request_decision(c, request.user, code, request.POST.get("reason", ""), request.POST.get("note", "").strip())
    when = timezone.localtime(ap.requested_at)
    msg = "Pedido enviado às sócias." if created else f"Já existe um pedido de {when:%d/%m} esperando as sócias."
    if request.headers.get("HX-Request"):
        return HttpResponse(f'<span class="pill gold">🗳️ {msg}</span>')
    messages.success(request, msg)
    return redirect("g_creator", c.pk)


@staff_required(Role.ADMIN)
def app_test_view(request):
    """Teste do app (só as sócias, passo 3.7): quem participa, as datas, a trava do código e o uso de cada um."""
    from . import app_test

    ag = request.agency
    st = AgencySettings.objects.get(agency=ag)
    if request.method == "POST":
        a = request.POST.get("a")
        if a == "dates":
            start, end = _date(request.POST.get("start")), _date(request.POST.get("end"))
            if start and end and end < start:
                messages.error(request, "O fim do teste precisa ser depois do início.")
            else:
                st.app_test_start, st.app_test_end = start, end
                st.app_test_only_testers = bool(request.POST.get("only_testers"))
                st.save(update_fields=["app_test_start", "app_test_end", "app_test_only_testers"])
                AuditLog.objects.create(agency=ag, actor=request.user, action="teste_app_datas",
                                        target=f"{start or '-'} a {end or '-'} · trava {'ligada' if st.app_test_only_testers else 'desligada'}")
                messages.success(request, "Teste do app salvo.")
        elif a == "add":
            handle = request.POST.get("handle", "").strip().lstrip("@")
            c = C.Creator.objects.filter(agency=ag, username__iexact=handle).exclude(
                status__in=[C.CreatorStatus.SAIU, C.CreatorStatus.ANONIMIZADO]).first() if handle else None
            if c is None:
                messages.error(request, f"Não achei um criador ativo com o @{handle}." if handle else "Informe o @ do criador.")
            else:
                c.app_tester = True
                c.save(update_fields=["app_tester"])
                AuditLog.objects.create(agency=ag, actor=request.user, action="teste_app_entra", target=f"@{c.username}")
                messages.success(request, f"@{c.username} entrou no teste do app.")
        elif a == "remove":
            c = C.Creator.objects.filter(agency=ag, pk=_int(request.POST.get("creator")), app_tester=True).first()
            if c:
                c.app_tester = False
                c.save(update_fields=["app_tester"])
                AuditLog.objects.create(agency=ag, actor=request.user, action="teste_app_sai", target=f"@{c.username}")
                messages.success(request, f"@{c.username} saiu do teste do app.")
        elif a == "survey":
            sv, created = app_test.create_survey(ag, st)
            messages.success(request, "Pesquisa do fim do teste criada." if created else "A pesquisa do teste já existe.")
        return redirect("g_app_test")
    rows = app_test.tester_rows(ag)
    survey = M.Survey.objects.filter(agency=ag, only_app_testers=True).order_by("-opens_at").first()
    return render(request, "gestao/app_test.html", {
        "nav": "teste", "st": st, "rows": rows, "sum": app_test.summary(rows), "status": app_test.status(st),
        "survey": survey, "areas": app_test.AREA_ORDER, "monday": app_test.week_start(timezone.localdate())})


@staff_required(Role.ADMIN)
def portfolios(request):
    """Carteiras (só as sócias): divisão dos criadores entre as gestoras, quem cobre cada uma e os dias sem trabalhar.

    A troca de carteira leva o histórico junto: ele pertence ao criador, e a nova gestora passa a ver tudo."""
    ag = request.agency
    managers = list(_active_managers(ag))
    if request.method == "POST":
        a = request.POST.get("a")
        mgr = next((m for m in managers if str(m.pk) == request.POST.get("manager", "")), None)
        try:
            if a == "move":
                _move_creators(request, managers)
            elif a == "cover" and mgr:
                cover = None
                if request.POST.get("cover"):
                    cover = absence.cover_candidates(ag).filter(pk=_int(request.POST.get("cover"))).first()
                    if cover is None:
                        raise absence.AbsenceError("Quem cobre precisa ser uma sócia ou uma recrutadora ativa.")
                absence.set_default_cover(ag, mgr, cover)
                messages.success(request, f"Quem cobre {absence.name_of(mgr)}: {absence.name_of(cover) or 'as sócias'}.")
            elif a == "absence_start" and mgr:
                day = _date(request.POST.get("day")) or absence.today()
                ab = absence.start(ag, mgr, by=request.user, day=day)
                messages.success(request, f"{absence.name_of(mgr)} não trabalha em {ab.day:%d/%m}. Cobre: {absence.name_of(ab.cover) or 'as sócias'}.")
            elif a == "absence_cancel":
                ab = C.Absence.objects.filter(agency=ag, pk=_int(request.POST.get("absence")), cancelled_at__isnull=True).first()
                if ab:
                    absence.cancel(ab, by=request.user)
                    messages.success(request, "Ausência desfeita.")
        except absence.AbsenceError as e:
            messages.error(request, str(e))
        back = request.POST.get("next", "")
        return redirect(reverse("g_portfolios") + (back if back.startswith("?") else ""))
    rows, unassigned = S.portfolio_overview(ag)
    f = request.GET
    today = E.tiktok_today()
    st = AgencySettings.objects.get(agency=ag)
    qs = C.Creator.objects.filter(agency=ag).exclude(status__in=[C.CreatorStatus.SAIU, C.CreatorStatus.ANONIMIZADO])
    which = f.get("gestora", "")
    if which == "sem":
        qs = qs.exclude(pk__in=C.PortfolioAssignment.objects.filter(valid_to__isnull=True).values("creator_id"))
    elif _int(which):
        qs = qs.filter(assignments__manager_id=_int(which), assignments__valid_to__isnull=True)
    if f.get("q"):
        qs = qs.filter(Q(username__icontains=f["q"]) | Q(display_name__icontains=f["q"]))
    contacted = set(C.Contact.objects.filter(creator__in=qs).values_list("creator_id", flat=True))
    people = []
    for c in qs.distinct().prefetch_related("snapshots", "group_history", "assignments__manager").order_by("username")[:500]:
        cur = next((x for x in c.assignments.all() if x.valid_to is None), None)
        g = next((h for h in c.group_history.all() if h.until is None), None)
        people.append({"c": c, "manager": cur.manager if cur else None, "since": cur.valid_from if cur else None,
                       "phase": phases.phase_for(c, list(c.snapshots.all()), st, today, has_contact=c.pk in contacted),
                       "group": g.group_name if g else "—", "day": c.days_in_agency(today)})
    return render(request, "gestao/portfolios.html", {
        "nav": "port", "rows": rows, "unassigned": unassigned, "managers": managers, "people": people, "f": f, "which": which,
        "covers": list(absence.cover_candidates(ag)), "cap": st.daily_message_cap, "today": absence.today(),
        "history": AuditLog.objects.filter(agency=ag, action="carteira_troca").select_related("actor")[:15]})


# ================================================================== biblioteca de mensagens
LIBRARY_EDITORS = {Role.ADMIN, Role.CONTEUDO}  # sócias e quem tem o papel Conteúdo


def _template_row(t):
    return {"t": t, "problems": t.tone_problems, "tracks": [dict(C.TRACKS)[k] for k in t.tracks if k in dict(C.TRACKS)]}


@staff_required()
def message_library(request):
    """Todos os scripts do Playbook, por etapa, com as variações por trilha e por "faz batalha"."""
    f = request.GET
    rows = [_template_row(t) for t in M.MessageTemplate.objects.filter(agency=request.agency)]
    total = len(rows)
    counts = {"provisional": sum(1 for r in rows if r["t"].provisional), "tone": sum(1 for r in rows if r["problems"])}
    if f.get("q"):
        q = f["q"].lower()
        rows = [r for r in rows if q in r["t"].title.lower() or q in r["t"].body.lower() or q in r["t"].code.lower()]
    if f.get("trilha"):
        rows = [r for r in rows if not r["t"].tracks or f["trilha"] in r["t"].tracks]
    if f.get("ver") == "provisorias":
        rows = [r for r in rows if r["t"].provisional]
    elif f.get("ver") == "tom":
        rows = [r for r in rows if r["problems"]]
    groups = {}
    for r in rows:
        groups.setdefault(r["t"].stage, []).append(r)
    return render(request, "gestao/messages.html", {
        "nav": "msgs", "groups": groups, "f": f, "total": total, "shown": len(rows), "counts": counts, "tracks": C.TRACKS,
        "niche_guide": playbook.NICHE_GUIDE, "can_edit": bool(request.roles & LIBRARY_EDITORS)})


@staff_required()
def message_detail(request, pk):
    """Uma mensagem: texto, variáveis, variações, edição (com verificador de tom) e histórico de versões."""
    from django.core.exceptions import ValidationError

    t = get_object_or_404(M.MessageTemplate, pk=pk, agency=request.agency)
    can_edit = bool(request.roles & LIBRARY_EDITORS)
    errors = []
    draft = {"title": t.title, "body": t.body}
    if request.method == "POST":
        if not can_edit:
            raise PermissionDenied
        if request.POST.get("a") == "restore":
            v = get_object_or_404(M.MessageVersion, pk=request.POST.get("version"), template=t)
            draft = {"title": v.title, "body": v.body}
        else:
            draft = {"title": request.POST.get("title", "").strip()[:140], "body": request.POST.get("body", "").replace("\r\n", "\n").strip()}
        if not draft["title"] or not draft["body"]:
            errors.append("Escreva o título e a mensagem.")
        elif draft == {"title": t.title, "body": t.body}:
            messages.success(request, "Nada mudou.")
            return redirect("g_message", t.pk)
        else:
            t.title, t.body = draft["title"], draft["body"]
            t._editor = request.user  # quem aposentou a versão anterior (o sinal em engage/apps.py guarda a versão)
            try:
                t.full_clean()
            except ValidationError as e:
                errors.extend(m for msgs in e.message_dict.values() for m in msgs)
                t.refresh_from_db()
            else:
                t.save()
                messages.success(request, "Mensagem salva. A versão anterior ficou no histórico.")
                return redirect("g_message", t.pk)
    siblings = [_template_row(x) for x in M.MessageTemplate.objects.filter(agency=request.agency, code=t.code).exclude(pk=t.pk)]
    return render(request, "gestao/message.html", {
        "nav": "msgs", "row": _template_row(t), "t": t, "draft": draft, "errors": errors, "can_edit": can_edit, "siblings": siblings,
        "versions": t.versions.select_related("saved_by")[:30]})


# ================================================================== radar de graduação
@staff_required()
def graduation(request):
    """Quem está na janela de graduação (regra do TikTok), com o ritmo do mês e a agenda de gestão de cada um."""
    today = E.tiktok_today()
    st = AgencySettings.objects.get(agency=request.agency)
    since = timezone.now() - dt.timedelta(days=st.graduation_window_days + 1)
    qs = (scoped_creators(request.user).filter(joined_at__gte=since)
          .exclude(status__in=[C.CreatorStatus.SAIU, C.CreatorStatus.ANONIMIZADO]).prefetch_related("snapshots", "monthly"))
    m0 = timezone.make_aware(dt.datetime.combine(E.month_start(timezone.localdate()), dt.time()))
    rows = []
    for c in qs:
        r = phases.graduation_radar_row(c, list(c.snapshots.all()), st, today, monthly=list(c.monthly.all()))
        if r is None:
            continue
        last = c.contacts.first()
        o = c.one_on_ones.first()
        r.last_contact = last.sent_at if last else None
        r.contacts_month = c.contacts.filter(sent_at__gte=m0).count()
        r.next_1a1 = o.b7_next_date if o else None
        r.last_1a1 = o.date if o else None
        rows.append(r)
    order = {k: i for i, k in enumerate(phases.RadarRow.ORDER)}
    rows.sort(key=lambda r: (not (r.last_month and r.status != "graduou"), order[r.status], r.missing))
    counts = {k: sum(1 for r in rows if r.status == k) for k in order}
    counts["potencial"] = sum(1 for r in rows if r.potential)
    return render(request, "gestao/graduation.html", {"nav": "grad", "rows": rows, "counts": counts, "settings": st,
                                                      "last_month_n": sum(1 for r in rows if r.last_month), "today": today})


# ================================================================== importação
@staff_required(Role.ADMIN, Role.GESTORA, Role.FINANCEIRO)
def imports(request):
    ctx = {"nav": "import", "batches": ImportBatch.objects.filter(agency=request.agency).select_related("uploaded_by")[:30],
           "status": S.import_status(request.agency), "can_backstage": _can_import(request.roles, "backstage"),
           "can_key": Role.ADMIN in request.roles, "api_url": request.build_absolute_uri(reverse("api_import_backstage")),
           "api_campaigns_url": request.build_absolute_uri(reverse("api_import_campaigns")),
           "key_once": request.session.pop("import_key_once", None) if Role.ADMIN in request.roles else None}
    if request.method == "POST" and request.FILES.get("file"):
        f = request.FILES["file"]
        data = f.read()
        overrides = {}
        for k, v in request.POST.items():
            if k.startswith("map__") and v:
                overrides[k[5:]] = v
        try:
            b = importer.create_preview(request.agency, data, f.name, user=request.user, mapping_overrides=overrides or None)
            if not _can_import(request.roles, b.kind):
                b.delete()
                raise PermissionDenied
            if overrides and request.POST.get("save_template") and b.template is None:
                ImportTemplate.objects.create(agency=request.agency, name=request.POST.get("template_name") or f"Modelo {f.name[:40]}",
                                              kind=request.POST.get("kind", "backstage"), signature=list(overrides)[:5], column_map=overrides)
            return redirect("g_import_preview", b.pk)
        except importer.ImportError_ as e:
            headers, _ = importer.read_table(data, f.name)
            ctx.update({"error": str(e), "headers": headers, "fields": _mappable_fields(), "filename": f.name})
    return render(request, "gestao/imports.html", ctx)


@require_POST
@staff_required(Role.ADMIN)
def import_key(request):
    """Chave da leitura automática (porta de importação). Só as sócias geram ou desligam.

    O texto da chave aparece uma única vez, na tela seguinte; o banco guarda só o resumo dela."""
    if request.POST.get("a") == "revoke":
        port.revoke_key(request.agency)
        messages.success(request, "Leitura automática desligada. A chave antiga não funciona mais.")
    else:
        request.session["import_key_once"] = port.new_key(request.agency, by=request.user)
        messages.success(request, "Chave gerada. Copie agora: ela não aparece de novo.")
    return redirect("g_imports")


def _mappable_fields():
    from core.bootstrap import BACKSTAGE_PT_MAP, TASK_EN_MAP

    fields = sorted({v for v in list(BACKSTAGE_PT_MAP.values()) + list(TASK_EN_MAP.values()) if not v.startswith("_")})
    return fields


@staff_required(Role.ADMIN, Role.GESTORA, Role.FINANCEIRO)
def import_preview(request, pk):
    b = get_object_or_404(ImportBatch, pk=pk, agency=request.agency)
    if not _can_import(request.roles, b.kind):
        raise PermissionDenied
    if request.method == "POST":
        if request.POST.get("a") == "commit" and b.status == "preview":
            importer.commit(b)
            messages.success(request, "Importação gravada. Métricas, Tiers, alertas e campanhas recalculados.")
        elif request.POST.get("a") == "revert" and b.status == "committed":
            importer.revert(b)
            messages.success(request, "Importação desfeita.")
        elif request.POST.get("a") == "discard" and b.status == "preview":
            b.delete()
            messages.success(request, "Pré-visualização descartada.")
            return redirect("g_imports")
        return redirect("g_import_preview", b.pk)
    rows = b.rows.all()
    return render(request, "gestao/import_preview.html", {
        "nav": "import", "b": b, "errors": rows.filter(action="error")[:50], "new": rows.filter(action="new")[:50],
        "exits": rows.filter(action="exit").select_related("creator")[:50], "n_rows": rows.count()})


# ================================================================== batalhas e dúvidas
def _battle_confirm(request, b):
    """Confirmar (ou mudar) a batalha: data e hora entre as opções do criador ou outra, rounds, oponente e faixa."""
    P = request.POST
    opts = battle_rules.options(b)
    choice = P.get("choice", "0")
    if choice.isdigit() and int(choice) < len(opts):
        date, time = opts[int(choice)]
    else:
        try:
            date, time = dt.date.fromisoformat(P.get("other_date", "")), dt.time.fromisoformat(P.get("other_time", ""))
        except ValueError:
            raise battle_rules.BattleError("Escolha uma das opções do criador ou informe outra data e hora.") from None
    try:
        rounds = int(P.get("final_rounds") or 0)
    except ValueError:
        rounds = 0
    was_confirmed = b.status == "aprovada"
    battle_rules.confirm(b, date, time, rounds, P.get("opponent", ""), P.get("expected_range", ""), P.get("reply", ""))
    b.save()
    if b.creator.user_id:
        title = "Sua batalha oficial mudou" if was_confirmed else "Sua batalha oficial está confirmada"
        notify(user_id=b.creator.user_id, kind="batalha", title=f"{title}: {b.date:%d/%m} às {b.time:%H:%M}",
               body=b.manager_reply, url="/batalhas/")
    return was_confirmed


@staff_required()
def battles(request):
    """Pedidos de batalha oficial da carteira: confirmar com o oponente e a faixa (texto pronto da BAT-CONF para o
    grupo), sugerir outro dia ou hora, ou recusar. Passo 3.3."""
    ids = scoped_creators(request.user).values_list("pk", flat=True)
    if request.method == "POST":
        if not staff_roles(request.user) & {Role.ADMIN, Role.GESTORA}:
            raise PermissionDenied
        b = get_object_or_404(M.BattleRequest.objects.select_related("creator"), pk=request.POST.get("id"), creator_id__in=ids)
        if request.POST.get("a") == "confirm":
            try:
                changed = _battle_confirm(request, b)
            except battle_rules.BattleError as e:
                messages.error(request, str(e))
                return redirect(reverse("g_battles") + f"#b{b.pk}")
            messages.success(request, "Batalha atualizada. Envie a atualização no grupo do criador." if changed else
                             "Batalha confirmada. Copie a confirmação, envie no grupo do criador e marque “Enviei”.")
            return redirect(reverse("g_battles") + f"#b{b.pk}")
        status = request.POST.get("status", b.status)
        if status == "aprovada" and b.status != "aprovada":
            messages.error(request, "Para confirmar, use “Confirmar batalha”, com o oponente.")
            return redirect("g_battles")
        if status in dict(M.BattleRequest.STATUS):
            b.status = status
        b.manager_reply = request.POST.get("reply", "")[:240]
        b.save()
        if b.creator.user_id:
            notify(user_id=b.creator.user_id, kind="batalha", title=f"Seu pedido de batalha: {b.get_status_display()}",
                   body=b.manager_reply, url="/batalhas/")
        return redirect("g_battles")
    today = timezone.localdate()
    qs = list(M.BattleRequest.objects.filter(creator_id__in=ids).select_related("creator", "opponent")[:200])
    conf = {c: template_for(request.agency, c) for c in ("BAT-CONF", "BAT-ATUALIZA")}
    confirmed = sorted([b for b in qs if b.status == "aprovada" and b.date >= today], key=lambda b: (b.date, b.time))
    for b in confirmed:
        b.confirmation = battle_rules.fill_confirmation(conf["BAT-CONF"].body, b) if conf["BAT-CONF"] else ""
        b.cl = battle_rules.checklist(b)
    pending = sorted([b for b in qs if b.status in battle_rules.OPEN_STATUSES], key=lambda b: (b.date, b.time))
    for b in pending:
        b.opts = battle_rules.options(b)
    others = [b for b in qs if b not in confirmed and b not in pending]
    return render(request, "gestao/battles.html", {
        "nav": "battles", "pending": pending, "confirmed": confirmed, "others": others[:60], "statuses": M.BattleRequest.STATUS,
        "rounds": M.BattleRequest.ROUNDS, "update_tpl": conf["BAT-ATUALIZA"], "today": today,
        "notice_days": AgencySettings.objects.get(agency=request.agency).battle_notice_days})


@staff_required()
def tickets(request):
    ids = scoped_creators(request.user).values_list("pk", flat=True)
    items = M.SupportTicket.objects.filter(creator_id__in=ids).select_related("creator").order_by("status", "-created_at")[:100]
    return render(request, "gestao/tickets.html", {"nav": "tickets", "items": items})


# ================================================================== campanhas
CAMPAIGN_EDITORS = {Role.ADMIN, Role.GESTORA, Role.CONTEUDO}


def _campaign_edit(request):
    """Foco, "não oferecer" e os campos que a gestão confere (mecânica, premia até, resumo, prêmios, link)."""
    P = request.POST
    camp = get_object_or_404(M.Campaign, pk=_int(P.get("id")), agency=request.agency)
    a = P.get("a")
    if a == "focus":
        camp.featured = not camp.featured
        if camp.featured:
            camp.do_not_offer = False
        messages.success(request, f"“{camp.name}”: {'agora é foco e aparece no app para quem participa' if camp.featured else 'deixou de ser foco'}.")
    elif a == "do_not_offer":
        camp.do_not_offer = not camp.do_not_offer
        if camp.do_not_offer:
            camp.featured = False
        messages.success(request, f"“{camp.name}”: {'não será oferecida a ninguém' if camp.do_not_offer else 'volta a poder ser oferecida'}.")
    elif a == "details":
        link = P.get("tiktok_url", "").strip()
        if link and not link.startswith("https://"):
            messages.error(request, "Cole o link completo da campanha (começa com https://).")
            return
        camp.mechanic = P.get("mechanic", "") if P.get("mechanic", "") in dict(M.Campaign.MECHANICS) else ""
        camp.prize_until = _int(P.get("prize_until"))
        camp.what_to_do, camp.prizes, camp.tiktok_url = P.get("what_to_do", "")[:1000], P.get("prizes", "")[:1000], link
        messages.success(request, f"“{camp.name}” atualizada.")
    camp.save()
    AuditLog.objects.create(agency=request.agency, actor=request.user, action=f"campanha_{a}", target=camp.name[:200])


@staff_required()
def campaigns(request):
    """Campanhas (passo 3.4): as lidas do Backstage pelo Claude, para a gestão escolher o foco, e as outras."""
    today = E.tiktok_today()
    can_edit = bool(staff_roles(request.user) & CAMPAIGN_EDITORS)
    if request.method == "POST":
        if not can_edit:
            raise PermissionDenied
        _campaign_edit(request)
        return redirect(reverse("g_campaigns") + (f"#c{request.POST.get('id')}" if request.POST.get("id") else ""))
    items = list(M.Campaign.objects.filter(agency=request.agency, end__gte=today - dt.timedelta(days=30)).order_by("end", "name"))
    mine = set(scoped_creators(request.user).values_list("pk", flat=True))
    by_camp = {}
    for p in M.CampaignParticipant.objects.filter(campaign__in=items, creator_id__in=mine).values("campaign_id", "status"):
        d = by_camp.setdefault(p["campaign_id"], {})
        d[p["status"] or "manual"] = d.get(p["status"] or "manual", 0) + 1
    for c in items:
        c.mine = by_camp.get(c.pk, {})
        c.active = c.start <= today <= c.end
    read = [c for c in items if c.read_at]
    others = [c for c in items if not c.read_at]
    covered = set()
    for c in items:
        if c.active and not c.do_not_offer:
            covered |= set(int(t) for t in c.audience_tiers) if c.audience_tiers else set(range(1, 11))
    last_read = max((c.read_at for c in read), default=None)
    return render(request, "gestao/campaigns.html", {
        "nav": "camp", "read": read, "others": others, "today": today, "can_edit": can_edit, "last_read": last_read,
        "mechanics": M.Campaign.MECHANICS, "uncovered": [t for t in range(1, 11) if t not in covered]})


@staff_required()
def campaign_detail(request, pk):
    camp = get_object_or_404(M.Campaign, pk=pk, agency=request.agency)
    visible = set(scoped_creators(request.user).values_list("pk", flat=True))
    rows = [s for s in camp.standings.all() if s.creator_id_ref in visible]
    return render(request, "gestao/campaign.html", {"nav": "camp", "camp": camp, "rows": rows})


# ================================================================== conteúdos
@staff_required()
def content(request):
    gaps = (M.FaqSearch.objects.filter(agency=request.agency, results=0).values("query").annotate(n=Count("id")).order_by("-n")[:20])
    faq_bad = M.FaqItem.objects.filter(agency=request.agency, not_helpful__gt=0).order_by("-not_helpful")[:10]
    surveys = M.Survey.objects.filter(agency=request.agency).annotate(n=Count("completions"))
    offers = M.PartnerOffer.objects.filter(agency=request.agency).annotate(n_clicks=Count("clicks", filter=Q(clicks__used_coupon=False)), n_used=Count("clicks", filter=Q(clicks__used_coupon=True)))
    anns = M.Announcement.objects.filter(agency=request.agency)[:10]
    if request.method == "POST" and request.POST.get("publish"):
        ann = get_object_or_404(M.Announcement, pk=request.POST["publish"], agency=request.agency)
        n = publish_announcement(ann)
        messages.success(request, f"Aviso publicado: {n} streamers notificados no app.")
        return redirect("g_content")
    return render(request, "gestao/content.html", {"nav": "content", "gaps": gaps, "faq_bad": faq_bad, "surveys": surveys, "offers": offers, "anns": anns})


@staff_required()
def survey_results(request, pk):
    sv = get_object_or_404(M.Survey, pk=pk, agency=request.agency)
    qs = []
    for q in sv.questions.all():
        answers = list(q.answers.values_list("value", flat=True))
        data = {}
        if q.kind == "nps":
            vals = [int(a) for a in answers if a.isdigit()]
            prom = sum(1 for v in vals if v >= 9)
            det = sum(1 for v in vals if v <= 6)
            data["nps"] = round((prom - det) / len(vals) * 100) if vals else None
            data["n"] = len(vals)
        elif q.kind in ("single", "multi"):
            counts = {o: answers.count(o) for o in q.options}
            tot = max(sum(counts.values()), 1)
            data["counts"] = [(o, n, n / tot) for o, n in counts.items()]
        else:
            data["texts"] = answers[-50:]
        qs.append((q, data))
    return render(request, "gestao/survey_results.html", {"nav": "content", "sv": sv, "qs": qs})


# ================================================================== relatórios
@staff_required()
def reports(request):
    today = E.tiktok_today()
    creators = scoped_creators(request.user)
    ids = list(creators.values_list("pk", flat=True))
    months = []
    for i in range(5, -1, -1):
        m = E.month_start(today)
        for _ in range(i):
            m = E.prev_month(m)
        qs = MonthlyResult.objects.filter(creator_id__in=ids, month=m)
        if not qs.exists():
            continue
        agg = {"month": m, "n": qs.count(), "diamonds": sum(x.diamonds for x in qs), "hours": sum(x.live_seconds for x in qs) / 3600,
               "valid_days": sum(x.valid_days for x in qs), "min_ok": sum(1 for x in qs if x.valid_days >= 5 and x.live_seconds >= 15 * 3600)}
        agg["min_ok_pct"] = agg["min_ok"] / agg["n"] if agg["n"] else 0
        import calendar as _cal

        agg["freq"] = (agg["valid_days"] / agg["n"]) / (_cal.monthrange(m.year, m.month)[1] / 7) if agg["n"] else 0
        months.append(agg)
    # por gestora
    per_mgr = []
    pm = E.prev_month(today)
    for u in User.objects.filter(memberships__agency=request.agency, memberships__role=Role.GESTORA).distinct():
        cids = [cid for cid in C.PortfolioAssignment.objects.filter(manager=u, valid_to__isnull=True).values_list("creator_id", flat=True) if cid in ids]
        if not cids:
            continue
        mr = MonthlyResult.objects.filter(creator_id__in=cids, month=pm)
        o3 = C.OneOnOne.objects.filter(creator_id__in=cids, date__gte=pm)
        per_mgr.append({"u": u, "n": len(cids), "diamonds": sum(x.diamonds for x in mr),
                        "one_on_ones": o3.count(), "complete": sum(1 for o in o3 if o.complete)})
    # uso do app (streamers com acesso que abriram na semana)
    week_ago = timezone.now() - dt.timedelta(days=7)
    with_access = creators.filter(user__isnull=False).count()
    opened = AppEvent.objects.filter(event="app_open", at__gte=week_ago, user__creator__in=creators).values("user").distinct().count()
    # saídas em 15 dias e meta de onboarding
    since = today - dt.timedelta(days=90)
    joined = creators.filter(joined_at__date__gte=since)
    early_exits = C.ExitRecord.objects.filter(creator__in=joined, within_free_period=True).count()
    st = AgencySettings.objects.get(agency=request.agency)
    reached = eligible = 0
    for c in joined.prefetch_related("snapshots"):
        ob = E.onboarding_status(c, list(c.snapshots.all()), st)
        if ob and not ob["active"]:
            eligible += 1
            reached += 1 if ob["met"] else 0
    contacts_week = C.Contact.objects.filter(creator__in=creators, sent_at__gte=week_ago).count()
    if request.GET.get("export") == "csv":
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="relatorio-mensal-{pm:%Y-%m}.csv"'
        w = csv.writer(resp)
        w.writerow(["Mês", "@", "Diamantes", "Horas", "Dias válidos", "Tier", "Fonte"])
        for x in MonthlyResult.objects.filter(creator_id__in=ids, month=pm).select_related("creator"):
            w.writerow([f"{pm:%Y-%m}", x.creator.username, x.diamonds, round(x.live_seconds / 3600, 1), x.valid_days, x.tier, x.source])
        return resp
    return render(request, "gestao/reports.html", {
        "nav": "reports", "months": months, "per_mgr": per_mgr, "with_access": with_access, "opened": opened,
        "usage": opened / with_access if with_access else None, "joined": joined.count(), "early_exits": early_exits,
        "early_exit_rate": early_exits / joined.count() if joined.count() else None,
        "ob_rate": reached / eligible if eligible else None, "ob_eligible": eligible, "contacts_week": contacts_week, "pm": pm})

"""Telas do streamer (celular). Cada view só usa o creator ligado ao usuário logado."""
import datetime as dt
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.access import staff_roles
from core.models import AppEvent, Consent
from crm.models import Creator, CreatorPrivate, CreatorStatus
from data import engine as E
from engage import academy as academy_rules
from engage import models as M
from engage.services import notify, creator_facts, faq_search, matches_audience, render_faq_answer, whatsapp_link

from . import progress as P
from . import services as S


LEFT_STATUSES = (CreatorStatus.SAIU, CreatorStatus.ANONIMIZADO)


def left_agency(creator):
    """Quem saiu da agência não entra mais no app. Quem está em aviso prévio (em_saida) ainda entra."""
    return creator.status in LEFT_STATUSES


def streamer_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        creator = Creator.objects.filter(user=request.user).first()
        if creator is None:
            if staff_roles(request.user):
                return redirect("g_dashboard")
            return render(request, "streamer/no_access.html", status=403)
        if left_agency(creator):
            return render(request, "streamer/no_access.html", {"left": True}, status=403)
        if creator.partner_group_id and not creator.partner_group.streamer_access_enabled:
            return render(request, "streamer/no_access.html", {"partner": creator.partner_group}, status=403)
        request.creator = creator
        return view(request, *args, **kwargs)

    return wrapper


def _log_open(request):
    last = request.session.get("hera_open")
    today = timezone.localdate().isoformat()
    if last != today:
        AppEvent.objects.create(user=request.user, event="app_open")
        request.session["hera_open"] = today


@login_required
def root(request):
    if not Creator.objects.filter(user=request.user).exists() and staff_roles(request.user):
        return redirect("g_dashboard")
    return home(request)


@streamer_required
def home(request):
    """Meu progresso: a tela inicial do app (visão). A lógica fica em web/progress.py."""
    _log_open(request)
    ctx = P.my_progress(request.creator)
    ctx["nav"] = "home"
    return render(request, "streamer/home.html", ctx)


@streamer_required
def my_level(request):
    """Meu nível e próximo nível, com a faixa de diamantes de cada nível e os grupos."""
    ctx = P.my_progress(request.creator)
    rules = E.tier_rules(request.creator.agency)
    ctx.update({"nav": "home", "levels": P.level_table(rules), "group_rules": S.group_ranges(request.creator.agency, rules)})
    return render(request, "streamer/level.html", ctx)


@streamer_required
def performance(request):
    """A tela Desempenho foi unida ao Meu progresso (decisão de 14/11/2026). O endereço antigo leva para lá."""
    return redirect("/#meses" if request.GET.get("aba") == "historico" else "/#semanas")


@streamer_required
def campaigns(request):
    c = request.creator
    today = E.tiktok_today()
    facts = creator_facts(c)
    active = S.visible_campaigns(c, facts, today)
    past = [x for x in M.Campaign.objects.filter(agency=c.agency, published=True, end__lt=today).exclude(source="backstage", featured=False).order_by("-end")[:5] if matches_audience(x, facts)]
    tab = "hera" if request.GET.get("aba") == "hera" else "oficiais"
    official = [x for x in active if not x["c"].tracked_in_app]
    internal = [x for x in active if x["c"].tracked_in_app]
    return render(request, "streamer/campaigns.html", {"nav": "camp", "tab": tab, "official": official, "internal": internal,
                                                        "items": internal if tab == "hera" else official, "past": past})


@streamer_required
def campaign(request, pk):
    c = request.creator
    camp = get_object_or_404(M.Campaign, pk=pk, agency=c.agency, published=True)
    if camp.source == "backstage" and not camp.featured:
        raise Http404
    facts = creator_facts(c)
    has_manual = camp.participants.exists()
    if (has_manual and not camp.participants.filter(creator=c).exists()) or (not has_manual and not matches_audience(camp, facts)):
        raise Http404
    if camp.tiktok_url:
        return redirect(camp.tiktok_url)  # o card abre direto a campanha no TikTok
    return render(request, "streamer/campaign.html", {"nav": "camp", "camp": camp,
                                                       "days_left": (camp.end - E.tiktok_today()).days})


@streamer_required
def academy(request):
    """Hera Academy: módulos que abrem por nível e por marco (regras em engage/academy.py)."""
    c = request.creator
    mods = academy_rules.modules(c)
    done = set(M.LessonProgress.objects.filter(creator=c).values_list("lesson_id", flat=True))
    opened = academy_rules.open_lessons(mods)
    rec = academy_rules.recommended(c, mods=mods)
    return render(request, "streamer/academy.html", {"nav": "academy", "modules": mods, "done": done, "rec": rec,
                                                      "total": len(opened), "n_done": sum(1 for l in opened if l.pk in done)})


@streamer_required
def lesson(request, pk):
    c = request.creator
    ls = get_object_or_404(M.Lesson, pk=pk, course__agency=c.agency, course__published=True)
    is_open, hint = academy_rules.lesson_state(c, ls)
    if not is_open:
        if not hint:  # módulo que não vale para este criador (público) ou curso extra sem liberação
            raise Http404
        messages.info(request, f"“{ls.title}” ainda não abriu. {hint}")
        return redirect("academy")
    if request.method == "POST":
        M.LessonProgress.objects.get_or_create(lesson=ls, creator=c)
        messages.success(request, "Aula concluída! 🎉")
        return redirect("academy")
    done = M.LessonProgress.objects.filter(lesson=ls, creator=c).exists()
    return render(request, "streamer/lesson.html", {"nav": "academy", "lesson": ls, "done": done})


@streamer_required
def profile(request):
    c = request.creator
    priv, _ = CreatorPrivate.objects.get_or_create(creator=c)
    prof = getattr(c, "community", None)
    if request.method == "POST":
        priv.whatsapp = request.POST.get("whatsapp", "")[:30]
        priv.save()
        if prof:
            prof.about = request.POST.get("about", "")[:1000]
            prof.save(update_fields=["about"])
        messages.success(request, "Perfil atualizado.")
        return redirect("profile")
    tier, _ = E.official_tier(c)
    return render(request, "streamer/profile.html", {"nav": "profile", "c": c, "priv": priv, "prof": prof, "tier": tier,
                                                      "group": creator_facts(c)["group"], "history": c.group_history.all()[:6],
                                                      "manager": c.current_manager()})


@streamer_required
def notifications(request):
    qs = M.Notification.objects.filter(user=request.user)[:50]
    items = list(qs)
    M.Notification.objects.filter(user=request.user, read_at__isnull=True).update(read_at=timezone.now())
    return render(request, "streamer/notifications.html", {"items": items})


@streamer_required
def announcements(request):
    c = request.creator
    facts = creator_facts(c)
    now = timezone.now()
    items = [a for a in M.Announcement.objects.filter(agency=c.agency, publish_at__lte=now) if matches_audience(a, facts) and (not a.expires_at or a.expires_at > now)]
    return render(request, "streamer/announcements.html", {"items": items[:30]})


# ---------------------------------------------------------------- dúvidas (Q&A)
@streamer_required
def faq(request):
    c = request.creator
    cats = {}
    for it in M.FaqItem.objects.filter(agency=c.agency, active=True).order_by("category", "id"):
        cats.setdefault(it.category, []).append(it)
    icons = {"Dia válido": "📅", "Regras da plataforma": "🎯", "Tier": "🏅", "Batalhas": "⚔️", "Campanhas": "🏆", "Regras de LIVE": "🚫",
             "Saída": "🚪", "Suporte": "🕘", "Benefícios": "🎁", "Hera Academy": "🎓", "Academy": "🎓"}
    cat = request.GET.get("cat")
    return render(request, "streamer/faq.html", {"cats": [{"name": k, "items": v, "icon": icons.get(k, "❓")} for k, v in cats.items()],
                                                 "open_cat": cat, "open_items": cats.get(cat, []), "nav": "faq"})


@streamer_required
def faq_search_view(request):
    c = request.creator
    q = request.GET.get("q", "").strip()
    results = []
    if len(q) >= 3:
        results = [(it, render_faq_answer(it, c)) for it in faq_search(c.agency, q, user=request.user)]
    return render(request, "streamer/_faq_results.html", {"q": q, "results": results})


@require_POST
@streamer_required
def faq_feedback(request, pk):
    it = get_object_or_404(M.FaqItem, pk=pk, agency=request.creator.agency)
    if request.POST.get("v") == "1":
        M.FaqItem.objects.filter(pk=pk).update(helpful=it.helpful + 1)
        return HttpResponse('<small class="muted">Que bom! 💜</small>')
    M.FaqItem.objects.filter(pk=pk).update(not_helpful=it.not_helpful + 1)
    return HttpResponse('<small class="muted">Valeu por avisar! Vamos melhorar essa resposta.</small>')


@require_POST
@streamer_required
def ask_manager(request):
    c = request.creator
    q = request.POST.get("question", "").strip()[:1000]
    if not q:
        return redirect("faq")
    M.SupportTicket.objects.create(creator=c, question=q)
    mgr = c.current_manager()
    phone = ""
    if mgr:
        m = mgr.memberships.filter(agency=c.agency).exclude(phone="").first()
        phone = m.phone if m else ""
        notify(user=mgr, kind="duvida", title=f"@{c.username} mandou uma dúvida pelo app", body=q[:200], url=f"/gestao/creators/{c.pk}/")
    link = whatsapp_link(phone or c.agency.whatsapp_support, f"Oi! Tenho uma dúvida: {q}")
    return render(request, "streamer/ask_sent.html", {"link": link, "q": q})


# ---------------------------------------------------------------- benefícios
@streamer_required
def offers(request):
    c = request.creator
    facts = creator_facts(c)
    today = timezone.localdate()
    items = [o for o in M.PartnerOffer.objects.filter(agency=c.agency, active=True) if matches_audience(o, facts) and (not o.valid_until or o.valid_until >= today)]
    return render(request, "streamer/offers.html", {"items": items})


@streamer_required
def offer_go(request, pk):
    o = get_object_or_404(M.PartnerOffer, pk=pk, agency=request.creator.agency, active=True)
    M.OfferClick.objects.create(offer=o, user=request.user)
    return redirect(o.url or "offers")


@require_POST
@streamer_required
def offer_used(request, pk):
    o = get_object_or_404(M.PartnerOffer, pk=pk, agency=request.creator.agency)
    M.OfferClick.objects.create(offer=o, user=request.user, used_coupon=True)
    return HttpResponse('<span class="pill cyan">Anotado, valeu! 💜</span>')


# ---------------------------------------------------------------- pesquisas
@streamer_required
def survey(request, pk):
    c = request.creator
    sv = get_object_or_404(M.Survey, pk=pk, agency=c.agency)
    if not sv.is_open() or not matches_audience(sv, creator_facts(c)):
        raise Http404
    if M.SurveyCompletion.objects.filter(survey=sv, user=request.user).exists():
        return render(request, "streamer/survey_done.html", {"sv": sv})
    questions = list(sv.questions.all())
    step = int(request.POST.get("step", request.GET.get("step", 0)))
    answers = request.session.get(f"sv{sv.pk}", {})
    if request.method == "POST":
        q = questions[step]
        val = request.POST.getlist("value") if q.kind == "multi" else [request.POST.get("value", "")]
        answers[str(q.pk)] = [v for v in val if v]
        request.session[f"sv{sv.pk}"] = answers
        step += 1
        if step >= len(questions):
            for q in questions:
                for v in answers.get(str(q.pk), []):
                    M.SurveyAnswer.objects.create(question=q, value=v[:1000], user=None if sv.anonymous else request.user)
            M.SurveyCompletion.objects.create(survey=sv, user=request.user)
            request.session.pop(f"sv{sv.pk}", None)
            return render(request, "streamer/survey_done.html", {"sv": sv, "thanks": True})
    return render(request, "streamer/survey.html", {"sv": sv, "q": questions[step], "step": step, "total": len(questions),
                                                     "progress": step / len(questions), "nps": range(11)})


# ---------------------------------------------------------------- batalhas
@streamer_required
def battles(request):
    items = M.BattleRequest.objects.filter(creator=request.creator)[:20]
    return render(request, "streamer/battles.html", {"items": items, "nav": "battles"})


@streamer_required
def battle_new(request):
    c = request.creator
    error = None
    if request.method == "POST":
        try:
            # Um tipo só ("batalha agendada"). Quem batalha com quem é a Hera que avalia e sugere depois.
            rounds = int(request.POST.get("rounds") or 1)
            if rounds not in dict(M.BattleRequest.ROUNDS):
                raise ValueError("rounds")
            b = M.BattleRequest(
                creator=c, kind="oficial", date=dt.date.fromisoformat(request.POST["date"]),
                time=dt.time.fromisoformat(request.POST["time"]), rounds=rounds,
                goal_diamonds=int(request.POST["goal_diamonds"]) if request.POST.get("goal_diamonds") else None,
                notes=request.POST.get("notes", "")[:1000],
            )
            # outras opções de dia e hora que o criador oferece (linhas vazias são ignoradas)
            seen = {(b.date, b.time)}
            for d_txt, t_txt in zip(request.POST.getlist("alt_date"), request.POST.getlist("alt_time")):
                if not d_txt and not t_txt:
                    continue
                d, t = dt.date.fromisoformat(d_txt), dt.time.fromisoformat(t_txt)
                if d < timezone.localdate():
                    raise ValueError("data no passado")
                if (d, t) not in seen and len(b.other_options) < M.BattleRequest.MAX_OTHER_OPTIONS:
                    seen.add((d, t))
                    b.other_options.append({"date": d.isoformat(), "time": t.strftime("%H:%M")})
            if b.date < timezone.localdate():
                raise ValueError("data no passado")
            b.save()
            mgr = c.current_manager()
            if mgr:
                notify(user=mgr, kind="batalha", title=f"@{c.username} pediu uma batalha", url="/gestao/batalhas/")
            messages.success(request, "Pedido enviado! A Hera avisa no seu grupo e aqui no app quando a batalha estiver confirmada. 💜")
            return redirect("battles")
        except (KeyError, ValueError):
            error = "Confira os dias e as horas."
    # o botão da aula só aparece se a aula já abriu para este criador (Hera Academy)
    battle_lesson = next((l for l in academy_rules.open_lessons(academy_rules.modules(c)) if l.about_battles), None)
    return render(request, "streamer/battle_new.html", {"nav": "battles", "error": error, "today": timezone.localdate(), "battle_lesson": battle_lesson,
                                                         "rounds": M.BattleRequest.ROUNDS, "max_options": M.BattleRequest.MAX_OTHER_OPTIONS})


# ---------------------------------------------------------------- primeiro acesso
def first_access(request):
    """Tela aberta (sem login): o criador informa o @ e o código que recebeu no grupo, cadastra o e-mail e cria a senha.

    Serve também para criar uma senha nova: a Hera gera outro código. A conferência fica em crm/first_access.py."""
    from django.contrib.auth import login
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError
    from django.core.validators import validate_email

    from crm import first_access as FA

    if request.user.is_authenticated:
        return redirect("/")
    errors, P = [], request.POST
    if request.method == "POST":
        email, password = P.get("email", "").strip().lower(), P.get("password", "")
        try:
            validate_email(email)
        except ValidationError:
            errors.append("Informe um e-mail válido.")
        if password != P.get("password2", ""):
            errors.append("As duas senhas não são iguais.")
        else:
            try:
                validate_password(password)
            except ValidationError as e:
                errors.extend(e.messages)
        if not errors:
            try:
                user = FA.activate(P.get("handle"), P.get("code"), email, password)
            except FA.AccessError as e:
                errors.append(str(e))
            else:
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                return redirect("/boas-vindas/")
    return render(request, "account/first_access.html", {"errors": errors, "handle": P.get("handle", ""), "code": P.get("code", ""),
                                                         "email": P.get("email", "")})


@login_required
def welcome(request):
    c = Creator.objects.filter(user=request.user).first()
    if c is None:
        return redirect("/")
    if left_agency(c):
        return render(request, "streamer/no_access.html", {"left": True}, status=403)
    step = request.GET.get("s", "1")
    # depois do @ confirmado vem o cadastro (experiência com LIVE e aniversário), uma vez só
    after_confirm = "/boas-vindas/?s=3" if c.track_suggested else "/boas-vindas/?s=c"
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "consent" and request.POST.get("accept"):
            Consent.objects.get_or_create(user=request.user, version=settings.CONSENT_VERSION,
                                          defaults={"ip": request.META.get("REMOTE_ADDR")})
            # quem entrou pelo código já informou o próprio @: não precisa confirmar de novo
            return redirect(after_confirm if c.confirmed_username else "/boas-vindas/?s=2")
        if action == "cadastro":
            from crm.models import TRACKS

            exp = request.POST.get("experience", "")
            if exp in dict(TRACKS):
                c.track_suggested = exp  # só sugere a trilha: quem define é a gestão
                c.save(update_fields=["track_suggested"])
            try:
                day, month = int(request.POST.get("birth_day") or 0), int(request.POST.get("birth_month") or 0)
            except ValueError:
                day = month = 0
            if 1 <= day <= 31 and 1 <= month <= 12:
                priv, _ = CreatorPrivate.objects.get_or_create(creator=c)
                priv.birth_day, priv.birth_month = day, month
                priv.save(update_fields=["birth_day", "birth_month"])
            return redirect("/boas-vindas/?s=3")
        if action == "confirm":
            if request.POST.get("is_me") == "1":
                c.confirmed_username = True
                if c.status in (CreatorStatus.PENDENTE, CreatorStatus.CONVIDADO):
                    c.status = CreatorStatus.ATIVO
                c.save(update_fields=["confirmed_username", "status"])
                return redirect(after_confirm)
            mgr = c.current_manager()
            if mgr:
                notify(user=mgr, kind="cadastro", title=f"{request.user.email} disse que o @ {c.username} não é dele(a)", url=f"/gestao/creators/{c.pk}/")
            return render(request, "streamer/welcome.html", {"c": c, "step": "wrong"})
    first = academy_rules.next_open_lesson(c) if step == "4" else None  # a primeira aula aberta da Hera Academy
    has_consent = Consent.objects.filter(user=request.user, version=settings.CONSENT_VERSION).exists()
    if not has_consent:
        step = "1"
    return render(request, "streamer/welcome.html", {"c": c, "step": step, "lesson": first, "consent_version": settings.CONSENT_VERSION})


def manifest(request):
    from django.http import JsonResponse

    return JsonResponse({
        "name": "Hera Creator Hub", "short_name": "Hera", "start_url": "/", "display": "standalone",
        "background_color": "#f7f6f9", "theme_color": "#5c019b", "lang": "pt-BR",
        "icons": [{"src": "/static/img/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/static/img/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}],
    })


# Rede primeiro para os arquivos estáticos: a cópia guardada só é usada sem internet.
# (A versão anterior usava a cópia guardada para sempre e mostrava estilos antigos.)
SW = """const C='hera-v2';const OFF='/offline/';
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.addAll([OFF,'/static/css/hera.css'])));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==C).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{const r=e.request;if(r.method!=='GET')return;
if(r.mode==='navigate'){e.respondWith(fetch(r).catch(()=>caches.match(OFF)));return;}
if(r.url.includes('/static/')){e.respondWith(fetch(r).then(res=>{if(res.ok){const cp=res.clone();caches.open(C).then(c=>c.put(r,cp));}return res;}).catch(()=>caches.match(r)));}});
"""


def service_worker(request):
    return HttpResponse(SW, content_type="application/javascript")


def offline(request):
    return render(request, "offline.html")

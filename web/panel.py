"""Painel das sócias (etapa 4, passo 4.1; visão, "Painel das sócias").

Só Admin (Mariana e Aline). Mostra, sem ninguém montar nada, se o método está sendo aplicado e se está dando
resultado. Todos os números saem de "Dados do criador" (fonte única, dados até ontem).

Decisões da Mariana de 19/11/2026: bônus, receita e a simulação de compra de moedas ficam fora do app (as colunas
de bônus da planilha Task continuam ignoradas); o sorteio é de 5 "Enviei" por semana no total, espalhados entre as
gestoras.

Também ficam aqui: o pedido de decisão às sócias (manter ou encerrar), o sorteio semanal e o retrato da fila de cada
gestora, que a rotina das 6h tira para medir a fila concluída.
"""
import calendar
import datetime as dt
import random
import statistics

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone

from core.models import AgencySettings, Membership, PartnerGroup, Role
from crm.models import (AlertDismissal, ApprovalRequest, Contact, Creator, CreatorStatus, ExitRecord, OneOnOne,
                        PortfolioAssignment, QueueDay, Reply, SentCheck, STOP_REASONS)
from data import engine as E
from data import phases
from data.models import CreatorSnapshot, GroupRule, MonthlyResult

User = get_user_model()
LEFT = [CreatorStatus.SAIU, CreatorStatus.ANONIMIZADO]
DRAW_SIZE = 5


class PanelError(Exception):
    pass


def _local_day(ts):
    return timezone.localtime(ts).date()


def week_start(day):
    return day - dt.timedelta(days=day.weekday())


def band(pct, good, bad, higher_is_better=True):
    """'bom', 'atencao' ou 'ruim', pelas referências da visão (ex.: saídas abaixo de 10% é bom, acima de 20% é ruim)."""
    if pct is None:
        return ""
    if higher_is_better:
        return "bom" if pct >= good else "ruim" if pct < bad else "atencao"
    return "bom" if pct < good else "ruim" if pct > bad else "atencao"


# ------------------------------------------------------------------ resultado do mês
def month_result(creators, today):
    """Diamantes do mês até ontem, comparados ao mesmo ponto do mês passado, e a projeção do fechamento."""
    ids = list(creators.values_list("pk", flat=True))
    m0, pm = E.month_start(today), E.prev_month(today)
    snaps = {}
    for s in CreatorSnapshot.objects.filter(creator_id__in=ids, period_start=m0).order_by("creator_id", "period_end"):
        snaps[s.creator_id] = s  # fica o mais recente de cada criador
    diamonds = sum(s.diamonds for s in snaps.values())
    end_ref = max((s.period_end for s in snaps.values()), default=None)
    last_total = MonthlyResult.objects.filter(creator_id__in=ids, month=pm).aggregate(t=Sum("diamonds"))["t"] or 0
    out = {"n": creators.exclude(status__in=LEFT).count(), "diamonds": diamonds, "end_ref": end_ref, "last_total": last_total,
           "with_live": sum(1 for s in snaps.values() if s.live_seconds > 0), "same_point": None, "change": None, "forecast": None}
    if end_ref:
        elapsed = (end_ref - m0).days + 1
        days = calendar.monthrange(m0.year, m0.month)[1]
        out["same_point"] = last_total * elapsed / calendar.monthrange(pm.year, pm.month)[1]
        out["change"] = (diamonds / out["same_point"] - 1) if out["same_point"] else None
        out["forecast"] = round(diamonds / elapsed * days) if elapsed else None
    return out


def result_blocks(agency, today):
    """Conta inteira primeiro (é sobre ela que o TikTok paga), depois só a Hera e cada grupo parceiro."""
    allc = Creator.objects.filter(agency=agency)
    blocks = [{"name": "Conta inteira", **month_result(allc, today)}]
    direct = PartnerGroup.objects.filter(agency=agency, is_direct=True).values_list("pk", flat=True)
    hera = allc.filter(partner_group__isnull=True) | allc.filter(partner_group_id__in=list(direct))
    blocks.append({"name": "Só a Hera", **month_result(hera, today)})
    for pg in PartnerGroup.objects.filter(agency=agency, is_direct=False).order_by("name"):
        qs = allc.filter(partner_group=pg)
        if qs.exists():
            blocks.append({"name": pg.name, **month_result(qs, today)})
    return blocks


# ------------------------------------------------------------------ funil do onboarding e retenção
def _ever_live(c, snaps):
    return bool(c.first_live_at) or any(iv.had_live for iv in E.intervals(snaps))


def _graduated(c, snaps, monthly, st, today):
    """Teve pelo menos um mês com a marca de graduação dentro da janela (meses fechados ou o mês corrente)."""
    if not c.joined_at:
        return False
    start = c.joined_at.date()
    end = start + dt.timedelta(days=st.graduation_window_days - 1)
    for m in monthly:
        if m.diamonds >= st.graduation_diamonds and E.month_end(m.month) >= start and m.month <= end:
            return True
    cur = [s for s in snaps if s.period_start == E.month_start(today)]
    return bool(cur and cur[-1].diamonds >= st.graduation_diamonds and E.month_start(today) <= end)


def funnel(agency, today, months=6):
    """Por mês de entrada: entrou, fez a 1ª LIVE, fechou 5 dias e 15h, ficou depois do D15, graduou."""
    st = AgencySettings.objects.get(agency=agency)
    m0 = E.month_start(today)
    first = m0
    for _ in range(months - 1):
        first = E.prev_month(first)
    rows = {}
    m = first
    while m <= m0:
        rows[m] = {"month": m, "joined": 0, "first_live": 0, "rule": 0, "past15": 0, "stayed": 0, "graduated": 0}
        m = E.month_start(E.month_end(m) + dt.timedelta(days=1))
    qs = (Creator.objects.filter(agency=agency, joined_at__date__gte=first)
          .prefetch_related("snapshots", "monthly", "exits"))
    for c in qs:
        r = rows.get(E.month_start(c.joined_at.date()))
        if r is None:
            continue
        snaps, monthly = list(c.snapshots.all()), list(c.monthly.all())
        r["joined"] += 1
        r["first_live"] += _ever_live(c, snaps)
        ob = E.onboarding_status(c, snaps, st)
        r["rule"] += bool(ob and ob["met"])
        if (c.days_in_agency(today) or 0) > st.free_exit_days:
            r["past15"] += 1
            r["stayed"] += not any(x.within_free_period for x in c.exits.all())
        r["graduated"] += _graduated(c, snaps, monthly, st, today)
    out = list(rows.values())
    for r in out:
        r["stayed_pct"] = r["stayed"] / r["past15"] if r["past15"] else None
    return list(reversed(out))


def retention(agency, today, days=90):
    """Saída nos 15 primeiros dias (abaixo de 10% é bom, acima de 20% é ruim), encerramentos e motivos de saída."""
    since = today - dt.timedelta(days=days)
    joined = Creator.objects.filter(agency=agency, joined_at__date__gte=since)
    early = ExitRecord.objects.filter(creator__in=joined, within_free_period=True).count()
    n = joined.count()
    pct = early / n if n else None
    exits = ExitRecord.objects.filter(creator__agency=agency, requested_at__gte=since)
    labels = dict(STOP_REASONS)
    reasons = {}
    for code in exits.values_list("reason_code", flat=True):
        key = labels.get(code, "Sem motivo registrado")
        reasons[key] = reasons.get(key, 0) + 1
    closed = ApprovalRequest.objects.filter(agency=agency, kind="manter_encerrar", decision="encerrar", decided_at__date__gte=since)
    return {"days": days, "joined": n, "early": early, "early_pct": pct, "early_band": band(pct, 0.10, 0.20, higher_is_better=False),
            "exits": exits.count(), "reasons": sorted(reasons.items(), key=lambda x: -x[1]),
            "closed_30": closed.filter(item_code__startswith="regua_").count(), "closed_onboarding": closed.filter(item_code__startswith="onboarding_").count()}


# ------------------------------------------------------------------ graduação e base por nível
def graduation(agency, today):
    st = AgencySettings.objects.get(agency=agency)
    rows = []
    for c in (Creator.objects.filter(agency=agency, joined_at__isnull=False).exclude(status__in=LEFT)
              .filter(joined_at__date__gte=today - dt.timedelta(days=st.graduation_window_days + 31))
              .prefetch_related("snapshots", "monthly")):
        r = phases.graduation_radar_row(c, list(c.snapshots.all()), st, today, monthly=list(c.monthly.all()))
        if r:
            rows.append(r)
    return {"window": len(rows), "reached": [r for r in rows if r.status in ("graduou", "conferir")],
            "on_pace": [r for r in rows if r.status == "no_ritmo"], "speed_up": [r for r in rows if r.status == "acelerar"],
            "last_month": [r for r in rows if r.last_month and r.status not in ("graduou",)], "target": st.graduation_diamonds}


def base_by_level(agency, today):
    """Criadores por grupo (Tier do mês fechado) e quem subiu ou desceu em relação ao mês anterior."""
    pm = E.prev_month(today)
    ppm = E.prev_month(pm)
    groups = list(GroupRule.objects.filter(agency=agency).order_by("order"))
    active = Creator.objects.filter(agency=agency).exclude(status__in=LEFT)
    now = {m.creator_id: m.tier or 1 for m in MonthlyResult.objects.filter(creator__in=active, month=pm)}
    before = {m.creator_id: m.tier or 1 for m in MonthlyResult.objects.filter(creator__in=active, month=ppm)}
    count = {g.name: 0 for g in groups}
    for tier in now.values():
        name = E.group_for_tier(tier, groups)
        if name in count:
            count[name] += 1
    names = dict(active.values_list("pk", "username"))
    up = [(names[cid], before[cid], t) for cid, t in now.items() if cid in before and t > before[cid]]
    down = [(names[cid], before[cid], t) for cid, t in now.items() if cid in before and t < before[cid]]
    return {"month": pm, "groups": [{"name": g.name, "range": f"T{g.tier_min}" + (f"–T{g.tier_max}" if g.tier_max != g.tier_min else ""),
                                     "n": count[g.name]} for g in groups],
            "up": sorted(up), "down": sorted(down)}


# ------------------------------------------------------------------ execução da gestão
def snapshot_queue(agency, today=None):
    """Retrato da fila de cada gestora no começo do dia (rotina das 6h). Refazer no mesmo dia só atualiza."""
    from .services import action_queue

    today = today or timezone.localdate()
    active = Creator.objects.filter(agency=agency).exclude(status__in=LEFT)
    queue = action_queue(active, agency)
    by = {}
    for i in queue:
        mid = next((a.manager_id for a in i.creator.assignments.all() if a.valid_to is None), None)
        row = by.setdefault(mid, {"ids": set(), "items": 0})
        row["items"] += 1
        if i.is_message:
            row["ids"].add(i.creator.pk)
    for mid in set(by) | set(queue.overflow_by):
        row = by.get(mid, {"ids": set(), "items": 0})
        QueueDay.objects.update_or_create(agency=agency, manager_id=mid, day=today, defaults={
            "creator_ids": sorted(row["ids"]), "items": row["items"], "overflow": queue.overflow_by.get(mid, 0)})


def _queue_done(qd):
    """Criadores da fila daquele dia que tiveram "Enviei" ou "Adiar" no mesmo dia."""
    if not qd.creator_ids:
        return 0
    start = timezone.make_aware(dt.datetime.combine(qd.day, dt.time.min))
    end = start + dt.timedelta(days=1)
    sent = set(Contact.objects.filter(creator_id__in=qd.creator_ids, sent_at__gte=start, sent_at__lt=end).values_list("creator_id", flat=True))
    deferred = set(AlertDismissal.objects.filter(creator_id__in=qd.creator_ids, created_at__gte=start, created_at__lt=end)
                   .values_list("creator_id", flat=True))
    return len(set(qd.creator_ids) & (sent | deferred))


def execution(agency, today):
    """Por gestora: fila concluída nos últimos 7 dias, tempo até o 1º contato com o novato, respostas, 1:1 e dias sem
    trabalhar no mês. Referência da visão: acima de 90% da fila concluída no dia."""
    from crm import absence

    st = AgencySettings.objects.get(agency=agency)
    week_ago = today - dt.timedelta(days=6)
    m0 = E.month_start(today)
    skipped = absence.skipped_days(agency)
    managers = (User.objects.filter(memberships__agency=agency, memberships__role=Role.GESTORA, memberships__active=True)
                .distinct().order_by("first_name", "email"))
    rows = []
    for u in managers:
        cids = list(PortfolioAssignment.objects.filter(manager=u, valid_to__isnull=True, creator__agency=agency)
                    .exclude(creator__status__in=LEFT).values_list("creator_id", flat=True))
        days = [qd for qd in QueueDay.objects.filter(agency=agency, manager=u, day__gte=week_ago, day__lte=today)
                if qd.day not in skipped.get(u.pk, [])]
        total = sum(len(qd.creator_ids) for qd in days)
        done = sum(_queue_done(qd) for qd in days)
        pct = done / total if total else None
        # tempo até o primeiro "Enviei" para quem entrou nos últimos 30 dias
        waits = []
        for c in Creator.objects.filter(pk__in=cids, joined_at__date__gte=today - dt.timedelta(days=30)):
            first = Contact.objects.filter(creator=c).order_by("sent_at").first()
            if first:
                waits.append(max((first.sent_at - c.joined_at).total_seconds() / 86400, 0))
        week_start_dt = timezone.make_aware(dt.datetime.combine(week_ago, dt.time.min))
        sent = Contact.objects.filter(creator_id__in=cids, sent_at__gte=week_start_dt).count()
        replies = Reply.objects.filter(creator_id__in=cids, created_at__gte=week_start_dt).count()
        need_1a1 = one_on_one_needed(agency, cids, today, st)
        done_1a1 = {o.creator_id for o in OneOnOne.objects.filter(creator_id__in=[c.pk for c in need_1a1], date__gte=m0)
                    .prefetch_related("actions") if o.complete}  # só conta 1:1 completo (passo 4.2)
        rows.append({
            "user": u, "name": absence.name_of(u), "n": len(cids), "queue_days": len(days), "queue_total": total, "queue_done": done,
            "queue_pct": pct, "queue_band": band(pct, 0.90, 0.70), "overflow": sum(qd.overflow for qd in days),
            "first_contact_days": statistics.median(waits) if waits else None, "newcomers": len(waits),
            "sent_week": sent, "replies_week": replies, "one_on_one_need": len(need_1a1), "one_on_one_done": len(done_1a1),
            "one_on_one_missing": [c.username for c in need_1a1 if c.pk not in done_1a1],
            "skipped": skipped.get(u.pk, []),
        })
    return rows


def one_on_one_needed(agency, creator_ids, today, st=None):
    """Quem precisa de 1:1 no mês (visão): criadores Diamante e quem tem potencial de graduação."""
    from crm.one_on_one import diamond_min_tier, monthly_reason  # a mesma regra da tela 1:1 e da fila (passo 4.2)

    st = st or AgencySettings.objects.get(agency=agency)
    dtier = diamond_min_tier(agency)
    pm = E.prev_month(today)
    tiers = {m.creator_id: m.tier or 1 for m in MonthlyResult.objects.filter(creator_id__in=creator_ids, month=pm)}
    return [c for c in Creator.objects.filter(pk__in=creator_ids).prefetch_related("snapshots", "monthly")
            if monthly_reason(c, tiers.get(c.pk), list(c.snapshots.all()), st, today, dtier, monthly=list(c.monthly.all()))]


# ------------------------------------------------------------------ Hera Academy, batalhas e recrutamento
def academy(agency, today):
    from engage.models import Course, LessonProgress

    active = Creator.objects.filter(agency=agency).exclude(status__in=LEFT)
    with_login = active.filter(user__isnull=False).count()
    mods = []
    for co in Course.objects.filter(agency=agency, published=True).prefetch_related("lessons"):
        lessons = [l.pk for l in co.lessons.all()]
        prog = LessonProgress.objects.filter(lesson_id__in=lessons, creator__in=active)
        per = {}
        for cid in prog.values_list("creator_id", flat=True):
            per[cid] = per.get(cid, 0) + 1
        mods.append({"title": co.title, "lessons": len(lessons), "watched": len(per),
                     "finished": sum(1 for n in per.values() if lessons and n >= len(lessons))})
    # novatos que viram o primeiro módulo antes da 1ª LIVE (indicador novo da visão)
    first = Course.objects.filter(agency=agency, published=True, opens_on="acesso").order_by("order").first()
    before = total = 0
    if first:
        lessons = list(first.lessons.values_list("pk", flat=True))
        for c in active.filter(joined_at__date__gte=today - dt.timedelta(days=60), first_live_at__isnull=False):
            total += 1
            seen = LessonProgress.objects.filter(creator=c, lesson_id__in=lessons).order_by("completed_at").first()
            before += bool(seen and _local_day(seen.completed_at) <= c.first_live_at)
    return {"with_login": with_login, "modules": mods, "first_module": first.title if first else "", "before_first_live": before,
            "newcomers_live": total}


def battles(agency, today, weeks=4):
    """Batalhas por semana por criador que fez LIVE (6 ou mais é bom, menos de 3 é ruim) e batalhas oficiais."""
    from engage.models import BattleRequest

    active = list(Creator.objects.filter(agency=agency).exclude(status__in=LEFT).prefetch_related("snapshots"))
    first_week = week_start(today) - dt.timedelta(days=7 * weeks)
    by_week = {}
    for c in active:
        mine = {}  # a semana que cruza a virada do mês vem em dois pedaços: junta por criador antes de contar
        for w in E.weekly_intervals(list(c.snapshots.all())):
            key = w.end - dt.timedelta(days=w.end.weekday())
            if key < first_week:
                continue
            if w.start < key - dt.timedelta(days=2):
                continue  # a leitura cobre mais de uma semana (ex.: o mês chegou numa importação só): não dá para dizer a semana
            live, n = mine.get(key, (False, 0))
            mine[key] = (live or w.had_live, n + (w.battles or 0))
        for key, (live, n) in mine.items():
            if not live:
                continue
            row = by_week.setdefault(key, {"week": key, "creators": 0, "battles": 0, "good": 0, "bad": 0})
            row["creators"] += 1
            row["battles"] += n
            row["good"] += n >= 6
            row["bad"] += n < 3
    rows = sorted(by_week.values(), key=lambda r: r["week"], reverse=True)[:weeks]
    for r in rows:
        r["avg"] = r["battles"] / r["creators"] if r["creators"] else 0
        r["band"] = band(r["avg"], 6, 3)
    m0 = E.month_start(today)
    official = BattleRequest.objects.filter(creator__agency=agency, kind="oficial")
    return {"weeks": rows, "official_confirmed": official.filter(status="aprovada", date__gte=m0).count(),
            "official_pending": official.filter(status="pendente").count(),
            "official_done": official.filter(status__in=["aprovada", "realizada"], date__gte=m0, date__lt=today).count()}


def recruitment(agency, today, months=6):
    st = AgencySettings.objects.get(agency=agency)
    first = E.month_start(today)
    for _ in range(months - 1):
        first = E.prev_month(first)
    rows = {}
    for c in (Creator.objects.filter(agency=agency, joined_at__date__gte=first, recruited_by__isnull=False)
              .select_related("recruited_by").prefetch_related("snapshots", "monthly")):
        r = rows.setdefault(c.recruited_by_id, {"user": c.recruited_by, "joined": 0, "rule": 0, "graduated": 0, "left15": 0})
        snaps = list(c.snapshots.all())
        r["joined"] += 1
        ob = E.onboarding_status(c, snaps, st)
        r["rule"] += bool(ob and ob["met"])
        r["graduated"] += _graduated(c, snaps, list(c.monthly.all()), st, today)
        r["left15"] += c.exits.filter(within_free_period=True).exists()
    from crm import absence

    out = sorted(rows.values(), key=lambda r: -r["joined"])
    for r in out:
        r["name"] = absence.name_of(r["user"])
    return {"since": first, "rows": out}


# ------------------------------------------------------------------ aprovações
def request_decision(creator, user, item_code, reason, note=""):
    """A gestora pede às sócias a decisão de manter ou encerrar. Um pedido em aberto por criador."""
    from engage.services import notify

    open_ = ApprovalRequest.objects.filter(creator=creator, kind="manter_encerrar", decided_at__isnull=True).first()
    if open_:
        return open_, False
    ap = ApprovalRequest.objects.create(agency=creator.agency, creator=creator, kind="manter_encerrar", item_code=item_code[:40],
                                        reason=reason[:160], note=note[:2000], requested_by=user)
    for m in Membership.objects.filter(agency=creator.agency, role=Role.ADMIN, active=True):
        notify(user=m.user, kind="aprovacao", url="/gestao/painel/#aprovacoes",
               title=f"Decisão pedida: manter ou encerrar @{creator.username}", body=(note or reason)[:200])
    return ap, True


def decide(ap, user, decision, note=""):
    from engage.services import notify

    if not ap.pending:
        raise PanelError("Este pedido já foi decidido.")
    if decision not in dict(ApprovalRequest.DECISIONS.get(ap.kind, [])):
        raise PanelError("Escolha uma das decisões.")
    ap.decision, ap.decision_note, ap.decided_by, ap.decided_at = decision, note[:2000], user, timezone.now()
    ap.save(update_fields=["decision", "decision_note", "decided_by", "decided_at"])
    if ap.requested_by_id and ap.requested_by_id != user.pk:
        who = f"@{ap.creator.username}" if ap.creator_id else ap.get_kind_display()
        notify(user_id=ap.requested_by_id, kind="aprovacao", url=f"/gestao/creators/{ap.creator_id}/" if ap.creator_id else "/gestao/",
               title=f"As sócias decidiram: {ap.decision_label.lower()} {who}", body=note[:200])
    return ap


def pending_by_creator(creator_ids):
    """Pedidos em aberto por criador, para a fila mostrar "aguardando as sócias"."""
    return {a.creator_id: a for a in ApprovalRequest.objects.filter(creator_id__in=creator_ids, decided_at__isnull=True)}


# ------------------------------------------------------------------ sorteio semanal
def ensure_draw(agency, today=None, rng=None):
    """Sorteia 5 "Enviei" da semana anterior (segunda a domingo), espalhados entre as gestoras: uma de cada por vez,
    em ordem aleatória, até completar 5. Se o sorteio da semana já existe, não sorteia de novo."""
    today = today or timezone.localdate()
    week = week_start(today)
    if SentCheck.objects.filter(agency=agency, week=week).exists():
        return list(SentCheck.objects.filter(agency=agency, week=week).select_related("contact__creator", "manager", "checked_by"))
    rng = rng or random.SystemRandom()
    start = timezone.make_aware(dt.datetime.combine(week - dt.timedelta(days=7), dt.time.min))
    end = timezone.make_aware(dt.datetime.combine(week, dt.time.min))
    pools = {}
    for ct in Contact.objects.filter(creator__agency=agency, sent_at__gte=start, sent_at__lt=end, user__isnull=False):
        pools.setdefault(ct.user_id, []).append(ct)
    for pool in pools.values():
        rng.shuffle(pool)
    order = list(pools)
    rng.shuffle(order)
    picked = []
    while len(picked) < DRAW_SIZE and any(pools.values()):
        for uid in order:
            if pools[uid] and len(picked) < DRAW_SIZE:
                picked.append(pools[uid].pop())
    for ct in picked:
        SentCheck.objects.create(agency=agency, week=week, contact=ct, manager_id=ct.user_id)
    return list(SentCheck.objects.filter(agency=agency, week=week).select_related("contact__creator", "manager", "checked_by"))


def check_sent(sc, user, result, note=""):
    if result not in ("estava", "nao_achei"):
        raise PanelError("Escolha o resultado da conferência.")
    sc.result, sc.note, sc.checked_by, sc.checked_at = result, note[:240], user, timezone.now()
    sc.save(update_fields=["result", "note", "checked_by", "checked_at"])
    return sc


def draw_history(agency, weeks=8):
    rows = {}
    for sc in SentCheck.objects.filter(agency=agency).order_by("-week")[: weeks * DRAW_SIZE]:
        r = rows.setdefault(sc.week, {"week": sc.week, "n": 0, "found": 0, "missing": 0})
        r["n"] += 1
        r["found"] += sc.result == "estava"
        r["missing"] += sc.result == "nao_achei"
    return sorted(rows.values(), key=lambda r: r["week"], reverse=True)


def _risks(agency, today):
    """Lista "Diamante em risco" (passo 4.3): quem tem sinais pelos números ou pela conversa."""
    from .month_items import diamonds_at_risk

    return [{"c": c, "total": r["total"], "labels": r["numbers"] + [s.get_kind_display().lower() for s in r["talk_kinds"]]}
            for c, r in diamonds_at_risk(agency, today)]


# ------------------------------------------------------------------ tudo junto
def overview(agency, today=None):
    today = today or E.tiktok_today()
    local = timezone.localdate()
    return {
        "today": today, "results": result_blocks(agency, today), "funnel": funnel(agency, today), "retention": retention(agency, today),
        "graduation": graduation(agency, today), "base": base_by_level(agency, today), "execution": execution(agency, local),
        "academy": academy(agency, today), "battles": battles(agency, today), "recruitment": recruitment(agency, today),
        "approvals": list(ApprovalRequest.objects.filter(agency=agency, decided_at__isnull=True)
                          .select_related("creator", "requested_by").order_by("requested_at")),
        "decided": list(ApprovalRequest.objects.filter(agency=agency, decided_at__isnull=False)
                        .select_related("creator", "decided_by").order_by("-decided_at")[:10]),
        "draw": ensure_draw(agency, local), "draw_week": week_start(local), "draw_history": draw_history(agency),
        "draw_from": week_start(local) - dt.timedelta(days=7), "draw_to": week_start(local) - dt.timedelta(days=1),
        "risks": _risks(agency, today),
        "campaigns_waiting": _campaigns_waiting(agency),
    }


def _campaigns_waiting(agency):
    """Campanhas novas do TikTok esperando a aprovação das sócias (passo 4.5)."""
    from engage.campaigns import waiting_approval

    return waiting_approval(agency)

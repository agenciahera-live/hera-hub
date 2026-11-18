"""Motor de cálculo: tudo sai dos snapshots.

- Datas de período são dias do TikTok (UTC: 21h–20h59 de Brasília).
- Tier oficial = mês fechado (D5). No mês corrente só existe a barra de progresso.
- Métricas por intervalo = diferença entre snapshots consecutivos do mesmo mês.
"""
import calendar
import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.models import AgencySettings
from core.rls import system_context
from crm.models import Creator, CreatorOnboarding, CreatorStatus, OnboardingItem

from .models import CreatorGroupHistory, CreatorSnapshot, GroupRule, MonthlyResult, TaskResult, TierRule

FIRST_MONTH = "Primeiro Mês"
METRIC_ATTR = {
    "diamonds": lambda s: s.diamonds,
    "hours": lambda s: s.live_seconds / 3600,
    "valid_days": lambda s: s.valid_days,
    "battles": lambda s: s.battles,
    "new_followers": lambda s: s.new_followers,
    "streams": lambda s: s.streams,
}


# ------------------------------------------------------------------ datas
def month_start(d):
    return d.replace(day=1)


def month_end(d):
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


def prev_month(d):
    return month_start(month_start(d) - dt.timedelta(days=1))


def tiktok_today():
    """Data do dia TikTok (UTC)."""
    return timezone.now().astimezone(dt.timezone.utc).date()


# ------------------------------------------------------------------ Tier e grupo
def tier_rules(agency):
    return list(TierRule.objects.filter(agency=agency).order_by("tier"))


def tier_for(diamonds, rules):
    """Maior Tier cujo mínimo foi atingido. Limite inferior inclusivo (40.000 = Tier 2)."""
    t = rules[0].tier if rules else 1
    for r in rules:
        if diamonds >= r.min_diamonds:
            t = r.tier
    return t


def next_tier_rule(tier, rules):
    for r in rules:
        if r.tier == tier + 1:
            return r
    return None


def group_for_tier(tier, groups):
    for g in groups:
        if g.tier_min <= tier <= g.tier_max:
            return g.name
    return groups[-1].name if groups else ""


def official_month(today=None):
    """Mês fechado que vale como oficial: o mês anterior ao corrente (dia TikTok)."""
    return prev_month(today or tiktok_today())


def official_tier(creator, today=None, rules=None):
    """Tier do último mês fechado; sem mês fechado → primeiro Tier (1)."""
    rules = rules if rules is not None else tier_rules(creator.agency)
    mr = MonthlyResult.objects.filter(creator=creator, month__lte=official_month(today)).order_by("-month").first()
    if mr is None:
        return rules[0].tier if rules else 1, None
    return (mr.tier or tier_for(mr.diamonds, rules)), mr


def group_for(creator, today=None, settings_=None, groups=None, rules=None):
    today = today or tiktok_today()
    settings_ = settings_ or AgencySettings.objects.get(agency=creator.agency)
    groups = groups if groups is not None else list(GroupRule.objects.filter(agency=creator.agency))
    days = creator.days_in_agency(today)
    tier, mr = official_tier(creator, today, rules)
    if (days is not None and days <= settings_.first_month_days) or mr is None:
        return FIRST_MONTH
    return group_for_tier(tier, groups)


# ------------------------------------------------------------------ snapshots
def snapshots_by_month(snaps):
    by = defaultdict(list)
    for s in snaps:
        by[month_start(s.period_start)].append(s)
    for m in by:
        by[m].sort(key=lambda s: s.period_end)
    return by


def latest_in_month(creator, month):
    return (
        CreatorSnapshot.objects.filter(creator=creator, period_start__gte=month, period_start__lte=month_end(month))
        .order_by("-period_end").first()
    )


def cumulative_until(snaps, date, metric):
    """Soma acumulada da métrica desde sempre até `date` (último snapshot ≤ date em cada mês)."""
    total = 0
    for m, lst in snapshots_by_month(snaps).items():
        if m > date:
            continue
        cands = [s for s in lst if s.period_end <= date]
        if cands:
            total += METRIC_ATTR[metric](cands[-1])
    return total


@dataclass
class Interval:
    start: dt.date
    end: dt.date
    diamonds: int
    live_seconds: int
    valid_days: int
    streams: int
    battles: int
    new_fans: int = 0  # novos membros do fã-clube (0 quando a exportação não traz a coluna)

    @property
    def days(self):
        return (self.end - self.start).days + 1

    @property
    def hours(self):
        return self.live_seconds / 3600

    @property
    def had_live(self):
        return self.live_seconds > 0 or self.streams > 0

    @property
    def diamonds_per_day(self):
        return self.diamonds / self.days if self.days else 0


def intervals(snaps):
    """Diferença entre snapshots consecutivos do mesmo mês. O 1º do mês compara com zero.

    Com importação diária, cada intervalo é um dia; com semanal, uma semana.
    """
    out = []
    for m, lst in sorted(snapshots_by_month(snaps).items()):
        prev = None
        for s in lst:
            if prev is None:
                start = s.period_start
                d = (s.diamonds, s.live_seconds, s.valid_days, s.streams, s.battles, s.new_fans or 0)
            else:
                start = prev.period_end + dt.timedelta(days=1)
                d = (s.diamonds - prev.diamonds, s.live_seconds - prev.live_seconds, s.valid_days - prev.valid_days,
                     s.streams - prev.streams, s.battles - prev.battles, (s.new_fans or 0) - (prev.new_fans or 0))
            if s.period_end >= start:
                out.append(Interval(start, s.period_end, *d))
            prev = s
    return out


def weekly_intervals(snaps):
    """Intervalos somados por semana (segunda a domingo), sem cruzar a virada do mês.

    É o que as telas "semana a semana" mostram. Com importação diária, cada semana soma os dias;
    com importação semanal, o intervalo inteiro cai na semana em que termina.
    """
    weeks = {}
    for iv in intervals(snaps):
        key = (month_start(iv.end), iv.end - dt.timedelta(days=iv.end.weekday()))
        w = weeks.get(key)
        if w is None:
            weeks[key] = Interval(iv.start, iv.end, iv.diamonds, iv.live_seconds, iv.valid_days, iv.streams, iv.battles, iv.new_fans)
        else:
            w.end = iv.end
            w.new_fans += iv.new_fans
            w.diamonds += iv.diamonds
            w.live_seconds += iv.live_seconds
            w.valid_days += iv.valid_days
            w.streams += iv.streams
            w.battles += iv.battles
    return [weeks[k] for k in sorted(weeks)]


def days_without_live(snaps):
    """Dias desde o fim do último intervalo com LIVE (limitado pela frequência de importação).
    None se nunca houve LIVE. 0 se o último intervalo teve LIVE."""
    ivs = intervals(snaps)
    if not ivs:
        return None
    last_end = ivs[-1].end
    for iv in reversed(ivs):
        if iv.had_live:
            return (last_end - iv.end).days
    return (last_end - ivs[0].start).days + 1


# ------------------------------------------------------------------ metas e ritmo
@dataclass
class Pace:
    metric: str
    value: float
    target: float
    target_source: str  # tiktok | padrao
    elapsed_days: int
    remaining_days: int
    month_days: int
    avg_per_day: float
    needed_per_day: float
    forecast: float
    on_track: bool

    @property
    def pct(self):
        return (self.value / self.target) if self.target else 0

    @property
    def missing(self):
        return max(self.target - self.value, 0)


def tiktok_target(value, pct):
    """Meta implícita do TikTok: valor ÷ % alcançada."""
    if pct is None or pct <= 0 or value <= 0:
        return None
    return float(Decimal(value) / Decimal(pct))


def compute_pace(value, target, period_start, period_end, metric="diamonds", source="tiktok"):
    month_days = calendar.monthrange(period_start.year, period_start.month)[1]
    elapsed = (period_end - month_start(period_start)).days + 1
    remaining = max(month_days - elapsed, 0)
    avg = value / elapsed if elapsed else 0
    missing = max(target - value, 0)
    if remaining > 0:
        needed = missing / remaining
    else:
        needed = 0.0 if missing == 0 else float("inf")
    on_track = value >= target or (remaining > 0 and avg >= needed)
    forecast = value + avg * remaining
    return Pace(metric, float(value), float(target), source, elapsed, remaining, month_days, avg, needed, forecast, on_track)


def targets_for(creator, snap, rules=None, settings_=None):
    """Referência por métrica: TikTok (derivada) > padrão Hera. A gestão não define número para o criador."""
    rules = rules if rules is not None else tier_rules(creator.agency)
    settings_ = settings_ or AgencySettings.objects.get(agency=creator.agency)
    out = {}
    for metric, value, pct in [
        ("diamonds", snap.diamonds, snap.pct_diamonds),
        ("hours", snap.live_seconds / 3600, snap.pct_hours),
        ("valid_days", snap.valid_days, snap.pct_valid_days),
    ]:
        t = tiktok_target(value, pct)
        if t:
            out[metric] = (round(t, 1 if metric == "hours" else 0), "tiktok")
            continue
        if metric == "diamonds":
            tier, _ = official_tier(creator, rules=rules)
            nxt = next_tier_rule(tier, rules)
            out[metric] = (float(nxt.min_diamonds if nxt else rules[-1].min_diamonds), "padrao")
        elif metric == "hours":
            out[metric] = (float(settings_.monthly_min_hours), "padrao")
        else:
            out[metric] = (float(settings_.monthly_min_valid_days), "padrao")
    return out


def month_paces(creator, snap, **kw):
    targets = targets_for(creator, snap, **kw)
    values = {"diamonds": snap.diamonds, "hours": snap.live_seconds / 3600, "valid_days": snap.valid_days}
    return {m: compute_pace(values[m], t, snap.period_start, snap.period_end, m, src) for m, (t, src) in targets.items()}


# ------------------------------------------------------------------ onboarding
def onboarding_status(creator, snaps=None, settings_=None):
    """Meta de onboarding: X dias válidos e Y horas nos primeiros N dias de casa."""
    settings_ = settings_ or AgencySettings.objects.get(agency=creator.agency)
    if not creator.joined_at:
        return None
    snaps = snaps if snaps is not None else list(creator.snapshots.all())
    start = creator.joined_at.astimezone(dt.timezone.utc).date()
    end = start + dt.timedelta(days=settings_.onboarding_window_days - 1)
    last_date = max((s.period_end for s in snaps), default=None)
    upto = min(end, last_date) if last_date else None
    vd = cumulative_until(snaps, upto, "valid_days") if upto else 0
    hours = cumulative_until(snaps, upto, "hours") if upto else 0
    today = last_date or tiktok_today()
    day_n = (today - start).days + 1
    met = vd >= settings_.onboarding_valid_days and hours >= settings_.onboarding_hours
    remaining_days = max((end - today).days, 0)
    need_days = max(settings_.onboarding_valid_days - vd, 0)
    need_hours = max(settings_.onboarding_hours - hours, 0)
    # Regra do Playbook: no Dia 10 (ou depois) quem ainda não bateu a meta entra em risco.
    at_risk = (not met) and day_n >= 10 and today <= end
    return {
        "start": start, "end": end, "day": day_n, "valid_days": vd, "hours": hours, "met": met,
        "remaining_days": remaining_days, "need_days": need_days, "need_hours": need_hours,
        "active": day_n <= settings_.onboarding_window_days + 1, "at_risk": at_risk,
        "failed": (not met) and today > end,
    }


# ------------------------------------------------------------------ graduação
def graduation_status(creator, snap, settings_, today=None):
    """Graduação (regra do TikTok): X diamantes em UM mês, dentro dos primeiros N dias de casa.

    Conta os diamantes do mês corrente (snapshot acumulado do mês), nunca a soma desde a entrada.
    Devolve None para quem está fora da janela (ou sem data de entrada)."""
    today = today or tiktok_today()
    days = creator.days_in_agency(today)
    if days is None or days > settings_.graduation_window_days:
        return None
    start = creator.joined_at.astimezone(dt.timezone.utc).date()
    diamonds = snap.diamonds if snap and month_start(snap.period_start) == month_start(today) else 0
    target = settings_.graduation_diamonds
    return {
        "day": days, "window_end": start + dt.timedelta(days=settings_.graduation_window_days - 1),
        "diamonds": diamonds, "target": target, "missing": max(target - diamonds, 0), "graduated": diamonds >= target,
    }


def _auto_done(rule, totals, ob):
    if not rule:
        return False
    if rule == "meta_onboarding":
        return bool(ob and ob["met"])
    key, n = rule.split(">=")
    return totals.get(key, 0) >= int(n)


def update_onboarding(creator, snaps, settings_):
    items = OnboardingItem.objects.filter(agency=creator.agency)
    if not items:
        return
    totals = {"streams": cumulative_until(snaps, dt.date.max, "streams"), "battles": cumulative_until(snaps, dt.date.max, "battles")}
    ob = onboarding_status(creator, snaps, settings_)
    now = timezone.now()
    existing = {co.item_id: co for co in CreatorOnboarding.objects.filter(creator=creator)}
    for it in items:
        co = existing.get(it.id)
        if co is None:
            co = CreatorOnboarding.objects.create(creator=creator, item=it)
        if not co.done and _auto_done(it.auto_rule, totals, ob):
            co.done, co.auto, co.done_at = True, True, now
            co.save()


# ------------------------------------------------------------------ recálculo
def _monthly_results(creator, snaps, task_by_month, rules):
    by = snapshots_by_month(snaps)
    results = {}
    # 1) colunas "mês passado" de qualquer snapshot
    for m, lst in by.items():
        s = lst[-1]
        if s.lm_diamonds is not None:
            pm = prev_month(m)
            results.setdefault(pm, ("last_month", s.lm_diamonds, s.lm_live_seconds or 0, s.lm_valid_days or 0, s.lm_streams, None))
    # 2) snapshot que cobre o mês inteiro
    for m, lst in by.items():
        s = lst[-1]
        if s.period_end == month_end(m):
            results[m] = ("backstage", s.diamonds, s.live_seconds, s.valid_days, s.streams, s.battles)
    # 3) Task (fechamento oficial)
    for m, t in task_by_month.items():
        results[m] = ("task", t.diamonds, int(float(t.live_hours) * 3600), t.valid_days, None, None)
    for m, (src, dia, sec, vd, streams, battles) in results.items():
        MonthlyResult.objects.update_or_create(
            creator=creator, month=m,
            defaults={"source": src, "diamonds": dia, "live_seconds": sec, "valid_days": vd,
                      "streams": streams, "battles": battles, "tier": tier_for(dia, rules)},
        )


def _update_group(creator, today, settings_, groups, rules):
    from engage.models import CommunityProfile
    from engage.services import notify

    gname = group_for(creator, today, settings_, groups, rules)
    current = creator.group_history.filter(until__isnull=True).first()
    if current and current.group_name == gname:
        return gname
    if current:
        current.until = today
        current.save(update_fields=["until"])
    reason = "entrada" if current is None else ("fim do Primeiro Mês" if current.group_name == FIRST_MONTH else "fechamento do mês")
    CreatorGroupHistory.objects.create(creator=creator, group_name=gname, since=today, reason=reason)
    if current is not None:
        if creator.user_id:
            notify(user_id=creator.user_id, kind="grupo", title=f"Você agora faz parte do grupo {gname}! 💜", url="/")
        mgr = creator.current_manager()
        if mgr:
            notify(user=mgr, kind="grupo", title=f"@{creator.username} mudou para o grupo {gname}", url=f"/gestao/creators/{creator.pk}/")
    tier, _ = official_tier(creator, today, rules)
    CommunityProfile.objects.filter(creator=creator).update(tier=tier)
    return gname


def ensure_profile(creator, tier):
    from engage.models import CommunityProfile

    CommunityProfile.objects.update_or_create(
        creator=creator,
        defaults={"agency": creator.agency, "public_name": creator.first_name, "username": creator.username, "tier": tier},
    )


@transaction.atomic
def recalculate(agency, creator_ids=None, today=None):
    """Recalcula mês fechado, Tier, grupo, onboarding e rankings. Roda como sistema."""
    with system_context():
        today = today or tiktok_today()
        settings_ = AgencySettings.objects.get(agency=agency)
        rules = tier_rules(agency)
        groups = list(GroupRule.objects.filter(agency=agency))
        qs = Creator.objects.filter(agency=agency).exclude(status=CreatorStatus.ANONIMIZADO)
        if creator_ids is not None:
            qs = qs.filter(pk__in=creator_ids)
        for c in qs:
            snaps = list(c.snapshots.all())
            tasks = {t.month: t for t in TaskResult.objects.filter(creator=c)}
            _monthly_results(c, snaps, tasks, rules)
            if snaps:
                first = next((iv for iv in intervals(snaps) if iv.had_live), None)
                if first and c.first_live_at != first.start:
                    c.first_live_at = max(first.start, c.joined_at.date() if c.joined_at else first.start)
                    c.save(update_fields=["first_live_at"])
            tier, _ = official_tier(c, today, rules)
            ensure_profile(c, tier)
            if c.status not in (CreatorStatus.SAIU,):
                _update_group(c, today, settings_, groups, rules)
                days = c.days_in_agency(today)
                if days is not None and days <= 45:
                    update_onboarding(c, snaps, settings_)
        from engage.services import recompute_standings

        recompute_standings(agency, today=today)

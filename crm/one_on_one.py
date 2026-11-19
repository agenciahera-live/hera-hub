"""1:1 com o modelo novo (etapa 4, passo 4.2; visão, "Template do registro de 1:1").

- Cabeçalho: data, canal e quem conduziu. Bloco 1 (performance) preenchido pelo sistema; blocos 2 a 5; plano com 2 a 3
  ações e quem faz; próximo 1:1 marcado; anotações.
- Print da conversa (decisão da Mariana de 19/11/2026): o app não recebe a imagem. A gestora guarda o print no drive
  dela e só marca no app que guardou. Sem essa marca, o 1:1 não conta como completo.
- Frequência: 1:1 todo mês para os criadores Diamante e para quem tem potencial de graduação. Só conta 1:1 completo
  ("sem registro, o 1:1 não conta").
O registro do 1:1 fica só na gestão; o criador nunca vê.
"""
import datetime as dt

from django.utils import timezone

from data import engine as E

MONTHLY_DAYS = 30  # visão: aviso ao passar de 30 dias sem 1:1


def diamond_min_tier(agency):
    """Tier a partir do qual o criador está no grupo Diamante (o último grupo das regras)."""
    from data.models import GroupRule

    last = GroupRule.objects.filter(agency=agency).order_by("-order").first()
    return last.tier_min if last else 5


def monthly_reason(creator, tier, snaps, settings_, today, diamond_tier, monthly=None):
    """Por que este criador tem 1:1 todo mês ("grupo Diamante", "potencial de graduação") ou "" se não tem."""
    from data import phases

    if (tier or 1) >= diamond_tier:
        return "grupo Diamante"
    r = phases.graduation_radar_row(creator, snaps, settings_, today, monthly=monthly)
    return "potencial de graduação" if r and r.potential else ""


def last_complete(creator):
    for o in creator.one_on_ones.prefetch_related("actions").all():
        if o.complete:
            return o
    return None


def _snap_on_or_before(snaps, month, day):
    cands = [s for s in snaps if s.period_start == month and s.period_end.day <= day]
    return max(cands, key=lambda s: s.period_end) if cands else None


def _fmt(n):
    return f"{int(n):,}".replace(",", ".")


def _h(hours):
    return f"{hours:.1f}".replace(".", ",") + "h"


def performance_text(creator, today=None):
    """Bloco 1 do 1:1: os números do mês até ontem, comparados ao mesmo ponto do mês passado, e o mês passado fechado.

    A média de espectadores, que a visão pede, só existe na leitura detalhada por criador, que ainda não chega."""
    from data.models import MonthlyResult

    today = today or E.tiktok_today()
    snaps = list(creator.snapshots.all())
    m0, pm = E.month_start(today), E.prev_month(today)
    cur = [s for s in snaps if s.period_start == m0]
    if not cur:
        return "Ainda sem números deste mês."
    s = max(cur, key=lambda x: x.period_end)
    parts = [f"Até {s.period_end:%d/%m}: {_fmt(s.diamonds)} diamantes, {_h(s.hours)} de LIVE, {s.valid_days} dias válidos e "
             f"{s.battles} batalhas."]
    prev = _snap_on_or_before(snaps, pm, s.period_end.day)
    if prev:
        diff = (s.diamonds / prev.diamonds - 1) * 100 if prev.diamonds else None
        parts.append(f"No mesmo ponto do mês passado (até {prev.period_end:%d/%m}): {_fmt(prev.diamonds)} diamantes, {_h(prev.hours)}, "
                     f"{prev.valid_days} dias válidos e {prev.battles} batalhas" + (f" ({diff:+.0f}% em diamantes)." if diff is not None else "."))
    last = MonthlyResult.objects.filter(creator=creator, month=pm).first()
    if last:
        parts.append(f"Mês passado fechado: {_fmt(last.diamonds)} diamantes, {_h(last.live_seconds / 3600)}, {last.valid_days} dias válidos"
                     + (f", Tier {last.tier}." if last.tier else "."))
    return " ".join(parts)


def agenda(creators, agency, today=None):
    """Tela 1:1: quem precisa de 1:1 todo mês (com o último completo e o próximo marcado), os marcados e os atrasados."""
    from core.models import AgencySettings
    from data.models import MonthlyResult

    today = today or timezone.localdate()
    st = AgencySettings.objects.get(agency=agency)
    dtier = diamond_min_tier(agency)
    pm = E.prev_month(E.tiktok_today())
    cs = list(creators.prefetch_related("snapshots", "monthly", "one_on_ones__actions", "one_on_ones__conducted_by"))
    tiers = {m.creator_id: m.tier or 1 for m in MonthlyResult.objects.filter(creator__in=[c.pk for c in cs], month=pm)}
    monthly, scheduled, late = [], [], []
    for c in cs:
        ones = list(c.one_on_ones.all())
        latest = ones[0] if ones else None
        done = next((o for o in ones if o.complete), None)
        next_date = latest.b7_next_date if latest else None
        reason = monthly_reason(c, tiers.get(c.pk), list(c.snapshots.all()), st, E.tiktok_today(), dtier, monthly=list(c.monthly.all()))
        row = {"c": c, "reason": reason, "last": done, "latest": latest, "next": next_date,
               "days": (today - done.date).days if done else None}
        if reason:
            row["status"] = "nunca" if not done else ("atrasado" if row["days"] >= MONTHLY_DAYS else "em_dia")
            monthly.append(row)
        if next_date and next_date >= today:
            scheduled.append(row)
        elif next_date and next_date < today:
            late.append(row)
    order = {"nunca": 0, "atrasado": 1, "em_dia": 2}
    monthly.sort(key=lambda r: (order[r["status"]], -(r["days"] or 9999), r["c"].username))
    scheduled.sort(key=lambda r: (r["next"], r["c"].username))
    late.sort(key=lambda r: (r["next"], r["c"].username))
    return {"monthly": monthly, "scheduled": scheduled, "late": late, "days": MONTHLY_DAYS,
            "pending": sum(1 for r in monthly if r["status"] != "em_dia")}


def queue_items(ctx):
    """Fila do dia: "1:1 do mês" para Diamante e potencial de graduação sem 1:1 completo há 30 dias ou mais.

    Não entra quem já tem 1:1 marcado para hoje ou depois, nem quem tem 1:1 atrasado (esse já tem o próprio item)."""
    from web.services import QueueItem

    today = ctx["today"]
    if today.weekday() == 6:
        return []  # domingo: só suporte
    dtier = diamond_min_tier(ctx["agency"])
    out = []
    for pk, d in ctx["info"].items():
        c = d["c"]
        reason = monthly_reason(c, d["tier"], d["snaps"], ctx["settings"], today, dtier)
        if not reason:
            continue
        ones = list(c.one_on_ones.prefetch_related("actions").all())
        latest = ones[0] if ones else None
        if latest and latest.b7_next_date:
            continue  # marcado (no futuro) ou atrasado (item "1a1_atrasado")
        done = next((o for o in ones if o.complete), None)
        days = (today - done.date).days if done else None
        if done and days < MONTHLY_DAYS:
            continue
        detail = (f"{reason.capitalize()}: último 1:1 completo em {done.date:%d/%m} ({days} dias)." if done
                  else f"{reason.capitalize()}: nenhum 1:1 completo registrado.")
        out.append(QueueItem(c, "1a1_mes", 3, "1:1 do mês", detail + " Combine o 1:1 e registre na aba 1:1 da ficha."))
    return out

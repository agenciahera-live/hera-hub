"""Meu progresso: a tela inicial do app do criador (visão, "Meu progresso: a tela inicial do app").

Regras desta tela:
- Tudo sai de "Dados do criador" (fonte única): a tela diz até que dia os dados vão e quando foram atualizados.
- No app o criador vê "Meu nível" e "Próximo nível" (o Tier da gestão). O nível vale pelo mês fechado; no mês
  corrente existe só a barra até o próximo nível.
- Nunca aparece ranking, comparação com outro criador, "meta" nem "relatório". A tela nunca pede horas, dias ou
  horário: mostra fatos e, quando projeta, diz que é estimativa.
- O que é regra do TikTok (14 dias, graduação) aparece com o selo "regra do TikTok".

O simulador ("Onde posso chegar") e o Indique e ganhe entram nas etapas 5 e 4 da visão.
"""
from django.utils import timezone

from core.models import AgencySettings
from data import engine as E
from data import phases
from data.models import MonthlyResult
from engage.models import Announcement, Survey
from engage.services import creator_facts, fmt_hours, fmt_int, matches_audience

ESTIMATE_NOTE = "Estimativa pelo seu histórico, não é garantia."
MIN_DAYS_FOR_FORECAST = 3  # nos dois primeiros dias do mês a conta do ritmo ainda não diz nada


def round_estimate(value):
    """ "Em torno de X": arredonda para não parecer conta exata."""
    value = max(float(value or 0), 0)
    step = 10 if value < 1000 else 100 if value < 10000 else 1000
    return int(round(value / step) * step)


def level_info(creator, snap, rules, today):
    """Meu nível (mês fechado) e a barra até o próximo nível com os diamantes do mês corrente."""
    tier, mr = E.official_tier(creator, today, rules)
    nxt = E.next_tier_rule(tier, rules)
    diamonds = snap.diamonds if snap else 0
    out = {"level": tier, "level_month": mr.month if mr else None, "next": nxt, "diamonds": diamonds, "top": nxt is None}
    if nxt:
        out.update({"pct": min(diamonds / nxt.min_diamonds, 1) if nxt.min_diamonds else 1,
                    "missing": max(nxt.min_diamonds - diamonds, 0), "reached": diamonds >= nxt.min_diamonds})
    return out


def level_table(rules):
    """Faixa de diamantes de cada nível, como está em Configurações (nada fixo na tela)."""
    out = []
    for n, r in enumerate(rules):
        upper = rules[n + 1].min_diamonds - 1 if n + 1 < len(rules) else None
        out.append({"level": r.tier, "min": r.min_diamonds, "max": upper})
    return out


def month_phrase(level, snap, pace, last_closed, near_pct):
    """A frase do mês: uma linha só, escolhida pelos números (as três versões da visão, nesta ordem).

    Nunca "você vai subir de nível", nunca um pedido de horas, de dias ou de horário."""
    if not snap:
        return None
    nxt = level.get("next")
    if nxt and level["reached"]:
        return {"kind": "chegou", "text": f"Você já passou da marca do Nível {nxt.tier} neste mês. O nível muda no fechamento do mês."}
    if nxt and pace and pace.elapsed_days >= MIN_DAYS_FOR_FORECAST and pace.forecast >= nxt.min_diamonds:
        return {"kind": "no_ritmo", "text": f"No seu ritmo, você chega ao Nível {nxt.tier} este mês. Parabéns pela constância!", "estimate": True}
    if nxt and snap.diamonds >= nxt.min_diamonds * near_pct / 100:
        return {"kind": "perto", "text": f"Você está a {fmt_int(level['missing'])} 💎 do Nível {nxt.tier}. Dá pra chegar."}
    # abaixo do mês passado: o fato e um convite. Primeiro cai a LIVE, depois o diamante: olha horas, depois dias.
    if last_closed and pace:
        share = pace.elapsed_days / pace.month_days  # mesmo ponto do mês passado
        if last_closed.live_seconds and snap.live_seconds < last_closed.live_seconds * share:
            return {"kind": "abaixo", "text": "Suas horas de LIVE estão abaixo do mês passado. Quer ver a aula sobre rotina?", "lesson": True}
        if last_closed.valid_days and snap.valid_days < last_closed.valid_days * share:
            return {"kind": "abaixo", "text": "Seus dias de LIVE estão abaixo do mês passado. Quer ver a aula sobre rotina?", "lesson": True}
    return None


def weeks_of_month(snaps, today):
    """Semanas do mês corrente, com a mais fraca destacada e o motivo ao lado (nunca só o número).

    A semana em andamento não é comparada: ainda não terminou."""
    m0 = E.month_start(today)
    weeks = [iv for iv in E.weekly_intervals(snaps) if iv.start >= m0]
    if not weeks:
        return []
    last_date = max(s.period_end for s in snaps)
    top = max([w.diamonds for w in weeks] + [1])
    rows = []
    for w in weeks:
        closed = w.end.weekday() == 6 or w.end == E.month_end(m0) or w.end < last_date
        rows.append({"iv": w, "pct": w.diamonds / top, "closed": closed, "weak": False, "note": ""})
    done = [r for r in rows if r["closed"]]
    if len(done) >= 2:
        weak = min(done, key=lambda r: r["iv"].diamonds)
        best = max(done, key=lambda r: r["iv"].diamonds)
        if weak is not best and weak["iv"].diamonds < best["iv"].diamonds:
            w, b = weak["iv"], best["iv"]
            weak["weak"] = True
            if not w.had_live:
                weak["note"] = "Semana sem LIVE."
            elif w.valid_days < b.valid_days:
                weak["note"] = "Semana mais leve: menos dias de LIVE que na sua melhor semana."
            elif w.hours < b.hours:
                weak["note"] = "Semana mais leve: menos tempo de LIVE que na sua melhor semana."
            else:
                weak["note"] = "Mesma rotina e menos diamantes: vale olhar a interação e as batalhas."
    return list(reversed(rows))  # a mais recente primeiro


def months_since_entry(creator, today, limit=12):
    """Meses fechados desde a entrada, com diamantes e nível de cada um, para o criador ver a própria evolução."""
    months = [m for m in MonthlyResult.objects.filter(creator=creator, month__lt=E.month_start(today)).order_by("-month")[:limit]
              if m.diamonds or m.live_seconds]
    best = max(months, key=lambda m: m.diamonds, default=None)
    top = max([m.diamonds for m in months] + [1])
    return [{"m": m, "pct": m.diamonds / top, "best": best is not None and m.pk == best.pk and len(months) > 1} for m in months]


def graduation_block(creator, snaps, settings_, today, phase):
    """Graduação (regra do TikTok): destaque do criador depois do D30, enquanto a janela estiver aberta."""
    if phase.base != "graduacao":
        return None
    row = phases.graduation_radar_row(creator, snaps, settings_, today)
    if row is None:
        return None
    m0 = E.month_start(today)
    months_left = (row.window_end.year - m0.year) * 12 + (row.window_end.month - m0.month) + 1
    return {"diamonds": row.diamonds, "target": row.target, "missing": row.missing, "pct": min(row.diamonds / row.target, 1) if row.target else 0,
            "per_day": row.avg_per_day, "window_end": row.window_end, "months_left": max(months_left, 1), "reached": row.diamonds >= row.target,
            "done_before": row.graduations}


def next_step(ob, ever_live):
    """Próximo passo de quem está nos 14 dias: a 1ª LIVE ou o que falta da contagem do TikTok (fato, não pedido)."""
    if not ever_live:
        return "Abrir a sua primeira LIVE. As primeiras aulas mostram como."
    parts = []
    if ob["need_days"]:
        parts.append(f"{ob['need_days']} dia{'s' if ob['need_days'] > 1 else ''} válido{'s' if ob['need_days'] > 1 else ''}")
    if ob["need_hours"] > 0:
        parts.append(f"{fmt_hours(ob['need_hours'])}h de LIVE")
    return "Para completar a contagem do TikTok: " + " e ".join(parts) + "." if parts else "A contagem do TikTok está completa. 🎉"


def campaign_of_the_moment(campaigns):
    """Uma campanha só. Por enquanto, a que fecha primeiro entre as que valem para o criador; a escolha por
    encaixe, chance, prêmio e esforço entra quando a leitura de campanhas existir (visão, "Uma campanha de cada vez")."""
    return min(campaigns, key=lambda x: (x["c"].end, x["c"].pk), default=None)


def my_progress(creator):
    from engage import academy

    from .services import data_freshness, daily_tip, month_name, visible_campaigns

    today = E.tiktok_today()
    settings_ = AgencySettings.objects.get(agency=creator.agency)
    rules = E.tier_rules(creator.agency)
    facts = creator_facts(creator)
    snaps = list(creator.snapshots.all())
    snap = E.latest_in_month(creator, E.month_start(today))
    phase = phases.phase_for(creator, snaps, settings_, today)
    ob = E.onboarding_status(creator, snaps, settings_)
    counting = phase.base in ("chegada", "novato")  # D1 a D14 sem fechar a regra: o topo é a contagem do TikTok
    ever_live = any(iv.had_live for iv in E.intervals(snaps))
    level = level_info(creator, snap, rules, today)
    pace = E.compute_pace(snap.diamonds, level["next"].min_diamonds if level["next"] else max(snap.diamonds, 1),
                          snap.period_start, snap.period_end) if snap else None
    last_closed = MonthlyResult.objects.filter(creator=creator, month=E.prev_month(today)).first()
    # aula recomendada (Hera Academy): escolha da gestora > ponto mais fraco do mês > próxima aula aberta
    rec = academy.recommended(creator, snap=snap, today=today, counting=counting)
    lesson = rec["lesson"] if rec else None
    phrase = None if counting else month_phrase(level, snap, pace, last_closed, settings_.near_tier_pct)
    forecast = None
    if not counting and pace and snap.diamonds > 0 and pace.elapsed_days >= MIN_DAYS_FOR_FORECAST and pace.remaining_days > 0:
        forecast = round_estimate(pace.forecast)
    survey = None
    for s in Survey.objects.filter(agency=creator.agency).exclude(completions__user=creator.user_id):
        if s.is_open() and matches_audience(s, facts):
            survey = s
            break
    pinned = [a for a in Announcement.objects.filter(agency=creator.agency, pinned=True, publish_at__lte=timezone.now()) if matches_audience(a, facts)][:1]
    return {
        "creator": creator, "today": today, "month_label": month_name(today), "snap": snap, "settings": settings_,
        "phase": phase, "counting": counting, "onboarding": ob, "ever_live": ever_live,
        "next_step": next_step(ob, ever_live) if counting else "",
        "closed_rule": bool(ob and ob["met"] and ob["active"]),
        "level": level, "group": facts["group"], "phrase": phrase, "forecast": forecast, "estimate_note": ESTIMATE_NOTE,
        "graduation": graduation_block(creator, snaps, settings_, today, phase),
        "campaign": campaign_of_the_moment(visible_campaigns(creator, facts, today)),
        "weeks": weeks_of_month(snaps, today), "lesson": lesson, "lesson_why": rec["why"] if rec else "", "months": months_since_entry(creator, today),
        "data_until": snap.period_end if snap else max((s.period_end for s in snaps), default=None),
        "updated_at": data_freshness(creator.agency), "survey": survey, "pinned": pinned,
        "tip": daily_tip(creator.agency, facts, today),
    }

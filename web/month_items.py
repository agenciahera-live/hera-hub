"""Itens do mês na fila do dia (etapa 4, passo 4.3; Playbook, "Agenda do mês" e "Sinais de risco dos criadores Diamante").

- Resumo do mês (dias 1 a 7): primeiro quem foi menos constante (dias 1 a 5), depois os constantes (dias 6 e 7).
  "Menos constante" = menos dias válidos no mês que fechou do que no anterior (decisão da Mariana de 19/11/2026).
  Mensagem de parabéns ou de apoio; quem fez mais LIVE e recebeu menos diamantes recebe a 2.5 (APO-05).
  Sem números no WhatsApp: o resumo fica no app.
- Nível novo (dias 1 a 7): quem subiu de Tier no mês que fechou. Entra no lugar do resumo do mês.
- Quase lá (última semana do mês): perto do próximo nível ou da graduação (o mesmo corte de "perto", 85%) vira mensagem
  com prioridade. "Perto de prêmio de campanha" é o item `campanha_posicao` (engage/campaigns.py, passo 4.5), que na
  última semana do mês também sobe para a prioridade 1.
- Módulo concluído: terminou todas as aulas de um módulo da Hera Academy nos últimos 3 dias.
- Sinais de risco dos criadores Diamante: pelos números e pela conversa (marcados na ficha, valem 30 dias). Um sinal:
  aviso na ficha. Dois ou mais: conversa em até 48 horas (prioridade 1) e aviso às sócias (rotina diária).

As mensagens novas são provisórias até a revisão da Mariana (engage/playbook.py, "Itens do mês").
"""
import datetime as dt

from django.utils import timezone

from data import engine as E
from data.states import weeks_readable  # a regra mora com o estado da semana; vale para a fila e para os sinais

SUMMARY_DAYS = 7  # dias 1 a 7
LESS_CONSTANT_UNTIL = 5  # dias 1 a 5: só quem foi menos constante
LAST_WEEK_DAYS = 7  # "Quase lá": os últimos 7 dias do mês
MODULE_RECENT_DAYS = 3
SUMMARY_CODES = ("MES-PARABENS", "MES-APOIO", "APO-05", "NIVEL-NOVO")


def _fmt(n):
    return f"{int(round(n)):,}".replace(",", ".")


def _sent_since(contacts, codes, since):
    return any(x.template_code in codes and timezone.localtime(x.sent_at).date() >= since for x in contacts)


def in_last_week(today):
    return today >= E.month_end(today) - dt.timedelta(days=LAST_WEEK_DAYS - 1)


# ------------------------------------------------------------------ resumo do mês e nível novo
def _closed_months(ids, today):
    from data.models import MonthlyResult

    pm = E.prev_month(today)
    ppm = E.prev_month(pm)
    rows = MonthlyResult.objects.filter(creator_id__in=ids, month__in=[pm, ppm])
    last = {r.creator_id: r for r in rows if r.month == pm}
    before = {r.creator_id: r for r in rows if r.month == ppm}
    return last, before


def summary_items(ctx):
    """Resumo do mês e nível novo, dias 1 a 7. Uma mensagem por criador no período (a primeira que for enviada)."""
    from .services import QueueItem

    today = ctx["today"]
    if today.day > SUMMARY_DAYS:
        return []
    m0 = E.month_start(today)
    window = ctx["settings"].onboarding_window_days + 1
    last, before = _closed_months(ctx["ids"], today)
    out = []
    for pk, d in ctx["info"].items():
        c, cur = d["c"], last.get(pk)
        if cur is None or not (cur.live_seconds or cur.valid_days):
            continue  # sem LIVE no mês que fechou: quem cuida é a régua de quem está sem LIVE
        if d["day"] is not None and d["day"] <= window:
            continue  # nos 14 dias, o roteiro do onboarding cuida
        if _sent_since(d["contacts"], SUMMARY_CODES, m0):
            continue
        prev = before.get(pk)
        if prev and (cur.tier or 1) > (prev.tier or 1):
            out.append(QueueItem(c, "nivel_novo", 2, f"Nível novo: fechou o mês no Tier {cur.tier}",
                                 f"Subiu do Tier {prev.tier or 1} para o Tier {cur.tier} no mês que fechou. Parabéns no grupo individual.",
                                 "NIVEL-NOVO", vars={"nivel_novo": cur.tier}))
            continue
        less = bool(prev and cur.valid_days < prev.valid_days)
        if not less and today.day <= LESS_CONSTANT_UNTIL:
            continue  # os constantes ficam para os dias 6 e 7
        more_live = prev and (cur.live_seconds > prev.live_seconds or cur.valid_days > prev.valid_days
                              or (cur.battles or 0) > (prev.battles or 0))
        if prev and more_live and cur.diamonds < prev.diamonds:
            tpl, why = "APO-05", "fez mais LIVE e recebeu menos diamantes: mensagem 2.5 (antes, veja onde foi a queda no Backstage)"
        elif less:
            tpl, why = "MES-APOIO", f"menos dias válidos que no mês anterior ({cur.valid_days} contra {prev.valid_days}): mensagem de apoio"
        else:
            tpl, why = "MES-PARABENS", "manteve a constância: mensagem de parabéns"
        out.append(QueueItem(c, "resumo_mes", 2 if less else 3, "Resumo do mês", f"Mês que fechou: {why}. O número fica no app.", tpl))
    return out


# ------------------------------------------------------------------ quase lá
def almost_items(ctx):
    """Última semana do mês: perto do próximo nível ou da graduação vira mensagem com prioridade (uma por semana)."""
    from .services import QueueItem

    today = ctx["today"]
    if not in_last_week(today):
        return []
    st, rules = ctx["settings"], E.tier_rules(ctx["agency"])
    end = E.month_end(today)
    start = end - dt.timedelta(days=LAST_WEEK_DAYS - 1)
    out = []
    for pk, d in ctx["info"].items():
        c, snaps = d["c"], d["snaps"]
        if _sent_since(d["contacts"], ("QUASE-NIVEL", "QUASE-GRAD"), start):
            continue
        cur = [s for s in snaps if s.period_start == E.month_start(today)]
        snap = max(cur, key=lambda s: s.period_end) if cur else None
        if snap is None:
            continue
        grad = E.graduation_status(c, snap, st, today)
        if grad and not grad["graduated"] and grad["diamonds"] >= grad["target"] * st.near_tier_pct / 100:
            out.append(QueueItem(c, "quase_la", 1, "Quase lá: graduação",
                                 f"{_fmt(grad['diamonds'])} de {_fmt(grad['target'])} diamantes neste mês, faltam {_fmt(grad['missing'])}. "
                                 "Última semana do mês: contato prioritário.", "QUASE-GRAD",
                                 vars={"faltam": _fmt(grad["missing"]), "graduacao": _fmt(grad["target"]), "fim_do_mes": f"{end:%d/%m}"}))
            continue
        tier, _ = E.official_tier(c, today, rules)
        nxt = E.next_tier_rule(tier, rules)
        if nxt and nxt.min_diamonds * st.near_tier_pct / 100 <= snap.diamonds < nxt.min_diamonds:
            missing = nxt.min_diamonds - snap.diamonds
            out.append(QueueItem(c, "quase_la", 1, f"Quase lá: Tier {nxt.tier}",
                                 f"{_fmt(snap.diamonds)} de {_fmt(nxt.min_diamonds)} diamantes neste mês, faltam {_fmt(missing)}. "
                                 "Última semana do mês: contato prioritário.", "QUASE-NIVEL",
                                 vars={"faltam": _fmt(missing), "proximo_nivel": nxt.tier, "fim_do_mes": f"{end:%d/%m}"}))
    return out


# ------------------------------------------------------------------ módulo concluído
def module_items(ctx):
    from engage.models import Course, LessonProgress

    from .services import QueueItem

    since = timezone.now() - dt.timedelta(days=MODULE_RECENT_DAYS)
    recent = {}
    for p in LessonProgress.objects.filter(creator_id__in=ctx["ids"], completed_at__gte=since).select_related("lesson"):
        recent.setdefault(p.creator_id, set()).add(p.lesson.course_id)
    if not recent:
        return []
    courses = {co.pk: co for co in Course.objects.filter(pk__in={cid for s in recent.values() for cid in s}).prefetch_related("lessons")}
    out = []
    for pk, course_ids in recent.items():
        d = ctx["info"].get(pk)
        if d is None:
            continue
        done = dict(LessonProgress.objects.filter(creator_id=pk).values_list("lesson_id", "completed_at"))
        for cid in sorted(course_ids):
            co = courses[cid]
            lessons = [l.pk for l in co.lessons.all()]
            if not lessons or any(l not in done for l in lessons):
                continue
            finished = max(done[l] for l in lessons)
            if finished < since or _sent_since(d["contacts"], ("MODULO-OK",), timezone.localtime(finished).date()):
                continue
            from engage.academy import next_open_lesson

            nxt = next_open_lesson(d["c"])
            frase = f"A próxima aula aberta é “{nxt.title}”. " if nxt else ""
            out.append(QueueItem(d["c"], "modulo_concluido", 3, f"Terminou o módulo “{co.title}”",
                                 f"Concluiu todas as aulas em {timezone.localtime(finished):%d/%m}. Reconheça e indique o próximo passo.",
                                 "MODULO-OK", vars={"modulo": co.title, "proxima_frase": frase}))
            break  # um por criador
    return out


# ------------------------------------------------------------------ sinais de risco dos criadores Diamante
def number_signals(ws):
    """Sinais pelos números (Playbook): queda de 30% ou mais, horas ou dias abaixo do normal, batalhas em queda forte e
    nenhum fã novo com 5 horas ou mais de LIVE. "Queda forte" das batalhas = metade da média das 3 semanas anteriores."""
    if ws is None:
        return []
    w = ws.weeks
    w4, prev = w[4], w[1:4]
    out = []
    if ws.pct is not None and ws.pct <= -30:
        out.append(f"queda de {abs(ws.pct)}% nos diamantes da semana")
    avg_h = sum(x.hours for x in prev) / 3
    avg_d = sum(x.valid_days for x in prev) / 3
    if (avg_h and w4.hours < 0.7 * avg_h) or (avg_d and w4.valid_days <= avg_d - 2):
        out.append("horas ou dias abaixo do normal")
    avg_b = sum(x.battles for x in prev) / 3
    if avg_b >= 3 and w4.battles < 0.5 * avg_b:
        out.append(f"batalhas em queda forte ({w4.battles} contra {avg_b:.0f} por semana)")
    if "Fã-clube parado" in (ws.signals or []):
        out.append("nenhum fã novo com 5h ou mais de LIVE")
    return out


def talk_signals(creator, now=None):
    from crm.models import RiskSignal

    now = now or timezone.now()
    return list(RiskSignal.objects.filter(creator=creator, created_at__gte=now - dt.timedelta(days=RiskSignal.VALID_DAYS))
                .select_related("author"))


def risk_for(creator, ws, tier, diamond_tier, snaps, now=None):
    """Sinais de risco de um criador Diamante (None para quem não é Diamante).

    Os sinais pelos números só entram quando as semanas comparadas têm leitura própria (`weeks_readable`)."""
    if (tier or 1) < diamond_tier:
        return None
    readable = weeks_readable(snaps, ws)
    nums = number_signals(ws) if readable else []
    talk = talk_signals(creator, now)
    kinds = {}
    for s in talk:
        kinds.setdefault(s.kind, s)  # o mesmo sinal marcado duas vezes conta uma vez
    total = len(nums) + len(kinds)
    return {"numbers": nums, "talk": talk, "talk_kinds": list(kinds.values()), "total": total, "readable": readable,
            "level": "conversa" if total >= 2 else "observar" if total == 1 else ""}


def risk_items(ctx):
    from crm.one_on_one import diamond_min_tier

    from .services import QueueItem

    dtier = diamond_min_tier(ctx["agency"])
    out = []
    for pk, d in ctx["info"].items():
        r = risk_for(d["c"], d["ws"], d["tier"], dtier, d["snaps"], ctx["now"])
        if r and r["total"] >= 2:
            labels = r["numbers"] + [s.get_kind_display().lower() for s in r["talk_kinds"]]
            out.append(QueueItem(d["c"], "risco_diamante", 1, f"Diamante com {r['total']} sinais de risco",
                                 "Sinais: " + "; ".join(labels) + ". Conversa em até 48 horas; as sócias foram avisadas."))
    return out


def diamonds_at_risk(agency, today=None):
    """Criadores Diamante com algum sinal de risco: [(criador, sinais)], os com mais sinais primeiro."""
    from crm.models import Creator, CreatorStatus
    from crm.one_on_one import diamond_min_tier
    from data.models import MonthlyResult
    from data.states import analysed_sunday, week_state

    today = today or E.tiktok_today()
    dtier = diamond_min_tier(agency)
    pm = E.prev_month(analysed_sunday(today))
    tiers = {m.creator_id: m for m in MonthlyResult.objects.filter(creator__agency=agency, month=pm, tier__gte=dtier)}
    out = []
    for c in (Creator.objects.filter(pk__in=list(tiers)).exclude(status__in=[CreatorStatus.SAIU, CreatorStatus.ANONIMIZADO])
              .prefetch_related("snapshots")):
        snaps = list(c.snapshots.all())
        r = risk_for(c, week_state(c, snaps, today, prev_month_diamonds=tiers[c.pk].diamonds), tiers[c.pk].tier, dtier, snaps)
        if r and r["total"]:
            out.append((c, r))
    return sorted(out, key=lambda x: (-x[1]["total"], x[0].username))


def notify_risks(agency, today=None):
    """Rotina diária: avisa as sócias do Diamante com dois sinais ou mais. Um aviso por criador a cada 7 dias."""
    from core.models import Membership, Role
    from engage.models import Notification
    from engage.services import notify

    admins = list(Membership.objects.filter(agency=agency, role=Role.ADMIN, active=True).select_related("user"))
    sent = 0
    for c, r in diamonds_at_risk(agency, today):
        if r["total"] < 2:
            continue
        url = f"/gestao/creators/{c.pk}/"
        week_ago = timezone.now() - dt.timedelta(days=7)
        for m in admins:
            if not Notification.objects.filter(user=m.user, kind="risco", url=url, created_at__gte=week_ago).exists():
                notify(user=m.user, kind="risco", url=url, title=f"@{c.username} (Diamante) com {r['total']} sinais de risco",
                       body="Conversa em até 48 horas. Veja os sinais na ficha.")
                sent += 1
    return sent

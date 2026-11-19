"""Meu plano (etapa 3, passo 3.6): dias de LIVE, objetivos e lembretes escolhidos pelo próprio criador.

Regras (visão, "As outras áreas" e "Risco trabalhista"):
- Tudo é escolha do criador e pode ser mudado ou apagado a qualquer momento. O app nunca sugere dias, horas,
  horário ou número, e nunca compara o plano com o que aconteceu (nada de "cumpriu" ou "não cumpriu").
- Lembretes começam desligados. Por enquanto chegam no sininho do app, pela rotina diária (decisão da Mariana de
  19/11/2026); quando houver notificação no celular, as mesmas chaves valem para ela.
- A gestão lê o plano na ficha (decisão de 19/11/2026), mas não edita. Só o criador grava (regra também no banco).
"""
import datetime as dt

from django.utils import timezone

from data import engine as E

from .models import BattleRequest, CreatorGoal, CreatorPlan, Notification

WEEKDAYS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
WEEKDAYS_SHORT = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MAX_GOALS = 3  # objetivos em aberto ao mesmo tempo
REMINDERS = [
    ("remind_live_day", "Hoje é um dos meus dias de LIVE", "No dia que você marcou acima."),
    ("remind_battle", "Minha batalha oficial é amanhã", "Na véspera da batalha confirmada pela Hera."),
    ("remind_campaign", "Campanha que fecha hoje", "No último dia de uma campanha em que você participa."),
    ("remind_lesson", "Módulo novo na Hera Academy", "Quando um módulo novo abrir para você."),
]
NOTIFY_KIND = "plano"


class PlanError(Exception):
    pass


def plan_of(creator):
    """O plano do criador, ou um plano vazio (ainda não gravado) para quem não montou."""
    return CreatorPlan.objects.filter(creator=creator).first() or CreatorPlan(creator=creator)


def day_list(plan):
    return sorted({int(d) for d in (plan.live_days or "") if d.isdigit() and int(d) < 7})


def days_label(plan):
    """'seg, qua e sex' (ou '' se não escolheu)."""
    names = [WEEKDAYS_SHORT[d] for d in day_list(plan)]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " e " + names[-1]


def save_days(creator, days):
    plan = plan_of(creator)
    plan.live_days = "".join(str(d) for d in sorted({int(d) for d in days if str(d).isdigit() and 0 <= int(d) < 7}))
    plan.save()
    return plan


def save_reminders(creator, on):
    """`on`: nomes dos lembretes ligados. Os outros ficam desligados."""
    plan = plan_of(creator)
    for field, _, _ in REMINDERS:
        setattr(plan, field, field in on)
    plan.save()
    return plan


def open_goals(creator):
    return list(CreatorGoal.objects.filter(creator=creator, done_at__isnull=True).order_by("created_at"))


def add_goal(creator, kind, level=None, text=""):
    text = (text or "").strip()[:140]
    if len(open_goals(creator)) >= MAX_GOALS:
        raise PlanError(f"Você já tem {MAX_GOALS} objetivos em aberto. Marque um como “consegui” ou apague um para escrever outro.")
    if kind == "nivel":
        rules = E.tier_rules(creator.agency)
        if not any(r.tier == level for r in rules):
            raise PlanError("Escolha um dos níveis da lista.")
        text = ""
    elif kind == "livre":
        if not text:
            raise PlanError("Escreva o seu objetivo.")
        level = None
    else:
        raise PlanError("Escolha o tipo de objetivo.")
    return CreatorGoal.objects.create(creator=creator, kind=kind, level=level, text=text)


def goal_title(goal):
    return f"Chegar ao Nível {goal.level}" if goal.kind == "nivel" else goal.text


def goal_status(goal, creator, today=None, rules=None):
    """Onde o criador está em relação ao objetivo de nível: um fato com os dados de ontem, sem pedido nem promessa.

    Objetivo livre não tem conta: o criador marca "consegui" quando quiser."""
    if goal.kind != "nivel" or goal.done_at:
        return ""
    today = today or E.tiktok_today()
    rules = rules if rules is not None else E.tier_rules(creator.agency)
    target = next((r for r in rules if r.tier == goal.level), None)
    if target is None:
        return ""
    tier, _ = E.official_tier(creator, today, rules)
    if (tier or 0) >= goal.level:
        return f"Você já está no Nível {tier}. 🎉"
    snap = E.latest_in_month(creator, E.month_start(today))
    diamonds = snap.diamonds if snap else 0
    if diamonds >= target.min_diamonds:
        return f"Seus diamantes deste mês já estão na faixa do Nível {goal.level}. A mudança acontece no fechamento do mês."
    return (f"O Nível {goal.level} começa em {target.min_diamonds:,} 💎 no mês. "
            f"Neste mês: {diamonds:,} 💎.").replace(",", ".")


def level_choices(creator):
    """Níveis acima do atual, para o objetivo "chegar a um nível" (todos, se o criador ainda não tem nível)."""
    rules = E.tier_rules(creator.agency)
    tier, _ = E.official_tier(creator, E.tiktok_today(), rules)
    return [r for r in rules if r.tier > (tier or 0)] or list(rules)


def for_creator(creator):
    """Tudo o que a tela Meu plano (e o cartão da tela inicial) mostra."""
    plan = plan_of(creator)
    rules = E.tier_rules(creator.agency)
    today = E.tiktok_today()
    goals = list(CreatorGoal.objects.filter(creator=creator).order_by("done_at", "created_at"))
    rows = [{"g": g, "title": goal_title(g), "status": goal_status(g, creator, today, rules)} for g in goals]
    chosen = set(day_list(plan))
    return {
        "plan": plan, "days": [{"n": n, "name": WEEKDAYS[n], "short": WEEKDAYS_SHORT[n], "on": n in chosen} for n in range(7)],
        "days_label": days_label(plan), "goals": [r for r in rows if not r["g"].done_at],
        "done_goals": [r for r in rows if r["g"].done_at], "reminders": [{"field": f, "label": l, "help": h, "on": getattr(plan, f)}
                                                                           for f, l, h in REMINDERS],
        "can_add": sum(1 for r in rows if not r["g"].done_at) < MAX_GOALS, "max_goals": MAX_GOALS,
        "levels": level_choices(creator), "has_plan": bool(chosen or goals),
    }


# ------------------------------------------------------------------ lembretes (rotina diária)
def _already_sent(user_id, title, today):
    start = timezone.make_aware(dt.datetime.combine(today, dt.time.min))
    return Notification.objects.filter(user_id=user_id, kind=NOTIFY_KIND, title=title, created_at__gte=start).exists()


def _send(creator, title, body, url, today):
    if _already_sent(creator.user_id, title, today):
        return 0
    Notification.objects.create(user_id=creator.user_id, kind=NOTIFY_KIND, title=title, body=body, url=url)
    return 1


def daily_reminders(agency, today=None):
    """Cria, no sininho do app, os lembretes que cada criador ligou. Roda na rotina diária, como sistema.

    Não repete o mesmo lembrete no mesmo dia, mesmo que a rotina rode duas vezes. Devolve quantos criou."""
    from crm.models import CreatorStatus

    from . import academy
    from .campaigns import creator_campaigns
    from .services import creator_facts

    today = today or timezone.localdate()
    sent = 0
    plans = (CreatorPlan.objects.filter(creator__agency=agency, creator__user__isnull=False)
             .exclude(creator__status__in=[CreatorStatus.SAIU, CreatorStatus.ANONIMIZADO]).select_related("creator"))
    for plan in plans:
        c = plan.creator
        if plan.remind_live_day and today.weekday() in day_list(plan):
            sent += _send(c, "Hoje é um dos seus dias de LIVE 💜", "Você escolheu este dia no Meu plano. Dá para mudar quando quiser.",
                          "/meu-plano/", today)
        if plan.remind_battle:
            b = BattleRequest.objects.filter(creator=c, status="aprovada", date=today + dt.timedelta(days=1)).order_by("time").first()
            if b:
                sent += _send(c, f"Sua batalha oficial é amanhã, às {b.time:%H:%M} ⚔️", "O checklist da batalha está em Batalhas.", "/batalhas/", today)
        if plan.remind_campaign:
            for item in creator_campaigns(c, creator_facts(c), today):
                if item["c"].end == today:
                    sent += _send(c, f"A campanha {item['c'].name} fecha hoje 🏆", "", f"/campanhas/{item['c'].pk}/", today)
        # módulo novo: compara com o que estava aberto na última rotina (na primeira vez, só guarda)
        mods = academy.modules(c)
        opened = sorted(m.course.pk for m in mods if m.open)
        if plan.known_modules is not None and plan.remind_lesson:
            for m in mods:
                if m.open and m.course.pk not in plan.known_modules:
                    sent += _send(c, f"Abriu um módulo novo na Hera Academy: {m.course.title} 🎓", "", "/academy/", today)
        if plan.known_modules != opened:
            plan.known_modules = opened
            plan.save(update_fields=["known_modules"])
    return sent


def forget(creator):
    """LGPD: apaga o plano e os objetivos de quem foi anonimizado."""
    CreatorGoal.objects.filter(creator=creator).delete()
    CreatorPlan.objects.filter(creator=creator).delete()

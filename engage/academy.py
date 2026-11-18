"""Hera Academy: a página educacional da visão ("Página educacional").

Regras:
- O que abre um módulo é o nível e o marco alcançado, nunca o tempo de casa sozinho (`Course.opens_on`):
  primeiro acesso, depois da 1ª LIVE, ao fechar os 14 dias (ou no D15), ao chegar a um nível.
- Quem chega ao nível de `AgencySettings.academy_all_open_level` (3, na visão) abre todos os módulos de uma vez,
  inclusive quem vem de outra agência.
- A gestão libera qualquer módulo antes da hora para um criador (`ModuleRelease`). Cursos extras
  (`opens_on="gestao"`) só aparecem para quem recebeu a liberação.
- O que ainda não abriu aparece com o motivo ("Abre no Nível 3", "Abre depois da sua 1ª LIVE"), nunca como
  cadeado sem explicação. Nada de "obrigatória".
- Aula recomendada: a escolha da gestora na ficha (`LessonPick`) vence; sem escolha, o ponto mais fraco do mês;
  sem ponto fraco, a próxima aula não assistida.
"""
from dataclasses import dataclass, field

from core.models import AgencySettings
from data import engine as E
from data.models import MonthlyResult

from .models import Course, LessonPick, LessonProgress, ModuleRelease
from .services import creator_facts, matches_audience


@dataclass
class Module:
    course: object
    open: bool
    released: object = None  # ModuleRelease, quando foi a gestão que abriu
    hint: str = ""  # por que ainda não abriu (texto para o criador)
    lessons: list = field(default_factory=list)
    done: int = 0

    @property
    def total(self):
        return len(self.lessons)


def milestones(creator, snaps=None, settings_=None, today=None, rules=None):
    """Nível e marcos que abrem os módulos: nível (o maior entre o mês fechado e o mês corrente), 1ª LIVE e 14 dias."""
    today = today or E.tiktok_today()
    settings_ = settings_ or AgencySettings.objects.get(agency=creator.agency)
    rules = rules if rules is not None else E.tier_rules(creator.agency)
    snaps = snaps if snaps is not None else list(creator.snapshots.all())
    official, _ = E.official_tier(creator, today, rules)
    snap = max((s for s in snaps if E.month_start(s.period_start) == E.month_start(today)), key=lambda s: s.period_end, default=None)
    level = max(official, E.tier_for(snap.diamonds, rules) if snap and rules else official)
    ever_live = any(s.live_seconds > 0 or s.valid_days > 0 for s in snaps) or \
        MonthlyResult.objects.filter(creator=creator, live_seconds__gt=0).exists()
    day = creator.days_in_agency(today)
    ob = E.onboarding_status(creator, snaps, settings_)
    closed_14 = day is None or day > settings_.onboarding_window_days or bool(ob and ob["met"])
    return {"level": level, "ever_live": ever_live, "closed_14": closed_14, "all_open": level >= settings_.academy_all_open_level,
            "all_open_level": settings_.academy_all_open_level}


def _rule_opens(course, ms):
    """(abre?, motivo para o criador quando ainda não abre)."""
    if course.opens_on == "gestao":
        return False, ""
    if ms["all_open"] or course.opens_on == "acesso":
        return True, ""
    if course.opens_on == "primeira_live":
        return ms["ever_live"], "Abre depois da sua 1ª LIVE."
    if course.opens_on == "dia15":
        return ms["closed_14"], "Abre quando os seus primeiros 14 dias terminarem."
    if course.opens_on == "nivel":
        need = course.opens_level or ms["all_open_level"]
        return ms["level"] >= need, f"Abre no Nível {need}."
    return True, ""


def modules(creator, today=None, ms=None, facts=None, include_hidden=False):
    """Módulos da Hera Academy para este criador, na ordem, com o que abriu e o que falta.

    Cursos extras sem liberação ficam de fora (o criador não vê), a não ser com include_hidden (ficha da gestão)."""
    facts = facts or creator_facts(creator, today)
    ms = ms or milestones(creator, today=today)
    released = {r.course_id: r for r in ModuleRelease.objects.filter(creator=creator)}
    done = set(LessonProgress.objects.filter(creator=creator).values_list("lesson_id", flat=True))
    out = []
    for co in Course.objects.filter(agency=creator.agency, published=True).prefetch_related("lessons"):
        if not matches_audience(co, facts):
            continue
        by_rule, hint = _rule_opens(co, ms)
        rel = released.get(co.pk) if not by_rule else None  # liberação só conta quando a regra ainda não abriu
        if co.opens_on == "gestao" and not rel and not include_hidden:
            continue
        ls = list(co.lessons.all())
        out.append(Module(course=co, open=by_rule or rel is not None, released=rel, hint="" if rel else hint,
                          lessons=ls, done=sum(1 for l in ls if l.pk in done)))
    return out


def open_lessons(mods):
    return [l for m in mods if m.open for l in m.lessons]


def lesson_state(creator, lesson):
    """(aberta?, motivo) de uma aula para este criador. Aula de módulo que não vale para ele: (False, "")."""
    for m in modules(creator):
        if m.course.pk == lesson.course_id:
            return m.open, m.hint
    return False, ""


# ------------------------------------------------------------------ aula recomendada
WEAK_REASONS = {
    "rotina": "Sua rotina de LIVE está abaixo do mês passado.",
    "batalhas": "Menos batalhas que no mês passado.",
    "interacao": "Mesma rotina e menos diamantes que no mês passado.",
}


def weak_point(snap, last_closed, today=None):
    """O ponto mais fraco do mês, comparado com o mesmo ponto do mês passado (fato, não pedido).

    Ordem: rotina (primeiro cai a LIVE), batalhas, fã-clube e, com a rotina mantida, interação."""
    if not snap or not last_closed:
        return None
    month_days = (E.month_end(snap.period_start) - E.month_start(snap.period_start)).days + 1
    elapsed = (snap.period_end - E.month_start(snap.period_start)).days + 1
    if elapsed < 3:
        return None
    share = elapsed / month_days
    if (last_closed.valid_days and snap.valid_days < last_closed.valid_days * share) or \
            (last_closed.live_seconds and snap.live_seconds < last_closed.live_seconds * share):
        return "rotina"
    if last_closed.battles and snap.battles < last_closed.battles * share:
        return "batalhas"
    # Fã-clube: o mês fechado não guarda fãs novos, então ainda não dá para comparar (aulas de fã-clube
    # aparecem pela escolha da gestora ou como próxima aula).
    if last_closed.diamonds and snap.diamonds < last_closed.diamonds * share:
        return "interacao"
    return None


def recommended(creator, mods=None, snap=None, today=None, counting=False, use_pick=True):
    """A aula recomendada e o motivo. Devolve {"lesson", "why", "by"} ou None.

    by = "gestao" (escolha da gestora), "ponto" (ponto mais fraco do mês) ou "proxima" (próxima não assistida).
    use_pick=False devolve só a sugestão automática (a ficha mostra as duas)."""
    today = today or E.tiktok_today()
    mods = mods if mods is not None else modules(creator, today)
    lessons = open_lessons(mods)
    if not lessons:
        return None
    by_pk = {l.pk: l for l in lessons}
    pick = LessonPick.objects.filter(creator=creator).first() if use_pick else None
    if pick and pick.lesson_id in by_pk:
        return {"lesson": by_pk[pick.lesson_id], "why": "Escolhida pela Hera para você.", "by": "gestao"}
    done = set(LessonProgress.objects.filter(creator=creator).values_list("lesson_id", flat=True))
    pending = [l for l in lessons if l.pk not in done]
    if not counting:
        snap = snap if snap is not None else E.latest_in_month(creator, E.month_start(today))
        last_closed = MonthlyResult.objects.filter(creator=creator, month=E.prev_month(today)).first()
        topic = weak_point(snap, last_closed, today)
        if topic:
            hit = next((l for l in pending if l.topic == topic), None)
            if hit:
                return {"lesson": hit, "why": WEAK_REASONS[topic], "by": "ponto", "topic": topic}
    if pending:
        return {"lesson": pending[0], "why": "", "by": "proxima"}
    return None


def next_open_lesson(creator, today=None):
    """Próxima aula aberta e não assistida (rodízio da fila e primeiro acesso)."""
    rec = recommended(creator, today=today, counting=True)
    return rec["lesson"] if rec else None

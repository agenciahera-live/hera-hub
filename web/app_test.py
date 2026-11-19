"""Teste do app com poucos criadores (etapa 3, passo 3.7).

Decisões da Mariana de 19/11/2026: 5 criadores, escolhidos por ela depois (marcados na tela Teste do app);
o teste dura de 2 semanas a 1 mês (início e fim na mesma tela); pesquisa no fim, identificada; os vídeos da Hera
Academy são cadastrados por ela no sistema.

O que esta parte faz:
- registra o uso do app: um evento "app_open" por dia e um evento por área usada por dia (`log_use`);
- monta a tela Teste do app das sócias (`tester_rows`, `summary`);
- cria a pesquisa do fim do teste, só para quem participa (`create_survey`).
A trava do código de acesso (só quem participa recebe código) fica em crm/first_access.py:new_code.
"""
import datetime as dt

from django.utils import timezone

from core.models import AgencySettings, AppEvent

# nome da tela (url) -> área do app, como aparece na barra de baixo e nos cartões
AREAS = {
    "home": "Meu progresso", "my_level": "Meu progresso",
    "academy": "Hera Academy", "lesson": "Hera Academy",
    "campaigns": "Campanhas", "campaign": "Campanhas",
    "battles": "Batalhas", "battle_new": "Batalhas", "battle_check": "Batalhas",
    "faq": "Ajuda", "faq_search": "Ajuda", "ask_manager": "Ajuda", "help_account": "Ajuda", "help_exit": "Ajuda",
    "my_plan": "Meu plano",
}
AREA_ORDER = ["Meu progresso", "Hera Academy", "Campanhas", "Batalhas", "Ajuda", "Meu plano"]
AREA_PREFIX = "area:"
SUGGESTED_TESTERS = 5  # decisão de 19/11; não é limite, a tela só mostra


def log_use(request):
    """Um "app_open" por dia e uma linha por área usada por dia (guardado na sessão para não repetir)."""
    today = timezone.localdate().isoformat()
    seen = request.session.get("hera_use", {})
    if seen.get("day") != today:
        seen = {"day": today, "areas": []}
        AppEvent.objects.create(user=request.user, event="app_open")
        request.session["hera_open"] = today
    match = getattr(request, "resolver_match", None)
    area = AREAS.get(match.url_name) if match else None
    if area and area not in seen["areas"]:
        AppEvent.objects.create(user=request.user, event=AREA_PREFIX + area)
        seen["areas"].append(area)
    request.session["hera_use"] = seen


def week_start(today):
    return today - dt.timedelta(days=today.weekday())


def _local_day(ts):
    return timezone.localtime(ts).date()


def tester_rows(agency, today=None):
    """Uma linha por criador do teste: gestora, código, primeiro acesso, dias com o app aberto e áreas usadas."""
    from crm.models import Creator
    from engage.models import Survey, SurveyCompletion

    today = today or timezone.localdate()
    st = AgencySettings.objects.get(agency=agency)
    monday = week_start(today)
    since = st.app_test_start or monday
    surveys = list(Survey.objects.filter(agency=agency, only_app_testers=True).values_list("pk", flat=True))
    rows = []
    for c in Creator.objects.filter(agency=agency, app_tester=True).order_by("username"):
        code = c.access_codes.order_by("-created_at").first()
        used = c.access_codes.filter(used_at__isnull=False).order_by("used_at").first()
        events = list(AppEvent.objects.filter(user_id=c.user_id, at__date__gte=min(since, monday) - dt.timedelta(days=1))
                      .values_list("event", "at")) if c.user_id else []
        opens = sorted({_local_day(at) for ev, at in events if ev == "app_open"})
        week_areas = {ev[len(AREA_PREFIX):] for ev, at in events if ev.startswith(AREA_PREFIX) and _local_day(at) >= monday}
        test_areas = {ev[len(AREA_PREFIX):] for ev, at in events if ev.startswith(AREA_PREFIX) and _local_day(at) >= since}
        last = AppEvent.objects.filter(user_id=c.user_id, event="app_open").order_by("-at").first() if c.user_id else None
        rows.append({
            "c": c, "manager": c.current_manager(), "code": code, "first_access": used.used_at if used else None,
            "has_login": bool(c.user_id), "days_week": sum(1 for d in opens if d >= monday),
            "days_test": sum(1 for d in opens if d >= since) if st.app_test_start and st.app_test_start <= today else None,
            "last_open": last.at if last else None,
            "areas_week": [a for a in AREA_ORDER if a in week_areas], "areas_test": [a for a in AREA_ORDER if a in test_areas],
            "answered": bool(c.user_id and surveys and SurveyCompletion.objects.filter(survey_id__in=surveys, user_id=c.user_id).exists()),
        })
    return rows


def summary(rows):
    with_login = [r for r in rows if r["has_login"]]
    return {"n": len(rows), "with_login": len(with_login), "opened_week": sum(1 for r in rows if r["days_week"]),
            "answered": sum(1 for r in rows if r["answered"]), "suggested": SUGGESTED_TESTERS}


def status(st, today=None):
    """Situação do teste pelas datas: 'sem_datas', 'antes', 'andamento' ou 'terminou'."""
    today = today or timezone.localdate()
    if not st.app_test_start:
        return "sem_datas"
    if today < st.app_test_start:
        return "antes"
    if st.app_test_end and today > st.app_test_end:
        return "terminou"
    return "andamento"


# Rascunho da pesquisa do fim do teste: a Mariana revisa no arquivo do roteiro e pode editar no cadastro de pesquisas
SURVEY_TITLE = "Como foi usar o app da Hera?"
SURVEY_INTRO = "São 5 perguntas rápidas. A sua resposta ajuda a Hera a melhorar o app antes de abrir para todo mundo."
SURVEY_QUESTIONS = [
    ("nps", "De 0 a 10, quanto você indicaria o app da Hera para outro criador?", []),
    ("multi", "O que você mais usou no app?", AREA_ORDER),
    ("single", "Ficou fácil entender os seus números em Meu progresso?", ["Sim", "Mais ou menos", "Não"]),
    ("text", "O que faltou ou ficou confuso?", []),
    ("text", "Se você pudesse mudar uma coisa no app, o que seria?", []),
]


def create_survey(agency, st):
    """Cria a pesquisa do fim do teste: identificada (decisão de 19/11), só para quem participa, abre no último dia
    do teste e fica aberta por 7 dias. Se já existir, devolve a que existe."""
    from engage.models import Survey, SurveyQuestion

    existing = Survey.objects.filter(agency=agency, only_app_testers=True).order_by("-opens_at").first()
    if existing:
        return existing, False
    end = st.app_test_end or timezone.localdate()
    opens = timezone.make_aware(dt.datetime.combine(end, dt.time(9, 0)))
    sv = Survey.objects.create(agency=agency, title=SURVEY_TITLE, intro=SURVEY_INTRO, anonymous=False, only_app_testers=True,
                               opens_at=opens, closes_at=opens + dt.timedelta(days=7))
    for i, (kind, text, options) in enumerate(SURVEY_QUESTIONS):
        SurveyQuestion.objects.create(survey=sv, kind=kind, text=text, options=list(options), order=i)
    return sv, True

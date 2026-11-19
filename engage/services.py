import datetime as dt
import re
import unicodedata
from urllib.parse import quote

from django.db import connection
from django.db.models import Q
from django.utils import timezone

from core.rls import system_context
from crm.models import Creator, CreatorStatus

from .models import Announcement, Campaign, CampaignStanding, FaqItem, FaqSearch, Notification

ACTIVE_STATUSES = [CreatorStatus.PENDENTE, CreatorStatus.CONVIDADO, CreatorStatus.ATIVO, CreatorStatus.EM_SAIDA]


# ------------------------------------------------------------------ público
def creator_facts(creator, today=None):
    """Tier oficial, grupo e parceira de um creator (para decidir público)."""
    from data.engine import FIRST_MONTH, official_tier

    tier, _ = official_tier(creator, today)
    g = creator.group_history.filter(until__isnull=True).first()
    return {"tier": tier, "group": g.group_name if g else FIRST_MONTH, "partner": creator.partner_group_id,
            "app_tester": creator.app_tester}


def matches_audience(obj, facts):
    if getattr(obj, "only_app_testers", False) and not facts.get("app_tester"):
        return False  # pesquisa do teste do app (passo 3.7): só quem participa
    if obj.audience_tiers and facts["tier"] not in [int(t) for t in obj.audience_tiers]:
        return False
    if obj.audience_groups and facts["group"] not in obj.audience_groups:
        return False
    if obj.only_first_month and facts["group"] != "Primeiro Mês":
        return False
    partners = list(obj.audience_partners.values_list("pk", flat=True)) if obj.pk else []
    if partners and facts["partner"] not in partners:
        return False
    return True


def visible_items(qs, creator, today=None):
    facts = creator_facts(creator, today)
    return [o for o in qs if matches_audience(o, facts)]


# ------------------------------------------------------------------ campanhas
def campaign_value(snaps, metric, start, end):
    """Valor da métrica dentro do período da campanha (acumulado no fim − acumulado antes do início)."""
    from data.engine import cumulative_until

    return cumulative_until(snaps, end, metric) - cumulative_until(snaps, start - dt.timedelta(days=1), metric)


def campaign_members(campaign, today=None):
    manual = list(campaign.participants.values_list("creator_id", flat=True))
    qs = Creator.objects.filter(agency=campaign.agency, status__in=ACTIVE_STATUSES)
    if manual:
        return list(qs.filter(pk__in=manual))
    return [c for c in qs if matches_audience(campaign, creator_facts(c, today))]


def recompute_standings(agency, today=None):
    """Progresso de cada participante nas campanhas internas ativas (ou encerradas há até 14 dias).

    Não existe ranking: guarda só o valor da métrica e se a pessoa chegou ao alvo da campanha. Roda como sistema."""
    from data.engine import official_tier, tiktok_today

    today = today or tiktok_today()
    with system_context():
        CampaignStanding.objects.filter(campaign__agency=agency, campaign__source="backstage").delete()
        for camp in Campaign.objects.filter(agency=agency, published=True, start__lte=today, end__gte=today - dt.timedelta(days=14)).exclude(source="backstage"):
            objs = []
            for c in campaign_members(camp, today):
                snaps = list(c.snapshots.all())
                val = round(campaign_value(snaps, camp.metric, camp.start, camp.end), 2)
                tier, _ = official_tier(c, today)
                objs.append(CampaignStanding(
                    campaign=camp, creator_id_ref=c.pk, username=c.username, tier=tier, value=val,
                    reached_goal=bool(camp.goal and val >= float(camp.goal)),
                ))
            CampaignStanding.objects.filter(campaign=camp).delete()
            CampaignStanding.objects.bulk_create(objs)


# ------------------------------------------------------------------ avisos
def publish_announcement(ann):
    """Cria as notificações no app para o público do aviso (uma vez)."""
    if ann.notified:
        return 0
    n = 0
    with system_context():
        for c in Creator.objects.filter(agency=ann.agency, user__isnull=False, status__in=ACTIVE_STATUSES):
            if matches_audience(ann, creator_facts(c)):
                notify(user_id=c.user_id, kind="aviso", title=ann.title, body=ann.body[:200], url="/avisos/")
                n += 1
    Announcement.objects.filter(pk=ann.pk).update(notified=True)
    return n


# ------------------------------------------------------------------ mensagens
class SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def fmt_int(n):
    return f"{int(round(n)):,}".replace(",", ".")


def fmt_hours(h):
    return f"{h:.1f}".replace(".", ",").replace(",0", "")


def message_vars(creator):
    from data.engine import latest_in_month, month_start, official_tier, onboarding_status, tiktok_today

    snap = latest_in_month(creator, month_start(tiktok_today())) or creator.snapshots.order_by("-period_end").first()
    tier, mr = official_tier(creator)
    facts = creator_facts(creator)
    mgr = creator.current_manager()
    v = {
        "nome": creator.first_name, "gestora": (mgr.first_name or mgr.email.split("@")[0]) if mgr else "sua gestora",
        "tier": tier, "grupo": facts["group"], "dias_validos": 0, "horas": "0", "diamantes": "0", "lives": 0,
        "falta_dias": 0, "falta_horas": "0", "dias_restantes": 0, "comparacao": "",
        # convite para o app: a tela informa o link_app; o código vem da ficha (só quem edita o criador enxerga)
        "link_app": "[link do app]", "codigo_acesso": "[gere o código na ficha]", "codigo_validade": "[data]",
        # rodízio: a fila preenche quando sabe; fora dela ficam os colchetes do Playbook, para a gestora completar
        "proxima_aula": "[tema]", "campanha": "[campanha]", "campanha_regra": "[resumo da regra]", "campanha_link": "[link]",
    }
    from crm.first_access import active_code

    ac = active_code(creator)
    if ac:
        v.update(codigo_acesso=ac.display, codigo_validade=f"{timezone.localtime(ac.expires_at):%d/%m}")
    from core.models import AgencySettings

    st = AgencySettings.objects.get(agency=creator.agency)
    ob = onboarding_status(creator, list(creator.snapshots.all()), st)
    if ob and ob["active"]:
        v.update(dias_validos=ob["valid_days"], horas=fmt_hours(ob["hours"]), falta_dias=ob["need_days"],
                 falta_horas=fmt_hours(ob["need_hours"]), dias_restantes=ob["remaining_days"])
    elif snap:
        v.update(dias_validos=snap.valid_days, horas=fmt_hours(snap.hours),
                 falta_dias=max(st.monthly_min_valid_days - snap.valid_days, 0),
                 falta_horas=fmt_hours(max(st.monthly_min_hours - snap.hours, 0)))
    if snap:
        v.update(diamantes=fmt_int(snap.diamonds), lives=snap.streams)
        if snap.lm_diamonds:
            diff = (snap.diamonds - snap.lm_diamonds) / snap.lm_diamonds
            v["comparacao"] = (f"🚀 Você cresceu {diff:.0%} em diamantes em relação ao mês passado!" if diff >= 0
                               else "Mês desafiador — bora recuperar o ritmo no próximo! 💪")
    return v


def render_message(template_body, creator, **extra):
    """Preenche o modelo com os dados do criador. `extra` traz o que só a tela sabe (ex.: link_app)."""
    return template_body.format_map(SafeDict({**message_vars(creator), **extra}))


# ------------------------------------------------------------------ biblioteca: a variação certa para cada criador
def creator_track(creator):
    """Trilha que vale para o roteiro: a definida pela gestão; sem ela, a sugerida pelo cadastro; sem nenhuma, Primeira LIVE."""
    if creator is None:
        return "primeira_live"
    return creator.track or creator.track_suggested or "primeira_live"


def outside_track(template, creator):
    """O modelo é de outra trilha (ex.: Desafio dos 5 dias para quem já tem nível e público)."""
    return bool(template.tracks) and creator_track(creator) not in template.tracks


def pick_variant(rows, creator=None):
    """Entre os modelos com o mesmo código, o que vale para a trilha do criador e para "faz batalha".

    Vence o mais específico. Sem nenhum que sirva (modelo só de outra trilha), devolve o modelo geral."""
    if not rows:
        return None
    track = creator_track(creator)
    battles = (creator.does_battles if creator is not None else "") or ""
    best, best_score = None, -1
    for t in rows:
        score = 0
        if t.tracks:
            if track not in t.tracks:
                continue
            score += 2
        if t.battles:
            if t.battles != battles:
                continue
            score += 1
        if score > best_score or (score == best_score and not t.variant):
            best, best_score = t, score
    return best or min(rows, key=lambda t: (t.variant != "", t.order))


def templates_by_code(agency):
    """{código: [modelos]} da agência, na ordem da biblioteca."""
    from .models import MessageTemplate

    out = {}
    for t in MessageTemplate.objects.filter(agency=agency):
        out.setdefault(t.code, []).append(t)
    return out


def template_for(agency, code, creator=None):
    from .models import MessageTemplate

    return pick_variant(list(MessageTemplate.objects.filter(agency=agency, code=code)), creator)


def whatsapp_link(phone, text):
    digits = re.sub(r"\D", "", phone or "")
    if digits and not digits.startswith("55") and len(digits) <= 11:
        digits = "55" + digits
    return f"https://wa.me/{digits}?text={quote(text)}" if digits else f"https://wa.me/?text={quote(text)}"


# ------------------------------------------------------------------ Q&A (central de dúvidas)
def _norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", s)


STOP = {"a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "que", "um", "uma", "eu", "meu", "minha", "como", "para", "pra",
        "por", "com", "no", "na", "nos", "nas", "se", "qual", "quais", "e", "em", "ao", "ou", "mais", "tem", "ter", "sobre", "posso", "faco", "fazer"}


def faq_search(agency, query, user=None, limit=3):
    """Busca tolerante a acento, erro de digitação e sinônimos. Sem IA.

    Pontua cada pergunta por: termos em comum com pergunta/sinônimos/resposta + similaridade de trigramas (pg_trgm)."""
    q = _norm(query).strip()
    items = list(FaqItem.objects.filter(agency=agency, active=True))
    if not q:
        return []
    terms = [t for t in q.split() if t not in STOP and len(t) > 1]
    trigram = {}
    if connection.vendor == "postgresql":
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id, greatest(word_similarity(unaccent(lower(%s)), unaccent(lower(question))),"
                " word_similarity(unaccent(lower(%s)), unaccent(lower(keywords)))) FROM engage_faqitem WHERE agency_id=%s AND active",
                [query, query, agency.pk],
            )
            trigram = dict(cur.fetchall())
    scored = []
    for it in items:
        qn, kn, an = _norm(it.question), _norm(it.keywords), _norm(it.answer)
        kw_phrases = [k.strip() for k in kn.split("  ") if k.strip()] + [k.strip() for k in _norm(it.keywords.replace(",", "|")).split("|") if k.strip()]
        score = 0.0
        for t in terms:
            if re.search(rf"\b{re.escape(t)}", kn):
                score += 3
            if re.search(rf"\b{re.escape(t)}", qn):
                score += 2
            if re.search(rf"\b{re.escape(t)}", an):
                score += 0.5
        for ph in kw_phrases:
            if len(ph) > 3 and ph in q:
                score += 3
        score += 4 * float(trigram.get(it.pk, 0))
        if score >= 1.5:
            scored.append((score, it))
    scored.sort(key=lambda x: -x[0])
    result = [it for _, it in scored[:limit]]
    FaqSearch.objects.create(agency=agency, user=user, query=query[:240], results=len(result))
    return result


def faq_vars(creator):
    from core.models import AgencySettings
    from data.engine import latest_in_month, month_start, official_tier, tiktok_today

    st = AgencySettings.objects.get(agency=creator.agency)
    snap = latest_in_month(creator, month_start(tiktok_today()))
    tier, _ = official_tier(creator)
    vd = snap.valid_days if snap else 0
    hrs = snap.hours if snap else 0
    return {
        "nome": creator.first_name, "tier": tier, "dias_validos_mes": vd, "horas_mes": fmt_hours(hrs),
        "falta_dias_min": max(st.monthly_min_valid_days - vd, 0), "falta_horas_min": fmt_hours(max(st.monthly_min_hours - hrs, 0)),
    }


def render_faq_answer(item, creator):
    if creator is None:
        return item.answer
    return item.answer.format_map(SafeDict(faq_vars(creator)))


def notify(user=None, user_id=None, **fields):
    """Cria notificação no app para outra pessoa. Roda como sistema porque quem cria
    (ex.: streamer avisando a gestora) não pode ler a notificação alheia (RLS)."""
    with system_context():
        return Notification.objects.create(user_id=user_id or user.pk, **fields)

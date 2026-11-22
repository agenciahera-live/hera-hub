"""Montagem das telas: resumo do streamer e fila de ação da gestão."""
import datetime as dt
import hashlib
import re
from dataclasses import dataclass, field

from django.db.models import Max, Sum
from django.utils import timezone

from core.models import AgencySettings
from crm.models import ActionItem, CadenceState, Contact, Creator, CreatorPrivate, CreatorStatus, OneOnOne, Reminder
from data import engine as E
from data.models import CreatorSnapshot, ImportBatch, MonthlyResult
from engage import battles as battle_rules
from engage.models import BattleRequest, Campaign, SupportTicket, Tip
from engage.services import creator_facts, fmt_hours, fmt_int, matches_audience

MONTHS_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def month_name(d):
    return MONTHS_PT[d.month - 1]


def manager_contact(creator):
    """Link para falar com a gestora: grupo individual do WhatsApp > WhatsApp da gestora > suporte da agência."""
    from engage.services import whatsapp_link

    priv = getattr(creator, "private", None)
    if priv and priv.whatsapp_group_url:
        return priv.whatsapp_group_url
    mgr = creator.current_manager()
    phone = ""
    if mgr:
        m = mgr.memberships.filter(agency=creator.agency).exclude(phone="").first()
        phone = m.phone if m else ""
    phone = phone or creator.agency.whatsapp_support
    # sem grupo e sem telefone cadastrados: leva para a pergunta pelo app
    return whatsapp_link(phone, f"Oi! Aqui é @{creator.username}. Tenho uma dúvida.") if phone else "/duvidas/#perguntar"


def data_freshness(agency):
    b = ImportBatch.objects.filter(agency=agency, status="committed", kind="backstage").order_by("-exported_at").first()
    return b.exported_at if b else None


def import_status(agency, now=None):
    """Situação da importação diária do Backstage: feita hoje? atrasada?

    "Hoje" é o dia em São Paulo. "Atrasada" usa o limite configurável (stale_data_days)."""
    from data.port import active_key

    now = now or timezone.now()
    local_now = timezone.localtime(now)
    last = (ImportBatch.objects.filter(agency=agency, status="committed", kind="backstage", committed_at__isnull=False)
            .select_related("uploaded_by").order_by("-committed_at").first())
    fresh = data_freshness(agency)
    settings_ = AgencySettings.objects.get(agency=agency)
    done_today = bool(last and timezone.localtime(last.committed_at).date() == local_now.date())
    key = active_key(agency)
    # leitura automática que chegou hoje mas ficou esperando conferência (ver data/port.py)
    day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    held = None if done_today else (ImportBatch.objects.filter(agency=agency, via="porta", status="preview", created_at__gte=day_start)
                                    .order_by("-created_at").first())
    return {
        "last": last,
        "done_today": done_today,
        "stale": (now - fresh).days >= settings_.stale_data_days if fresh else True,
        # leitura automática (porta de importação)
        "auto_on": key is not None,
        "auto_key": key,
        "auto_deadline": settings_.auto_import_deadline_hour,
        "auto_late": key is not None and not done_today and held is None and local_now.hour >= settings_.auto_import_deadline_hour,
        "auto_held": held,
    }


# ================================================================== STREAMER
# A tela inicial do criador (Meu progresso) fica em web/progress.py.
def visible_campaigns(creator, facts, today):
    """Campanhas que o criador vê no app (regra em engage/campaigns.py, passo 3.4)."""
    from engage.campaigns import creator_campaigns

    return creator_campaigns(creator, facts, today)


def next_lesson(creator, facts=None):
    """Próxima aula já aberta e não assistida na Hera Academy (regras em engage/academy.py)."""
    from engage.academy import next_open_lesson

    return next_open_lesson(creator)


def daily_tip(agency, facts, today):
    tips = [t for t in Tip.objects.filter(agency=agency, active=True) if matches_audience(t, facts)]
    if not tips:
        return None
    h = int(hashlib.md5(today.isoformat().encode()).hexdigest(), 16)
    return tips[h % len(tips)]


def group_ranges(agency, rules):
    """Grupos e as faixas de nível de cada um, como estão em Configurações (nada fixo na tela).
    No app do criador o Tier aparece como "Nível"."""
    from data.models import GroupRule

    top = rules[-1].tier if rules else 10
    out = []
    for g in GroupRule.objects.filter(agency=agency):
        if g.tier_min == g.tier_max:
            txt = f"Nível {g.tier_min}"
        elif g.tier_max >= top:
            txt = f"Nível {g.tier_min} ou mais"
        else:
            txt = f"Nível {g.tier_min} a {g.tier_max}"
        out.append({"name": g.name, "range": txt})
    return out


# ================================================================== GESTÃO
# Fila do dia (visão, "Regras de contato da carteira"). Ordem dos blocos:
BLOCKS = {1: "Suporte e pedidos", 2: "O que tem data", 3: "O que vem do dado", 4: "Rodízio: 4 dias sem contato"}

# TODOS os tipos de item da fila, com o bloco de cada um. É a única tabela que diz onde cada item entra:
# ordenação, "uma mensagem por dia", teto e domingo leem daqui. Tipo novo = uma linha aqui + quem gera os itens.
# Os tipos marcados "a construir" já existem para a fila não precisar ser mexida quando eles chegarem.
ITEM_TYPES = {
    # bloco 1: suporte e restrições
    "duvida": (1, "Dúvida sem resposta no app"),
    "batalha": (1, "Pedido de batalha"),
    "restricao": (1, "Restrição ou banimento na conta"),
    # bloco 2: o que tem data
    "onboarding": (2, "Roteiro do onboarding (passo 2.5)"),
    "onboarding_risco": (2, "Regra dos 14 dias em risco (D10 a D14)"),
    "cadencia": (2, "Cadência de não-resposta"),
    "regua": (2, "Régua sem LIVE (4, 14, 21 e 30 dias)"),
    "volta": (2, "Data de volta chegou"),
    "batalha_proxima": (2, "Batalha oficial em até 4 dias"),
    "aniversario": (2, "Aniversário (no dia e 30 dias antes)"),
    "visita": (2, "Sugestão de visita (até 3 por dia)"),
    "lembrete": (2, "Lembrete com data"),
    "1a1_atrasado": (2, "1:1 atrasado"),
    "1a1_mes": (2, "1:1 do mês: Diamante e potencial de graduação sem 1:1 completo há 30 dias (passo 4.2)"),
    "plano_vencido": (2, "Plano de ação vencido"),
    "campanha": (2, "Acompanhamento de campanha: inscrição, perto de prêmio e chegou perto (passo 4.5)"),
    "rodada_batalhas": (2, "Rodada de batalhas oficiais do dia 8: a construir (módulo de batalhas)"),
    "resumo_mes": (2, "Resumo do mês, dias 1 a 7 (passo 4.3)"),
    # bloco 3: o que vem do dado
    "queda": (3, "Queda na semana"),
    "subindo": (3, "Subindo na semana"),
    "irregular": (3, "Semana irregular"),
    "perto_tier": (3, "Perto do próximo Tier"),
    "perto_graduar": (3, "Perto de graduar"),
    "quase_la": (3, "Quase lá, última semana do mês (passo 4.3)"),
    "nivel_novo": (3, "Nível novo, dias 1 a 7 (passo 4.3)"),
    "modulo_concluido": (3, "Módulo da Hera Academy concluído (passo 4.3)"),
    "risco_diamante": (3, "Diamante com dois sinais de risco ou mais: conversa em até 48 horas (passo 4.3)"),
    # bloco 4
    "rodizio": (4, "Rodízio: dias sem mensagem individual"),
}


# Itens que não podem esperar quando a gestora avisa "Hoje não trabalho" (visão, "Ausência da gestora"): D10, D12, D14,
# encerramento, batalha oficial e restrição. Vão para quem cobre; os outros passam para o dia seguinte.
# O reconhecimento de quem fechou a regra só entra aqui a partir do D14 (quem marca é _onboarding_items).
URGENT_CODES = {
    "restricao",              # restrição ou banimento na conta
    "batalha_proxima",        # batalha oficial nos próximos dias
    "onboarding_nl10",        # D10 de quem nunca abriu LIVE
    "onboarding_d10",         # D10: conferência dos dias válidos
    "onboarding_risco",       # D10 a D13: regra dos 14 dias em risco
    "onboarding_acolher",     # D14 sem fechar a regra
    "onboarding_encerrar",    # encerramento até o D14 (nunca abriu LIVE)
    "onboarding_encerrar15",  # encerramento no D15
}


# Itens em que a decisão de manter ou encerrar é das sócias (visão, princípio 9). Na fila aparece o botão
# "Pedir decisão às sócias", que leva o pedido para a lista de aprovações do painel. A régua dos 30 dias sem LIVE
# é marcada onde o item nasce (o último passo da régua vem de Configurações).
PARTNER_DECISION_CODES = {"onboarding_encerrar", "onboarding_encerrar15"}


def item_kind(code):
    """Tipo do item pelo código ("regua_14" → "regua", "aniversario_30" → "aniversario")."""
    return code if code in ITEM_TYPES else code.rsplit("_", 1)[0]


@dataclass
class QueueItem:
    creator: Creator
    code: str
    priority: int
    title: str
    detail: str
    template: str = ""  # com modelo = item de mensagem (conta para "uma por dia", teto e domingo); sem modelo = tarefa
    text: str = ""  # mensagem pronta (preenchida só para os itens exibidos)
    group_url: str = ""  # link do grupo individual, se cadastrado na ficha
    vars: dict = field(default_factory=dict)  # variáveis só deste item (ex.: nome da próxima aula)
    state: object = None  # estado da semana do criador, para dar contexto
    urgent: bool = False  # não pode esperar: na ausência da gestora, vai para quem cobre (ver URGENT_CODES)
    asks_partners: bool = False  # manter ou encerrar: a gestora pede a decisão das sócias (passo 4.1, PARTNER_DECISION_CODES)
    block: int = field(init=False, default=2)  # vem de ITEM_TYPES, pelo código

    def __post_init__(self):
        self.block = ITEM_TYPES[item_kind(self.code)][0]
        self.urgent = self.urgent or self.code in URGENT_CODES
        self.asks_partners = self.asks_partners or self.code in PARTNER_DECISION_CODES

    @property
    def is_message(self):
        return bool(self.template)

    @property
    def block_label(self):
        return BLOCKS[self.block]

    # só para a tela (card da fila, 19/11): o título "D7 · motivo" vira a etiqueta "D7" e a linha do motivo
    @property
    def day_tag(self):
        m = re.match(r"^(D\d+)\s*·\s*", self.title or "")
        return m.group(1) if m else ""

    @property
    def reason(self):
        return re.sub(r"^D\d+\s*·\s*", "", self.title or "")


class Queue(list):
    """Lista de itens da fila, com o que ficou de fora hoje."""

    sunday = False  # domingo a fila não traz envios
    overflow = 0  # mensagens que passaram do teto da gestora e ficam para amanhã
    deferred = 0  # mensagens que esperam porque o criador já tem outra hoje (uma por dia por criador)

    def __init__(self, *args):
        super().__init__(*args)
        self.overflow_by = {}  # as que passaram do teto, por gestora (para a tela Carteiras)


def fill_queue_messages(items, agency, **extra):
    """Preenche a mensagem pronta e o link do grupo dos itens que vão aparecer na tela.

    `extra` são variáveis que só a tela conhece (ex.: link_app, o endereço do app)."""
    from engage.services import pick_variant, render_message, templates_by_code

    from engage.services import whatsapp_link

    tpls = templates_by_code(agency)
    private = {cid: (group, phone) for cid, group, phone in CreatorPrivate.objects.filter(creator_id__in={i.creator.pk for i in items})
               .values_list("creator_id", "whatsapp_group_url", "whatsapp")}
    for i in items:
        i.group_url, phone = private.get(i.creator.pk, ("", ""))
        t = pick_variant(tpls.get(i.template, []), i.creator)  # variação da trilha e do "faz batalha" do criador
        if t is not None:
            replace = i.vars.get("_replace", {})  # trechos entre colchetes que o item já conhece (ex.: "@[oponente]")
            i.text = render_message(t.body, i.creator, **{**extra, **{k: v for k, v in i.vars.items() if k != "_replace"}})
            for old, new in replace.items():
                i.text = i.text.replace(old, new)
            # "Enviar no WhatsApp" (decisão da Mariana de 22/11): o grupo individual vem primeiro. Sem link do grupo e com o
            # número do criador, abre a conversa privada com a mensagem escrita (wa.me). Sem os dois, o caminho de antes
            # (g_open: WhatsApp com a mensagem, sem número). Abrir não registra contato: só "Marcar como enviada" registra.
            has_phone = bool(re.sub(r"\D", "", phone or ""))
            i.wa_url = whatsapp_link(phone, i.text) if has_phone and not i.group_url else ""
    return items


def contact_days(since, today):
    """Dias de segunda a sábado entre o último contato e hoje (o domingo não conta)."""
    return sum(1 for n in range(1, (today - since).days + 1) if (since + dt.timedelta(days=n)).weekday() != 6)


def no_live_steps(settings_):
    try:
        return sorted({int(x) for x in settings_.no_live_steps.split(",") if x.strip()}) or [4, 14, 21, 30]
    except ValueError:
        return [4, 14, 21, 30]


def _birthday_delta(private, today):
    """Dias até o próximo aniversário (0 = hoje). None sem data cadastrada."""
    if not private or not private.birth_day or not private.birth_month:
        return None
    for year in (today.year, today.year + 1):
        try:
            d = dt.date(year, private.birth_month, private.birth_day)
        except ValueError:  # 29/02 em ano que não é bissexto
            d = dt.date(year, 2, 28)
        if d >= today:
            return (d - today).days
    return None


def _pick_rotation(creator, last_code):
    """Mensagem do rodízio, pelo que há de novo para o criador, sem repetir o modelo da última vez."""
    facts = creator_facts(creator)
    options = []
    if creator.user_id:
        options.append(("ROD-APP", {}))
    lesson = next_lesson(creator, facts)
    if lesson:
        options.append(("ROD-AULA", {"proxima_aula": lesson.title}))
    from engage.campaigns import campaign_of_the_moment, campaign_vars

    moment = campaign_of_the_moment(creator, visible_campaigns(creator, facts, E.tiktok_today()))  # a gestora só oferece essa
    if moment:
        options.append(("ROD-CAMP", campaign_vars(moment["item"]["c"])))
    # "Vaga de batalha" (ROD-BAT) entra aqui quando o mural de batalhas existir (módulo de batalhas)
    options.append(("ROD-PERG", {}))
    for code, extra in options:
        if code != last_code:
            return code, extra
    return options[-1]


def _restriction_items(ctx):
    """Restrição ou banimento: todo dia, enquanto o caso estiver aberto. No 4º dia sem solução, está com as sócias."""
    from crm.models import AccountCase

    out = []
    limit = ctx["settings"].restriction_escalate_days
    for case in AccountCase.objects.filter(creator_id__in=ctx["ids"], resolved_at__isnull=True):
        n = case.days_open(timezone.localtime(ctx["now"]).date())
        extra = f" Dia {n} sem solução: o caso está com as sócias." if n >= limit else f" No dia {limit} sem solução, o caso sobe para as sócias."
        out.append(QueueItem(ctx["info"][case.creator_id]["c"], "restricao", 1, f"{case.get_kind_display()} na conta: dia {n}",
                             "Peça o print da restrição e da negativa do recurso, oriente o recurso, abra o chamado no TikTok "
                             f"e atualize a situação na ficha.{extra}"))
    return out


def _visit_items(ctx):
    """Sugestão de visita: até N por gestora por dia, nesta ordem: queda de prioridade 1, novato nos 5 primeiros dias
    de LIVE, grupo Diamante, potencial de graduação e quem está há 14 dias ou mais sem visita. Sempre com o motivo.

    Quem recebeu visita nos últimos 7 dias não é sugerido de novo (a não ser pela regra dos 14 dias)."""
    from django.db.models import Max

    from crm.models import Visit
    from data import phases
    from data.models import GroupRule

    today, st = ctx["today"], ctx["settings"]
    if today.weekday() == 6:
        return []  # domingo: só suporte
    last = dict(Visit.objects.filter(creator_id__in=ctx["ids"]).values("creator_id").annotate(d=Max("date")).values_list("creator_id", "d"))
    diamante = GroupRule.objects.filter(agency=ctx["agency"], name="Diamante").values_list("tier_min", flat=True).first() or 5
    ranked = []
    for pk, d in ctx["info"].items():
        c, ws = d["c"], d["ws"]
        if ws.state in ("sem_live", "inativo"):
            continue  # não há LIVE para visitar
        seen = last.get(pk)
        days = (today - seen).days if seen else None
        recent = days is not None and days < 7
        if ws.state == "queda" and ws.priority == 1 and not recent and d.get("readable", True):
            ranked.append((1, c, f"caiu {abs(ws.pct)}% na semana"))
        elif c.first_live_at and 0 <= (today - c.first_live_at).days < 5 and not recent:
            ranked.append((2, c, "novato nos 5 primeiros dias de LIVE"))
        elif d["tier"] >= diamante and not recent:
            ranked.append((3, c, "grupo Diamante"))
        elif not recent and getattr(phases.graduation_radar_row(c, d["snaps"], st, today), "potential", False):
            ranked.append((4, c, "potencial de graduação"))
        elif (days is None or days >= 14) and ws.week.hours > 0:
            ranked.append((5, c, f"há {days} dias sem visita" if days is not None else "ainda sem visita registrada"))
    ranked.sort(key=lambda r: (r[0], r[1].username))
    out, per_manager = [], {}
    for _rank, c, why in ranked:
        mgr = ctx["manager_of"].get(c.pk)
        if per_manager.get(mgr, 0) >= st.visit_suggestions_per_day:
            continue
        per_manager[mgr] = per_manager.get(mgr, 0) + 1
        out.append(QueueItem(c, "visita", 2, "Sugestão de visita", f"Motivo: {why}. Assista à próxima LIVE, marque “Visitei” na ficha com nota "
                             "de 1 a 3 e mande o retorno. Olhe cenário, câmera, áudio, interação, batalha e respeito às diretrizes."))
    return out


NR_STEPS = [(24, "NR-24H", "+24h"), (48, "NR-2D", "+2 dias"), (72, "NR-3D", "+3 dias (no privado, pela própria gestora)"), (120, "NR-5D", "+5 dias")]
# Fora do onboarding, a cadência é acionada pela régua de sem LIVE: a pergunta aberta do 4º dia e o contato dos 14 dias.
CADENCE_TRIGGERS = {"REG-04", "REG-14"}
# Depois do D15, o texto de cada etapa para quem já é da casa (decisão da Mariana de 18/11).
CADENCE_HOUSE = {"NR-24H": "NR-24H-CASA", "NR-2D": "NR-2D-CASA", "NR-3D": "NR-3D-CASA"}


def _recruiter(c):
    return f": {c.recruited_by.first_name or c.recruited_by.email}" if c.recruited_by_id else ""


def _cadence_items(ctx):
    """Cadência de não-resposta (Playbook, "Bloco de Referência"): um desvio que roda em paralelo, na carteira inteira.

    Entra sozinha quando uma mensagem fica sem "Respondeu" e sem LIVE depois dela:
    - no onboarding (até o D15), depois de qualquer mensagem do roteiro;
    - depois do D15, depois da pergunta aberta do 4º dia sem LIVE e do contato dos 14 dias (régua).
    Etapas: +24h, +2 dias, +3 dias (no privado, pela própria gestora) e +5 dias. Se seguir sem resposta depois do
    +5 dias, a gestora aciona quem recrutou. "Respondeu" na ficha ou uma LIVE encerram a cadência.
    A cadência iniciada à mão na ficha (CadenceState) continua existindo e, quando está ativa, vale no lugar desta."""
    from crm.models import CadenceState, Reply

    now, st, ids = ctx["now"], ctx["settings"], ctx["ids"]
    last_reply = {}
    for cid, at in Reply.objects.filter(creator_id__in=ids).order_by("created_at").values_list("creator_id", "created_at"):
        last_reply[cid] = at
    manual = set(CadenceState.objects.filter(creator_id__in=ids, resolved_at__isnull=True).values_list("creator_id", flat=True))
    out = []
    for pk, d in ctx["info"].items():
        d["waiting"] = False
        contacts = d["contacts"]
        base = next((x for x in contacts if not x.template_code.startswith("NR-")), None)  # última mensagem que não é da cadência
        if base is None or pk in manual:
            continue
        in_onboarding = d["day"] is not None and d["day"] <= st.onboarding_window_days + 1
        if not (in_onboarding or base.template_code in CADENCE_TRIGGERS):
            continue
        if pk in last_reply and last_reply[pk] >= base.sent_at:
            continue  # respondeu
        if d["last_live"] is not None and d["last_live"] >= timezone.localtime(base.sent_at).date():
            continue  # o dado confirma: houve LIVE depois da mensagem
        c = d["c"]
        prefix = f"D{d['day']} · " if in_onboarding else ""
        nr = [x for x in contacts if x.template_code.startswith("NR-") and x.sent_at > base.sent_at]  # mais recente primeiro
        if len(nr) < len(NR_STEPS):
            hours, code, label = NR_STEPS[len(nr)]
            d["waiting"] = True
            if now >= base.sent_at + dt.timedelta(hours=hours):
                # depois do D15, a versão para quem já é da casa (decisão de 18/11); o +5 dias é o mesmo para todos
                if not in_onboarding and code in CADENCE_HOUSE:
                    code = CADENCE_HOUSE[code]
                out.append(QueueItem(c, "cadencia", 1, f"{prefix}sem resposta: etapa {label}",
                                     f"A mensagem de {timezone.localtime(base.sent_at):%d/%m} ficou sem resposta e não houve LIVE depois dela. "
                                     f"Se o criador respondeu no grupo, marque “Respondeu” na ficha.", code))
        else:
            hours = (now - nr[0].sent_at).total_seconds() / 3600
            if 24 <= hours <= 24 * 6:  # do dia seguinte ao +5 dias até uma semana depois
                out.append(QueueItem(c, "cadencia_recrutou", 1, f"{prefix}sem resposta depois do +5 dias",
                                     f"A cadência terminou sem resposta. Acione quem recrutou{_recruiter(c)} e anote na ficha o que foi combinado."))
    return out


def _onboarding_items(ctx):
    """Roteiro do novato, pela data de entrada e pelo dado (Playbook: "Os relógios e as travas" e "Regra para criador inativo").

    1. Entrou e ainda não abriu LIVE: D1 boas-vindas e convite para o app; D2 regra dos 14 dias (sempre, mesmo sem resposta)
       e data da 1ª LIVE; data combinada que passou (apoio e, no dia seguinte, "está tudo bem?"); D3 mensagem de apoio;
       D5 entender o motivo; D7 transparência; D10 último dia viável; até o D14, encerramento com aprovação das sócias.
    2. Abriu LIVE: conferências do D3 e do D7; D10 (no caminho, ou "uma ajudinha com a contagem" com 0 a 2 dias válidos);
       D12 e D13 (reforço, ou transparência com 0 a 2 dias válidos e sem LIVE desde o D10, ou sem resposta);
       D14 (fechou, ou acolhimento sem cobrança); D15 (conversa de evolução, ou encerramento com aprovação das sócias).

    Os 14 dias contam do aceite no Backstage. Aparece só o passo mais adiantado que ainda não foi enviado.
    A trava da não-resposta fica em _cadence_items."""
    today, st = ctx["today"], ctx["settings"]
    window = st.onboarding_window_days
    out = []
    for pk, d in ctx["info"].items():
        day = d["day"]
        if day is None or day > window + 7:  # o D15 fica na fila por uma semana
            continue
        c, contacts, snaps, last_live = d["c"], d["contacts"], d["snaps"], d["last_live"]
        joined = c.joined_at.date()
        sent = {x.template_code for x in contacts if timezone.localtime(x.sent_at).date() >= joined}

        def sent_since(code, date):
            return any(x.template_code == code and timezone.localtime(x.sent_at).date() >= date for x in contacts)

        def add(code, prio, title, detail, template="", urgent=False):
            out.append(QueueItem(c, code, prio, f"D{day} · {title}", detail, template, urgent=urgent))

        socias ="Só com a aprovação das sócias: remova no Backstage, registre o motivo na ficha e então envie a mensagem de encerramento."
        if last_live is None:
            # 1. entrou e ainda não abriu LIVE
            planned = c.first_live_planned
            if day > 10:
                if "ONB-NL-ENC" not in sent:
                    add("onboarding_encerrar", 1, f"nunca abriu LIVE: encerramento até o D{window}",
                        f"Encerrando até o D{window}, o criador pode voltar sem espera. {socias}", "ONB-NL-ENC")
            elif day == 10:
                if "ONB-NL-D10" not in sent:
                    add("onboarding_nl10", 1, "sem LIVE: último dia para fechar os 5 dias válidos",
                        "Mensagem de transparência, no grupo e no privado. As sócias são avisadas hoje.", "ONB-NL-D10")
            elif day >= 7:
                if "ONB-NL-D7" not in sent:
                    add("onboarding_nl7", 1, "sem LIVE: transparência sobre a contagem do TikTok",
                        "Com as duas saídas possíveis: começar nesta semana, ou sair antes do 15º dia e voltar sem espera.", "ONB-NL-D7")
            elif day >= 5:
                if "ONB-NL-D5" not in sent:
                    add("onboarding_nl5", 2, "sem LIVE: entender o motivo (no privado)",
                        f"Registre o motivo na ficha (quadro “Parou de fazer LIVE?”) e acione quem recrutou{_recruiter(c)}.", "ONB-NL-D5")
            elif planned and planned < today and not sent_since("DES-D1-04", planned):
                add("onboarding_datapassou", 1, "a LIVE combinada não aconteceu", f"Estava combinada para {planned:%d/%m}. Mensagem de apoio, sem cobrança.", "DES-D1-04")
            elif planned and planned < today and "DES-D1-05" not in sent and not sent_since("DES-D1-04", today):
                add("onboarding_tudobem", 2, "a LIVE combinada não aconteceu: “está tudo bem?”", "Dia seguinte à mensagem de apoio, ainda sem LIVE.", "DES-D1-05")
            elif day >= 2 and "ONB-D2-04" not in sent:  # a regra dos 14 dias sai até o D2 para todos, mesmo sem resposta
                add("onboarding_d2", 2, "enviar a regra dos 14 dias" + ("" if planned else " e combinar a data da 1ª LIVE"),
                    "Envie mesmo sem resposta do criador" + ("." if planned else " e registre a data combinada na ficha (Cadastro).")
                    + " Lembre do módulo Começar antes da 1ª LIVE.", "ONB-D2-04")
            elif not planned and day >= 3 and "DES-D1-04" not in sent:
                add("onboarding_nl3", 2, "sem LIVE e sem data combinada: mensagem de apoio",
                    "Mensagem de apoio do roteiro e oferta de combinar a 1ª LIVE. Registre a data na ficha (Cadastro).", "DES-D1-04")
            elif day == 1 and "ONB-D1-01" not in sent:
                add("onboarding_d1", 2, "boas-vindas no grupo individual", "Primeiro contato. Depois, convide para o primeiro acesso ao app.", "ONB-D1-01")
            elif day <= 2 and not c.user_id and "CONVITE-APP" not in sent and not d.get("waiting"):
                add("onboarding_app", 3, "convite para o primeiro acesso ao app", "Gere o código de acesso na ficha (quadro “Acesso ao app”) antes de enviar.", "CONVITE-APP")
            continue
        # 2. já abriu LIVE
        ob = E.onboarding_status(c, snaps, st)
        if not ob:
            continue
        nums = f"{ob['valid_days']} de {st.onboarding_valid_days} dias válidos e {fmt_hours(ob['hours'])} de {st.onboarding_hours}h"
        few = ob["valid_days"] <= 2
        if ob["met"]:
            if "META-D14" not in sent:
                add("onboarding_fechou", 2, "fechou a regra dos 14 dias 🎉", f"{nums}. Reconhecimento.", "META-D14", urgent=day >= window)
            elif day >= 15 and "TIER-D15" not in sent:
                add("onboarding_d15", 2, "conversa de evolução", f"{nums} nos primeiros 14 dias. Mostre a evolução desde o dia 1 e marque o 1:1 de desenvolvimento.", "TIER-D15")
        elif day >= 15:
            if "ONB-D15-ENC" not in sent:
                add("onboarding_encerrar15", 1, "não fechou a regra dos 14 dias: encerramento",
                    f"{nums}. Regra da Hera: quem não fechou 5 dias válidos e 15h é excluído depois do D15. {socias}", "ONB-D15-ENC")
        elif day == 14:
            if "META-D14-NAO" not in sent:
                add("onboarding_acolher", 1, "os 14 dias terminam hoje sem fechar a regra: acolhimento",
                    f"{nums}. Não envie cobrança. Registre o que o criador disser e aplique a árvore de decisão (frequência antes de qualquer ação).", "META-D14-NAO")
        elif day >= 12:
            no_live_since_d10 = last_live < joined + dt.timedelta(days=9)
            if few and (no_live_since_d10 or d.get("waiting")):
                if "META-D12-TRANSP" not in sent:
                    add("onboarding_risco", 1, "regra dos 14 dias em risco: transparência",
                        f"{nums} e sem LIVE desde o D10, ou sem resposta. No grupo e no privado: explica a regra e que dá para sair agora e voltar sem espera. "
                        "Com motivo pessoal informado, ofereça seguir agora ou sair agora.", "META-D12-TRANSP")
            elif "META-D12" not in sent:
                add("onboarding_risco", 1, "regra dos 14 dias em risco: reforço", f"{nums}. Sem cobrança: se houver algo pessoal, acolha antes de sugerir.", "META-D12")
        elif day >= 10:
            if few:
                if "META-D10-RISCO" not in sent:
                    add("onboarding_risco", 1, "regra dos 14 dias em risco: uma ajudinha com a contagem", f"{nums}. Mensagem de apoio, sem cobrança, com pergunta aberta.", "META-D10-RISCO")
            elif "META-D10" not in sent:
                add("onboarding_d10", 2, "conferência dos dias válidos: no caminho", f"{nums}. Olhe o Backstage antes de enviar.", "META-D10")
        elif day in (3, 7):
            add(f"onboarding_conf{day}", 3, f"conferência do D{day}", f"{nums}. Se estiver atrás, combine os próximos dias de LIVE com o criador (ele escolhe).")
    return out


def _monthly_1a1_items(ctx):
    """1:1 do mês (passo 4.2): regra em crm/one_on_one.py."""
    from crm.one_on_one import queue_items

    return queue_items(ctx)


def _in_last_week(today):
    from .month_items import in_last_week

    return in_last_week(today)


def _month_items(name):
    """Itens do mês (passo 4.3): regras em web/month_items.py. O "nível novo" sai junto com o resumo do mês."""
    def collect(ctx):
        from . import month_items

        return getattr(month_items, name)(ctx)

    return collect


def _campaign_items(ctx):
    """Acompanhamento de campanha (passo 4.5): regras em engage/campaigns.py:queue_items."""
    from engage.campaigns import queue_items

    return queue_items(ctx)


def _to_build(_ctx):
    """Tipo já declarado em ITEM_TYPES que ainda não gera itens (depende de módulo que não existe)."""
    return []


# Quem gera os itens de cada tipo fora do laço principal. Tipo novo: uma linha aqui e outra em ITEM_TYPES.
COLLECTORS = {
    "cadencia": _cadence_items,     # antes do onboarding: ele consulta se o criador está esperando resposta
    "onboarding": _onboarding_items,
    "restricao": _restriction_items,
    "visita": _visit_items,
    "1a1_mes": _monthly_1a1_items,
    "campanha": _campaign_items,    # dia seguinte à abertura, metade, véspera do fechamento, dia seguinte ao fim
    "rodada_batalhas": _to_build,   # dia 8: batalhas oficiais do mês seguinte para Ouro e Diamante
    "resumo_mes": _month_items("summary_items"),   # dias 1 a 7: primeiro quem foi menos constante (e o nível novo)
    "quase_la": _month_items("almost_items"),      # última semana: perto do próximo nível ou da graduação (prêmio de campanha: "campanha", prioridade 1)
    "modulo_concluido": _month_items("module_items"),
    "risco_diamante": _month_items("risk_items"),
}


def action_queue(creators, agency, today=None, now=None, raw=False):
    """Fila do dia da gestão: quem precisa de contato hoje, por quê, e com qual mensagem.

    Regras: 4 blocos em ordem; uma mensagem por dia por criador; teto por gestora; domingo sem envios;
    um item só sai quando a gestora marca "Enviei", adia com motivo, ou o dado muda."""
    from data.states import analysed_sunday, week_state, weeks_readable

    now = now or timezone.now()
    today = today or E.tiktok_today()
    settings_ = AgencySettings.objects.get(agency=agency)
    rules = E.tier_rules(agency)
    steps = no_live_steps(settings_)
    week_start = analysed_sunday(today) + dt.timedelta(days=1)  # segunda da semana corrente
    day_start = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
    items = []
    creators = list(creators.exclude(status__in=[CreatorStatus.SAIU, CreatorStatus.ANONIMIZADO]).select_related("private")
                    .prefetch_related("snapshots", "dismissals", "contacts", "stop_reasons", "assignments"))
    ids = [c.pk for c in creators]
    pm = E.prev_month(analysed_sunday(today))
    lm = {m.creator_id: m for m in MonthlyResult.objects.filter(creator_id__in=ids, month=pm)}
    contacted_today, manager_of, info = set(), {}, {}
    for c in creators:
        dismissed = {d.code for d in c.dismissals.all() if d.until > now}
        snaps = list(c.snapshots.all())
        contacts = list(c.contacts.all())  # mais recente primeiro
        if contacts and contacts[0].sent_at >= day_start:
            contacted_today.add(c.pk)
        manager_of[c.pk] = next((a.manager_id for a in c.assignments.all() if a.valid_to is None), None)
        cur = [s for s in snaps if E.month_start(s.period_start) == E.month_start(today)]
        snap = cur[-1] if cur else None
        day = c.days_in_agency(today)
        ws = week_state(c, snaps, today, prev_month_diamonds=lm[c.pk].diamonds if c.pk in lm else 0)
        ivs = E.intervals(snaps)
        last_live = next((iv.end for iv in reversed(ivs) if iv.had_live), None)  # último dia com LIVE nos dados (None = nunca abriu)
        info[c.pk] = {"c": c, "ws": ws, "snaps": snaps, "dismissed": dismissed, "tier": (lm[c.pk].tier or 1) if c.pk in lm else 1,
                      "contacts": contacts, "day": day, "last_live": last_live}
        mine = []

        def add(code, prio, title, detail, template="", **vars_):
            if code not in dismissed:
                mine.append(QueueItem(c, code, prio, title, detail, template, vars=vars_, state=ws))

        def sent_since(code, date):
            return any(x.template_code == code and timezone.localtime(x.sent_at).date() >= date for x in contacts)

        # ---------------- bloco 2: o que tem data
        # (o roteiro do novato, do D1 ao D15, fica em _onboarding_items)
        # régua sem LIVE depois do D15 (4, 14, 21 e 30 dias), só para quem já fez LIVE
        after_onboarding = day is None or day > settings_.onboarding_window_days + 1
        if last_live is not None and after_onboarding:
            dwl = (ivs[-1].end - last_live).days
            sr = next(iter(c.stop_reasons.all()), None)  # motivo mais recente
            back = sr.return_date if sr and sr.return_date and timezone.localtime(sr.created_at).date() >= last_live else None
            stage = max((s for s in steps if s <= dwl), default=None)
            if back and today < back:
                pass  # informou a data de volta: silêncio até lá
            elif back and dwl >= steps[0] and not sent_since("REG-VOLTA", back):
                add("volta", 2, "Data de volta chegou", f"Informou que voltaria em {back:%d/%m} e ainda não abriu LIVE. Mensagem de boas-vindas de volta.", "REG-VOLTA")
            elif stage is not None and not sent_since(f"REG-{stage:02d}", last_live + dt.timedelta(days=1)):
                how = {
                    steps[0]: "Pergunta aberta no grupo individual, sem cobrança. Depois da conversa, registre o motivo na ficha. "
                              "Sem resposta, a cadência de não-resposta entra sozinha.",
                    14: "No privado, com oferta de conversa curta. Sem resposta, a cadência de não-resposta entra sozinha.",
                    21: "Conversa de alinhamento, no privado ou por ligação, com o aviso transparente de que, com 30 dias sem LIVE, a parceria é encerrada.",
                    steps[-1]: "Encerramento. Só com a aprovação das sócias: remova no Backstage, registre o motivo na ficha e então envie a mensagem.",
                }.get(stage, "Contato da régua de quem está sem LIVE, sem cobrança.")
                add(f"regua_{stage}", 1 if stage == steps[-1] else 2, f"Sem LIVE há {dwl} dias (régua: {stage} dias)",
                    f"Última LIVE em {last_live:%d/%m}, pela última leitura. {how}", f"REG-{stage:02d}")
                if stage == steps[-1] and mine and mine[-1].code == f"regua_{stage}":
                    mine[-1].asks_partners = True  # encerramento dos 30 dias: "Pedir decisão às sócias" (passo 4.1)
        # aniversário: no dia, e convite 30 dias antes (fica na fila por uma semana)
        delta = _birthday_delta(getattr(c, "private", None), today)
        if delta == 0 and not sent_since("ANIV-DIA", today):
            add("aniversario", 1, "Aniversário hoje 🎂", "Parabéns no grupo individual.", "ANIV-DIA")
        elif delta is not None and 24 <= delta <= 30 and not sent_since("ANIV-30", today - dt.timedelta(days=10)):
            add("aniversario_30", 3, f"Aniversário em {delta} dias", "Ofereça uma batalha oficial ou uma LIVE de aniversário.", "ANIV-30")

        # ---------------- bloco 3: o que vem do dado (estado da última semana completa)
        w = ws.week
        semana = f"Semana de {w.start:%d/%m} a {w.end:%d/%m}: {fmt_int(w.diamonds)} 💎"
        # decisão da Mariana de 19/11: semana sem leitura própria (ex.: mês importado de uma vez) não gera queda, subida
        # nem semana irregular, porque a conta compararia semanas vazias com semanas infladas (data/states.py)
        readable = weeks_readable(snaps, ws)
        info[c.pk]["readable"] = readable
        if not readable:
            pass
        elif ws.state == "queda" and not (sent_since("APO-03", week_start) or sent_since("QUEDA-01", week_start)):
            why = ("Caíram as horas ou os dias válidos: a conversa é sobre rotina, não sobre resultado." if ws.hours_dropped
                   else "Horas e dias mantidos: veja audiência, presentes e batalhas; se nada explicar, assista a uma LIVE.")
            add("queda", ws.priority, f"Queda de {abs(ws.pct)}% na semana ({ws.segment_label})",
                f"{semana}, contra o normal de {fmt_int(ws.base)}. {why}", "APO-03" if ws.hours_dropped else "QUEDA-01")
        elif ws.state == "subindo" and today.weekday() >= 2 and not sent_since("REC-01", week_start):
            add("subindo", ws.priority, f"Subindo {ws.pct}% na semana ({ws.segment_label})",
                f"{semana}, contra o normal de {fmt_int(ws.base)}. Reconheça e pergunte o que mudou.", "REC-01")
        elif ws.state == "irregular" and ws.base >= 2000 and today.weekday() >= 2 and not sent_since("APO-03", week_start):
            add("irregular", ws.priority, f"Semana irregular ({ws.segment_label})",
                f"{semana} em {w.valid_days} dia{'s' if w.valid_days != 1 else ''} válido{'s' if w.valid_days != 1 else ''}. Conversa sobre rotina.", "APO-03")
        # na última semana do mês, "perto" vira o item "Quase lá", com mensagem (passo 4.3, web/month_items.py)
        last_week = _in_last_week(today)
        if snap and not last_week:
            tier, _ = E.official_tier(c, today, rules)
            nxt = E.next_tier_rule(tier, rules)
            if nxt and nxt.min_diamonds * settings_.near_tier_pct / 100 <= snap.diamonds < nxt.min_diamonds:
                add("perto_tier", 3, f"Perto do Tier {nxt.tier}", f"{fmt_int(snap.diamonds)} de {fmt_int(nxt.min_diamonds)} diamantes neste mês.")
        # Graduação: diamantes do mês corrente, só dentro da janela (regra do TikTok, valores em AgencySettings)
        grad = None if last_week else E.graduation_status(c, snap, settings_, today)
        if grad and not grad["graduated"] and grad["diamonds"] >= grad["target"] * settings_.near_tier_pct / 100:
            add("perto_graduar", 3, f"Perto de graduar ({fmt_int(grad['target'])} no mês)",
                f"{fmt_int(grad['diamonds'])} diamantes neste mês · faltam {fmt_int(grad['missing'])} · janela de graduação até {grad['window_end']:%d/%m}.")

        # ---------------- bloco 4: rodízio (ninguém fica mais de N dias, de segunda a sábado, sem mensagem individual)
        in_onboarding = day is not None and day <= settings_.onboarding_window_days  # o roteiro do novato cuida dele
        if not any(i.is_message for i in mine) and not in_onboarding and ws.state not in ("sem_live", "inativo"):
            last = timezone.localtime(contacts[0].sent_at).date() if contacts else (c.joined_at.date() if c.joined_at else None)
            quiet = contact_days(last, today) if last else settings_.contact_limit_days
            if quiet >= settings_.contact_limit_days:
                add("rodizio", 3, f"{quiet} dias sem mensagem individual" if contacts else "Ainda sem mensagem individual registrada",
                    "Rodízio: avise o que há de novo para o criador. Não envie resumo de números pelo WhatsApp.", "ROD",
                    _last_code=contacts[0].template_code if contacts else "")
        items.extend(mine)

    cad = CadenceState.objects.filter(creator_id__in=ids, resolved_at__isnull=True).select_related("creator")
    for cs in cad:
        if cs.due_at <= now:
            items.append(QueueItem(cs.creator, "cadencia", 1, f"Sem resposta: enviar etapa {cs.get_step_display()}",
                                   "Cadência de não-resposta do Playbook.", CadenceState.STEP_TEMPLATE[cs.step]))
    for o in OneOnOne.objects.filter(creator_id__in=ids, b7_next_date__lt=today).select_related("creator"):
        latest = o.creator.one_on_ones.first()
        if latest and latest.pk == o.pk:
            items.append(QueueItem(o.creator, "1a1_atrasado", 3, "1:1 atrasado", f"Estava marcado para {o.b7_next_date:%d/%m}."))
    for a in ActionItem.objects.filter(creator_id__in=ids, done=False, due_date__lt=today).select_related("creator"):
        items.append(QueueItem(a.creator, "plano_vencido", 3, "Plano de ação vencido", f"{a.action} (combinado para {a.due_date:%d/%m})."))
    for r in Reminder.objects.filter(creator_id__in=ids, done_at__isnull=True, due_date__lte=timezone.localtime(now).date()).select_related("creator"):
        items.append(QueueItem(r.creator, "lembrete", 2, f"Lembrete de {r.due_date:%d/%m}", f"{r.text} Marque “Feito” na ficha."))
    # batalha oficial confirmada (decisão de 18/11): do 4º ao 1º dia antes, a mensagem BAT-4D até o "Enviei"; no dia, a BAT-DIA
    soon = today + dt.timedelta(days=4)
    for b in BattleRequest.objects.filter(creator_id__in=ids, status="aprovada", date__gte=today, date__lte=soon).select_related("creator"):
        n = (b.date - today).days
        ci = info.get(b.creator.pk, {})
        tpl, since = ("BAT-DIA", today) if n == 0 else ("BAT-4D", b.date - dt.timedelta(days=4))
        if "batalha_proxima" in ci.get("dismissed", ()) or any(
                x.template_code == tpl and timezone.localtime(x.sent_at).date() >= since for x in ci.get("contacts", [])):
            continue
        quando = "hoje" if n == 0 else f"em {n} dia{'s' if n > 1 else ''}"
        opp = battle_rules.opponent_handle(b.opponent_text, empty="o oponente")
        detail = (f"{b.date:%d/%m} às {b.time:%H:%M} com {opp}. " +
                  ("Mensagem do dia da batalha." if n == 0 else
                   "Mensagem dos 4 dias antes. Checklist: ferramentas (luvas), divulgação nos vídeos e nas LIVEs, confirmação com a "
                   "agência oponente, seguir o oponente e LIVE aberta para todos."))
        items.append(QueueItem(b.creator, "batalha_proxima", 1 if n == 0 else 2, f"Batalha oficial {quando}", detail, tpl,
                               vars={"_replace": {"@[oponente]": battle_rules.opponent_handle(b.opponent_text)}}, state=ci.get("ws")))
    for b in BattleRequest.objects.filter(creator_id__in=ids, status="pendente").select_related("creator"):
        items.append(QueueItem(b.creator, "batalha", 2, "Pedido de batalha", f"{b.get_kind_display()} em {b.date:%d/%m} às {b.time:%H:%M}."))
    # pedidos da tela Ajuda (passo 3.5); o aviso de restrição já abriu o caso da conta, que tem o próprio item ("restricao")
    ticket_titles = {"duvida": "Dúvida sem resposta no app", "conversa": "Pedido de conversa pelo app",
                     "saida": "Quer conversar sobre sair da agência"}
    for t in SupportTicket.objects.filter(creator_id__in=ids, status="aberto").exclude(kind="restricao").select_related("creator"):
        items.append(QueueItem(t.creator, "duvida", 1, ticket_titles.get(t.kind, ticket_titles["duvida"]), t.question[:120]))
    # tipos gerados à parte (ver COLLECTORS): restrição, visita e os que ainda devolvem lista vazia
    ctx = {"info": info, "ids": ids, "today": today, "now": now, "settings": settings_, "agency": agency, "manager_of": manager_of}
    for kind, collect in COLLECTORS.items():
        for it in collect(ctx):
            if it.code not in info[it.creator.pk]["dismissed"]:
                it.state = it.state or info[it.creator.pk]["ws"]
                items.append(it)

    def key(i):
        return (i.block, i.priority, i.creator.username)

    if raw:  # tudo o que foi gerado, sem as regras do dia (quadro de onboarding usa para mostrar o próximo passo)
        return Queue(sorted(items, key=key))
    out = Queue(i for i in items if not i.is_message)
    messages = sorted((i for i in items if i.is_message and i.creator.pk not in contacted_today), key=key)
    # uma mensagem por dia por criador: vale a primeira pela ordem da fila; as outras esperam o próximo dia livre
    seen, one_each = set(), []
    for i in messages:
        if i.creator.pk in seen:
            out.deferred += 1
        else:
            seen.add(i.creator.pk)
            one_each.append(i)
    if today.weekday() == 6:  # domingo: a fila não traz envios
        out.sunday = True
        one_each = []
    # teto por gestora: o que passa fica para amanhã, começando pelo fim da fila (rodízio)
    sent_by = {}
    for uid in Contact.objects.filter(sent_at__gte=day_start, user_id__in={m for m in manager_of.values() if m}).values_list("user_id", flat=True):
        sent_by[uid] = sent_by.get(uid, 0) + 1
    for i in one_each:
        mgr = manager_of.get(i.creator.pk)
        if mgr is not None:
            if sent_by.get(mgr, 0) >= settings_.daily_message_cap:
                out.overflow += 1
                out.overflow_by[mgr] = out.overflow_by.get(mgr, 0) + 1
                continue
            sent_by[mgr] = sent_by.get(mgr, 0) + 1
        if i.template == "ROD":
            i.template, extra = _pick_rotation(i.creator, i.vars.pop("_last_code", ""))
            i.vars.update(extra)
        out.append(i)
    out.sort(key=key)
    return out


# ------------------------------------------------------------------ ausência da gestora e carteiras
def portfolio_of(agency, manager_id):
    """Criadores da carteira vigente de uma gestora."""
    return Creator.objects.filter(agency=agency, assignments__manager_id=manager_id, assignments__valid_to__isnull=True).distinct()


def coverage_blocks(user, agency, is_admin, today=None, now=None):
    """Para quem cobre: os itens que NÃO podem esperar das carteiras de quem avisou "Hoje não trabalho".

    Os outros itens da gestora ausente não aparecem: passam para o dia seguinte, na ordem da fila.
    Valem as regras do dia (uma mensagem por criador, domingo sem envios)."""
    from crm import absence

    blocks = []
    for a in absence.to_show(user, agency, is_admin):
        queue = action_queue(portfolio_of(agency, a.manager_id), agency, today=today, now=now)
        blocks.append({"absence": a, "manager": absence.name_of(a.manager), "cover": absence.name_of(a.cover),
                       "mine": a.cover_id == user.pk or (a.cover_id is None and is_admin),
                       "items": [i for i in queue if i.urgent], "waiting": sum(1 for i in queue if not i.urgent)})
    return blocks


def portfolio_overview(agency, today=None, now=None):
    """Tela Carteiras (sócias): uma linha por gestora, com o tamanho da carteira, a fila de hoje e as ausências.

    Devolve (linhas, sem_gestora). Entram as gestoras ativas e também quem ainda tem criadores na carteira sem ter
    mais o papel (para as sócias redistribuírem)."""
    from django.contrib.auth import get_user_model

    from core.models import Membership, Role
    from crm import absence
    from crm.models import PortfolioAssignment

    User = get_user_model()
    st = AgencySettings.objects.get(agency=agency)
    today = today or E.tiktok_today()
    active = Creator.objects.filter(agency=agency).exclude(status__in=[CreatorStatus.SAIU, CreatorStatus.ANONIMIZADO])
    by_manager, newcomers = {}, {}
    current = PortfolioAssignment.objects.filter(creator__in=active, valid_to__isnull=True).values_list("manager_id", "creator__joined_at")
    for mid, joined in current:
        by_manager[mid] = by_manager.get(mid, 0) + 1
        if joined and (today - joined.date()).days + 1 <= st.onboarding_window_days + 1:
            newcomers[mid] = newcomers.get(mid, 0) + 1
    members = {m.user_id: m for m in Membership.objects.filter(agency=agency, role=Role.GESTORA).select_related("covered_by")}
    ids = {uid for uid, m in members.items() if m.active} | set(by_manager)
    queue = action_queue(active, agency, today=today, now=now)
    msgs = {}
    for i in queue:
        if i.is_message:
            mid = next((a.manager_id for a in i.creator.assignments.all() if a.valid_to is None), None)
            msgs[mid] = msgs.get(mid, 0) + 1
    skipped, upcoming = absence.skipped_days(agency), absence.upcoming(agency)
    away = {a.manager_id: a for a in absence.to_show(None, agency, True)}
    candidates = {u.pk for u in absence.cover_candidates(agency)}
    rows = []
    for u in User.objects.filter(pk__in=ids).order_by("first_name", "email"):
        m = members.get(u.pk)
        cover = m.covered_by if m and m.covered_by_id in candidates else None
        rows.append({"user": u, "name": absence.name_of(u), "active": bool(m and m.active), "n": by_manager.get(u.pk, 0),
                     "newcomers": newcomers.get(u.pk, 0), "messages": msgs.get(u.pk, 0), "overflow": queue.overflow_by.get(u.pk, 0),
                     "cover": cover, "away": away.get(u.pk), "away_cover": absence.name_of(away[u.pk].cover) if u.pk in away else "",
                     "skipped": skipped.get(u.pk, []), "upcoming": upcoming.get(u.pk, [])})
    unassigned = active.exclude(pk__in=PortfolioAssignment.objects.filter(valid_to__isnull=True).values("creator_id")).count()
    return rows, {"n": unassigned, "messages": msgs.get(None, 0)}


def dashboard_numbers(creators, agency):
    today = E.tiktok_today()
    ids = list(creators.values_list("pk", flat=True))
    m0, pm = E.month_start(today), E.prev_month(today)
    latest = (CreatorSnapshot.objects.filter(creator_id__in=ids, period_start=m0).values("creator_id")
              .annotate(end=Max("period_end")))
    cur = {}
    for row in latest:
        s = CreatorSnapshot.objects.filter(creator_id=row["creator_id"], period_start=m0, period_end=row["end"]).first()
        cur[row["creator_id"]] = s
    active_statuses = [CreatorStatus.ATIVO, CreatorStatus.CONVIDADO, CreatorStatus.PENDENTE, CreatorStatus.EM_SAIDA]
    act = creators.filter(status__in=active_statuses)
    with_live = sum(1 for s in cur.values() if s and s.live_seconds > 0)
    diamonds_now = sum(s.diamonds for s in cur.values() if s)
    end_ref = max((s.period_end for s in cur.values() if s), default=today)
    # mês passado até o mesmo dia (comparação justa) = proporcional ao total do mês passado
    last_total = MonthlyResult.objects.filter(creator_id__in=ids, month=pm).aggregate(t=Sum("diamonds"))["t"] or 0
    elapsed = (end_ref - m0).days + 1
    import calendar

    last_same_point = last_total * elapsed / calendar.monthrange(pm.year, pm.month)[1]
    rules = E.tier_rules(agency)
    dist = {r.tier: 0 for r in rules}
    for m in MonthlyResult.objects.filter(creator_id__in=act.values_list("pk", flat=True), month=pm):
        dist[m.tier or 1] = dist.get(m.tier or 1, 0) + 1
    maxd = max(dist.values()) or 1
    return {
        "active": act.count(), "with_live": with_live, "without_live": act.count() - with_live,
        "new": creators.filter(joined_at__date__gte=m0).count(), "diamonds": diamonds_now,
        "diamonds_last_same_point": last_same_point,
        "diamonds_change": (diamonds_now / last_same_point - 1) if last_same_point else None,
        "tier_dist": [{"tier": t, "n": n, "pct": n / maxd} for t, n in sorted(dist.items())],
        "updated_at": data_freshness(agency), "end_ref": end_ref,
        "import": import_status(agency),
    }

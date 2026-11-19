"""Resumo do mês no app (Meu progresso), pedido da Mariana de 19/11/2026.

Quando o mês fecha, o criador vê no topo do Meu progresso, do dia 1 ao dia 10, um cartão como o resumo que a Hera
envia: a mudança de nível, onde ele se superou (sempre comparado com ele mesmo, mês contra mês) e 2 ideias para o mês
que começa. Depois do dia 10, o resumo de cada mês continua em "Meses desde a entrada".

Regras do tom: "Nível" no lugar de "Tier"; nada de meta, cobrança, prazo ou horário; nunca sugere número de horas, de
dias nem horário; nada de comparação com outro criador. As ideias saem de um banco de dicas com regras (sem
inteligência artificial até a etapa 5). A gestora pode escrever a própria dica na ficha (`MonthTip`), que entra no
lugar da primeira dica automática.

Dados que ainda não chegam (pessoas que mandaram presentes, vídeos) só entram quando houver a leitura detalhada por
criador. As dicas são provisórias até a revisão da Mariana.
"""
import datetime as dt

from data import engine as E

TOP_UNTIL_DAY = 10  # o cartão fica no topo do Meu progresso do dia 1 ao dia 10
MAX_HIGHLIGHTS = 3
MAX_TIPS = 2

MONTHS_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
             "novembro", "dezembro"]


def _fmt(n):
    return f"{int(round(n)):,}".replace(",", ".")


def _h(hours):
    return (f"{hours:.1f}".replace(".", ",") + "h").replace(",0h", "h")


class Month:
    """Os números de um mês fechado: o mês fechado (MonthlyResult) e a última leitura daquele mês (seguidores, fã-clube,
    diamantes de batalha e de convidado, que o mês fechado não guarda)."""

    def __init__(self, mr, snap):
        self.month = mr.month
        self.tier = mr.tier or 1
        self.diamonds = mr.diamonds or 0
        self.hours = (mr.live_seconds or 0) / 3600
        self.valid_days = mr.valid_days or 0
        self.streams = mr.streams if mr.streams is not None else (snap.streams if snap else None)
        self.battles = mr.battles if mr.battles is not None else (snap.battles if snap else None)
        self.new_followers = snap.new_followers if snap else None
        self.new_fans = snap.new_fans if snap else None
        self.battle_diamonds = snap.battle_diamonds if snap else 0
        self.guest_diamonds = snap.guest_diamonds if snap else 0

    @property
    def had_live(self):
        return self.hours > 0 or self.valid_days > 0 or bool(self.streams)


def _month(creator, month):
    from data.models import CreatorSnapshot, MonthlyResult

    mr = MonthlyResult.objects.filter(creator=creator, month=month).first()
    if mr is None:
        return None
    snap = CreatorSnapshot.objects.filter(creator=creator, period_start=month).order_by("-period_end").first()
    return Month(mr, snap)


# ------------------------------------------------------------------ primeira linha: o nível
def headline(cur, prev, groups):
    name = MONTHS_PT[cur.month.month - 1]
    g = E.group_for_tier(cur.tier, groups) if groups else ""
    if prev is None:
        return f"Seu primeiro mês fechado com a Hera: Nível {cur.tier}" + (f", grupo {g}" if g else "") + " 🎉"
    if cur.tier > prev.tier:
        pg = E.group_for_tier(prev.tier, groups) if groups else ""
        tail = (f" e passou para o grupo {g}" if g != pg else f" e segue no grupo {g}") if g else ""
        icon = " 💎🚀" if g == (groups[-1].name if groups else "") else " 🚀"
        return f"Você subiu do Nível {prev.tier} para o Nível {cur.tier}{tail}{icon}"
    return f"Você fechou {name} no Nível {cur.tier}" + (f", no grupo {g}" if g else "") + " 💜"


# ------------------------------------------------------------------ onde se superou
def highlights(cur, prev):
    """Os números que mais melhoraram contra o mês anterior (até 3). Sem mês anterior ou sem melhora: um fato do mês."""
    if prev is not None:
        pname = MONTHS_PT[prev.month.month - 1]
        cands = []

        def add(cur_v, prev_v, min_gain, text):
            if cur_v is None or prev_v is None:
                return
            gain = cur_v - prev_v
            if gain >= min_gain and cur_v > 0:
                cands.append(((gain / prev_v) if prev_v else 10.0, text(cur_v, gain)))

        if prev.diamonds and cur.diamonds > prev.diamonds:
            pct = (cur.diamonds / prev.diamonds - 1) * 100
            if pct >= 5:
                cands.append((pct / 100, f"{pct:.0f}% a mais de diamantes que em {pname} 📈"))
        add(cur.new_followers, prev.new_followers, 10, lambda v, g: f"{_fmt(v)} seguidores novos, {_fmt(g)} a mais que em {pname} 👥")
        add(cur.new_fans, prev.new_fans, 3, lambda v, g: f"{_fmt(v)} pessoas novas no seu fã-clube, {_fmt(g)} a mais que em {pname} 💜")
        add(cur.battles, prev.battles, 3, lambda v, g: f"{_fmt(v)} batalhas, {_fmt(g)} a mais que em {pname} ⚔️")
        add(cur.valid_days, prev.valid_days, 2, lambda v, g: f"{v} dias válidos, {g} a mais que em {pname} 📅")
        add(cur.hours, prev.hours, 3, lambda v, g: f"{_h(v)} de LIVE, {_h(g)} a mais que em {pname} ⏱️")
        cands.sort(key=lambda x: -x[0])
        if cands:
            return [t for _, t in cands[:MAX_HIGHLIGHTS]]
    # fato do mês (primeiro mês, ou mês sem melhora): o que ele fez, sem comparação
    parts = []
    if cur.streams:
        parts.append(f"{cur.streams} LIVE{'s' if cur.streams != 1 else ''}")
    if cur.valid_days:
        parts.append(f"{cur.valid_days} dia{'s' if cur.valid_days != 1 else ''} válido{'s' if cur.valid_days != 1 else ''}")
    out = [f"Você fez {' em '.join(parts)} 💪"] if parts else []
    if cur.diamonds:
        out.append(f"{_fmt(cur.diamonds)} diamantes no mês 💎")
    return out


# ------------------------------------------------------------------ ideias para o mês (banco de dicas, provisório)
# Cada dica: (código, regra, texto). As regras olham só os números do criador. A ordem decide a prioridade.
def _ratio(a, b):
    return a / b if b else 0


TIPS = [
    ("seguidores", lambda c, p, x: (c.new_followers or 0) >= 20 and (p is None or (c.new_followers or 0) > (p.new_followers or 0)),
     "Seus seguidores novos estão chegando. Avisar no vídeo e no perfil quando vai ser a próxima LIVE leva essa gente até você."),
    ("mais_live_menos_diamantes", lambda c, p, x: p is not None and c.hours > p.hours and c.diamonds < p.diamonds,
     "Quando a LIVE cresce e os presentes não acompanham, vale testar ganchos de conversa e chamar as pessoas pelo nome. "
     "A aula de interação da Hera Academy mostra como."),
    ("fa_clube", lambda c, p, x: c.new_fans is not None and c.new_fans <= 0 and c.hours >= 10,
     "Lembrar do Heart Me durante a LIVE ajuda quem gosta de você a entrar no seu fã-clube."),
    ("batalha", lambda c, p, x: (c.battles or 0) < 10 and c.hours >= 5,
     "Batalhas costumam mexer bastante com os diamantes. Se quiser, peça uma batalha oficial pelo app: a Hera busca alguém do seu nível."),
    ("batalha_rende", lambda c, p, x: _ratio(c.battle_diamonds, c.diamonds) >= 0.6,
     "As batalhas estão rendendo bem pra você. Avisar o público antes da batalha ajuda a ter mais gente com você na hora."),
    ("cohost", lambda c, p, x: (c.guest_diamonds or 0) == 0 and c.hours >= 10,
     "Co-host e convidados trazem público novo dos dois lados. Vale chamar para a sua LIVE alguém que você admira."),
    ("ritmo", lambda c, p, x: p is not None and c.valid_days < p.valid_days,
     "Escolher os seus dias de LIVE no Meu plano ajuda a manter o ritmo do jeito que funciona pra você."),
    ("graduacao", lambda c, p, x: x.get("in_graduation_window"),
     "Você ainda está na janela de graduação do TikTok. Se quiser planejar o mês com a Hera, é só chamar."),
    ("cortes", lambda c, p, x: (c.new_followers or 0) < 10 and c.hours >= 10,
     "Cortes curtos da sua LIVE viram vídeos que levam gente nova para o seu perfil."),
    ("repetir", lambda c, p, x: p is not None and p.diamonds and c.diamonds >= p.diamonds * 1.3,
     "O que você fez de diferente neste mês funcionou. Vale repetir o formato que mais rendeu."),
    ("campanha", lambda c, p, x: x.get("has_campaign"),
     "Dá uma olhada em Campanhas no app: a campanha do momento foi escolhida para combinar com o seu jeito de fazer LIVE."),
    ("titulo_capa", lambda c, p, x: True,
     "Um título claro e uma capa com o seu rosto ajudam a LIVE a chamar atenção no feed."),
    ("academy", lambda c, p, x: True,
     "A aula recomendada em Meu progresso foi escolhida pelo seu mês. São poucos minutos e tem ideias para testar na próxima LIVE."),
]


def tips(cur, prev, extra, own=None):
    chosen = [own] if own else []
    for _code, rule, text in TIPS:
        if len(chosen) >= MAX_TIPS:
            break
        try:
            ok = rule(cur, prev, extra)
        except (TypeError, ZeroDivisionError):
            ok = False
        if ok and text not in chosen:
            chosen.append(text)
    return chosen


# ------------------------------------------------------------------ o resumo
def for_month(creator, month, extra=None):
    """Resumo de um mês fechado (None se o mês não fechou ou não teve LIVE)."""
    from data.models import GroupRule
    from engage.models import MonthTip

    cur = _month(creator, month)
    if cur is None or not cur.had_live:
        return None
    prev = _month(creator, E.prev_month(month))
    if prev is not None and not prev.had_live:
        prev = None
    groups = list(GroupRule.objects.filter(agency=creator.agency).order_by("order"))
    nxt = E.month_start(E.month_end(month) + dt.timedelta(days=1))
    own = MonthTip.objects.filter(creator=creator, month=month).first()
    hl = highlights(cur, prev)
    return {
        "month": month, "month_name": MONTHS_PT[month.month - 1], "next_name": MONTHS_PT[nxt.month - 1],
        "headline": headline(cur, prev, groups), "highlights": hl,
        "highlights_title": "Onde você se superou" if any("a mais" in t for t in hl) else "O seu mês",
        "tips": tips(cur, prev, extra or {}, own.text if own else None), "own_tip": own,
    }


def current(creator, today=None, extra=None):
    """O resumo do mês que acabou de fechar, para o topo do Meu progresso (dias 1 a 10). None fora desses dias."""
    today = today or E.tiktok_today()
    if today.day > TOP_UNTIL_DAY:
        return None
    return for_month(creator, E.prev_month(today), extra)


def notify_ready(agency, today=None):
    """Rotina diária, dias 2 e 3: avisa no sininho do app que o resumo do mês chegou. Um aviso por mês por criador.

    Começa no dia 2 porque o último dia do mês só chega com a leitura do dia 1 (até as 10h), depois da rotina das 6h."""
    from crm.models import Creator, CreatorStatus
    from engage.models import Notification

    today = today or E.tiktok_today()
    if not 2 <= today.day <= 3:
        return 0
    month = E.prev_month(today)
    since = E.month_start(today)
    sent = 0
    for c in Creator.objects.filter(agency=agency, user__isnull=False).exclude(status__in=[CreatorStatus.SAIU, CreatorStatus.ANONIMIZADO]):
        if Notification.objects.filter(user_id=c.user_id, kind="resumo_mes", created_at__date__gte=since).exists():
            continue
        if for_month(c, month) is None:
            continue  # o mês ainda não fechou para ele (a leitura chega até as 10h) ou não teve LIVE
        Notification.objects.create(user_id=c.user_id, kind="resumo_mes", url="/", title=f"Seu resumo de {MONTHS_PT[month.month - 1]} chegou 🎉",
                                    body="Veja onde você se superou e as ideias para o mês, em Meu progresso.")
        sent += 1
    return sent


def extra_for(creator, today=None):
    """O que as dicas precisam saber além dos números: janela de graduação e campanha do momento."""
    from core.models import AgencySettings

    today = today or E.tiktok_today()
    st = AgencySettings.objects.get(agency=creator.agency)
    in_window = bool(creator.joined_at and (today - creator.joined_at.date()).days < st.graduation_window_days)
    return {"in_graduation_window": in_window}

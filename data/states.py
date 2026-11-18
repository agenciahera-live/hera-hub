"""Estado da semana, segmento, prioridade e sinais de cada criador.

Regras trazidas como estão do Acompanhamento Semanal (docs/regras-estado-prioridade.md, extraídas de build_semana.py).
Não mude limite nenhum aqui sem mudar aquele documento.

Atenção: SEGMENTO (Top, Médio, Desenvolvimento, Base) não é GRUPO (Bronze, Prata, Ouro, Diamante).
O segmento vem do ritmo de diamantes e serve para priorizar a fila. O grupo vem do Tier do mês fechado
(data/engine.py) e serve para as campanhas internas. As duas classificações convivem.

Diferenças para o script, por causa dos dados que o app recebe:
- o script lê 7 períodos direto do Backstage; aqui as semanas saem da diferença entre snapshots;
- "dias sem LIVE" sai do último intervalo com LIVE (o app não recebe a data da última LIVE);
- o sinal "Sem vídeos" não é calculado: a exportação "Dados do criador" não traz a coluna de vídeos.
"""
import calendar
import datetime as dt
from dataclasses import dataclass, field
from statistics import median

from . import engine as E

STATES = [
    ("inativo", "Inativo 30d+"),
    ("sem_live", "Sem LIVE"),
    ("queda", "Queda"),
    ("subindo", "Subindo"),
    ("novo", "Novo"),
    ("horas_sem_retorno", "Horas sem retorno"),
    ("irregular", "Irregular"),
    ("estavel", "Estável"),
]
STATE_LABELS = dict(STATES)
SEGMENTS = [("top", "Top", 100_000), ("medio", "Médio", 20_000), ("desenvolvimento", "Desenvolvimento", 2_000), ("base", "Base", 0)]
SEGMENT_LABELS = {code: label for code, label, _ in SEGMENTS}
NEVER = 999  # dias sem LIVE de quem nunca fez LIVE (como no script)


@dataclass
class Week:
    start: dt.date
    end: dt.date
    diamonds: int = 0
    live_seconds: int = 0
    valid_days: int = 0
    battles: int = 0
    new_fans: int = 0

    @property
    def hours(self):
        return self.live_seconds / 3600


@dataclass
class WeekState:
    state: str
    segment: str
    priority: int
    weeks: list  # 5 semanas, da mais antiga (w0) para a analisada (w4)
    base: float  # normal do criador: mediana dos diamantes das 3 semanas anteriores
    pct: int = None  # variação da semana contra o normal, em % (None quando o normal é zero)
    since: int = NEVER  # dias sem LIVE
    signals: list = field(default_factory=list)
    hours_dropped: bool = False  # caíram as horas ou os dias válidos (primeira pergunta do diagnóstico de queda)

    @property
    def week(self):
        return self.weeks[4]

    @property
    def label(self):
        return STATE_LABELS[self.state]

    @property
    def segment_label(self):
        return SEGMENT_LABELS[self.segment]


def analysed_sunday(today):
    """Domingo que fecha a última semana completa (segunda a domingo, dias do TikTok)."""
    return today - dt.timedelta(days=today.weekday() + 1)


def last_weeks(snaps, sunday, n=5):
    weeks = [Week(sunday - dt.timedelta(days=6 + 7 * (n - 1 - i)), sunday - dt.timedelta(days=7 * (n - 1 - i))) for i in range(n)]
    for iv in E.intervals(snaps):
        for w in weeks:
            if w.start <= iv.end <= w.end:
                w.diamonds += iv.diamonds
                w.live_seconds += iv.live_seconds
                w.valid_days += iv.valid_days
                w.battles += iv.battles
                w.new_fans += iv.new_fans
                break
    return weeks


def days_since_live(snaps, ref):
    """Dias entre a última LIVE e `ref` (a segunda depois da semana analisada). NEVER se não houve LIVE."""
    last = None
    for iv in E.intervals(snaps):
        if iv.had_live and iv.end < ref:
            last = iv.end
    return NEVER if last is None else max(0, (ref - last).days)


def segment_for(snaps, sunday, prev_month_diamonds):
    """Segmento pelo maior entre o mês anterior inteiro e a projeção do mês corrente até o domingo."""
    m0 = E.month_start(sunday)
    cur = [s for s in snaps if E.month_start(s.period_start) == m0 and s.period_end <= sunday]
    mtd = cur[-1].diamonds if cur else 0
    proj = mtd * calendar.monthrange(sunday.year, sunday.month)[1] / sunday.day
    mref = max(prev_month_diamonds or 0, proj)
    for code, _label, floor in SEGMENTS:
        if mref >= floor:
            return code
    return "base"


def _state(weeks, base, pct, since, joined_days):
    w4, w3 = weeks[4], weeks[3]
    if since >= 30:
        return "inativo"
    if since >= 7 or (w4.valid_days == 0 and w4.hours < 1 and w3.valid_days == 0):
        return "sem_live"
    if base >= 2000 and pct is not None and pct < -30:
        return "queda"
    if w4.diamonds >= 2000 and pct is not None and pct >= 30:
        return "subindo"
    if joined_days is not None and joined_days <= 30:
        return "novo"
    if w4.hours >= 10 and (w4.diamonds / w4.hours) < 150:
        return "horas_sem_retorno"
    if w4.valid_days <= 3:
        return "irregular"
    return "estavel"


def _priority(state, segment, base, weeks):
    w4 = weeks[4]
    topmed = segment in ("top", "medio")
    if ((topmed and state in ("queda", "sem_live")) or (state == "queda" and base >= 5000)
            or (state == "subindo" and (segment == "top" or w4.diamonds >= 50_000))):
        return 1
    if (state in ("subindo", "horas_sem_retorno") or (state == "novo" and w4.valid_days > 0)
            or (state == "irregular" and base >= 2000) or (state == "estavel" and topmed)):
        return 2
    return 3


def _signals(state, weeks, has_fans_data):
    w4, w3 = weeks[4], weeks[3]
    out = []
    if (w4.hours + w3.hours) >= 20 and (w4.battles + w3.battles) < 10:
        out.append("Quase sem batalhas")
    if has_fans_data and w4.new_fans <= 0 and w4.hours >= 5:
        out.append("Fã-clube parado")
    if 1 <= w4.valid_days <= 4 and state != "irregular":
        out.append(f"{w4.valid_days} dia{'s' if w4.valid_days > 1 else ''} válido{'s' if w4.valid_days > 1 else ''}")
    return out


def week_state(creator, snaps, today=None, prev_month_diamonds=None):
    """Estado da última semana completa. `prev_month_diamonds`: diamantes do mês anterior fechado (quem chama pode passar)."""
    today = today or E.tiktok_today()
    sunday = analysed_sunday(today)
    monday_after = sunday + dt.timedelta(days=1)
    weeks = last_weeks(snaps, sunday)
    base = median([w.diamonds for w in weeks[1:4]])
    pct = round((weeks[4].diamonds / base - 1) * 100) if base else None
    since = days_since_live(snaps, monday_after)
    joined_days = (monday_after - creator.joined_at.date()).days if creator.joined_at else None
    if prev_month_diamonds is None:
        from .models import MonthlyResult

        mr = MonthlyResult.objects.filter(creator=creator, month=E.prev_month(sunday)).first()
        prev_month_diamonds = mr.diamonds if mr else 0
    segment = segment_for(snaps, sunday, prev_month_diamonds)
    state = _state(weeks, base, pct, since, joined_days)
    # Passo 1 do diagnóstico de queda (docs/regras-estado-prioridade.md, "Cortes do diagnóstico de queda").
    # Aqui é MÉDIA das 3 semanas anteriores, de propósito: só os diamantes usam mediana (um presente grande
    # distorce a semana); horas e dias não têm esse pico. Não uniformize.
    avg_hours = sum(w.hours for w in weeks[1:4]) / 3
    avg_days = sum(w.valid_days for w in weeks[1:4]) / 3
    dropped = (avg_hours > 0 and weeks[4].hours < 0.7 * avg_hours) or (weeks[4].valid_days <= avg_days - 2)
    return WeekState(state, segment, _priority(state, segment, base, weeks), weeks, base, pct, since,
                     _signals(state, weeks, any(s.new_fans is not None for s in snaps)), dropped)

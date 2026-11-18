"""Motor de fases (visão, "O motor de fases"): em que momento da jornada cada criador está.

A fase vem da data de entrada e dos dados do Backstage; ninguém marca à mão. Nada é gravado: a fase é
calculada na hora, a partir dos snapshots, e por isso nunca fica desatualizada.

    Chegada → Novato → Primeiro mês → Graduação → Veterano
                 └────────── Pausa (de qualquer fase depois da chegada) ──────────┘   e Saída

Os limites (14 dias, 30 dias, janela de graduação, dias sem LIVE da pausa) ficam em AgencySettings.
"""
import datetime as dt
from dataclasses import dataclass

from crm.models import CreatorStatus

from . import engine as E

PHASES = [
    ("chegada", "Chegada"),
    ("novato", "Novato"),
    ("primeiro_mes", "Primeiro mês"),
    ("graduacao", "Graduação"),
    ("veterano", "Veterano"),
    ("pausa", "Pausa"),
    ("saida", "Saída"),
]
LABELS = dict(PHASES)


@dataclass
class Phase:
    code: str  # fase que vale hoje
    base: str  # fase da jornada pelo tempo de casa (a pausa e a saída ficam por cima dela)
    day: int = None  # dia de casa (D1 = dia da entrada)
    detail: str = ""

    @property
    def label(self):
        return LABELS[self.code]

    @property
    def base_label(self):
        return LABELS[self.base]


def _journey(creator, snaps, settings_, today, has_contact, ever_live):
    """Fase pelo tempo de casa e pela regra dos 14 dias, sem olhar pausa nem saída."""
    day = creator.days_in_agency(today)
    if day is None:
        return "veterano", None, "Sem data de entrada no Backstage."
    if day <= settings_.onboarding_window_days:
        ob = E.onboarding_status(creator, snaps, settings_)
        if not (ob and ob["met"]):
            if not has_contact and not ever_live:
                return "chegada", day, f"D{day}: ainda sem primeiro contato registrado e sem LIVE."
            falta = f"faltam {ob['need_days']} dia(s) válido(s) e {ob['need_hours']:.1f}h" if ob else ""
            return "novato", day, f"D{day} de {settings_.onboarding_window_days}: {falta} da regra do TikTok.".replace(".0h", "h")
    if day <= settings_.first_month_days:
        return "primeiro_mes", day, f"D{day} de {settings_.first_month_days}."
    if day <= settings_.graduation_window_days:
        end = creator.joined_at.astimezone(dt.timezone.utc).date() + dt.timedelta(days=settings_.graduation_window_days - 1)
        return "graduacao", day, f"Janela de graduação até {end:%d/%m}."
    return "veterano", day, ""


def phase_for(creator, snaps=None, settings_=None, today=None, has_contact=None):
    """Fase do criador hoje. `has_contact`: já existe um "Enviei" registrado (quem chama pode passar, para não consultar de novo)."""
    from core.models import AgencySettings

    settings_ = settings_ or AgencySettings.objects.get(agency=creator.agency)
    today = today or E.tiktok_today()
    snaps = snaps if snaps is not None else list(creator.snapshots.all())
    if has_contact is None:
        has_contact = creator.contacts.exists()
    ivs = E.intervals(snaps)
    ever_live = any(iv.had_live for iv in ivs)
    base, day, detail = _journey(creator, snaps, settings_, today, has_contact, ever_live)
    if creator.status in (CreatorStatus.SAIU, CreatorStatus.ANONIMIZADO):
        return Phase("saida", base, day, "Saiu da agência.")
    if creator.status == CreatorStatus.EM_SAIDA:
        return Phase("pausa", base, day, "Em aviso prévio de saída.")
    if base != "chegada":
        if ever_live:
            dwl = E.days_without_live(snaps)
            if dwl is not None and dwl >= settings_.pause_after_days:
                return Phase("pausa", base, day, f"Sem LIVE há {dwl} dias (pela última leitura).")
        elif day is not None and day > settings_.onboarding_window_days:
            return Phase("pausa", base, day, "Entrou e nunca abriu LIVE.")
    return Phase(base, base, day, detail)


# ------------------------------------------------------------------ radar de graduação
@dataclass
class RadarRow:
    creator: object
    day: int
    window_end: dt.date
    diamonds: int
    target: int
    missing: int
    avg_per_day: float
    needed_per_day: float
    forecast: float
    status: str  # faixas do Acompanhamento Semanal (docs/regras-estado-prioridade.md), ver STATUS_LABELS
    last_month: bool
    graduations: int  # meses já fechados com a marca, dentro da janela

    STATUS_LABELS = {"conferir": "Conferir graduação", "graduou": "Bateu a marca no mês", "no_ritmo": "No ritmo",
                     "acelerar": "Precisa acelerar", "dificil": "Difícil no mês", "no_radar": "No radar", "formacao": "Em formação"}
    ORDER = ["conferir", "no_ritmo", "acelerar", "dificil", "no_radar", "formacao", "graduou"]

    @property
    def status_label(self):
        return self.STATUS_LABELS[self.status]

    @property
    def potential(self):
        """Potencial de graduação (1:1 mensal e escolha de campanha): No ritmo e Precisa acelerar."""
        return self.status in ("no_ritmo", "acelerar")


def graduation_radar_row(creator, snaps, settings_, today=None, monthly=None):
    """Linha do radar para quem está na janela de graduação (None para quem está fora).

    Regra do TikTok: X diamantes em UM mês, dentro dos primeiros N dias de casa. Conta o mês corrente."""
    today = today or E.tiktok_today()
    m0 = E.month_start(today)
    cur = [s for s in snaps if E.month_start(s.period_start) == m0]
    snap = cur[-1] if cur else None
    g = E.graduation_status(creator, snap, settings_, today)
    if g is None:
        return None
    from .states import analysed_sunday, last_weeks

    target = g["target"]
    if snap:
        pace = E.compute_pace(snap.diamonds, target, snap.period_start, snap.period_end)
        avg, needed, forecast = pace.avg_per_day, pace.needed_per_day, pace.forecast
    else:
        avg = forecast = 0.0
        needed = float("inf")
    start = creator.joined_at.astimezone(dt.timezone.utc).date()
    monthly = monthly if monthly is not None else list(creator.monthly.all())
    done = sum(1 for m in monthly if m.month < m0 and m.diamonds >= target and E.month_end(m.month) >= start and m.month <= g["window_end"])
    week = last_weeks(snaps, analysed_sunday(today))[4]
    last_closed = next((m for m in monthly if m.month == E.prev_month(today)), None)
    not_graduated = bool(snaps) and "não se graduou" in (snaps[-1].graduation_status or "").lower()
    # faixas testadas nesta ordem (regras do Acompanhamento Semanal)
    if last_closed and last_closed.diamonds >= target and not_graduated:
        status = "conferir"  # fez a marca no mês anterior, mas o Backstage ainda diz "Não se graduou"
    elif g["graduated"]:
        status = "graduou"
    elif forecast >= target:
        status = "no_ritmo"
    elif forecast >= target / 2:
        status = "acelerar"
    elif g["diamonds"] >= 5000 or week.diamonds >= 3000:
        status = "dificil"
    elif week.hours < 3:
        status = "no_radar"
    else:
        status = "formacao"
    return RadarRow(creator, g["day"], g["window_end"], g["diamonds"], target, g["missing"], avg, needed, forecast, status,
                    last_month=E.month_start(g["window_end"]) == m0, graduations=done)

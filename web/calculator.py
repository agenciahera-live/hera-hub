"""Calculadora "Onde posso chegar" (etapa 5, passo 5.2; visão, "Calculadora 'Onde posso chegar'" e item 4 do
Meu progresso, "Simulador").

- A base são os diamantes por dia de LIVE do próprio criador nas últimas 8 semanas (`LOOKBACK_DAYS`). A faixa vai
  do 1º ao 3º quartil (metade dos dias dele fica dentro dela); a mediana fica guardada para a gestão conferir.
- O criador escolhe quantos dos dias que faltam no mês pretende fazer LIVE. O número de dias vem dele, nunca da Hera:
  o controle começa no ritmo atual dele (dias válidos do mês até agora, levados até o fim do mês).
- O app mostra a faixa de diamantes do fechamento (o que já fez + dias × faixa) e o nível em que ela cai.
- Três referências fixas: o ritmo atual ("No seu ritmo"), o melhor mês dele e quanto falta para o próximo nível.
- Sempre "Estimativa pelo seu histórico, não é garantia", sempre em diamantes (nunca em reais).
- Só aparece com pelo menos 3 semanas de dados (`MIN_DATA_DAYS`) e 3 dias de LIVE na base; no D1 a D14 a tela
  inicial mostra a contagem do TikTok e não tem calculadora.
"""
import datetime as dt
import statistics

from data import engine as E
from data.models import MonthlyResult

LOOKBACK_DAYS = 56  # 8 semanas
MIN_DATA_DAYS = 21  # 3 semanas de dados
MIN_LIVE_DAYS = 3


def live_day_values(snaps, until):
    """Diamantes por dia de LIVE nas últimas 8 semanas até `until`.

    Leitura diária: cada dia com LIVE é um valor. Leitura de vários dias juntos: o total dividido pelos dias válidos
    do intervalo (pelo menos 1), repetido esse número de vezes, para pesar como dias."""
    since = until - dt.timedelta(days=LOOKBACK_DAYS - 1)
    vals = []
    for iv in E.intervals(snaps):
        if iv.end < since or iv.end > until or not iv.had_live:
            continue
        n = 1 if iv.days == 1 else max(iv.valid_days, 1)
        vals += [max(iv.diamonds, 0) / n] * n
    return vals


def calculator(creator, snaps, snap, level, forecast, rules, today):
    """Os números da calculadora para a tela (o cálculo da faixa é feito no celular, conforme os dias escolhidos)."""
    if not snap or not rules or not snaps:
        return None
    m0 = E.month_start(today)
    if E.month_start(snap.period_end) != m0:
        return None  # o mês virou e a leitura do mês novo ainda não chegou
    remaining = (E.month_end(m0) - snap.period_end).days
    if remaining <= 0:
        return None
    first = min(s.period_start for s in snaps)
    start = max(first, creator.joined_at.date()) if creator.joined_at else first
    if (snap.period_end - start).days + 1 < MIN_DATA_DAYS:
        return None
    vals = live_day_values(snaps, snap.period_end)
    if len(vals) < MIN_LIVE_DAYS:
        return None
    q1, median, q3 = statistics.quantiles(vals, n=4, method="inclusive")
    if q3 <= 0:
        return None
    elapsed = (snap.period_end - m0).days + 1
    default = min(remaining, round(snap.valid_days / elapsed * remaining))
    best = MonthlyResult.objects.filter(creator=creator, month__lt=m0, diamonds__gt=0).order_by("-diamonds").first()
    nxt = level.get("next")
    return {
        "current": snap.diamonds, "remaining": remaining, "default": default, "low": q1, "high": q3, "median": median,
        "samples": len(vals), "tiers": [[r.tier, r.min_diamonds] for r in rules], "until": snap.period_end,
        "forecast": forecast, "best": best,
        "next": nxt if nxt and not level.get("reached") else None, "missing": level.get("missing"),
    }


def js_data(calc):
    """O que o celular precisa para refazer a conta quando o criador mexe nos dias."""
    return {k: calc[k] for k in ("current", "remaining", "default", "low", "high", "tiers")}

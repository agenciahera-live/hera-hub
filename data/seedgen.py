"""Gerador de exportações FICTÍCIAS no formato real do TikTok Backstage.

Nenhum dado real: nomes, IDs e e-mails são inventados (sufixo .demo).
Gera ~120 creators distribuídos pelos 10 Tiers, 3 meses (jul–set/2026), exportações semanais
"Dados do criador" (PT, acumulado do período, duração e % em texto) e "Task" (EN) de jul e ago.
"""
import calendar
import datetime as dt
import random
from pathlib import Path

import openpyxl

from core.bootstrap import BACKSTAGE_PT_MAP, TASK_EN_MAP

LEFT = "O criador deixou a agência"
DIRECT = "Não está em um grupo"
GROUPS = [DIRECT, DIRECT, DIRECT, "Rede Aurora", "Rede Boreal", "Coletivo Cometa", "Estúdio Delta"]
AGENTS = ["gestora1@hera.demo", "gestora2@hera.demo", "gestora3@hera.demo"]
NAMES = ["ana", "bia", "carol", "duda", "elis", "fabi", "gabi", "helo", "iara", "ju", "kaka", "lari", "malu", "nina",
         "olga", "paty", "quel", "rafa", "sol", "tati", "vivi", "yas", "zoe", "leo", "theo", "davi", "enzo", "caio", "luan", "igor"]

# Diamantes "típicos" por mês para cada Tier alvo (min, max)
TIER_BANDS = {1: (0, 36_000), 2: (42_000, 76_000), 3: (85_000, 145_000), 4: (155_000, 240_000), 5: (255_000, 340_000),
              6: (360_000, 490_000), 7: (510_000, 780_000), 8: (820_000, 1_150_000), 9: (1_250_000, 1_550_000), 10: (1_650_000, 2_100_000)}
TIER_COUNTS = {1: 78, 2: 14, 3: 9, 4: 6, 5: 4, 6: 3, 7: 2, 8: 2, 9: 1, 10: 1}

MONTHS = [dt.date(2026, 7, 1), dt.date(2026, 8, 1), dt.date(2026, 9, 1)]
SNAPSHOT_ENDS = {
    dt.date(2026, 7, 1): [5, 12, 19, 26, 31],
    dt.date(2026, 8, 1): [2, 9, 16, 23, 30, 31],
    dt.date(2026, 9, 1): [6, 13, 20, 27],
}
TASK_MONTHS = [dt.date(2026, 7, 1), dt.date(2026, 8, 1)]

BACKSTAGE_BASE_COLS = [h for h in BACKSTAGE_PT_MAP if h not in ("Novos fãs", "Total de Diamantes do Fã-clube", "% de contribuição de fãs", "Total de fãs", "Fãs ativos do Fã-clube", "Status")]
FAN_COLS = ["Novos fãs", "Total de Diamantes do Fã-clube", "% de contribuição de fãs", "Total de fãs", "Fãs ativos do Fã-clube"]


def fmt_duration(sec):
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def fmt_pct(x):
    return "-" if x is None else f"{x * 100:.2f}%"


class Sim:
    """Simula dia a dia um creator fictício."""

    def __init__(self, rnd, idx, tier):
        self.rnd = rnd
        self.idx = idx
        self.tier = tier
        self.id = str(7_400_000_000_000_000_000 + rnd.randint(10**15, 9 * 10**16))
        self.username = f"{NAMES[idx % len(NAMES)]}.{rnd.choice(['lives', 'on', 'play', 'show', 'vibes'])}{idx:03d}.demo"
        self.group = rnd.choice(GROUPS)
        self.agent = AGENTS[idx % len(AGENTS)]
        lo, hi = TIER_BANDS[tier]
        self.base = rnd.randint(lo, hi)
        # frequência: Tiers altos fazem mais LIVE
        self.p_live = min(0.95, 0.25 + 0.07 * tier + rnd.uniform(-0.1, 0.2))
        self.join = dt.datetime(2026, 7, 1, tzinfo=dt.timezone.utc) - dt.timedelta(days=rnd.randint(40, 700), hours=rnd.randint(0, 23), minutes=rnd.randint(0, 59))
        self.leave = None  # data de saída
        self.daily = {}  # date -> (diamonds, seconds, valid, streams, battles, followers)
        self.dormant = tier == 1 and rnd.random() < 0.15
        self.drop_sep = tier <= 3 and rnd.random() < 0.08  # queda em setembro (alimenta alerta)

    def month_factor(self, month):
        f = self.rnd.uniform(0.8, 1.15)
        if self.drop_sep and month.month == 9:
            f *= 0.35
        return f

    def simulate(self, month):
        days = calendar.monthrange(month.year, month.month)[1]
        target = self.base * self.month_factor(month)
        p = self.p_live * (0.15 if self.drop_sep and month.month == 9 else 1.0)
        if self.dormant:
            p = 0.05
        live_days = []
        for d in range(1, days + 1):
            day = month.replace(day=d)
            if self.join.date() > day or (self.leave and day >= self.leave):
                continue
            if self.rnd.random() < p:
                live_days.append(day)
        per_day = target / max(len(live_days), 1)
        for day in live_days:
            secs = int(self.rnd.uniform(0.4, 1.4 + 0.25 * self.tier) * 3600)
            streams = 1 if self.rnd.random() < 0.8 else 2
            dia = int(max(per_day * self.rnd.uniform(0.3, 1.7), 0)) if target > 0 else 0
            battles = self.rnd.randint(0, 1 + self.tier * 2)
            fol = self.rnd.randint(0, 5 + self.tier * 8)
            self.daily[day] = (dia, secs, 1 if secs >= 3600 else 0, streams, battles, fol)

    def cumulative(self, start, end):
        tot = [0, 0, 0, 0, 0, 0]
        d = start
        while d <= end:
            v = self.daily.get(d)
            if v:
                tot = [a + b for a, b in zip(tot, v)]
            d += dt.timedelta(days=1)
        return tot


def build(seed=42):
    rnd = random.Random(seed)
    sims = []
    idx = 0
    for tier, n in TIER_COUNTS.items():
        for _ in range(n):
            sims.append(Sim(rnd, idx, tier))
            idx += 1
    # 6 novatos que entram em agosto e setembro (Primeiro Mês)
    for k in range(6):
        s = Sim(rnd, idx, 1 if k < 5 else 2)
        s.join = dt.datetime(2026, 8 if k < 3 else 9, rnd.randint(3, 20), rnd.randint(0, 23), rnd.randint(0, 59), tzinfo=dt.timezone.utc)
        s.p_live = rnd.uniform(0.4, 0.8)
        sims.append(s)
        idx += 1
    # 5 saídas ao longo do período
    for s in rnd.sample([s for s in sims if s.tier == 1 and s.join.month < 7], 5):
        s.leave = dt.date(2026, rnd.choice([8, 9]), rnd.randint(5, 20))
    for m in MONTHS:
        for s in sims:
            s.simulate(m)
    return sims


def _month_totals(s, month):
    return s.cumulative(month, month.replace(day=calendar.monthrange(month.year, month.month)[1]))


def backstage_rows(sims, month, end_day, with_fans):
    start = month
    end = month.replace(day=end_day)
    prev = (month - dt.timedelta(days=1)).replace(day=1)
    rows = []
    for s in sims:
        if s.join.date() > end:
            continue
        period = f"{start.isoformat()} ~ {end.isoformat()}"
        left = s.leave and s.leave <= end
        dia, sec, vd, st, bt, fol = s.cumulative(start, end)
        lm = _month_totals(s, prev) if prev >= MONTHS[0] or True else None
        lm_dia, lm_sec, lm_vd, lm_st, _, lm_fol = lm
        tgt_dia = max(int(lm_dia * 1.1), 5000)
        tgt_sec, tgt_vd, tgt_st, tgt_fol = max(lm_sec, 15 * 3600), max(lm_vd, 5), max(lm_st, 5), max(lm_fol, 20)
        days_in = (end - s.join.date()).days
        row = {
            "Período dos dados": period,
            "ID do criador": LEFT if left else s.id,
            "Nome do criador": s.username,
            "Grupo": s.group,
            "Agente": "" if left else s.agent,
            "Horário de ingresso": "-" if left else s.join.strftime("%Y-%m-%d %H:%M:%S") + " (UTC+0)",
            "Dias desde que entrou para a rede": "-" if left else str(days_in),
            "Diamantes": str(dia),
            "Duração da LIVE": fmt_duration(sec),
            "Dias válidos de início de LIVE": str(vd),
            "Novos seguidores": str(fol),
            "Transmissões de LIVE": str(st),
            "Diamantes do mês passado": str(lm_dia),
            "Duração de LIVE (horas) no último mês": fmt_duration(lm_sec),
            "Dias de início de LIVE válidos no mês passado": str(lm_vd),
            "Novos seguidores no último mês": str(lm_fol),
            "Transmissões de LIVE no mês passado": str(lm_st),
            "Diamantes - Porcentagem alcançada": fmt_pct(dia / tgt_dia),
            "Duração da LIVE - Porcentagem alcançada": fmt_pct(sec / tgt_sec),
            "Dias válidos de início de LIVE - Porcentagem alcançada": fmt_pct(vd / tgt_vd),
            "Novos seguidores - Porcentagem alcançada": fmt_pct(fol / tgt_fol),
            "Transmissões de LIVE - Porcentagem alcançada": fmt_pct(st / tgt_st),
            "Diamantes - vs. mês passado": fmt_pct(dia / lm_dia - 1) if lm_dia else "-",
            "Duração da LIVE - vs. mês passado": fmt_pct(sec / lm_sec - 1) if lm_sec else "-",
            "Dias válidos de início de LIVE - vs. mês passado": fmt_pct(vd / lm_vd - 1) if lm_vd else "-",
            "Novos seguidores - vs. mês passado": fmt_pct(fol / lm_fol - 1) if lm_fol else "-",
            "Transmissões de LIVE - vs. mês passado": fmt_pct(st / lm_st - 1) if lm_st else "-",
            "Batalhas": str(bt),
            "Diamantes obtidos de batalhas": str(int(dia * 0.35)),
            "Novos criadores de LIVE": "Sim" if s.join.date() >= month else "Não",
            "Diamantes de convidados": str(int(dia * 0.05)),
            "Diamantes de convidados (como apresentador)": str(int(dia * 0.03)),
            "Diamantes de convidados (como convidado)": str(int(dia * 0.02)),
            "Status da graduação": "Criador já existente" if days_in > 90 else ("Graduou-se" if dia >= 80_000 else "Não se graduou"),
            "Status do nível": "-" if end_day < 20 else ("Subiu de nível" if dia > lm_dia * 1.2 else ("Mantido" if dia >= lm_dia * 0.9 else "Não foi mantido")),
        }
        if with_fans:
            row.update({"Novos fãs": str(fol // 3), "Total de Diamantes do Fã-clube": str(int(dia * 0.4)),
                        "% de contribuição de fãs": f"{s.rnd.uniform(0.3, 0.99):.5f}", "Total de fãs": str(100 + fol * 4),
                        "Fãs ativos do Fã-clube": str(fol)})
        row["Status"] = "Saiu" if left else ""
        rows.append(row)
    return rows


def task_rows(sims, month):
    rows = []
    end = month.replace(day=calendar.monthrange(month.year, month.month)[1])
    for s in sims:
        if s.join.date() > end or (s.leave and s.leave <= end):
            continue
        dia, sec, vd, *_ = _month_totals(s, month)
        rows.append({
            "Data Month": month.strftime("%Y%m"), "Creator ID": s.id, "Creator nickname": s.username, "Handle": s.username,
            "Creator Network manager": "rede@hera.demo", "Group": s.group, "Group manager": "gestor.grupo@hera.demo",
            "Is violative creators": False, "The creator was Rookie at the time of first joining": "Yes" if (end - s.join.date()).days < 90 else "No",
            "Diamonds": dia, "Valid days(d)": vd, "LIVE duration(h)": round(sec / 3600, 3),
            "Estimated bonus": round(dia * 0.0003, 4), "Estimated bonus - Maintained tiers": 0,
            "Estimated bonus - Incremental revenue incentive": round(dia * 0.0002, 4), "Estimated bonus - Activeness incentive": round(dia * 0.0001, 4),
            "Estimated bonus - Mature creator rank-up rate": 0, "Estimated bonus - Mature creator maintenance rate": 0, "Estimated bonus - Ranked up": 0,
        })
    return rows


def write_xlsx(path, headers, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(headers)
    for r in rows:
        ws.append([r.get(h) for h in headers])
    wb.save(path)


def generate(out_dir, seed=42):
    """Escreve os arquivos e devolve a lista em ordem cronológica de importação."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sims = build(seed)
    files = []
    for m in MONTHS:
        for d in SNAPSHOT_ENDS[m]:
            end = m.replace(day=d)
            exported = dt.datetime.combine(end + dt.timedelta(days=1), dt.time(10, 5))
            with_fans = m.month == 9
            headers = BACKSTAGE_BASE_COLS + (FAN_COLS if with_fans else []) + ["Status"]
            name = f"Dados do criador {exported:%Y_%m_%d %H_%M} UTC+0.xlsx"
            write_xlsx(out / name, headers, backstage_rows(sims, m, d, with_fans))
            files.append((exported, out / name))
        if m in TASK_MONTHS:
            nxt = (m + dt.timedelta(days=32)).replace(day=12)
            name = f"_Task_{m:%Y%m}_UTC+0_{nxt:%Y_%m_%d}_11_43_13.xlsx"
            write_xlsx(out / name, list(TASK_EN_MAP), task_rows(sims, m))
            files.append((dt.datetime.combine(nxt, dt.time(11, 43)), out / name))
    files.sort()
    return [p for _, p in files], sims

"""Calculadora "Onde posso chegar" (etapa 5, passo 5.2).

Diamantes por dia de LIVE do próprio criador (8 semanas), dias escolhidos por ele, faixa do 1º ao 3º quartil, nível
em que a faixa cai e três referências fixas (ritmo, melhor mês, próximo nível). Só com 3 semanas de dados.
Dados inventados (sufixo .demo)."""
import datetime as dt
import json
import re
from unittest import mock

from django.test import TestCase

from core.rls import set_context, system_context
from data import engine as E
from data.models import MonthlyResult
from web import calculator as CALC
from web import progress as P

from . import factories as F

LIVES = {2: 800, 5: 1200, 8: 1000, 11: 1600, 14: 900, 17: 1100, 20: 1400}  # dia de setembro: diamantes do dia
HOJE = dt.date(2026, 9, 23)


class CalculadoraTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.ua = F.user()
        cls.c = F.creator(cls.ag, username="calcula.demo", streamer_user=cls.ua)  # entrou em março: não está nos 14 dias
        total = valid = 0
        for day in range(1, 23):  # leitura diária de 01/09 a 22/09
            if day in LIVES:
                total, valid = total + LIVES[day], valid + 1
            F.snapshot(cls.c, dt.date(2026, 9, 1), dt.date(2026, 9, day), diamonds=total, hours=valid * 1.5, valid_days=valid, streams=valid)
        MonthlyResult.objects.create(creator=cls.c, month=dt.date(2026, 8, 1), diamonds=30000, live_seconds=3600 * 20, valid_days=15, tier=2)
        MonthlyResult.objects.create(creator=cls.c, month=dt.date(2026, 7, 1), diamonds=12000, live_seconds=3600 * 10, valid_days=8, tier=1)
        set_context()

    def tearDown(self):
        set_context()

    def _calc(self, until=dt.date(2026, 9, 22), today=HOJE):
        with system_context():
            snaps = [s for s in self.c.snapshots.all() if s.period_end <= until]
            snap = max(snaps, key=lambda s: s.period_end)
            rules = E.tier_rules(self.ag)
            level = P.level_info(self.c, snap, rules, today)
            return CALC.calculator(self.c, snaps, snap, level, 9000, rules, today)

    def test_base_e_faixa_pelos_dias_de_live_do_proprio_criador(self):
        with system_context():
            vals = CALC.live_day_values(list(self.c.snapshots.all()), dt.date(2026, 9, 22))
        self.assertEqual(sorted(vals), sorted(LIVES.values()))  # só os dias com LIVE
        calc = self._calc()
        self.assertEqual((calc["current"], calc["remaining"], calc["default"]), (8000, 8, 3))  # 7 dias em 22, levados a 8 dias
        self.assertEqual((calc["low"], calc["median"], calc["high"]), (950, 1100, 1300))
        self.assertEqual((calc["best"].month, calc["best"].diamonds), (dt.date(2026, 8, 1), 30000))
        self.assertEqual(calc["forecast"], 9000)

    def test_leitura_de_varios_dias_pesa_como_dias_validos(self):
        with system_context():
            outro = F.creator(self.ag, username="semanal.demo")
            F.snapshot(outro, dt.date(2026, 9, 1), dt.date(2026, 9, 7), diamonds=3000, hours=6, valid_days=3, streams=4)
            self.assertEqual(CALC.live_day_values(list(outro.snapshots.all()), dt.date(2026, 9, 7)), [1000, 1000, 1000])

    def test_so_aparece_com_3_semanas_de_dados_e_dias_no_mes(self):
        self.assertIsNone(self._calc(until=dt.date(2026, 9, 20), today=dt.date(2026, 9, 21)))  # 20 dias de dados
        self.assertIsNotNone(self._calc(until=dt.date(2026, 9, 21), today=dt.date(2026, 9, 22)))  # 21 dias
        self.assertIsNone(self._calc(today=dt.date(2026, 10, 1)))  # o mês virou e a leitura nova ainda não chegou

    def test_tela_meu_progresso(self):
        self.client.force_login(self.ua)
        with mock.patch("data.engine.tiktok_today", return_value=HOJE):
            tela = self.client.get("/")
        self.assertContains(tela, "Onde posso chegar")
        self.assertContains(tela, "Em quantos dos 8 dias que faltam em setembro você pretende fazer LIVE?")
        self.assertContains(tela, "Estimativa pelo seu histórico, não é garantia.")
        self.assertContains(tela, "Seu melhor mês: ago/26")
        dados = json.loads(re.search(r'id="calc-data"[^>]*>(.*?)</script>', tela.content.decode(), re.S).group(1))
        self.assertEqual((dados["current"], dados["remaining"], dados["default"], dados["low"], dados["high"]), (8000, 8, 3, 950, 1300))

"""Resumo do mês no app (Meu progresso), pedido da Mariana de 19/11/2026.

Decisões: o cartão fica no topo do dia 1 ao 10 e depois em "Meses desde a entrada"; as dicas saem de um banco com
regras (provisório até a revisão); a gestora pode escrever a própria dica na ficha, que entra no lugar da primeira."""
import datetime as dt

from django.db import DatabaseError, transaction
from django.test import TestCase
from django.urls import reverse

from core.access import assign_manager
from core.rls import set_context, system_context
from crm.models import Creator
from data.models import MonthlyResult
from engage.models import MonthTip, Notification
from engage.tom import verificar_tom
from web import month_summary as MS

from . import factories as F
from .test_tom import _texto_da_pagina

SET, OUT, NOV = dt.date(2026, 9, 1), dt.date(2026, 10, 1), dt.date(2026, 11, 1)


def _mes(c, month, diamonds, tier, hours=40, days=15, battles=20, streams=18):
    MonthlyResult.objects.create(creator=c, month=month, diamonds=diamonds, live_seconds=hours * 3600, valid_days=days,
                                 battles=battles, streams=streams, source="task", tier=tier)


class ResumoDoMesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.gestora = F.user(role="gestora", ag=cls.ag)
        cls.u1, cls.u2 = F.user(), F.user()
        cls.c1 = F.creator(cls.ag, username="um.demo", streamer_user=cls.u1)
        cls.c2 = F.creator(cls.ag, username="dois.demo", streamer_user=cls.u2)
        assign_manager(cls.c1, cls.gestora)
        assign_manager(cls.c2, cls.gestora)
        # um.demo: subiu do Tier 5 para o 7, com mais diamantes e mais seguidores
        _mes(cls.c1, SET, 300_000, 5, battles=12)
        _mes(cls.c1, OUT, 603_000, 7, battles=12)
        F.snapshot(cls.c1, SET, dt.date(2026, 9, 30), diamonds=300_000, hours=40, valid_days=15, streams=18, battles=12, new_followers=180)
        F.snapshot(cls.c1, OUT, dt.date(2026, 10, 31), diamonds=603_000, hours=40, valid_days=15, streams=18, battles=12, new_followers=320)
        # dois.demo: mês mais fraco que o anterior, mesmo nível
        _mes(cls.c2, SET, 20_000, 1, days=12)
        _mes(cls.c2, OUT, 15_000, 1, days=8)
        set_context()

    def tearDown(self):
        set_context()

    def _resumo(self, c, month=OUT):
        with system_context():
            return MS.for_month(Creator.objects.get(pk=c.pk), month)

    def test_subiu_de_nivel_e_onde_se_superou(self):
        s = self._resumo(self.c1)
        self.assertEqual(s["month_name"], "outubro")
        self.assertEqual(s["next_name"], "novembro")
        self.assertIn("Você subiu do Nível 5 para o Nível 7", s["headline"])
        self.assertIn("grupo Diamante", s["headline"])
        self.assertEqual(s["highlights_title"], "Onde você se superou")
        self.assertIn("101% a mais de diamantes que em setembro 📈", s["highlights"])
        self.assertIn("320 seguidores novos, 140 a mais que em setembro 👥", s["highlights"])
        self.assertEqual(len(s["tips"]), 2)
        self.assertIn("Seus seguidores novos estão chegando", s["tips"][0])
        self.assertNotIn("Tier", s["headline"])

    def test_mes_mais_fraco_mostra_fato_e_dica_de_ritmo(self):
        s = self._resumo(self.c2)
        self.assertIn("Você fechou outubro no Nível 1", s["headline"])
        self.assertEqual(s["highlights_title"], "O seu mês")
        self.assertTrue(s["highlights"][0].startswith("Você fez 18 LIVEs em 8 dias válidos"))
        self.assertIn("Meu plano", " ".join(s["tips"]))

    def test_primeiro_mes_e_mes_sem_resumo(self):
        s = self._resumo(self.c1, SET)
        self.assertIn("Seu primeiro mês fechado com a Hera: Nível 5", s["headline"])
        self.assertIsNone(self._resumo(self.c1, NOV))  # novembro não fechou

    def test_topo_so_do_dia_1_ao_10(self):
        with system_context():
            c = Creator.objects.get(pk=self.c1.pk)
            self.assertIsNotNone(MS.current(c, dt.date(2026, 11, 10)))
            self.assertIsNone(MS.current(c, dt.date(2026, 11, 11)))

    def test_textos_sem_palavra_vetada(self):
        for _code, _rule, text in MS.TIPS:
            self.assertEqual(verificar_tom(text), [], text)
        for c in (self.c1, self.c2):
            s = self._resumo(c)
            self.assertEqual(verificar_tom(" ".join([s["headline"], *s["highlights"], *s["tips"]])), [])

    def test_tela_do_mes_e_link_em_meses_desde_a_entrada(self):
        self.client.force_login(self.u1)
        r = self.client.get(reverse("my_month", args=[2026, 10]))
        self.assertContains(r, "Seu mês de outubro")
        self.assertContains(r, "Ideias para novembro, use o que fizer sentido para você")
        self.assertContains(r, "Conta com a Hera para o que precisar")
        self.assertEqual(verificar_tom(_texto_da_pagina(r)), [])
        self.assertContains(self.client.get("/"), reverse("my_month", args=[2026, 10]))
        self.assertEqual(self.client.get(reverse("my_month", args=[2026, 13])).status_code, 404)

    # ------------------------------------------------------------ dica da gestora
    def test_dica_da_gestora_entra_no_lugar_da_primeira(self):
        self.client.force_login(self.gestora)
        url = reverse("g_creator_action", args=[self.c1.pk])
        r = self.client.post(url, {"a": "month_tip", "text": "Bater a meta de 10 LIVEs", "next": "?tab=visao"}, follow=True)
        self.assertContains(r, "A dica não foi salva")
        month = MS.E.prev_month(MS.E.tiktok_today())
        r = self.client.post(url, {"a": "month_tip", "text": "Que tal convidar a @amiga.demo para um co-host?", "next": "?tab=visao"}, follow=True)
        self.assertContains(r, "Dica salva.")
        with system_context():
            tip = MonthTip.objects.get(creator=self.c1, month=month)
            self.assertEqual(tip.author_id, self.gestora.pk)
            MonthTip.objects.filter(pk=tip.pk).update(month=OUT)  # o mês fechado dos dados do teste
        s = self._resumo(self.c1)
        self.assertEqual(s["tips"][0], "Que tal convidar a @amiga.demo para um co-host?")
        self.assertEqual(len(s["tips"]), 2)

    def test_banco_isola_a_dica(self):
        with system_context():
            MonthTip.objects.create(creator=self.c1, month=OUT, text="Dica só do um", author=self.gestora)
        set_context(user_id=self.u1.pk)
        self.assertEqual(MonthTip.objects.count(), 1)  # o próprio criador lê a dele
        with self.assertRaises(DatabaseError), transaction.atomic():
            MonthTip.objects.create(creator=self.c1, month=SET, text="escrita pelo criador")
        set_context(user_id=self.u2.pk)
        self.assertEqual(MonthTip.objects.count(), 0)

    # ------------------------------------------------------------ aviso no sininho
    def test_aviso_de_resumo_nos_dias_2_e_3_uma_vez(self):
        with system_context():
            self.assertEqual(MS.notify_ready(self.ag, dt.date(2026, 11, 1)), 0)  # dia 1: ainda chega a leitura
            self.assertEqual(MS.notify_ready(self.ag, dt.date(2026, 11, 2)), 2)
            self.assertEqual(MS.notify_ready(self.ag, dt.date(2026, 11, 3)), 0)
            self.assertTrue(Notification.objects.filter(user=self.u1, kind="resumo_mes", title="Seu resumo de outubro chegou 🎉").exists())

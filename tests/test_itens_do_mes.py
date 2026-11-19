"""Itens do mês na fila (etapa 4, passo 4.3).

Decisões da Mariana de 19/11/2026: "menos constante" = menos dias válidos no mês que fechou do que no anterior; os
sinais de risco marcados pela gestora valem 30 dias. Confere: resumo do mês (dias 1 a 5 e 6 a 7), nível novo, módulo
concluído, sinais de risco dos Diamante (fila, ficha, aviso às sócias e isolamento no banco)."""
import datetime as dt

from django.db import DatabaseError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.rls import set_context, system_context
from crm.models import Contact, Creator, RiskSignal
from data import engine as E
from data.models import MonthlyResult
from data.states import analysed_sunday
from engage.models import Course, Lesson, LessonProgress, Notification
from engage.tom import verificar_tom_mensagem
from web import month_items
from web import services as S

from . import factories as F


def _fila(ag, today):
    with system_context():
        itens = S.action_queue(Creator.objects.filter(agency=ag), ag, today=today, raw=True)
        S.fill_queue_messages(itens, ag)
    return itens


def _de(itens, c, code):
    return [i for i in itens if i.creator.pk == c.pk and i.code == code]


def _mes(c, month, valid_days, tier=1, diamonds=10_000, hours=20, battles=5):
    MonthlyResult.objects.create(creator=c, month=month, diamonds=diamonds, live_seconds=hours * 3600, valid_days=valid_days,
                                 battles=battles, source="task", tier=tier)


class ResumoDoMesTests(TestCase):
    NOV, OUT = dt.date(2026, 11, 1), dt.date(2026, 10, 1)

    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.gestora = F.user(role="gestora", ag=cls.ag)
        cls.menos = F.creator(cls.ag, username="menos.demo")
        cls.constante = F.creator(cls.ag, username="constante.demo")
        cls.subiu = F.creator(cls.ag, username="subiu.demo")
        cls.esforco = F.creator(cls.ag, username="esforco.demo")
        for c in (cls.menos, cls.constante, cls.subiu, cls.esforco):
            assign_manager(c, cls.gestora)
        _mes(cls.menos, cls.OUT, 10), _mes(cls.menos, cls.NOV, 5)
        _mes(cls.constante, cls.OUT, 8), _mes(cls.constante, cls.NOV, 10, diamonds=12_000)
        _mes(cls.subiu, cls.OUT, 10, tier=2, diamonds=45_000), _mes(cls.subiu, cls.NOV, 12, tier=3, diamonds=90_000)
        _mes(cls.esforco, cls.OUT, 10, diamonds=30_000, hours=20), _mes(cls.esforco, cls.NOV, 12, diamonds=20_000, hours=30)
        set_context()

    def tearDown(self):
        set_context()

    def test_dias_1_a_5_so_quem_foi_menos_constante_e_o_nivel_novo(self):
        itens = _fila(self.ag, dt.date(2026, 12, 3))
        apoio = _de(itens, self.menos, "resumo_mes")
        self.assertEqual([i.template for i in apoio], ["MES-APOIO"])
        self.assertIn("5 contra 10", apoio[0].detail)
        self.assertFalse(_de(itens, self.constante, "resumo_mes"))
        novo = _de(itens, self.subiu, "nivel_novo")
        self.assertEqual([i.template for i in novo], ["NIVEL-NOVO"])
        self.assertIn("Nível 3", novo[0].text)
        self.assertFalse(_de(itens, self.subiu, "resumo_mes"))  # o nível novo entra no lugar do resumo

    def test_dias_6_e_7_os_constantes_e_a_mensagem_2_5(self):
        itens = _fila(self.ag, dt.date(2026, 12, 7))
        self.assertEqual([i.template for i in _de(itens, self.constante, "resumo_mes")], ["MES-PARABENS"])
        self.assertEqual([i.template for i in _de(itens, self.esforco, "resumo_mes")], ["APO-05"])
        self.assertTrue(_de(itens, self.menos, "resumo_mes"))  # quem não recebeu nos dias 1 a 5 continua na fila
        self.assertFalse([i for i in itens if i.code == "resumo_mes" and "{" in i.text])

    def test_depois_do_enviei_e_depois_do_dia_7_sai_da_fila(self):
        with system_context():
            Contact.objects.create(creator=self.menos, user=self.gestora, template_code="MES-APOIO",
                                   sent_at=timezone.make_aware(dt.datetime(2026, 12, 2, 10)))
        self.assertFalse(_de(_fila(self.ag, dt.date(2026, 12, 3)), self.menos, "resumo_mes"))
        itens = _fila(self.ag, dt.date(2026, 12, 9))
        self.assertFalse([i for i in itens if i.code in ("resumo_mes", "nivel_novo")])

    def test_textos_provisorios_sem_palavra_vetada(self):
        from engage import playbook

        for m in playbook.MESSAGES:
            if m["stage"] == "Itens do mês":
                self.assertEqual(verificar_tom_mensagem(m["body"]), [], m["code"])


class ModuloConcluidoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.gestora = F.user(role="gestora", ag=cls.ag)
        cls.u = F.user()
        cls.c = F.creator(cls.ag, username="aluno.demo", streamer_user=cls.u)
        assign_manager(cls.c, cls.gestora)
        co = Course.objects.create(agency=cls.ag, title="1. Começar", opens_on="acesso")
        cls.aulas = [Lesson.objects.create(course=co, title=f"Aula {i}", video_url="https://example.com/v", order=i) for i in range(2)]
        co2 = Course.objects.create(agency=cls.ag, title="3. Interação", opens_on="acesso", order=2)
        Lesson.objects.create(course=co2, title="Ganchos de conversa", video_url="https://example.com/v")
        set_context()

    def tearDown(self):
        set_context()

    def test_terminou_todas_as_aulas_do_modulo(self):
        hoje = E.tiktok_today()
        with system_context():
            LessonProgress.objects.create(lesson=self.aulas[0], creator=self.c)
        self.assertFalse(_de(_fila(self.ag, hoje), self.c, "modulo_concluido"))
        with system_context():
            LessonProgress.objects.create(lesson=self.aulas[1], creator=self.c)
        itens = _de(_fila(self.ag, hoje), self.c, "modulo_concluido")
        if hoje.weekday() == 6:
            return  # domingo: a fila não traz mensagens
        self.assertEqual([i.template for i in itens], ["MODULO-OK"])
        self.assertIn("“1. Começar”", itens[0].text)
        self.assertIn("A próxima aula aberta é “Ganchos de conversa”.", itens[0].text)
        with system_context():
            Contact.objects.create(creator=self.c, user=self.gestora, template_code="MODULO-OK")
        self.assertFalse(_de(_fila(self.ag, hoje), self.c, "modulo_concluido"))


class SinaisDeRiscoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.admin = F.user(role="admin", ag=cls.ag)
        cls.gestora = F.user(role="gestora", ag=cls.ag)
        cls.outra = F.user(role="gestora", ag=cls.ag)
        cls.u = F.user()
        cls.dia = F.creator(cls.ag, username="diamante.demo", streamer_user=cls.u)
        cls.comum = F.creator(cls.ag, username="comum.demo")
        for c in (cls.dia, cls.comum):
            assign_manager(c, cls.gestora)
        hoje = E.tiktok_today()
        for m in {E.prev_month(hoje), E.prev_month(analysed_sunday(hoje))}:
            _mes(cls.dia, m, 20, tier=5, diamonds=300_000)
            _mes(cls.comum, m, 20, tier=1)
        cls.hoje = hoje
        set_context()

    def tearDown(self):
        set_context()

    def _marcar(self, c, kind, dias_atras=0):
        with system_context():
            RiskSignal.objects.create(creator=c, kind=kind, author=self.gestora, created_at=timezone.now() - dt.timedelta(days=dias_atras))

    def test_dois_sinais_entram_na_fila_e_avisam_as_socias(self):
        self._marcar(self.dia, "tom")
        self.assertFalse(_de(_fila(self.ag, self.hoje), self.dia, "risco_diamante"))  # um sinal: observar
        self._marcar(self.dia, "outra_agencia")
        itens = _de(_fila(self.ag, self.hoje), self.dia, "risco_diamante")
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0].priority, 1)
        self.assertIn("falou de outra agência", itens[0].detail)
        with system_context():
            self.assertEqual(month_items.notify_risks(self.ag), 1)
            self.assertEqual(month_items.notify_risks(self.ag), 0)  # um aviso por criador a cada 7 dias
            self.assertTrue(Notification.objects.filter(user=self.admin, kind="risco").exists())

    def test_sinal_antigo_e_quem_nao_e_diamante_nao_contam(self):
        self._marcar(self.dia, "tom", dias_atras=31)
        self._marcar(self.dia, "reclamou", dias_atras=40)
        self._marcar(self.comum, "tom")
        self._marcar(self.comum, "reclamou")
        itens = _fila(self.ag, self.hoje)
        self.assertFalse([i for i in itens if i.code == "risco_diamante"])

    def test_gestora_marca_na_ficha_e_vai_para_a_linha_do_tempo(self):
        self.client.force_login(self.gestora)
        r = self.client.post(reverse("g_creator_action", args=[self.dia.pk]), {"a": "risk_signal", "kind": "demorou",
                                                                               "note": "3 dias sem ler", "next": "?tab=visao"}, follow=True)
        self.assertContains(r, "Sinal registrado: demorou a responder")
        self.assertContains(r, "Sinais de risco")
        self.assertContains(r, "1 sinal: anotar e observar")
        self.assertContains(r, "Sinal de risco: demorou a responder")
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("g_panel")), "@diamante.demo")

    def test_mes_importado_de_uma_vez_nao_gera_sinal_pelos_numeros(self):
        """Caso visto em produção em 19/11: novembro (01 a 17) chegou numa importação só e a semana 09 a 15 ficou vazia,
        o que acendia "batalhas em queda forte (0 contra 383 por semana)". Com leitura diária, os sinais voltam."""
        from data.states import week_state

        hoje = dt.date(2026, 11, 19)
        out_, nov = dt.date(2026, 10, 1), dt.date(2026, 11, 1)
        com_lote, diario = F.creator(self.ag, username="lote.demo"), F.creator(self.ag, username="diario.demo")
        for c in (com_lote, diario):
            for d in range(1, 32):  # outubro com leitura diária: 60 batalhas por semana
                F.snapshot(c, out_, out_.replace(day=d), diamonds=10_000 * d, hours=3 * d, valid_days=d, streams=d, battles=9 * d)
        F.snapshot(com_lote, nov, dt.date(2026, 11, 17), diamonds=170_000, hours=51, valid_days=17, streams=17, battles=153)
        for d in range(1, 16):  # novembro diário, mas sem batalhas na semana de 09 a 15
            F.snapshot(diario, nov, nov.replace(day=d), diamonds=10_000 * d, hours=3 * d, valid_days=d, streams=d,
                       battles=9 * min(d, 8))
        with system_context():
            r_lote, r_diario = [month_items.risk_for(c, week_state(c, list(c.snapshots.all()), hoje), 5, 5, list(c.snapshots.all()))
                                for c in (Creator.objects.get(pk=com_lote.pk), Creator.objects.get(pk=diario.pk))]
        self.assertFalse(r_lote["readable"])
        self.assertEqual(r_lote["numbers"], [])
        self.assertTrue(r_diario["readable"])
        self.assertTrue(any("batalhas em queda forte" in s for s in r_diario["numbers"]))

    def test_banco_isola_os_sinais(self):
        self._marcar(self.dia, "tom")
        set_context(user_id=self.outra.pk)
        self.assertEqual(RiskSignal.objects.count(), 0)
        with self.assertRaises(DatabaseError), transaction.atomic():
            RiskSignal.objects.create(creator=self.dia, kind="tom")
        set_context(user_id=self.u.pk)  # o próprio criador nunca vê
        self.assertEqual(RiskSignal.objects.count(), 0)
        set_context(user_id=self.gestora.pk)
        self.assertEqual(RiskSignal.objects.count(), 1)


class SemanaSemLeituraPropriaTests(TestCase):
    """Decisão da Mariana de 19/11/2026: semana sem leitura própria não gera queda, subida nem semana irregular."""

    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.gestora = F.user(role="gestora", ag=cls.ag)
        out_, nov = dt.date(2026, 10, 1), dt.date(2026, 11, 1)
        cls.lote, cls.diario = F.creator(cls.ag, username="lote.demo"), F.creator(cls.ag, username="diario.demo")
        for c in (cls.lote, cls.diario):
            assign_manager(c, cls.gestora)
            for d in range(1, 32):  # outubro diário: 7 mil por dia
                F.snapshot(c, out_, out_.replace(day=d), diamonds=7_000 * d, hours=2 * d, valid_days=d, streams=d, battles=3 * d)
        # lote.demo: 01 a 17/11 de uma vez e depois diário (a semana de 16 a 22 recebe o mês inteiro e parece enorme)
        F.snapshot(cls.lote, nov, dt.date(2026, 11, 17), diamonds=7_000 * 17, hours=34, valid_days=17, streams=17, battles=51)
        for d in range(18, 23):
            F.snapshot(cls.lote, nov, nov.replace(day=d), diamonds=7_000 * d, hours=2 * d, valid_days=d, streams=d, battles=3 * d)
        # diario.demo: novembro diário, com a semana de 16 a 22 de verdade bem acima (20 mil por dia)
        for d in range(1, 23):
            extra = 13_000 * max(d - 15, 0)
            F.snapshot(cls.diario, nov, nov.replace(day=d), diamonds=7_000 * d + extra, hours=2 * d, valid_days=d, streams=d, battles=3 * d)
        set_context()

    def tearDown(self):
        set_context()

    def test_semana_inflada_pelo_lote_nao_vira_subindo(self):
        itens = _fila(self.ag, dt.date(2026, 11, 25))  # quarta: a semana analisada é 16 a 22/11
        self.assertFalse(_de(itens, self.lote, "subindo"))
        self.assertEqual(len(_de(itens, self.diario, "subindo")), 1)

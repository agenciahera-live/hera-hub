"""Meu plano (etapa 3, passo 3.6): dias de LIVE, objetivos e lembretes escolhidos pelo criador.

Regras (visão e decisões da Mariana de 19/11/2026): tudo é escolha do criador e muda quando ele quiser; lembretes
começam desligados e chegam no sininho do app; a gestão lê o plano na ficha, mas só o criador grava (também no
banco); um criador nunca lê o plano de outro."""
import datetime as dt
import io

from django.core.management import call_command
from django.db import DatabaseError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.rls import set_context, system_context
from data import engine as E
from engage import plan as P
from engage.models import BattleRequest, Course, CreatorGoal, CreatorPlan, Notification
from engage.tom import verificar_tom

from . import factories as F
from .test_tom import _texto_da_pagina


class MeuPlanoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.gestora = F.user(role="gestora", ag=cls.ag)
        cls.outra = F.user(role="gestora", ag=cls.ag)
        cls.u1, cls.u2 = F.user(), F.user()
        cls.c1 = F.creator(cls.ag, username="um.demo", streamer_user=cls.u1)
        cls.c2 = F.creator(cls.ag, username="dois.demo", streamer_user=cls.u2)
        assign_manager(cls.c1, cls.gestora)
        assign_manager(cls.c2, cls.outra)
        today = E.tiktok_today()
        F.snapshot(cls.c1, E.month_start(today), today, diamonds=3000, hours=4, valid_days=2, streams=3)
        set_context()

    def tearDown(self):
        set_context()

    def _post(self, user, **data):
        self.client.force_login(user)
        return self.client.post(reverse("my_plan"), data, follow=True)

    # ------------------------------------------------------------ tela do criador
    def test_tela_abre_sem_palavra_vetada_e_lembretes_desligados(self):
        self.client.force_login(self.u1)
        r = self.client.get(reverse("my_plan"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(verificar_tom(_texto_da_pagina(r)), [])
        self.assertContains(r, "Meus dias de LIVE")
        self.assertNotContains(r, 'value="remind_live_day" checked')
        self.assertContains(self.client.get("/"), "Monte seu plano, se quiser")

    def test_criador_escolhe_os_dias_e_a_tela_inicial_mostra(self):
        self._post(self.u1, a="days", day=["0", "2", "4", "9", "x"])
        with system_context():
            self.assertEqual(CreatorPlan.objects.get(creator=self.c1).live_days, "024")
        self.client.force_login(self.u1)
        self.assertContains(self.client.get("/"), "seg, qua e sex")
        self._post(self.u1, a="days")  # desmarcar tudo também vale
        with system_context():
            self.assertEqual(CreatorPlan.objects.get(creator=self.c1).live_days, "")

    def test_lembretes_ligam_e_desligam(self):
        self._post(self.u1, a="reminders", on=["remind_battle", "remind_lesson", "inventado"])
        with system_context():
            p = CreatorPlan.objects.get(creator=self.c1)
        self.assertTrue(p.remind_battle and p.remind_lesson)
        self.assertFalse(p.remind_live_day or p.remind_campaign)

    def test_objetivos_nivel_e_livre_consegui_e_apagar(self):
        r = self._post(self.u1, a="goal_add", kind="nivel", level="3")
        self.assertContains(r, "Chegar ao Nível 3")
        self.assertContains(r, "Neste mês: 3.000 💎")
        r = self._post(self.u1, a="goal_add", kind="livre", text="Fazer minha primeira batalha")
        self.assertContains(r, "Fazer minha primeira batalha")
        r = self._post(self.u1, a="goal_add", kind="livre", text="  ")
        self.assertContains(r, "Escreva o seu objetivo.")
        with system_context():
            g = CreatorGoal.objects.get(creator=self.c1, kind="livre")
        r = self._post(self.u1, a="goal_done", goal=g.pk)
        self.assertContains(r, "Consegui 🎉")
        with system_context():
            self.assertIsNotNone(CreatorGoal.objects.get(pk=g.pk).done_at)
        self._post(self.u1, a="goal_delete", goal=g.pk)
        with system_context():
            self.assertFalse(CreatorGoal.objects.filter(pk=g.pk).exists())

    def test_no_maximo_tres_objetivos_em_aberto(self):
        for i in range(3):
            self._post(self.u1, a="goal_add", kind="livre", text=f"Objetivo {i}")
        r = self._post(self.u1, a="goal_add", kind="livre", text="Quarto")
        self.assertContains(r, "Você já tem 3 objetivos em aberto")
        with system_context():
            self.assertEqual(CreatorGoal.objects.filter(creator=self.c1).count(), 3)

    def test_criador_nao_mexe_no_objetivo_de_outro(self):
        with system_context():
            g = CreatorGoal.objects.create(creator=self.c2, kind="livre", text="Do outro")
        self.client.force_login(self.u1)
        r = self.client.post(reverse("my_plan"), {"a": "goal_delete", "goal": g.pk})
        self.assertEqual(r.status_code, 404)
        with system_context():
            self.assertTrue(CreatorGoal.objects.filter(pk=g.pk).exists())

    # ------------------------------------------------------------ gestão
    def test_gestora_le_o_plano_na_ficha(self):
        self._post(self.u1, a="days", day=["1", "5"])
        self._post(self.u1, a="goal_add", kind="livre", text="Fazer 1 LIVE de collab")
        self.client.force_login(self.gestora)
        r = self.client.get(reverse("g_creator", args=[self.c1.pk]))
        self.assertContains(r, "escolhido pelo criador")
        self.assertContains(r, "ter e sáb")
        self.assertContains(r, "Fazer 1 LIVE de collab")
        # sem plano
        self.client.force_login(self.outra)
        self.assertContains(self.client.get(reverse("g_creator", args=[self.c2.pk])), "ainda não montou o plano")

    # ------------------------------------------------------------ banco (RLS)
    def test_banco_isola_o_plano(self):
        with system_context():
            CreatorPlan.objects.create(creator=self.c1, live_days="0")
            CreatorGoal.objects.create(creator=self.c1, kind="livre", text="Meu")
        set_context(user_id=self.u2.pk)
        self.assertEqual(CreatorPlan.objects.count(), 0)
        self.assertEqual(CreatorGoal.objects.count(), 0)
        with self.assertRaises(DatabaseError), transaction.atomic():
            CreatorGoal.objects.create(creator=self.c1, kind="livre", text="Intruso")
        # a gestora da carteira lê, mas não grava
        set_context(user_id=self.gestora.pk)
        self.assertEqual(CreatorPlan.objects.count(), 1)
        with self.assertRaises(DatabaseError), transaction.atomic():
            CreatorGoal.objects.create(creator=self.c1, kind="livre", text="Da gestão")
        self.assertEqual(CreatorPlan.objects.filter(creator=self.c1).update(live_days="0123456"), 0)
        # a outra gestora nem lê
        set_context(user_id=self.outra.pk)
        self.assertEqual(CreatorPlan.objects.count(), 0)


class LembretesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.u1 = F.user()
        cls.c1 = F.creator(cls.ag, username="um.demo", streamer_user=cls.u1)
        cls.today = timezone.localdate()
        cls.plan = CreatorPlan.objects.create(creator=cls.c1, live_days=str(cls.today.weekday()))
        set_context()

    def setUp(self):
        set_context(system=True)

    def tearDown(self):
        set_context()

    def _titulos(self):
        return list(Notification.objects.filter(user=self.u1, kind=P.NOTIFY_KIND).values_list("title", flat=True))

    def test_desligado_nao_cria_nada(self):
        P.daily_reminders(self.ag, self.today)
        self.assertEqual(self._titulos(), [])

    def test_dia_de_live_e_batalha_de_amanha_sem_repetir(self):
        CreatorPlan.objects.filter(pk=self.plan.pk).update(remind_live_day=True, remind_battle=True)
        BattleRequest.objects.create(creator=self.c1, kind="oficial", date=self.today + dt.timedelta(days=1), time=dt.time(20, 30),
                                     status="aprovada")
        P.daily_reminders(self.ag, self.today)
        P.daily_reminders(self.ag, self.today)  # rotina rodou duas vezes: não repete
        titulos = self._titulos()
        self.assertEqual(len(titulos), 2)
        self.assertIn("Hoje é um dos seus dias de LIVE 💜", titulos)
        self.assertIn("Sua batalha oficial é amanhã, às 20:30 ⚔️", titulos)
        for t in titulos:
            self.assertEqual(verificar_tom(t), [])

    def test_dia_que_nao_foi_escolhido(self):
        outro = (self.today.weekday() + 1) % 7
        CreatorPlan.objects.filter(pk=self.plan.pk).update(remind_live_day=True, live_days=str(outro))
        P.daily_reminders(self.ag, self.today)
        self.assertEqual(self._titulos(), [])

    def test_modulo_novo_avisa_so_depois_da_primeira_rodada(self):
        CreatorPlan.objects.filter(pk=self.plan.pk).update(remind_lesson=True)
        Course.objects.create(agency=self.ag, title="1. Começar", opens_on="acesso")
        P.daily_reminders(self.ag, self.today)  # primeira vez: só guarda o que já está aberto
        self.assertEqual(self._titulos(), [])
        Course.objects.create(agency=self.ag, title="9. Novo", opens_on="acesso", order=9)
        P.daily_reminders(self.ag, self.today + dt.timedelta(days=1))
        self.assertEqual(self._titulos(), ["Abriu um módulo novo na Hera Academy: 9. Novo 🎓"])

    def test_rotina_diaria_roda_os_lembretes(self):
        CreatorPlan.objects.filter(pk=self.plan.pk).update(remind_live_day=True)
        set_context()
        call_command("rotina_diaria", stdout=io.StringIO())
        set_context(system=True)
        self.assertIn("Hoje é um dos seus dias de LIVE 💜", self._titulos())

    def test_lgpd_apaga_o_plano(self):
        CreatorGoal.objects.create(creator=self.c1, kind="livre", text="x")
        P.forget(self.c1)
        self.assertFalse(CreatorPlan.objects.filter(creator=self.c1).exists())
        self.assertFalse(CreatorGoal.objects.filter(creator=self.c1).exists())

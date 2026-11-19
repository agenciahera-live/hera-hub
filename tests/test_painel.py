"""Painel das sócias (etapa 4, passo 4.1).

Decisões da Mariana de 19/11/2026: bônus e moedas fora do app; sorteio de 5 "Enviei" por semana no total, espalhados
entre as gestoras. Confere: tela só das sócias, pedido de decisão pela fila, decisão só das sócias (também no banco),
sorteio, fila concluída e os números do funil."""
import datetime as dt
import random

from django.db import DatabaseError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.rls import set_context, system_context
from crm.models import ApprovalRequest, Contact, Creator, QueueDay, SentCheck
from crm.timeline import timeline
from engage.models import Notification
from web import panel
from web.services import QueueItem

from . import factories as F


class PainelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.admin = F.user(role="admin", ag=cls.ag)
        cls.ga = F.user(role="gestora", ag=cls.ag, first_name="Ana")
        cls.gb = F.user(role="gestora", ag=cls.ag, first_name="Bia")
        cls.u1 = F.user()
        cls.c1 = F.creator(cls.ag, username="um.demo", streamer_user=cls.u1)
        cls.c2 = F.creator(cls.ag, username="dois.demo")
        cls.novo = F.creator(cls.ag, username="novo.demo")
        cls.novo.joined_at = timezone.now() - dt.timedelta(minutes=5)
        cls.novo.save()
        assign_manager(cls.c1, cls.ga)
        assign_manager(cls.novo, cls.ga)
        assign_manager(cls.c2, cls.gb)
        set_context()

    def tearDown(self):
        set_context()

    # ------------------------------------------------------------ tela
    def test_so_as_socias_abrem_o_painel(self):
        self.client.force_login(self.ga)
        self.assertNotEqual(self.client.get(reverse("g_panel")).status_code, 200)
        self.client.force_login(self.admin)
        r = self.client.get(reverse("g_panel"))
        self.assertEqual(r.status_code, 200)
        for texto in ["Aprovações", "Resultado do mês", "Execução da gestão", "Sorteio da semana", "Funil do onboarding",
                      "Retenção", "Graduação", "Base por nível", "Hera Academy", "Batalhas", "Recrutamento"]:
            self.assertContains(r, texto)
        self.assertNotContains(r, "bônus estimado")

    def test_funil_conta_quem_entrou_no_mes(self):
        with system_context():
            rows = panel.funnel(self.ag, timezone.localdate())
        mes = next(r for r in rows if r["month"] == timezone.localdate().replace(day=1))
        self.assertGreaterEqual(mes["joined"], 1)

    # ------------------------------------------------------------ pedido e decisão
    def test_itens_de_encerramento_pedem_decisao(self):
        self.assertTrue(QueueItem(self.c1, "onboarding_encerrar", 1, "t", "d").asks_partners)
        self.assertFalse(QueueItem(self.c1, "onboarding_d10", 1, "t", "d").asks_partners)

    def test_gestora_pede_e_socia_decide(self):
        self.client.force_login(self.ga)
        url = reverse("g_approval_request", args=[self.c1.pk, "regua_30"])
        r = self.client.post(url, {"reason": "Sem LIVE há 30 dias", "note": "Não responde desde o dia 1."}, HTTP_HX_REQUEST="true")
        self.assertContains(r, "Pedido enviado às sócias.")
        r = self.client.post(url, {"reason": "Sem LIVE há 30 dias"}, HTTP_HX_REQUEST="true")
        self.assertContains(r, "Já existe um pedido")
        with system_context():
            ap = ApprovalRequest.objects.get(creator=self.c1)
            self.assertTrue(Notification.objects.filter(user=self.admin, kind="aprovacao").exists())
        # a gestora de outra carteira não pede pelo criador que não é dela
        self.client.force_login(self.gb)
        self.assertIn(self.client.post(url, {"reason": "x"}).status_code, (403, 404))
        # a sócia decide
        self.client.force_login(self.admin)
        r = self.client.post(reverse("g_panel"), {"a": "decide", "approval": ap.pk, "decision": "encerrar", "note": "Combinado."}, follow=True)
        self.assertContains(r, "Decisão registrada: Encerrar")
        r = self.client.post(reverse("g_panel"), {"a": "decide", "approval": ap.pk, "decision": "manter"}, follow=True)
        self.assertContains(r, "Este pedido já foi decidido.")
        with system_context():
            ap.refresh_from_db()
            self.assertEqual(ap.decision, "encerrar")
            self.assertTrue(Notification.objects.filter(user=self.ga, kind="aprovacao").exists())
            titulos = [e.title for e in timeline(Creator.objects.get(pk=self.c1.pk))]
        self.assertIn("Decisão das sócias: Encerrar", titulos)

    def test_banco_so_socia_decide(self):
        with system_context():
            ap = ApprovalRequest.objects.create(agency=self.ag, creator=self.c1, reason="x", requested_by=self.ga)
        set_context(user_id=self.ga.pk)
        self.assertEqual(ApprovalRequest.objects.count(), 1)
        self.assertEqual(ApprovalRequest.objects.filter(pk=ap.pk).update(decision="manter"), 0)
        set_context(user_id=self.gb.pk)
        self.assertEqual(ApprovalRequest.objects.count(), 0)
        with self.assertRaises(DatabaseError), transaction.atomic():
            ApprovalRequest.objects.create(agency=self.ag, creator=self.c1, reason="intrusa")
        set_context(user_id=self.u1.pk)  # o próprio criador não lê
        self.assertEqual(ApprovalRequest.objects.count(), 0)
        set_context(user_id=self.admin.pk)
        self.assertEqual(ApprovalRequest.objects.filter(pk=ap.pk).update(decision="manter"), 1)

    # ------------------------------------------------------------ sorteio
    def _contacts_last_week(self, user, creator, n):
        monday = panel.week_start(timezone.localdate())
        for i in range(n):
            when = timezone.make_aware(dt.datetime.combine(monday - dt.timedelta(days=7 - (i % 7)), dt.time(10, i)))
            Contact.objects.create(creator=creator, user=user, template_code=f"T{i}", sent_at=when)

    def test_sorteio_de_5_espalhado_entre_as_gestoras(self):
        with system_context():
            self._contacts_last_week(self.ga, self.c1, 8)
            self._contacts_last_week(self.gb, self.c2, 2)
            Contact.objects.create(creator=self.c1, user=self.ga, sent_at=timezone.now())  # desta semana: não entra
            picked = panel.ensure_draw(self.ag, rng=random.Random(1))
            self.assertEqual(len(picked), 5)
            self.assertEqual({sc.manager_id for sc in picked}, {self.ga.pk, self.gb.pk})
            self.assertEqual(sum(1 for sc in picked if sc.manager_id == self.gb.pk), 2)
            self.assertEqual(len(panel.ensure_draw(self.ag)), 5)  # mesma semana: não sorteia de novo
            self.assertEqual(SentCheck.objects.filter(agency=self.ag).count(), 5)
        self.client.force_login(self.admin)
        r = self.client.post(reverse("g_panel"), {"a": "check", "check": picked[0].pk, "result": "estava"}, follow=True)
        self.assertContains(r, "Conferência registrada.")
        with system_context():
            self.assertEqual(SentCheck.objects.get(pk=picked[0].pk).result, "estava")

    def test_gestora_nao_le_sorteio_nem_retrato_da_fila(self):
        with system_context():
            self._contacts_last_week(self.ga, self.c1, 2)
            panel.ensure_draw(self.ag)
            QueueDay.objects.create(agency=self.ag, manager=self.ga, day=timezone.localdate(), creator_ids=[self.c1.pk])
        set_context(user_id=self.ga.pk)
        self.assertEqual(SentCheck.objects.count(), 0)
        self.assertEqual(QueueDay.objects.count(), 0)

    # ------------------------------------------------------------ fila concluída
    def test_fila_concluida_conta_enviei_do_mesmo_dia(self):
        hoje = timezone.localdate()
        with system_context():
            QueueDay.objects.create(agency=self.ag, manager=self.ga, day=hoje, creator_ids=[self.c1.pk, self.novo.pk], items=2)
            Contact.objects.create(creator=self.c1, user=self.ga, sent_at=timezone.now())
            row = next(r for r in panel.execution(self.ag, hoje) if r["user"].pk == self.ga.pk)
        self.assertEqual((row["queue_done"], row["queue_total"]), (1, 2))
        self.assertEqual(row["queue_pct"], 0.5)
        self.assertEqual(row["queue_band"], "ruim")

    def test_batalhas_por_semana_so_com_leitura_diaria(self):
        hoje = dt.date(2026, 11, 19)
        m0 = dt.date(2026, 11, 1)
        for end, n in [(dt.date(2026, 11, 15), 10), (dt.date(2026, 11, 16), 12), (dt.date(2026, 11, 17), 15)]:
            F.snapshot(self.c1, m0, end, diamonds=1000, hours=n, valid_days=1, streams=n, battles=n)
        with system_context():
            semanas = {w["week"]: w for w in panel.battles(self.ag, hoje)["weeks"]}
        # 01 a 15/11 chegou numa leitura só: não vira semana. A semana de 16/11 tem 2 + 3 = 5 batalhas.
        self.assertNotIn(dt.date(2026, 11, 9), semanas)
        self.assertEqual(semanas[dt.date(2026, 11, 16)]["battles"], 5)
        self.assertEqual(semanas[dt.date(2026, 11, 16)]["band"], "atencao")

    def test_retrato_da_fila_roda(self):
        with system_context():
            panel.snapshot_queue(self.ag)
            panel.snapshot_queue(self.ag)  # de novo no mesmo dia: atualiza, não duplica
            dias = QueueDay.objects.filter(agency=self.ag, day=timezone.localdate())
            self.assertEqual(dias.count(), dias.values("manager").distinct().count())

"""Premiações (etapa 4, passo 4.6; decisões da Mariana de 23/11/2026): o criador não pede prêmio; a gestão registra na
ficha, as sócias aprovam todo prêmio, a entrega é marcada (diamantes na LIVE pela gestão, Pix pelo financeiro com
recibo) e a fila traz PIX-01, a entrega dos diamantes e a PIX-02. Dados inventados (sufixo .demo)."""
import datetime as dt
from decimal import Decimal

from django.db import DatabaseError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.rls import as_user, set_context, system_context
from crm.models import ApprovalRequest, Award, Contact, Creator, PixInfo
from engage.models import Notification
from web import panel
from web import services as S

from . import factories as F


class PremiacoesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.ua = F.user()
        cls.a = F.creator(cls.ag, username="ganhou.demo", streamer_user=cls.ua)
        cls.b = F.creator(cls.ag, username="outra.carteira.demo")
        cls.gx = F.user(role="gestora", ag=cls.ag)
        cls.gy = F.user(role="gestora", ag=cls.ag)
        cls.admin = F.user(role="admin", ag=cls.ag)
        cls.fin = F.user(role="financeiro", ag=cls.ag)
        assign_manager(cls.a, cls.gx)
        assign_manager(cls.b, cls.gy)
        set_context()

    def tearDown(self):
        set_context()

    def _registrar(self, **extra):
        dados = {"a": "award_add", "campaign": "", "campaign_name": "Cruzeiro Demo", "title": "1º lugar", "kind": "diamantes",
                 "diamonds": "5000", "value": "", "won_on": f"{timezone.localdate():%Y-%m-%d}"}
        dados.update(extra)
        self.client.force_login(self.gx)
        return self.client.post(reverse("g_creator_action", args=[self.a.pk]), dados, follow=True)

    def _premio(self):
        with system_context():
            return Award.objects.select_related("approval").filter(creator=self.a).order_by("-pk").first()

    def _decidir(self, aw, decisao="aprovar"):
        self.client.force_login(self.admin)
        self.client.post(reverse("g_panel"), {"a": "decide", "approval": aw.approval_id, "decision": decisao})

    def _fila(self):
        with system_context():
            return [i for i in S.action_queue(Creator.objects.filter(pk=self.a.pk), self.ag, raw=True) if i.code.startswith("premiacao")]

    def test_registro_na_ficha_pede_aprovacao_e_valida_os_campos(self):
        self.assertContains(self._registrar(title=""), "Escreva o que o criador ganhou")
        self.assertContains(self._registrar(kind="pix", value=""), "Informe o valor do Pix")
        self.assertContains(self._registrar(campaign_name=""), "Escolha a campanha")
        self.assertContains(self._registrar(), "aprovação das sócias")
        aw = self._premio()
        self.assertEqual((aw.status, aw.diamonds, aw.where, aw.approval.kind), ("aguardando", 5000, "Cruzeiro Demo", "premiacao"))
        with system_context():
            self.assertTrue(Notification.objects.filter(user=self.admin, title="Premiação para aprovar: @ganhou.demo").exists())
            # o pedido de prêmio não aparece como "aguardando as sócias" nos itens de encerramento
            self.assertEqual(panel.pending_by_creator([self.a.pk]), {})
        self.client.force_login(self.gx)
        self.assertContains(self.client.get(reverse("g_creator", args=[self.a.pk])), "Aguardando as sócias")
        self.assertContains(self.client.get(reverse("g_panel")), "", status_code=403)
        self.client.force_login(self.admin)
        tela = self.client.get(reverse("g_panel"))
        self.assertContains(tela, "1º lugar · Cruzeiro Demo · 5.000 diamantes na LIVE")
        self.assertContains(tela, "Não aprovar")

    def test_diamantes_aprovados_entram_na_fila_e_saem_com_a_entrega(self):
        self._registrar()
        aw = self._premio()
        self.assertEqual(self._fila(), [])  # antes da aprovação, nada
        self._decidir(aw)
        (item,) = self._fila()
        self.assertEqual((item.code, item.is_message), ("premiacao_diamantes", False))
        self.assertIn("5.000 diamantes na LIVE", item.title)
        self.client.force_login(self.gx)
        self.client.post(reverse("g_creator_action", args=[self.a.pk]), {"a": "award_delivered", "award": aw.pk,
                                                                          "on": f"{timezone.localdate():%Y-%m-%d}"})
        self.assertEqual(self._premio().status, "entregue")
        self.assertEqual(self._fila(), [])

    def test_recusado_nao_entra_na_fila(self):
        self._registrar()
        self._decidir(self._premio(), "recusar")
        self.assertEqual(self._premio().status, "recusada")
        self.assertEqual(self._fila(), [])

    def test_pix_pix01_pagamento_pelo_financeiro_pix02_e_recibo(self):
        self._registrar(kind="pix", value="250,50", diamonds="")
        aw = self._premio()
        self.assertEqual((aw.value, aw.prize_label), (Decimal("250.50"), "Pix de R$ 250,50"))
        self._decidir(aw)
        (item,) = self._fila()
        self.assertEqual((item.code, item.template), ("premiacao_pix", "PIX-01"))
        with system_context():
            S.fill_queue_messages([item], self.ag)
        self.assertIn("Você ganhou Pix de R$ 250,50 na Cruzeiro Demo", item.text)
        self.assertIn("docs.google.com/forms", item.text)  # sem Pix no app: o formulário da Hera, como hoje
        # a gestora não marca o Pix; o financeiro marca
        url = reverse("g_awards")
        self.client.force_login(self.gx)
        self.assertEqual(self.client.post(url, {"a": "paid", "award": aw.pk}).status_code, 403)
        self.assertEqual(self.client.get(reverse("g_award_receipt", args=[aw.pk])).status_code, 403)
        self.client.force_login(self.fin)
        r = self.client.post(url, {"a": "receipt", "award": aw.pk}, follow=True)
        self.assertContains(r, "O recibo é do prêmio em Pix já pago")
        self.client.post(url, {"a": "paid", "award": aw.pk, "on": f"{timezone.localdate():%Y-%m-%d}"})
        self.assertEqual(self._premio().status, "entregue")
        (item,) = self._fila()
        self.assertEqual((item.code, item.template), ("premiacao_enviado", "PIX-02"))
        with system_context():
            S.fill_queue_messages([item], self.ag)
        self.assertIn("R$ 250,50 via Pix, referente à Cruzeiro Demo", item.text)
        recibo = self.client.get(reverse("g_award_receipt", args=[aw.pk]))
        for trecho in ["@ganhou.demo", "Cruzeiro Demo", "1º lugar", "250,50", "Texto provisório"]:
            self.assertContains(recibo, trecho)
        self.client.post(url, {"a": "receipt", "award": aw.pk, "on": f"{timezone.localdate():%Y-%m-%d}"})
        self.assertEqual(self._premio().receipt_at, timezone.localdate())
        # a PIX-02 sai da fila com o "Enviei"
        with system_context():
            Contact.objects.create(creator=self.a, user=self.gx, template_code="PIX-02", body="x")
        self.assertEqual(self._fila(), [])

    def test_pix_ja_cadastrado_no_app_dispensa_o_formulario(self):
        with system_context():
            PixInfo.objects.create(creator=self.a, full_name="Ganhou Demo", cpf="52998224725", key_type="cpf", key="52998224725")
        self._registrar(kind="pix", value="100", diamonds="")
        self._decidir(self._premio())
        self.assertEqual(self._fila(), [])
        self.client.force_login(self.fin)
        self.assertContains(self.client.get(reverse("g_awards")), "529.982.247-25")
        self.client.force_login(self.gx)
        self.assertNotContains(self.client.get(reverse("g_awards")), "529.982.247-25")  # a gestora não vê o Pix

    def test_banco_isola_as_premiacoes(self):
        self._registrar()
        aw = self._premio()
        with as_user(self.ua):  # o criador não lê
            self.assertEqual(Award.objects.count(), 0)
        with as_user(self.gy):  # outra carteira não lê nem registra
            self.assertEqual(Award.objects.count(), 0)
            with self.assertRaises(DatabaseError), transaction.atomic():
                Award.objects.create(agency=self.ag, creator=self.a, title="x", kind="diamantes", diamonds=1, won_on=timezone.localdate())
        with as_user(self.gx):  # a gestora não aprova (a decisão é das sócias, também no banco)
            self.assertEqual(ApprovalRequest.objects.filter(pk=aw.approval_id).update(decision="aprovar", decided_at=timezone.now()), 0)
            self.assertEqual(Award.objects.filter(pk=aw.pk).delete()[0], 0)
        with as_user(self.fin):
            self.assertEqual(Award.objects.filter(pk=aw.pk).update(note="conferido"), 1)

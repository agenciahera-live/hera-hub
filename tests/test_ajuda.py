"""Ajuda (etapa 3, passo 3.5): central de dúvidas com as palavras novas (Nível), pedido de conversa, aviso de restrição
ou banimento (abre o caso e vai para o topo da fila), regras de saída e casos de inelegibilidade. Dados inventados."""
import datetime as dt
import re

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.rls import set_context, system_context
from crm.models import AccountCase, Creator
from engage import defaults as D
from engage.models import FaqItem, Notification, SupportTicket
from engage.tom import verificar_tom
from web import services as S

from . import factories as F


def _texto(resposta):
    html = resposta.content.decode()
    html = re.sub(r"<head>.*?</head>|<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


class TextosPadraoTests(SimpleTestCase):
    def test_central_e_dicas_sem_tier_e_sem_sugerir_horas_dias_ou_horario(self):
        textos = [f"{c} {q} {a}" for c, q, a, _k in D.FAQ] + list(D.TIPS)
        for t in textos:
            self.assertEqual(verificar_tom(t), [], t)
            self.assertNotRegex(t, r"\bTier\b", t)
            self.assertNotRegex(t, r"1[–-]2h|3[–-]4 dias|20h e 21h|entre 20h|Termine (suas LIVEs )?antes|na mesma hora", t)
        self.assertIn("Nível", {c for c, *_ in D.FAQ})
        perguntas = {q for _c, q, *_ in D.FAQ}
        self.assertEqual(len(perguntas), len(D.FAQ))  # sem pergunta repetida
        for nova, antiga in D.FAQ_RENAMED.items():
            self.assertIn(nova, perguntas)
            self.assertNotIn(antiga, perguntas)
        self.assertFalse(set(D.FAQ_RETIRED) & perguntas)


class AjudaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.ua, cls.ub, cls.us = F.user(), F.user(), F.user()
        cls.novo = F.creator(cls.ag, username="novo.ajuda.demo", streamer_user=cls.ua, joined_days_ago=5)
        cls.veterano = F.creator(cls.ag, username="veterano.ajuda.demo", streamer_user=cls.ub, joined_days_ago=60)
        cls.sem_gestora = F.creator(cls.ag, username="sem.gestora.demo", streamer_user=cls.us, joined_days_ago=60)
        cls.gx = F.user(role="gestora", ag=cls.ag)
        cls.gy = F.user(role="gestora", ag=cls.ag)
        cls.socia = F.user(role="admin", ag=cls.ag)
        agora = timezone.now()  # a fábrica conta a entrada a partir de uma data fixa; a tela de saída usa o dia de hoje
        for c, dias in ((cls.novo, 4), (cls.veterano, 59), (cls.sem_gestora, 59)):
            c.joined_at = agora - dt.timedelta(days=dias)
            c.save(update_fields=["joined_at"])
        assign_manager(cls.novo, cls.gx)
        assign_manager(cls.veterano, cls.gy)
        set_context()

    def tearDown(self):
        set_context()

    def _fila(self, *creators):
        with system_context():
            return S.action_queue(Creator.objects.filter(pk__in=[c.pk for c in creators]), self.ag)

    def test_tela_ajuda_com_temas_e_os_tres_caminhos(self):
        self.client.force_login(self.ua)
        tela = self.client.get(reverse("faq"))
        for trecho in ["Ajuda", "Nível", "Dinheiro e saque", "Público e fã-clube", "Falar com a Hera", "Quero conversar com a Hera",
                       "Minha conta foi restringida ou banida", "Sair da agência"]:
            self.assertContains(tela, trecho)
        self.assertEqual(verificar_tom(_texto(tela)), [])
        with system_context():
            cats = set(FaqItem.objects.filter(agency=self.ag).values_list("category", flat=True))
        self.assertNotIn("Tier", cats)
        for cat in cats:
            r = self.client.get(reverse("faq") + f"?cat={cat}")
            self.assertEqual(verificar_tom(_texto(r)), [], cat)
            self.assertNotRegex(_texto(r), r"\bTier\b")
        self.assertContains(self.client.get(reverse("faq") + "?cat=Nível"), "Você está no Nível")

    def test_pedido_de_conversa_entra_na_fila_para_a_gestora_da_carteira(self):
        self.client.force_login(self.ua)
        r = self.client.post(reverse("ask_manager"), {"kind": "conversa", "question": ""})
        self.assertContains(r, "pedido de conversa")
        with system_context():
            t = SupportTicket.objects.get(creator=self.novo)
            self.assertEqual((t.kind, t.question), ("conversa", "Quero conversar com a Hera."))
            self.assertTrue(Notification.objects.filter(user=self.gx, title__contains="pediu uma conversa").exists())
        item = next(i for i in self._fila(self.novo) if i.code == "duvida")
        self.assertEqual((item.title, item.block), ("Pedido de conversa pelo app", 1))
        self.client.force_login(self.gx)
        self.assertContains(self.client.get(reverse("g_tickets")), "Pedido de conversa")
        self.client.force_login(self.gy)
        self.assertNotContains(self.client.get(reverse("g_tickets")), "novo.ajuda.demo")
        # dúvida vazia não grava
        self.client.force_login(self.ua)
        self.client.post(reverse("ask_manager"), {"kind": "duvida", "question": "  "})
        with system_context():
            self.assertEqual(SupportTicket.objects.filter(creator=self.novo).count(), 1)

    def test_aviso_de_restricao_abre_o_caso_no_topo_da_fila(self):
        self.client.force_login(self.ub)
        form = self.client.get(reverse("help_account"))
        self.assertEqual(verificar_tom(_texto(form)), [])
        r = self.client.post(reverse("help_account"), {"kind": "banimento", "when": "2000-01-01", "what": "Conta suspensa por 7 dias",
                                                      "appeal": "nao"})
        self.assertContains(r, "A Hera já sabe")
        with system_context():
            case = AccountCase.objects.get(creator=self.veterano, resolved_at__isnull=True)
            self.assertEqual(case.kind, "banimento")
            self.assertIn("Conta suspensa por 7 dias", case.note)
            self.assertIn("ainda não fez o recurso", case.note)
            self.assertTrue(Notification.objects.filter(user=self.gy, title__contains="banimento na conta").exists())
        fila = self._fila(self.veterano)
        restr = next(i for i in fila if i.code == "restricao")
        self.assertEqual(restr.block, 1)
        self.assertNotIn("duvida", [i.code for i in fila])  # o aviso não aparece duas vezes
        # segundo aviso completa o mesmo caso; a tela lembra que já avisou
        self.client.post(reverse("help_account"), {"kind": "restricao", "what": "Agora LIVE interrompida", "appeal": "sim"})
        with system_context():
            self.assertEqual(AccountCase.objects.filter(creator=self.veterano).count(), 1)
            self.assertIn("Agora LIVE interrompida", AccountCase.objects.get(creator=self.veterano).note)
        self.assertContains(self.client.get(reverse("help_account")), "Você já avisou a Hera em")
        # o caso é interno: o criador não lê no banco
        set_context(user_id=self.ub.pk)
        self.assertEqual(AccountCase.objects.count(), 0)
        set_context()
        # encerrar o caso na ficha fecha o aviso
        self.client.force_login(self.gy)
        self.client.post(reverse("g_creator_action", args=[self.veterano.pk]), {"a": "case_resolve", "case": case.pk, "resolution": "Recurso aceito"})
        with system_context():
            self.assertFalse(SupportTicket.objects.filter(creator=self.veterano, kind="restricao", status="aberto").exists())

    def test_aviso_sem_gestora_vai_para_as_socias(self):
        self.client.force_login(self.us)
        self.client.post(reverse("help_account"), {"kind": "restricao", "what": "", "appeal": "nao_sei"})
        with system_context():
            self.assertTrue(Notification.objects.filter(user=self.socia, title__contains="restrição na conta").exists())

    def test_regras_de_saida_pela_data_de_entrada(self):
        self.client.force_login(self.ua)  # dia 5
        tela = self.client.get(reverse("help_exit"))
        texto = _texto(tela)
        self.assertRegex(texto, r"Nos seus primeiros 15 dias é o seu caso")
        for trecho in ["regra do TikTok", "aviso prévio", "90 dias", "300 mil diamantes nos últimos 6 meses", "mais de uma conta"]:
            self.assertIn(trecho, texto)
        self.assertEqual(verificar_tom(texto), [])
        self.client.force_login(self.ub)  # dia 60
        self.assertRegex(_texto(self.client.get(reverse("help_exit"))), r"Depois dos 15 dias é o seu caso")
        self.client.post(reverse("ask_manager"), {"kind": "saida", "question": ""})
        item = next(i for i in self._fila(self.veterano) if i.code == "duvida")
        self.assertEqual(item.title, "Quer conversar sobre sair da agência")

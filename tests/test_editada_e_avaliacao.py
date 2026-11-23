"""Mensagem editada antes de enviar e campanha nova avaliada pela gestora (decisões da Mariana de 23/11/2026).

1-B: a gestora pode editar a mensagem pronta; o envio fica "editada", com o original ao lado, e o motivo é opcional.
     As sócias veem no Painel (antes e depois, motivo, mais editadas) e na ficha (linha do tempo).
2-A: a campanha nova da plataforma é avaliada pela gestora (Dashboard, leitura da manhã) ou por uma sócia (Painel);
     vale quem avaliar primeiro, fica registrado quem foi e as sócias podem reabrir.
Dados inventados (sufixo .demo)."""
import datetime as dt
from urllib.parse import unquote

from django.test import TestCase
from django.urls import reverse

from core.access import assign_manager
from core.rls import set_context, system_context
from crm.models import Contact
from engage import campaigns as CP
from engage.models import Campaign, CampaignParticipant

from . import factories as F

TEXTO = "Oi, @edita.demo! Tudo bem?\nPassando para saber como foi a LIVE."


class MensagemEditadaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.a = F.creator(cls.ag, username="edita.demo")
        cls.gx = F.user(role="gestora", ag=cls.ag)
        cls.admin = F.user(role="admin", ag=cls.ag)
        assign_manager(cls.a, cls.gx)
        set_context()

    def tearDown(self):
        set_context()

    def _enviar(self, text, original=TEXTO, **extra):
        dados = {"text": text, "original": original, **extra}
        return self.client.post(reverse("g_sent", args=[self.a.pk, "APO-03"]), dados, HTTP_HX_REQUEST="true")

    def _ultimo(self):
        with system_context():
            return Contact.objects.filter(creator=self.a).order_by("-sent_at", "-pk").first()

    def test_sem_mudanca_nao_e_editada_e_com_mudanca_guarda_o_original_e_o_motivo(self):
        self.client.force_login(self.gx)
        r = self._enviar(TEXTO.replace("\n", "  \r\n") + "\n")  # só espaço e quebra de linha do Windows: não conta
        self.assertNotContains(r, "editada")
        c = self._ultimo()
        self.assertEqual((c.edited, c.original_body, c.edit_reason), (False, "", ""))
        novo = TEXTO + "\nVi que você remarcou para quinta, combinado!"
        r = self._enviar(novo, edit_reason="situacao", edit_note="Ela avisou no grupo que mudou o dia")
        self.assertContains(r, "Enviei ✓ registrado (editada)")
        c = self._ultimo()
        self.assertEqual((c.edited, c.body, c.original_body, c.edit_reason, c.edit_note),
                         (True, novo, TEXTO, "situacao", "Ela avisou no grupo que mudou o dia"))
        self._enviar(TEXTO + " Bjs", edit_reason="qualquer")  # motivo é opcional; valor fora da lista é ignorado
        c = self._ultimo()
        self.assertEqual((c.edited, c.edit_reason), (True, ""))

    def test_enviei_sem_o_original_continua_como_antes(self):
        self.client.force_login(self.gx)
        self.client.post(reverse("g_sent", args=[self.a.pk, "APO-03"]), {"text": "Texto qualquer"})
        self.assertFalse(self._ultimo().edited)

    def test_ficha_mostra_editar_e_a_linha_do_tempo_marca_editada(self):
        self.client.force_login(self.gx)
        self._enviar(TEXTO + " Bjs", edit_reason="tom")
        ficha = self.client.get(reverse("g_creator", args=[self.a.pk]))
        self.assertContains(ficha, "Enviei: APO-03 · editada (Ajustar o tom)")
        self.assertContains(ficha, "ver o texto pronto (antes da edição)")
        aba = self.client.get(reverse("g_creator", args=[self.a.pk]) + "?tab=mensagens")
        self.assertContains(aba, "heraEdit('f'")
        self.assertContains(aba, "Motivo da edição (opcional)")

    def test_aviso_de_tom_so_do_que_a_edicao_trouxe(self):
        self.client.force_login(self.gx)
        url = reverse("g_tone_check")
        r = self.client.post(url, {"text": TEXTO + " Você está em 3º no ranking, atrás da @outra.demo.", "original": TEXTO, "u": "edita.demo"})
        self.assertContains(r, "Confira antes de enviar")
        self.assertContains(r, "ranking")
        self.assertContains(r, "@outra.demo")
        self.assertNotContains(r, "@edita.demo")  # o @ do próprio criador não é aviso
        self.assertEqual(self.client.post(url, {"text": TEXTO + " Bjs", "original": TEXTO, "u": "edita.demo"}).content, b"")
        com_meta = TEXTO + " Bora para a meta?"
        self.assertEqual(self.client.post(url, {"text": com_meta + " Bjs", "original": com_meta, "u": "edita.demo"}).content, b"")

    def test_whatsapp_abre_com_o_texto_editado(self):
        self.client.force_login(self.gx)
        r = self.client.get(reverse("g_open", args=[self.a.pk, "APO-03"]), {"texto": "Mensagem do jeito que eu ajustei"})
        self.assertTrue(r["Location"].startswith("https://wa.me/"))
        self.assertIn("Mensagem do jeito que eu ajustei", unquote(r["Location"]))

    def test_painel_mostra_antes_e_depois_motivo_aviso_e_mais_editadas(self):
        self.client.force_login(self.gx)
        self._enviar(TEXTO)
        self._enviar(TEXTO + " Olha o ranking!", edit_reason="info", edit_note="Data errada no texto")
        self.client.force_login(self.gx)
        self.assertNotEqual(self.client.get(reverse("g_panel")).status_code, 200)  # só as sócias
        self.client.force_login(self.admin)
        tela = self.client.get(reverse("g_panel"))
        for trecho in ["Mensagens editadas", "@edita.demo", "Corrigir uma informação", "Data errada no texto", "ver antes e depois",
                       "⚠️ ranking", "Mais editadas", "editada 1 de 2 envios"]:
            self.assertContains(tela, trecho)


class AvaliacaoDaCampanhaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.a = F.creator(cls.ag, username="qualifica.demo")
        cls.b = F.creator(cls.ag, username="outra.demo")
        cls.gx = F.user(role="gestora", ag=cls.ag)
        cls.gy = F.user(role="gestora", ag=cls.ag)
        cls.admin = F.user(role="admin", ag=cls.ag)
        cls.fin = F.user(role="financeiro", ag=cls.ag)
        assign_manager(cls.a, cls.gx)
        assign_manager(cls.b, cls.gy)
        cls.hoje = dt.date.today()
        cls.nova = Campaign.objects.create(agency=cls.ag, name="Nova Demo", source="backstage", backstage_tab="plataforma", rules="-",
                                           start=cls.hoje - dt.timedelta(days=1), end=cls.hoje + dt.timedelta(days=10),
                                           approval="aguardando", mechanic="horas", prize_until=20)
        CampaignParticipant.objects.create(campaign=cls.nova, creator=cls.a, status="qualifica", from_backstage=True)
        CampaignParticipant.objects.create(campaign=cls.nova, creator=cls.b, status="inscrito", from_backstage=True)
        set_context()

    def tearDown(self):
        set_context()

    def _camp(self):
        with system_context():
            return Campaign.objects.select_related("approved_by").get(pk=self.nova.pk)

    def _decidir(self, decision, **extra):
        dados = {"campaign": self.nova.pk, "decision": decision, "mechanic": "batalha", "prize_until": "15", "prizes": "Diamantes",
                 "recommended_level": "nível 2", "what_to_do": "Faça batalhas.", **extra}
        return self.client.post(reverse("g_campaign_decide"), dados, follow=True)

    def test_gestora_avalia_no_dashboard_e_ja_poe_no_foco(self):
        self.client.force_login(self.gx)
        tela = self.client.get(reverse("g_dashboard"))
        for trecho in ["Campanhas novas para avaliar", "Nova Demo", "Na sua carteira: 1 pode se inscrever", "Aprovar e pôr no foco"]:
            self.assertContains(tela, trecho)
        self.assertNotContains(tela, "1 inscrito")  # o inscrito é da carteira da outra gestora
        r = self._decidir("aprovar_foco")
        self.assertContains(r, "aprovada e já no foco")
        c = self._camp()
        self.assertEqual((c.approval, c.featured, c.mechanic, c.prize_until, c.approved_by_id), ("aprovada", True, "batalha", 15, self.gx.pk))
        with system_context():
            self.assertIn("Nova Demo", [x["c"].name for x in CP.creator_campaigns(self.a, None, self.hoje, pick=False)])
        self.assertNotContains(self.client.get(reverse("g_dashboard")), "Campanhas novas para avaliar")
        # vale quem avaliar primeiro: a outra gestora (ou a sócia) não muda depois
        self.client.force_login(self.gy)
        r = self._decidir("recusar")
        self.assertContains(r, "já foi avaliada")
        self.assertEqual(self._camp().approval, "aprovada")

    def test_aprovar_sem_foco_e_nao_oferecer(self):
        self.client.force_login(self.gx)
        self._decidir("aprovar")
        c = self._camp()
        self.assertEqual((c.approval, c.featured), ("aprovada", False))
        with system_context():
            outra = Campaign.objects.create(agency=self.ag, name="Recusada Demo", rules="-", start=self.hoje, end=self.hoje, approval="aguardando")
        self.client.post(reverse("g_campaign_decide"), {"campaign": outra.pk, "decision": "recusar"})
        with system_context():
            outra = Campaign.objects.get(pk=outra.pk)
        self.assertEqual((outra.approval, outra.do_not_offer, outra.approved_by_id), ("recusada", True, self.gx.pk))

    def test_so_gestora_e_socia_avaliam(self):
        self.client.force_login(self.fin)
        self.assertEqual(self._decidir("aprovar").status_code, 403)
        self.assertEqual(self._camp().approval, "aguardando")

    def test_socia_ve_quem_avaliou_e_reabre(self):
        self.client.force_login(self.gx)
        self._decidir("aprovar_foco")
        self.client.force_login(self.admin)
        tela = self.client.get(reverse("g_panel"))
        self.assertContains(tela, "Avaliadas nos últimos 14 dias")
        self.assertContains(tela, "aprovada, no foco")
        self.client.post(reverse("g_panel"), {"a": "campaign_reopen", "campaign": self.nova.pk})
        c = self._camp()
        self.assertEqual((c.approval, c.featured, c.approved_by_id), ("aguardando", False, None))
        with system_context():
            self.assertNotIn("Nova Demo", [x["c"].name for x in CP.creator_campaigns(self.a, None, self.hoje, pick=False)])
        # a sócia também avalia no Painel, como antes
        self.client.post(reverse("g_panel"), {"a": "campaign", "campaign": self.nova.pk, "decision": "aprovar_foco", "mechanic": "horas"})
        c = self._camp()
        self.assertEqual((c.approval, c.featured, c.approved_by_id), ("aprovada", True, self.admin.pk))

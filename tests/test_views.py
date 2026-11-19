"""Isolamento pela URL/API e fluxos principais das telas."""
import datetime as dt

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.rls import set_context, system_context
from crm.models import Contact, Note, OneOnOne
from data.engine import recalculate
from engage.models import BattleRequest, FaqSearch, SupportTicket

from . import factories as F


class ViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.ua, cls.ub = F.user(), F.user()
        cls.a = F.creator(cls.ag, username="streamer.a", streamer_user=cls.ua)
        cls.b = F.creator(cls.ag, username="streamer.b", streamer_user=cls.ub)
        cls.gx = F.user(role="gestora", ag=cls.ag)
        cls.gy = F.user(role="gestora", ag=cls.ag)
        cls.admin = F.user(role="admin", ag=cls.ag)
        assign_manager(cls.a, cls.gx)
        assign_manager(cls.b, cls.gy)
        today = dt.date.today()
        for c in (cls.a, cls.b):
            F.snapshot(c, today.replace(day=1), today, diamonds=12_000, hours=10, valid_days=4, streams=5)
        Note.objects.create(creator=cls.b, body="segredo do B")
        recalculate(cls.ag)
        set_context()

    def tearDown(self):
        set_context()

    def test_streamer_home_shows_only_own_data(self):
        self.client.force_login(self.ua)
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Meu progresso")  # a tela inicial (visão de 14/11/2026)
        self.assertNotContains(r, "Missão da semana")  # removida em 14/11/2026
        self.assertEqual(self.client.get("/missao/").status_code, 404)
        self.assertNotContains(r, "streamer.b")

    def test_streamer_cannot_open_management_urls(self):
        self.client.force_login(self.ua)
        self.assertEqual(self.client.get(reverse("g_creator", args=[self.b.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("g_creator", args=[self.a.pk])).status_code, 403)
        self.assertEqual(self.client.get("/gestao/creators/").status_code, 403)
        self.assertEqual(self.client.get("/gestao/admin/").status_code, 302)  # sem acesso ao painel de cadastros

    def test_gestora_x_cannot_open_creator_of_y(self):
        self.client.force_login(self.gx)
        self.assertEqual(self.client.get(reverse("g_creator", args=[self.a.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("g_creator", args=[self.b.pk])).status_code, 404)
        r = self.client.get("/gestao/creators/")
        self.assertContains(r, "streamer.a")
        self.assertNotContains(r, "streamer.b")
        r = self.client.post(reverse("g_creator_action", args=[self.b.pk]), {"a": "note", "body": "x"})
        self.assertEqual(r.status_code, 404)

    def test_gestora_imports_backstage_daily_but_not_task(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from data.models import CreatorSnapshot, ImportBatch
        from tests.test_import import row, xlsx

        self.client.force_login(self.gx)
        # painel avisa que a importação de hoje não foi feita e leva para a tela de importar
        painel = self.client.get("/gestao/")
        self.assertContains(painel, "A importação de hoje do Backstage ainda não foi feita")
        self.assertContains(painel, "Importar agora")
        self.assertContains(self.client.get("/gestao/importar/"), "Todo dia")
        # o arquivo traz a agência inteira: quem é da carteira de outra gestora é reconhecido, não vira "novo"
        linhas = [row(), row(**{"ID do criador": self.b.tiktok_id, "Nome do criador": "streamer.b"})]
        f = SimpleUploadedFile("Dados do criador 2026_05_20 10_05 UTC+0.xlsx", xlsx(linhas))
        r = self.client.post("/gestao/importar/", {"file": f})
        with system_context():
            b = ImportBatch.objects.get(filename__startswith="Dados do criador")
        self.assertRedirects(r, f"/gestao/importar/{b.pk}/", fetch_redirect_response=False)
        self.assertEqual((b.counts["new"], b.counts["updated"]), (1, 1))
        self.assertEqual(self.client.get(f"/gestao/importar/{b.pk}/").status_code, 200)
        self.client.post(f"/gestao/importar/{b.pk}/", {"a": "commit"})
        with system_context():
            self.assertTrue(CreatorSnapshot.objects.filter(creator=self.b, batch=b).exists())
        # depois de importar, o aviso some e a carteira dela continua isolada
        painel = self.client.get("/gestao/")
        self.assertNotContains(painel, "ainda não foi feita")
        self.assertContains(painel, "Backstage importado hoje")
        self.assertEqual(self.client.get(reverse("g_creator", args=[self.b.pk])).status_code, 404)
        # a planilha Task (fechamento) continua só com sócias e financeiro
        from core.bootstrap import TASK_EN_MAP

        task = SimpleUploadedFile("_Task_202605.xlsx", xlsx([{h: 1 for h in TASK_EN_MAP}], headers=list(TASK_EN_MAP)))
        self.assertEqual(self.client.post("/gestao/importar/", {"file": task}).status_code, 403)

    def test_analista_cannot_import(self):
        u = F.user(role="analista", ag=self.ag)
        self.client.force_login(u)
        self.assertEqual(self.client.get("/gestao/importar/").status_code, 403)
        self.assertContains(self.client.get("/gestao/"), "Quem importa é a gestão ou as sócias")

    def test_one_on_one_with_7_blocks_and_action_plan(self):
        self.client.force_login(self.gx)
        # modelo novo (passo 4.2): canal, pelo menos 2 ações e o print guardado no drive da gestora
        r = self.client.post(reverse("g_1a1", args=[self.a.pk]), {
            "channel": "ligacao", "b1": "ok", "b2": "ok", "b3": "ok", "b4": "ok", "b5": "ok", "b7": "2026-10-10",
            "action1": "2 batalhas no sábado", "owner1": "streamer", "due1": "2026-10-05",
            "action2": "Ver a aula de interação", "owner2": "streamer", "print_saved": "on"})
        self.assertEqual(r.status_code, 302)
        with system_context():
            o = OneOnOne.objects.get(creator=self.a)
            self.assertTrue(o.complete)

    def test_opening_whatsapp_does_not_log_only_enviei_does(self):
        from crm.models import CreatorPrivate

        self.client.force_login(self.gx)
        # sem link do grupo: abre o WhatsApp com o texto, mas NÃO registra contato (abrir não é enviar)
        r = self.client.get(reverse("g_open", args=[self.a.pk, "APO-03"]))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r["Location"].startswith("https://wa.me/"))
        with system_context():
            self.assertEqual(Contact.objects.filter(creator=self.a).count(), 0)
            CreatorPrivate.objects.update_or_create(creator=self.a, defaults={"whatsapp_group_url": "https://chat.whatsapp.com/grupo-demo"})
        # com link do grupo: abre o grupo individual
        r = self.client.get(reverse("g_open", args=[self.a.pk, "APO-03"]))
        self.assertEqual(r["Location"], "https://chat.whatsapp.com/grupo-demo")
        with system_context():
            self.assertEqual(Contact.objects.filter(creator=self.a).count(), 0)
        # abrir é só leitura: GET em "Enviei" não registra
        self.assertEqual(self.client.get(reverse("g_sent", args=[self.a.pk, "APO-03"])).status_code, 405)
        # "Enviei" registra, com a mensagem preenchida, uma linha por envio
        r = self.client.post(reverse("g_sent", args=[self.a.pk, "APO-03"]), HTTP_HX_REQUEST="true")
        self.assertContains(r, "Enviei")
        self.client.post(reverse("g_sent", args=[self.a.pk, "APO-03"]))
        with system_context():
            contatos = Contact.objects.filter(creator=self.a, template_code="APO-03")
            self.assertEqual(contatos.count(), 2)
            self.assertTrue(all(x.body and x.user_id == self.gx.pk for x in contatos))
        # gestora de outra carteira não abre nem marca
        self.client.force_login(self.gy)
        self.assertEqual(self.client.get(reverse("g_open", args=[self.a.pk, "APO-03"])).status_code, 404)
        self.assertEqual(self.client.post(reverse("g_sent", args=[self.a.pk, "APO-03"])).status_code, 404)

    def test_enviei_advances_non_response_cadence(self):
        from django.utils import timezone

        from crm.models import CadenceState

        with system_context():
            CadenceState.objects.create(creator=self.a, started_at=timezone.now() - dt.timedelta(hours=25), step=1)
        self.client.force_login(self.gx)
        self.client.get(reverse("g_open", args=[self.a.pk, "NR-24H"]))
        with system_context():
            self.assertEqual(CadenceState.objects.get(creator=self.a).step, 1)  # abrir não avança
        self.client.post(reverse("g_sent", args=[self.a.pk, "NR-24H"]))
        with system_context():
            self.assertEqual(CadenceState.objects.get(creator=self.a).step, 2)

    def test_faq_search_tolerates_accent_and_synonym(self):
        self.client.force_login(self.ua)
        r = self.client.get(reverse("faq_search"), {"q": "que horas o dia vira"})
        self.assertContains(r, "21h")
        r = self.client.get(reverse("faq_search"), {"q": "como marco um pk"})
        self.assertContains(r, "batalha")
        r = self.client.get(reverse("faq_search"), {"q": "dia valdo"})  # erro de digitação
        self.assertContains(r, "pelo menos 1 hora de LIVE")
        r = self.client.get(reverse("faq_search"), {"q": "receita de bolo de cenoura"})
        self.assertContains(r, "Não encontrei")
        self.assertTrue(FaqSearch.objects.filter(results=0).exists())

    def test_ask_manager_creates_ticket_visible_only_to_right_manager(self):
        self.client.force_login(self.ua)
        self.client.post(reverse("ask_manager"), {"question": "Como troco meu @?"})
        self.client.force_login(self.gx)
        self.assertContains(self.client.get("/gestao/duvidas/"), "Como troco meu @?")
        self.client.force_login(self.gy)
        self.assertNotContains(self.client.get("/gestao/duvidas/"), "Como troco meu @?")

    def test_battle_request_flow(self):
        """O pedido segue o modelo oficial (BAT-PEDIDO); as regras detalhadas estão em tests/test_batalha_oficial.py."""
        self.client.force_login(self.ua)
        d = (timezone.localdate() + dt.timedelta(days=8)).isoformat()
        d2 = (timezone.localdate() + dt.timedelta(days=10)).isoformat()
        r = self.client.post(reverse("battle_new"), {"date": d, "date2": d2, "time": "20:30", "goal_diamonds": "20000", "rounds": "3",
                                                     "other_agency": "sim", "banner": "nao"})
        self.assertEqual(r.status_code, 302)
        with system_context():
            b = BattleRequest.objects.get(creator=self.a)
        self.assertEqual(b.rounds, 3)
        self.assertEqual(b.other_options, [{"date": d2, "time": "20:30"}])
        meus = self.client.get(reverse("battles"))
        self.assertContains(meus, "3 rounds")
        self.assertContains(meus, f"ou {dt.date.fromisoformat(d2):%d/%m} às 20:30")
        # um tipo só, sem escolha de oponente nem pedido de divulgação; o app não sugere hora
        self.assertEqual(b.get_kind_display(), "Batalha oficial")
        self.assertIsNone(b.opponent)
        self.assertFalse(b.promote)
        form = self.client.get(reverse("battle_new"))
        self.assertContains(form, "Batalha oficial")
        # decisão de 19/11/2026: o criador não escolhe se o oponente é da Hera ou de outra agência
        for campo in ['name="kind"', 'name="opponent"', 'name="opponent_text"', 'name="promote"', 'name="duration_min"', "Pico de audiência",
                      'value="20:00"', 'name="other_agency"', "outra agência"]:
            self.assertNotContains(form, campo)
        for campo in ['name="date2"', 'name="banner"', "1 round", "3 rounds", "Tanto faz"]:
            self.assertContains(form, campo)
        # botão para a aula que explica a batalha oficial: só aparece quando existe uma aula marcada
        from engage.models import Course, Lesson

        self.assertNotContains(form, "Entenda a batalha oficial")
        with system_context():
            curso = Course.objects.create(agency=self.ag, title="Batalhas")
            aula = Lesson.objects.create(course=curso, title="O que é uma batalha oficial", video_url="https://example.com/v", minutes=8, about_battles=True)
        self.client.force_login(self.ua)
        form = self.client.get(reverse("battle_new"))
        self.assertContains(form, "Entenda a batalha oficial em 8 min")
        self.assertContains(form, reverse("lesson", args=[aula.pk]))
        self.client.force_login(self.gx)
        self.client.post("/gestao/batalhas/", {"id": b.pk, "status": "aprovada", "reply": "Combinado!"})  # confirmar só com oponente
        with system_context():
            self.assertEqual(BattleRequest.objects.get(pk=b.pk).status, "pendente")
        self.client.post("/gestao/batalhas/", {"id": b.pk, "a": "confirm", "choice": "0", "final_rounds": "3", "opponent": "@rival.demo"})
        with system_context():
            self.assertEqual(BattleRequest.objects.get(pk=b.pk).status, "aprovada")

    def test_consent_required_before_using_app(self):
        u = F.user()
        with system_context():
            c = F.creator(self.ag, username="novo.sem.termo")
            c.user = u
            c.save()
        self.client.force_login(u)
        r = self.client.get("/")
        self.assertRedirects(r, "/boas-vindas/", fetch_redirect_response=False)
        self.client.post("/boas-vindas/", {"action": "consent", "accept": "on"})
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_removed_screens_are_gone(self):
        """Decisão de 14/11/2026: saem a meta individual, o disparo assistido e o convite por e-mail."""
        self.client.force_login(self.gx)
        self.assertEqual(self.client.get("/gestao/disparos/").status_code, 404)
        self.assertEqual(self.client.post(f"/gestao/creators/{self.a.pk}/convidar/", {"email": "x@teste.local"}).status_code, 404)
        ficha = self.client.get(reverse("g_creator", args=[self.a.pk]))
        self.assertNotContains(ficha, "Meta individual")
        self.assertNotContains(ficha, "Disparos")
        self.assertNotContains(ficha, "Convidar")

    def test_dashboard_and_reports_render(self):
        self.client.force_login(self.admin)
        for u in ["/gestao/", "/gestao/relatorios/", "/gestao/onboarding/", "/gestao/campanhas/", "/gestao/conteudos/"]:
            self.assertEqual(self.client.get(u).status_code, 200, u)


class ImportScreenTests(TestCase):
    def setUp(self):
        set_context(system=True)
        self.ag = F.agency()
        self.admin = F.user(role="admin", ag=self.ag)
        self.fin = F.user(role="financeiro", ag=self.ag)
        set_context()

    def test_admin_uploads_previews_commits_and_reverts(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from data.models import CreatorSnapshot, ImportBatch
        from tests.test_import import row, xlsx

        self.client.force_login(self.admin)
        f = SimpleUploadedFile("Dados do criador 2026_05_20 10_05 UTC+0.xlsx", xlsx([row()]))
        r = self.client.post("/gestao/importar/", {"file": f})
        b = ImportBatch.objects.get()
        self.assertRedirects(r, f"/gestao/importar/{b.pk}/", fetch_redirect_response=False)
        self.assertContains(self.client.get(f"/gestao/importar/{b.pk}/"), "novos")
        self.client.post(f"/gestao/importar/{b.pk}/", {"a": "commit"})
        with system_context():
            self.assertEqual(CreatorSnapshot.objects.count(), 1)
        self.client.post(f"/gestao/importar/{b.pk}/", {"a": "revert"})
        with system_context():
            self.assertEqual(CreatorSnapshot.objects.count(), 0)

    def test_financeiro_can_import_task_only(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from tests.test_import import row, xlsx

        self.client.force_login(self.fin)
        f = SimpleUploadedFile("dados.xlsx", xlsx([row()]))
        self.assertEqual(self.client.post("/gestao/importar/", {"file": f}).status_code, 403)


class PartnerAccessTests(TestCase):
    def test_partner_streamer_blocked_until_group_enabled(self):
        from core.models import PartnerGroup

        set_context(system=True)
        ag = F.agency()
        pg = PartnerGroup.objects.create(agency=ag, name="Rede Teste", streamer_access_enabled=False)
        u = F.user()
        F.creator(ag, username="parceira.demo", streamer_user=u, partner_group=pg)
        set_context()
        self.client.force_login(u)
        self.assertEqual(self.client.get("/").status_code, 403)
        set_context(system=True)
        pg.streamer_access_enabled = True
        pg.save()
        set_context()
        self.assertEqual(self.client.get("/").status_code, 200)


class CampaignAndShortcutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from engage.models import Campaign

        set_context(system=True)
        cls.ag = F.agency()
        cls.u = F.user()
        cls.c = F.creator(cls.ag, username="camp.demo", streamer_user=cls.u)
        today = dt.date.today()
        F.snapshot(cls.c, today.replace(day=1), today, diamonds=5000, hours=6, valid_days=3, streams=4)
        cls.official = Campaign.objects.create(agency=cls.ag, name="Oficial Teste", source="backstage", rules="r", prizes="Ring light",
                                              start=today.replace(day=1), end=today + dt.timedelta(days=3), tiktok_url="https://www.tiktok.com/",
                                              featured=True, what_to_do="Faça 15 dias válidos")
        cls.hidden = Campaign.objects.create(agency=cls.ag, name="Oficial Sem Destaque", source="backstage", rules="r",
                                            start=today.replace(day=1), end=today + dt.timedelta(days=3))
        cls.internal = Campaign.objects.create(agency=cls.ag, name="Relâmpago Teste", source="relampago", rules="r", metric="hours",
                                              tiktok_url="https://www.tiktok.com/relampago", what_to_do="Some 4h no fim de semana",
                                              start=today.replace(day=1), end=today + dt.timedelta(days=3))
        recalculate(cls.ag)
        set_context()

    def test_campaign_cards_open_tiktok_without_app_ranking(self):
        from engage.models import CampaignStanding

        self.assertFalse(CampaignStanding.objects.filter(campaign=self.official).exists())
        self.assertTrue(CampaignStanding.objects.filter(campaign=self.internal).exists())
        self.client.force_login(self.u)
        # cards abrem direto o TikTok; sem botão extra e sem ranking no app
        r = self.client.get("/campanhas/")
        self.assertContains(r, 'href="https://www.tiktok.com/"')
        self.assertContains(r, "Faça 15 dias válidos")
        self.assertContains(r, "Ring light")
        self.assertContains(r, "Falar com a Hera")
        self.assertNotContains(r, "Abrir a campanha no TikTok")
        self.assertNotContains(r, "Oficial Sem Destaque")
        r = self.client.get("/campanhas/?aba=hera")
        self.assertContains(r, 'href="https://www.tiktok.com/relampago"')
        self.assertContains(r, "Some 4h no fim de semana")
        self.assertNotContains(r, " de 1<")
        # link antigo (ex.: notificação) redireciona para o TikTok
        r = self.client.get(reverse("campaign", args=[self.internal.pk]))
        self.assertRedirects(r, "https://www.tiktok.com/relampago", fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("campaign", args=[self.hidden.pk])).status_code, 404)

    def test_home_shows_help_and_battle_shortcuts(self):
        self.client.force_login(self.u)
        r = self.client.get("/")
        self.assertContains(r, "Ajuda")  # passo 3.5: a barra de baixo chama a tela de Ajuda
        self.assertContains(r, "Pedir batalha")
        self.assertContains(r, reverse("faq"))
        self.assertContains(r, reverse("battle_new"))

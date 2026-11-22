"""Campanhas (etapa 3, passo 3.4): leitura de campanhas do Backstage pela porta de importação, foco escolhido pela
gestão, lista do criador só com as campanhas em que participa, campanha do momento (escolha da gestora ou encaixe)
e isolamento. Dados inventados (sufixo .demo)."""
import datetime as dt
import json
import re

from django.test import TestCase
from django.urls import reverse

from core.access import assign_manager
from core.rls import set_context, system_context
from data import engine as E
from data import port
from engage import campaigns as CP
from engage.models import Campaign, CampaignParticipant, CampaignPick, Notification
from engage.services import creator_facts
from engage.tom import verificar_tom

from . import factories as F


def _texto(resposta):
    html = resposta.content.decode()
    html = re.sub(r"<head>.*?</head>|<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


class MotivoDaSugestaoTests(TestCase):
    def test_motivo_sem_numero_zero_estranho(self):
        from types import SimpleNamespace as NS

        zero = {"weeks": 4, "battles": 0, "hours": 0, "valid_days": 0, "new_fans": 0, "diamonds": 0, "guest_share": 0}
        for mech, txt in [("batalha", "não fez batalha nas últimas semanas"), ("horas", "não teve dia válido nas últimas semanas"),
                          ("fa_clube", "sem fãs novos no fã-clube nas últimas semanas")]:
            self.assertEqual(CP.fit(NS(mechanic=mech, tiktok_kind=""), zero)[1], txt)
        self.assertEqual(CP.chance(NS(participants_n=0, prize_until=None)), (2, "ninguém participa ainda"))
        self.assertEqual(CP.fit(NS(mechanic="batalha", tiktok_kind=""), {**zero, "battles": 1})[1], "faz 1 batalha por semana")


class CampanhasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.ua, cls.ub, cls.uc = F.user(), F.user(), F.user()
        cls.a = F.creator(cls.ag, username="batalhador.demo", streamer_user=cls.ua)
        cls.b = F.creator(cls.ag, username="constante.demo", streamer_user=cls.ub)
        cls.c = F.creator(cls.ag, username="outra.carteira.demo", streamer_user=cls.uc)
        cls.gx = F.user(role="gestora", ag=cls.ag)
        cls.gy = F.user(role="gestora", ag=cls.ag)
        cls.analista = F.user(role="analista", ag=cls.ag)
        assign_manager(cls.a, cls.gx)
        assign_manager(cls.b, cls.gx)
        assign_manager(cls.c, cls.gy)
        cls.hoje = E.tiktok_today()
        m0 = E.month_start(E.prev_month(cls.hoje))
        for n in range(1, 5):  # mês passado, semana a semana: "a" batalha muito; "b" faz dias válidos e não batalha
            fim = m0 + dt.timedelta(days=7 * n - 1)
            F.snapshot(cls.a, m0, fim, diamonds=5000 * n, hours=8 * n, valid_days=2 * n, streams=3 * n, battles=8 * n)
            F.snapshot(cls.b, m0, fim, diamonds=5000 * n, hours=10 * n, valid_days=6 * n, streams=6 * n, battles=0)
        cls.key = port.new_key(cls.ag)
        set_context()

    def tearDown(self):
        set_context()

    # ------------------------------------------------------------ porta
    def _leitura(self, **extra):
        d = lambda n: (self.hoje + dt.timedelta(days=n)).isoformat()  # noqa: E731
        payload = {
            "campanhas": [
                {"id": "77001", "nome": "Duelo Teste", "aba": "plataforma", "inicio": d(-2), "fim": d(10), "tipo": "Desafio de batalha",
                 "nivel_recomendado": "nível 1", "participantes": 3, "elegiveis": 16, "diamantes": "3.100",
                 "link": "https://www.tiktok.com/t/ZTeste01/", "resumo": "Faça batalhas na LIVE durante a campanha.", "premios": "Diamantes",
                 "mecanica": "batalha", "premia_ate": 10},
                {"nome": "Constância Teste", "aba": "agencia", "inicio": d(-1), "fim": d(5), "tipo": "missao", "participantes": 40,
                 "resumo": "Abra LIVE em dias diferentes.", "mecanica": "horas"},
            ],
            "criadores": [
                {"usuario": "@batalhador.demo", "campanha": "77001", "situacao": "Inscrito"},
                {"usuario": "constante.demo", "campanha": "77001", "situacao": "qualifica-se"},
                {"usuario": "@batalhador.demo", "campanha": "Constância Teste", "situacao": "em andamento"},
                {"usuario": "@constante.demo", "campanha": "Constância Teste", "situacao": "em andamento"},
                {"usuario": "@outra.carteira.demo", "campanha": "Constância Teste", "situacao": "encerrada"},
                {"usuario": "@ninguem.demo", "campanha": "77001", "situacao": "inscrito"},
            ],
        }
        payload.update(extra)
        return payload

    def _enviar(self, payload, key=None, raw=None):
        return self.client.post(reverse("api_import_campaigns"), data=raw if raw is not None else json.dumps(payload),
                                content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {key or self.key}")

    def _camp(self, name):
        with system_context():
            return Campaign.objects.get(agency=self.ag, name=name)

    def _aprovar(self, *names):  # passo 4.5: campanha nova da plataforma espera as sócias
        with system_context():
            Campaign.objects.filter(agency=self.ag, name__in=names, approval="aguardando").update(approval="aprovada")

    def _foco(self, *names):
        self._aprovar(*names)
        with system_context():
            Campaign.objects.filter(agency=self.ag, name__in=names).update(featured=True)

    def test_porta_grava_a_leitura_sem_duplicar_e_sem_apagar_o_que_a_gestao_decidiu(self):
        self.assertEqual(self._enviar({}, key="hera_errada").status_code, 401)
        self.assertEqual(self._enviar(None, raw="não é json").status_code, 400)
        r = self._enviar({"campanhas": [{"nome": "Sem datas"}]})
        self.assertEqual(r.status_code, 422)
        self.assertIn("data AAAA-MM-DD", r.json()["mensagem"])
        r = self._enviar(self._leitura())
        self.assertEqual(r.status_code, 200, r.content)
        j = r.json()
        self.assertEqual((j["campanhas_novas"], j["situacoes"], j["criadores_desconhecidos"], j["sem_link"]), (2, 5, 1, 1))
        duelo = self._camp("Duelo Teste")
        self.assertEqual((duelo.source, duelo.featured, duelo.tiktok_kind, duelo.mechanic, duelo.prize_until, duelo.total_diamonds),
                         ("backstage", False, "batalha", "batalha", 10, 3100))
        self.assertEqual(duelo.tiktok_url, "https://www.tiktok.com/t/ZTeste01/")
        self.assertEqual(self._camp("Constância Teste").backstage_tab, "agencia")
        # passo 4.5: a da plataforma espera as sócias; a dirigida pela Agência não passa pela aprovação
        self.assertEqual((duelo.approval, self._camp("Constância Teste").approval, j["para_aprovar"]), ("aguardando", "", 1))
        with system_context():
            self.assertTrue(Notification.objects.filter(user=self.gx, title="Campanhas novas lidas do Backstage").exists())
            self.assertEqual(CampaignParticipant.objects.get(campaign=duelo, creator=self.b).status, "qualifica")
            # a gestão confere a mecânica, escolhe o foco e inclui alguém à mão
            Campaign.objects.filter(pk=duelo.pk).update(mechanic="horas", featured=True)
            CampaignParticipant.objects.create(campaign=duelo, creator=self.c)
        # reenviar não duplica; a decisão da gestão fica; quem sumiu da leitura deixa de valer; a inclusão manual fica
        leitura = self._leitura()
        leitura["criadores"] = [x for x in leitura["criadores"] if x["usuario"] != "constante.demo"]
        j = self._enviar(leitura).json()
        self.assertEqual((j["campanhas_novas"], j["campanhas_atualizadas"]), (0, 2))
        duelo = self._camp("Duelo Teste")
        self.assertEqual((duelo.mechanic, duelo.featured, duelo.approval), ("horas", True, "aguardando"))  # a releitura não aprova
        with system_context():
            self.assertEqual(Campaign.objects.filter(agency=self.ag).count(), 2)
            self.assertFalse(CampaignParticipant.objects.filter(campaign=duelo, creator=self.b).exists())
            self.assertTrue(CampaignParticipant.objects.filter(campaign=duelo, creator=self.c, from_backstage=False).exists())

    # ------------------------------------------------------------ app do criador
    def test_criador_ve_so_as_de_foco_em_que_participa(self):
        self._enviar(self._leitura())
        self.client.force_login(self.ua)
        self.assertContains(self.client.get(reverse("campaigns")), "Nenhuma campanha para você agora")  # nada é foco ainda
        self._foco("Duelo Teste", "Constância Teste")
        tela = self.client.get(reverse("campaigns"))
        for trecho in ["Duelo Teste", "Inscrição feita", "Constância Teste", "Valendo agora", "https://www.tiktok.com/t/ZTeste01/",
                       "Faça batalhas na LIVE", "campanha do momento"]:
            self.assertContains(tela, trecho)
        texto = _texto(tela)
        self.assertEqual(verificar_tom(texto), [])
        self.assertNotRegex(texto.lower(), r"ranking|posição|\dº")
        self.client.force_login(self.ub)
        self.assertContains(self.client.get(reverse("campaigns")), "Você pode se inscrever")
        self.client.force_login(self.uc)  # "encerrada" não aparece como campanha em que participa
        tela = self.client.get(reverse("campaigns"))
        self.assertNotContains(tela, "Constância Teste")
        self.assertNotContains(tela, "Duelo Teste")
        self.assertEqual(self.client.get(reverse("campaign", args=[self._camp("Duelo Teste").pk])).status_code, 404)
        # "não oferecer" some para todos
        with system_context():
            Campaign.objects.filter(name="Duelo Teste").update(do_not_offer=True)
        self.client.force_login(self.ua)
        self.assertNotContains(self.client.get(reverse("campaigns")), "Duelo Teste")

    def test_campanha_do_momento_pelo_encaixe_e_pela_escolha_da_gestora(self):
        self._enviar(self._leitura())
        self._foco("Duelo Teste", "Constância Teste")
        with system_context():
            a, b = self.a, self.b
            sug_a = CP.campaign_of_the_moment(a, CP.creator_campaigns(a, creator_facts(a)))
            sug_b = CP.campaign_of_the_moment(b, CP.creator_campaigns(b, creator_facts(b)))
        self.assertEqual(sug_a["item"]["c"].name, "Duelo Teste")  # batalha para quem batalha
        self.assertIn("batalhas por semana", sug_a["why"])
        self.assertIn("só 3 participantes e premia até o 10º", sug_a["why"])
        self.assertEqual(sug_b["item"]["c"].name, "Constância Teste")  # quem não batalha recebe a de constância
        self.assertIn("dias válidos por semana", sug_b["why"])
        self.client.force_login(self.ua)
        self.assertRegex(_texto(self.client.get("/")), r"Campanha do momento .* Duelo Teste")
        # a gestora vê a sugestão e o motivo na ficha e troca
        self.client.force_login(self.gx)
        ficha = self.client.get(reverse("g_creator", args=[self.a.pk]))
        self.assertContains(ficha, "Sugestão do app: faz")
        acao = reverse("g_creator_action", args=[self.a.pk])
        self.client.post(acao, {"a": "campaign_pick", "campaign": self._camp("Constância Teste").pk})
        with system_context():
            self.assertEqual(CampaignPick.objects.get(creator=self.a).campaign.name, "Constância Teste")
            self.assertTrue(Notification.objects.filter(user=self.ua, title="A Hera escolheu uma campanha para você").exists())
        self.client.force_login(self.ua)
        self.assertRegex(_texto(self.client.get("/")), r"Campanha do momento .* Constância Teste")
        # "nenhuma": a tela inicial fica sem campanha; vazio volta para a sugestão
        self.client.force_login(self.gx)
        self.client.post(acao, {"a": "campaign_pick", "campaign": "nenhuma"})
        self.client.force_login(self.ua)
        self.assertNotContains(self.client.get("/"), "Campanha do momento")
        self.client.force_login(self.gx)
        self.client.post(acao, {"a": "campaign_pick", "campaign": ""})
        with system_context():
            self.assertFalse(CampaignPick.objects.filter(creator=self.a).exists())

    def test_gestora_escolhe_campanha_fora_do_foco_so_para_um_criador(self):
        self._enviar(self._leitura())  # nada é foco
        self.client.force_login(self.gx)  # antes da aprovação das sócias, a campanha não é opção na ficha
        self.client.post(reverse("g_creator_action", args=[self.a.pk]), {"a": "campaign_pick", "campaign": self._camp("Duelo Teste").pk})
        with system_context():
            self.assertFalse(CampaignPick.objects.filter(creator=self.a).exists())
        self._aprovar("Duelo Teste")
        self.client.post(reverse("g_creator_action", args=[self.a.pk]), {"a": "campaign_pick", "campaign": self._camp("Duelo Teste").pk})
        self.client.force_login(self.ua)
        self.assertContains(self.client.get(reverse("campaigns")), "Duelo Teste")
        self.client.force_login(self.ub)
        self.assertNotContains(self.client.get(reverse("campaigns")), "Duelo Teste")
        # campanha em que o criador não participa não pode ser escolhida
        self.client.force_login(self.gx)
        self.client.post(reverse("g_creator_action", args=[self.b.pk]), {"a": "campaign_pick", "campaign": self._camp("Duelo Teste").pk + 999})
        with system_context():
            self.assertFalse(CampaignPick.objects.filter(creator=self.b).exists())

    # ------------------------------------------------------------ gestão e permissões
    def test_tela_da_gestao_foco_e_nao_oferecer(self):
        self._enviar(self._leitura())
        duelo = self._camp("Duelo Teste")
        self.client.force_login(self.gx)
        tela = self.client.get(reverse("g_campaigns"))
        self.assertContains(tela, "aguardando as sócias")
        self.client.post(reverse("g_campaigns"), {"id": duelo.pk, "a": "focus"})
        self.assertFalse(self._camp("Duelo Teste").featured)  # passo 4.5: antes da aprovação, a gestora não marca foco
        self._aprovar("Duelo Teste")
        tela = self.client.get(reverse("g_campaigns"))
        for trecho in ["Lidas do Backstage", "Duelo Teste", "Desafio de batalha", "3 / 16 participantes", "1 inscrito", "1 pode se inscrever",
                       "Foco", "Não oferecer", "sem link"]:
            self.assertContains(tela, trecho)
        self.client.post(reverse("g_campaigns"), {"id": duelo.pk, "a": "focus"})
        self.assertTrue(self._camp("Duelo Teste").featured)
        self.client.post(reverse("g_campaigns"), {"id": duelo.pk, "a": "details", "mechanic": "cohost", "prize_until": "5",
                                                  "what_to_do": "Resumo novo", "prizes": "", "tiktok_url": "http://errado"})
        self.assertEqual(self._camp("Duelo Teste").mechanic, "batalha")  # link sem https: nada é salvo
        self.client.post(reverse("g_campaigns"), {"id": duelo.pk, "a": "do_not_offer"})
        self.assertEqual((self._camp("Duelo Teste").do_not_offer, self._camp("Duelo Teste").featured), (True, False))
        # a outra gestora não vê os números da carteira de gx; analista só lê
        self.client.force_login(self.gy)
        self.assertNotContains(self.client.get(reverse("g_campaigns")), "1 inscrito")
        self.client.force_login(self.analista)
        self.assertEqual(self.client.post(reverse("g_campaigns"), {"id": duelo.pk, "a": "focus"}).status_code, 403)

    def test_outra_gestora_nao_escolhe_e_o_banco_isola_a_escolha(self):
        self._enviar(self._leitura())
        self.client.force_login(self.gy)
        r = self.client.post(reverse("g_creator_action", args=[self.a.pk]), {"a": "campaign_pick", "campaign": "nenhuma"})
        self.assertEqual(r.status_code, 404)
        with system_context():
            CampaignPick.objects.create(creator=self.a, campaign=self._camp("Duelo Teste"))
        set_context(user_id=self.ub.pk)
        self.assertEqual(CampaignPick.objects.count(), 0)
        self.assertEqual(CampaignParticipant.objects.filter(creator=self.a).count(), 0)
        set_context(user_id=self.ua.pk)
        self.assertEqual(CampaignPick.objects.count(), 1)

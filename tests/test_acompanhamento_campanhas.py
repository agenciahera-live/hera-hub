"""Acompanhamento de campanhas (etapa 4, passo 4.5; decisões da Mariana de 22/11/2026).

- A leitura traz a posição de cada criador da Hera; só a gestão vê, uma frase por criador (nunca tabela nem ranking).
- Campanha nova da plataforma espera a aprovação das sócias no painel.
- Três listas na tela Campanhas e o acompanhamento na fila do dia, na agenda do Playbook.
- "Perto de prêmio" = na faixa premiada ou até 3 posições depois dela.
Dados inventados (sufixo .demo)."""
import datetime as dt
import re

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.rls import set_context, system_context
from crm.models import Contact, Creator
from engage import campaigns as CP
from engage.models import Campaign, CampaignParticipant, CampaignPosition
from web import services as S

from . import factories as F

TERCA = dt.date(2026, 9, 15)  # metade da campanha de 10/09 a 20/09 (fora da última semana do mês)


def _em(dia, hora=12):
    return timezone.make_aware(dt.datetime(dia.year, dia.month, dia.day, hora))


class AcompanhamentoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.ua = F.user()
        cls.a = F.creator(cls.ag, username="perto.demo", streamer_user=cls.ua)
        cls.b = F.creator(cls.ag, username="qualifica.demo")
        cls.d = F.creator(cls.ag, username="caiu.demo")
        cls.c = F.creator(cls.ag, username="outra.carteira.demo")
        cls.gx = F.user(role="gestora", ag=cls.ag)
        cls.gy = F.user(role="gestora", ag=cls.ag)
        cls.admin = F.user(role="admin", ag=cls.ag)
        for cr in (cls.a, cls.b, cls.d):
            assign_manager(cr, cls.gx)
        assign_manager(cls.c, cls.gy)
        cls.duelo = Campaign.objects.create(
            agency=cls.ag, name="Duelo Demo", source="backstage", backstage_tab="plataforma", approval="aprovada", featured=True,
            rules="-", what_to_do="Faça batalhas na LIVE.", tiktok_url="https://www.tiktok.com/t/Demo01/", start=dt.date(2026, 9, 10),
            end=dt.date(2026, 9, 20), mechanic="batalha", prize_until=10, read_at=timezone.now())
        for cr, st in ((cls.a, "inscrito"), (cls.b, "qualifica"), (cls.d, "andamento"), (cls.c, "andamento")):
            CampaignParticipant.objects.create(campaign=cls.duelo, creator=cr, status=st, from_backstage=True)
        now = timezone.now()
        CampaignPosition.objects.create(campaign=cls.duelo, creator=cls.a, position=12, points=15300, to_next=800, prev_position=12, read_at=now)
        CampaignPosition.objects.create(campaign=cls.duelo, creator=cls.d, position=9, points=20000, to_next=150, prev_position=7, read_at=now)
        CampaignPosition.objects.create(campaign=cls.duelo, creator=cls.c, position=5, points=30000, read_at=now)
        set_context()

    def tearDown(self):
        set_context()

    def _fila(self, today, *creators):
        with system_context():
            creators = creators or (self.a, self.b, self.d)
            return S.action_queue(Creator.objects.filter(pk__in=[c.pk for c in creators]), self.ag, today=today, raw=True)

    def _item(self, itens, creator, prefix="campanha"):
        return [i for i in itens if i.creator.pk == creator.pk and i.code.startswith(prefix)]

    # ------------------------------------------------------------ leitura
    def test_leitura_grava_a_posicao_e_guarda_a_do_dia_anterior(self):
        def leitura(pos, **extra):
            row = {"usuario": "@perto.demo", "campanha": "Duelo Leitura", "situacao": "inscrito"}
            if pos is not None:
                row.update({"posicao": pos, "pontos": "15.300", "pontos_para_subir": 800})
            payload = {"campanhas": [{"nome": "Duelo Leitura", "aba": "plataforma", "inicio": "2026-09-10", "fim": "2026-09-20"}],
                       "criadores": [row, {"usuario": "@caiu.demo", "campanha": "Duelo Leitura", "situacao": "inscrito", "posicao": 30}]}
            payload["criadores"] = payload["criadores"][:1] if extra.get("so_um") else payload["criadores"]
            return payload

        dia1, dia2 = _em(dt.date(2026, 9, 14), 9), _em(dt.date(2026, 9, 15), 9)
        with system_context():
            counts = CP.receive_reading(self.ag, leitura("10º"), now=dia1)
            self.assertEqual((counts["posicoes"], counts["para_aprovar"]), (2, 1))
            camp = Campaign.objects.get(name="Duelo Leitura")
            p = CampaignPosition.objects.get(campaign=camp, creator=self.a)
            self.assertEqual((p.position, p.points, p.to_next, p.prev_position), (10, 15300, 800, None))
            CP.receive_reading(self.ag, leitura(12), now=dia1 + dt.timedelta(hours=3))  # reenviada no mesmo dia
            self.assertIsNone(CampaignPosition.objects.get(campaign=camp, creator=self.a).prev_position)
            CP.receive_reading(self.ag, leitura(14, so_um=True), now=dia2)  # dia seguinte; @caiu.demo saiu da tabela
            p = CampaignPosition.objects.get(campaign=camp, creator=self.a)
            self.assertEqual((p.position, p.prev_position), (14, 12))
            self.assertFalse(CampaignPosition.objects.filter(campaign=camp, creator=self.d).exists())
            CP.receive_reading(self.ag, leitura(None, so_um=True), now=dia2)  # leitura sem a tabela: a posição fica
            self.assertEqual(CampaignPosition.objects.get(campaign=camp, creator=self.a).position, 14)

    # ------------------------------------------------------------ aprovação das sócias
    def test_campanha_nova_espera_as_socias_e_a_socia_aprova_no_painel(self):
        with system_context():
            CP.receive_reading(self.ag, {"campanhas": [{"nome": "Nova Demo", "aba": "plataforma", "inicio": "2026-09-10", "fim": "2026-09-30",
                                                        "mecanica": "horas", "premia_ate": 20}],
                                         "criadores": [{"usuario": "@qualifica.demo", "campanha": "Nova Demo", "situacao": "qualifica"}]})
            nova = Campaign.objects.get(name="Nova Demo")
            Campaign.objects.filter(pk=nova.pk).update(featured=True)  # nem como foco ela aparece antes da aprovação
            self.assertEqual([x["c"].name for x in CP.creator_campaigns(self.b, None, TERCA, pick=False)], ["Duelo Demo"])
        self.assertEqual([i.vars["campanha"] for i in self._item(self._fila(TERCA, self.b), self.b)], ["Duelo Demo"])
        # a gestora não abre o painel; a sócia vê a campanha esperando com o que o Claude propôs
        self.client.force_login(self.gx)
        self.assertNotEqual(self.client.get(reverse("g_panel")).status_code, 200)
        self.client.force_login(self.admin)
        tela = self.client.get(reverse("g_panel"))
        self.assertContains(tela, "Campanhas novas do TikTok")
        self.assertContains(tela, "Nova Demo")
        self.client.post(reverse("g_panel"), {"a": "campaign", "campaign": nova.pk, "decision": "aprovar", "mechanic": "batalha",
                                              "prize_until": "15", "prizes": "Diamantes", "recommended_level": "nível 2",
                                              "what_to_do": "Faça batalhas."})
        with system_context():
            nova = Campaign.objects.get(pk=nova.pk)
            self.assertEqual((nova.approval, nova.mechanic, nova.prize_until, nova.approved_by_id), ("aprovada", "batalha", 15, self.admin.pk))
            self.assertEqual([x["c"].name for x in CP.creator_campaigns(self.b, None, TERCA, pick=False)], ["Duelo Demo", "Nova Demo"])
        # decidida uma vez, não muda de novo; "não oferecer" vale para todos
        with system_context():
            outra = Campaign.objects.create(agency=self.ag, name="Recusada Demo", rules="-", start=TERCA, end=TERCA, approval="aguardando")
        self.client.post(reverse("g_panel"), {"a": "campaign", "campaign": outra.pk, "decision": "recusar"})
        with system_context():
            outra = Campaign.objects.get(pk=outra.pk)
            self.assertEqual((outra.approval, outra.do_not_offer), ("recusada", True))
        self.client.force_login(self.gx)  # a gestora não volta a oferecer o que as sócias recusaram
        self.client.post(reverse("g_campaigns"), {"id": outra.pk, "a": "do_not_offer"})
        with system_context():
            self.assertTrue(Campaign.objects.get(pk=outra.pk).do_not_offer)

    # ------------------------------------------------------------ listas da gestão
    def test_tres_listas_so_da_carteira_e_sem_ranking(self):
        with system_context():
            listas = CP.follow_lists(self.ag, [self.a.pk, self.b.pk, self.d.pk], TERCA)
        self.assertEqual([r["creator"].username for r in listas["inscricao"]], ["qualifica.demo"])
        self.assertEqual([r["creator"].username for r in listas["premio"]], ["caiu.demo", "perto.demo"])  # pelo @, não pela posição
        self.assertEqual([r["creator"].username for r in listas["queda"]], ["caiu.demo"])
        self.assertEqual(listas["premio"][1]["why"], "está em 12º, faltam 800 pontos para o 11º (fora da faixa premiada, que vai até o 10º)")
        self.assertIn("caiu do 7º", listas["queda"][0]["why"])

    def test_tela_campanhas_da_gestora_e_o_criador_nunca_ve_posicao(self):
        hoje = timezone.localdate()
        with system_context():  # a tela usa o dia de hoje: a campanha passa a valer hoje
            Campaign.objects.filter(pk=self.duelo.pk).update(start=hoje - dt.timedelta(days=5), end=hoje + dt.timedelta(days=5))
        self.client.force_login(self.gx)
        tela = self.client.get(reverse("g_campaigns"))
        for trecho in ["Acompanhamento da sua carteira", "Pode se inscrever e não se inscreveu", "Perto de prêmio", "Pode perder posição",
                       "@perto.demo", "está em 12º, faltam 800 pontos para o 11º"]:
            self.assertContains(tela, trecho)
        self.assertNotContains(tela, "@outra.carteira.demo")  # a carteira de outra gestora
        self.client.force_login(self.ua)
        app = self.client.get(reverse("campaigns"))
        self.assertContains(app, "Duelo Demo")
        texto = re.sub(r"<[^>]+>", " ", app.content.decode())
        self.assertNotRegex(texto.lower(), r"ranking|posição|\d+º")

    # ------------------------------------------------------------ fila do dia
    def test_fila_na_metade_inscricao_e_perto_de_premio_com_a_posicao_preenchida(self):
        itens = self._fila(TERCA)
        (insc,) = self._item(itens, self.b)
        self.assertEqual((insc.code, insc.template, insc.block), ("campanha_inscricao", "ROD-CAMP", 2))
        (pos,) = self._item(itens, self.a)
        self.assertEqual((pos.code, pos.template, pos.priority), ("campanha_posicao", "CAMP-POS", 2))
        self.assertIn("Metade da campanha: está em 12º", pos.detail)
        (caiu,) = self._item(itens, self.d)
        self.assertEqual(caiu.code, "campanha_posicao")
        with system_context():
            S.fill_queue_messages([pos, insc], self.ag)
        self.assertIn("olhei a Duelo Demo agora e você está em 12º lugar", pos.text)
        self.assertIn("Faltam 800 pontos", pos.text)
        self.assertNotIn("[", pos.text)
        self.assertIn("https://www.tiktok.com/t/Demo01/", insc.text)
        self.assertIn("faça batalhas na LIVE", insc.text)

    def test_fila_respeita_o_enviei_a_vespera_e_o_ultimo_dia(self):
        with system_context():
            Contact.objects.create(creator=self.a, user=self.gx, template_code="CAMP-POS", body="x", sent_at=_em(TERCA))
        self.assertEqual(self._item(self._fila(TERCA + dt.timedelta(days=1)), self.a), [])  # já enviado na metade
        self.assertEqual([i.code for i in self._item(self._fila(dt.date(2026, 9, 19)), self.a)], ["campanha_posicao"])  # véspera
        self.assertEqual(self._item(self._fila(dt.date(2026, 9, 20)), self.a), [])  # último dia: os dados atrasam
        # campanha que ainda não foi aprovada não gera nada
        with system_context():
            Campaign.objects.filter(pk=self.duelo.pk).update(approval="aguardando")
        self.assertEqual(self._item(self._fila(dt.date(2026, 9, 19)), self.a), [])

    def test_dia_seguinte_ao_fim_chegou_perto(self):
        itens = self._fila(dt.date(2026, 9, 21))
        (fim,) = self._item(itens, self.a)  # 12º com prêmio até o 10º
        self.assertEqual((fim.code, fim.template), ("campanha_fim", "APO-06"))
        self.assertEqual(self._item(itens, self.d), [])  # 9º: ganhou, fica para o passo 4.6 (premiação)
        with system_context():
            S.fill_queue_messages([fim], self.ag)
        self.assertIn("muito perto na Duelo Demo", fim.text)
        self.assertEqual(self._item(self._fila(dt.date(2026, 9, 24)), self.a), [])  # passou da janela

    def test_campanha_curta_e_quase_la_na_ultima_semana(self):
        self.assertEqual(set(CP.checkpoints(Campaign(start=dt.date(2026, 9, 10), end=dt.date(2026, 9, 12)))), {"abertura", "vespera"})
        with system_context():
            Campaign.objects.filter(pk=self.duelo.pk).update(start=dt.date(2026, 9, 20), end=dt.date(2026, 9, 30))
        (pos,) = self._item(self._fila(dt.date(2026, 9, 29)), self.a)  # véspera, na última semana do mês
        self.assertEqual(pos.priority, 1)

"""Marco da primeira LIVE (etapa 5, passo 5.1; textos provisórios aprovados pela Mariana em 23/11/2026).

Na manhã seguinte à leitura da 1ª LIVE, o Meu progresso mostra quanto durou e se contou como dia válido, com três
perguntas opcionais de um toque. As respostas vão para a ficha e para os cards do novato; a gestora recebe aviso
na primeira resposta. Dados inventados (sufixo .demo)."""
import datetime as dt

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.rls import set_context, system_context
from crm.models import Creator
from data import engine as E
from engage import first_live as FL
from engage.models import FirstLiveCheckin, Notification
from engage.tom import verificar_tom
from web import services as S

from . import factories as F


def _leitura(c, dia_sem, dia_com, horas=4 / 3, validos=1):
    """Duas leituras diárias: a de `dia_sem` sem LIVE, a de `dia_com` com a 1ª LIVE."""
    F.snapshot(c, E.month_start(dia_sem), dia_sem)
    F.snapshot(c, E.month_start(dia_com), dia_com, diamonds=300, hours=horas, valid_days=validos, streams=1)


class MarcoPrimeiraLiveTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.ua = F.user()
        cls.a = F.creator(cls.ag, username="novata.demo", streamer_user=cls.ua)
        cls.g = F.user(role="gestora", ag=cls.ag)
        assign_manager(cls.a, cls.g)
        cls.hoje = E.tiktok_today()
        Creator.objects.filter(pk=cls.a.pk).update(joined_at=timezone.now() - dt.timedelta(days=4))
        cls.a.refresh_from_db()
        _leitura(cls.a, cls.hoje - dt.timedelta(days=2), cls.hoje - dt.timedelta(days=1))
        set_context()

    def tearDown(self):
        set_context()

    def _post(self, q, v=""):
        return self.client.post(reverse("first_live_answer"), {"q": q, "v": v}, HTTP_HX_REQUEST="true")

    def test_cartao_no_meu_progresso_com_duracao_e_dia_valido(self):
        self.client.force_login(self.ua)
        tela = self.client.get("/")
        for trecho in ["Sua primeira LIVE 🎉", "Sua primeira LIVE com a Hera durou 1h20 e contou como dia válido, pela regra do TikTok",
                       "O que foi mais difícil?", "Vergonha", "Como você se sentiu?", "Mais ou menos 😐",
                       "Com o que você quer ajuda agora?", "Como atrair público", "Fechar"]:
            self.assertContains(tela, trecho)
        with system_context():
            c = self.a
            card = FL.card(c, list(c.snapshots.all()), self.hoje)
        self.assertEqual(verificar_tom(card["headline"]), [])

    def test_responder_avisa_a_gestora_uma_vez_e_some_quando_completa(self):
        self.client.force_login(self.ua)
        r = self._post("hardest", "vergonha")
        self.assertContains(r, 'aria-pressed="true"')
        self._post("feeling", "nao_existe")  # resposta fora da lista não grava
        self._post("feeling", "mais_ou_menos")
        with system_context():
            ck = FirstLiveCheckin.objects.get(creator=self.a)
            self.assertEqual((ck.hardest, ck.feeling, ck.help, ck.live_date), ("vergonha", "mais_ou_menos", "", self.hoje - dt.timedelta(days=1)))
            avisos = Notification.objects.filter(user=self.g, kind="primeira_live")
            self.assertEqual(avisos.count(), 1)  # só na primeira resposta
            self.assertIn("mais difícil: vergonha", avisos.get().body)
        self.assertContains(self.client.get("/"), "Sua primeira LIVE com a Hera")  # ainda falta uma
        self.assertContains(self._post("help", "o_que_falar"), "Valeu por contar!")
        self.assertNotContains(self.client.get("/"), "Sua primeira LIVE com a Hera")
        # a gestora vê na ficha (aba Onboarding e linha do tempo)
        self.client.force_login(self.g)
        aba = self.client.get(reverse("g_creator", args=[self.a.pk]) + "?tab=onboarding")
        self.assertContains(aba, "1ª LIVE: o que contou no app")
        self.assertContains(aba, "Mais difícil: vergonha · sentiu: mais ou menos · quer ajuda: o que falar na live")
        self.assertContains(self.client.get(reverse("g_creator", args=[self.a.pk])), "1ª LIVE: o criador contou no app como foi")

    def test_fechar_tira_o_cartao(self):
        self.client.force_login(self.ua)
        self.assertEqual(self._post("close").content, b"")
        self.assertNotContains(self.client.get("/"), "Sua primeira LIVE com a Hera")
        with system_context():
            self.assertFalse(Notification.objects.filter(user=self.g, kind="primeira_live").exists())

    def test_gestora_nao_responde_pelo_criador(self):
        self.client.force_login(self.g)
        self.client.post(reverse("first_live_answer"), {"q": "hardest", "v": "nada"})
        with system_context():
            self.assertFalse(FirstLiveCheckin.objects.exists())


class RegrasDoCartaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.novata = F.creator(cls.ag, username="d3.demo", joined_days_ago=8)  # entrou em 20/09/2026
        cls.antiga = F.creator(cls.ag, username="antiga.demo", joined_days_ago=200)
        cls.semanal = F.creator(cls.ag, username="semanal.demo", joined_days_ago=8)
        cls.g = F.user(role="gestora", ag=cls.ag)
        for c in (cls.novata, cls.antiga, cls.semanal):
            assign_manager(c, cls.g)
        _leitura(cls.novata, dt.date(2026, 9, 20), dt.date(2026, 9, 21), horas=0.75, validos=0)
        _leitura(cls.antiga, dt.date(2026, 9, 20), dt.date(2026, 9, 21))
        F.snapshot(cls.semanal, dt.date(2026, 9, 1), dt.date(2026, 9, 27), diamonds=900, hours=5, valid_days=3, streams=4)  # uma leitura só
        set_context()

    def tearDown(self):
        set_context()

    def _card(self, c, today):
        with system_context():
            return FL.card(c, list(c.snapshots.all()), today)

    def test_texto_sem_dia_valido_leitura_de_varios_dias_e_base_antiga(self):
        self.assertEqual(self._card(self.novata, dt.date(2026, 9, 22))["headline"],
                         "Sua primeira LIVE com a Hera durou 45 min e ainda não contou como dia válido, pela regra do TikTok. 🎉")
        self.assertIsNone(self._card(self.novata, dt.date(2026, 9, 29)))  # mais de 7 dias depois
        self.assertIsNone(self._card(self.antiga, dt.date(2026, 9, 22)))  # base antiga: a "1ª LIVE" da leitura não é a 1ª
        self.assertEqual(self._card(self.semanal, dt.date(2026, 9, 28))["headline"], "Você fez a sua primeira LIVE com a Hera! 🎉")

    def test_respostas_aparecem_no_card_do_novato_na_fila(self):
        with system_context():
            FirstLiveCheckin.objects.create(creator=self.novata, live_date=dt.date(2026, 9, 21), hardest="tecnica", help="tecnica",
                                            answered_at=timezone.now())
            itens = S.action_queue(Creator.objects.filter(pk=self.novata.pk), self.ag, today=dt.date(2026, 9, 22), raw=True)
        detalhes = [i.detail for i in itens if i.code.startswith("onboarding")]
        self.assertTrue(detalhes)
        self.assertTrue(all("No app, sobre a 1ª LIVE: mais difícil: parte técnica · quer ajuda: parte técnica." in d for d in detalhes))

    def test_duracao(self):
        self.assertEqual([FL.fmt_duration(s) for s in (2700, 3600, 4800, 11100)], ["45 min", "1h", "1h20", "3h05"])

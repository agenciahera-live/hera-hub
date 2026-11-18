"""Meu progresso: a tela inicial do app do criador (etapa 3, passo 3.1).

O topo muda com a fase; a frase do mês tem três versões; a projeção é sempre estimativa; nada de ranking, de
comparação com outro criador, de "meta" nem de pedido de horas, dias ou horário."""
import datetime as dt
import re
from types import SimpleNamespace as NS
from unittest import mock

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core.rls import set_context, system_context
from data.models import MonthlyResult
from engage.models import Campaign
from engage.tom import verificar_tom
from web import progress as P

from . import factories as F

HOJE = dt.date(2026, 9, 24)  # quinta-feira; as fábricas contam a entrada a partir de 28/09


def _texto(resposta):
    html = resposta.content.decode()
    html = re.sub(r"<head>.*?</head>|<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


class FraseDoMesTests(SimpleTestCase):
    """As três versões da visão, nesta ordem, e o caso de quem já passou da marca."""

    def _frase(self, diamantes, previsao, horas=40, dias=20, horas_passado=40, dias_passado=20, dia_do_mes=20):
        nxt = NS(tier=3, min_diamonds=80_000)
        level = {"next": nxt, "reached": diamantes >= 80_000, "missing": max(80_000 - diamantes, 0)}
        snap = NS(diamonds=diamantes, live_seconds=horas * 3600, valid_days=dias)
        pace = NS(elapsed_days=dia_do_mes, month_days=30, forecast=previsao)
        passado = NS(live_seconds=horas_passado * 3600, valid_days=dias_passado)
        return P.month_phrase(level, snap, pace, passado, near_pct=85)

    def test_as_tres_versoes(self):
        self.assertEqual(self._frase(50_000, 85_000)["text"], "No seu ritmo, você chega ao Nível 3 este mês. Parabéns pela constância!")
        self.assertTrue(self._frase(50_000, 85_000)["estimate"])  # projeção: sempre com o aviso de estimativa
        self.assertEqual(self._frase(72_000, 76_000)["text"], "Você está a 8.000 💎 do Nível 3. Dá pra chegar.")
        abaixo = self._frase(20_000, 30_000, horas=10, horas_passado=40)  # 10h no dia 20 contra 26,7h no mesmo ponto
        self.assertEqual(abaixo["text"], "Suas horas de LIVE estão abaixo do mês passado. Quer ver a aula sobre rotina?")
        dias = self._frase(20_000, 30_000, horas=30, dias=5, dias_passado=20)  # horas mantidas, menos dias
        self.assertEqual(dias["text"], "Seus dias de LIVE estão abaixo do mês passado. Quer ver a aula sobre rotina?")

    def test_ordem_e_casos_sem_frase(self):
        # no ritmo de subir vence "perto"; e quem já passou da marca não recebe promessa
        self.assertEqual(self._frase(72_000, 90_000)["kind"], "no_ritmo")
        self.assertEqual(self._frase(81_000, 99_000)["text"], "Você já passou da marca do Nível 3 neste mês. O nível muda no fechamento do mês.")
        self.assertIsNone(self._frase(20_000, 30_000))  # mês igual ao passado e longe do próximo nível: sem frase
        self.assertIsNone(self._frase(3_000, 90_000, dia_do_mes=1))  # no 1º dia do mês o ritmo ainda não diz nada
        self.assertIsNone(P.month_phrase({"next": None}, None, None, None, 85))  # sem dados do mês

    def test_a_frase_nunca_promete_nem_pede(self):
        for args in [(50_000, 85_000), (72_000, 76_000), (81_000, 99_000)]:
            texto = self._frase(*args)["text"]
            self.assertEqual(verificar_tom(texto), [], texto)
            self.assertNotRegex(texto.lower(), r"vai subir|precisa|tem que|faça|por dia")
        for kw in [{"horas": 10}, {"horas": 30, "dias": 5}]:
            texto = self._frase(20_000, 30_000, **kw)["text"]
            self.assertEqual(verificar_tom(texto), [], texto)

    def test_estimativa_arredondada_e_faixas_de_nivel(self):
        self.assertEqual([P.round_estimate(v) for v in (0, 847, 3_456, 31_304, 149_500)], [0, 850, 3_500, 31_000, 150_000])
        regras = [NS(tier=1, min_diamonds=0), NS(tier=2, min_diamonds=40_000), NS(tier=3, min_diamonds=80_000)]
        self.assertEqual(P.level_table(regras), [{"level": 1, "min": 0, "max": 39_999}, {"level": 2, "min": 40_000, "max": 79_999},
                                                 {"level": 3, "min": 80_000, "max": None}])


class MeuProgressoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.u_vet, cls.u_grad, cls.u_novo = F.user(), F.user(), F.user()
        cls.vet = F.creator(cls.ag, username="vet.demo", streamer_user=cls.u_vet)  # entrou em março
        cls.grad = F.creator(cls.ag, username="grad.demo", streamer_user=cls.u_grad, joined_days_ago=40)  # D37: janela de graduação
        cls.novo = F.creator(cls.ag, username="novo.demo", streamer_user=cls.u_novo, joined_days_ago=8)  # D5
        # veterano: Nível 2 pelo mês de agosto; setembro com uma semana mais leve (a 2ª) e a 4ª em andamento
        MonthlyResult.objects.create(creator=cls.vet, month=dt.date(2026, 7, 1), diamonds=30_000, live_seconds=30 * 3600, valid_days=15, tier=1, source="backstage")
        MonthlyResult.objects.create(creator=cls.vet, month=dt.date(2026, 8, 1), diamonds=45_000, live_seconds=40 * 3600, valid_days=20, tier=2, source="backstage")
        for fim, diamantes, horas, dias in [(6, 10_000, 10, 4), (13, 12_000, 12, 5), (20, 22_000, 22, 9), (23, 24_000, 24, 10)]:
            F.snapshot(cls.vet, dt.date(2026, 9, 1), dt.date(2026, 9, fim), diamonds=diamantes, hours=horas, valid_days=dias, streams=dias, battles=3)
        F.snapshot(cls.grad, dt.date(2026, 9, 1), dt.date(2026, 9, 23), diamonds=50_000, hours=40, valid_days=15, streams=15)
        set_context()

    def setUp(self):
        patcher = mock.patch("data.engine.tiktok_today", return_value=HOJE)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        set_context()

    def _inicio(self, usuario):
        self.client.force_login(usuario)
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        return r, _texto(r)

    def test_veterano_ve_nivel_frase_ritmo_semanas_e_meses(self):
        r, texto = self._inicio(self.u_vet)
        for trecho in ["Oi, Teste!", "dados até 23/09", "Meu nível", "Nível 2", "24.000 💎 em setembro",
                       "Próximo nível: Nível 3, a partir de 80.000 💎 no mês. Faltam 56.000.",
                       "Neste mês: 24h de LIVE · 10 dias válidos · 3 batalhas",
                       "Suas horas de LIVE estão abaixo do mês passado. Quer ver a aula sobre rotina?",
                       "No seu ritmo", "Mantendo esse ritmo, você fecha o mês em torno de 31.000 💎",
                       "Estimativa pelo seu histórico, não é garantia.", "Pedir batalha oficial", "Semanas deste mês",
                       "Semana mais leve: menos dias de LIVE que na sua melhor semana.", "em andamento",
                       "Meses desde a entrada", "ago/26", "45.000 💎", "jul/26", "Em dourado, o seu melhor mês."]:
            self.assertIn(trecho, texto)
        for trecho in ["Tier", "Acelerar", "precisa", "Seus primeiros 14 dias", "Graduação", "Próximo passo"]:
            self.assertNotIn(trecho, texto)
        self.assertEqual(verificar_tom(texto), [])
        self.assertNotRegex(texto.lower(), r"ranking|posição|\dº")
        self.assertContains(r, 'class="weak"', count=1)  # só a semana mais fraca é destacada; a em andamento não entra na conta

    def test_novato_ve_a_contagem_e_o_proximo_passo_no_lugar_dos_numeros(self):
        _r, texto = self._inicio(self.u_novo)
        for trecho in ["Seus primeiros 14 dias", "regra do TikTok", "Dias válidos 0 de 5", "Tempo de LIVE 0h de 15h",
                       "A contagem vai até 03/10. O dia do TikTok vira às 21h de Brasília.", "Próximo passo",
                       "Abrir a sua primeira LIVE.", "sem dados ainda", "Pedir batalha oficial"]:
            self.assertIn(trecho, texto)
        for trecho in ["Meu nível", "No seu ritmo", "Mantendo esse ritmo", "Tier", "Meses desde a entrada"]:
            self.assertNotIn(trecho, texto)
        self.assertEqual(verificar_tom(texto), [])
        # depois da 1ª LIVE, o próximo passo é o que falta da contagem (fato da regra do TikTok, não pedido da Hera)
        with system_context():
            F.snapshot(self.novo, dt.date(2026, 9, 1), dt.date(2026, 9, 23), diamonds=900, hours=5, valid_days=2, streams=2)
        _r, texto = self._inicio(self.u_novo)
        for trecho in ["Dias válidos 2 de 5", "Tempo de LIVE 5h de 15h", "Para completar a contagem do TikTok: 3 dias válidos e 10h de LIVE.",
                       "dados até 23/09"]:
            self.assertIn(trecho, texto)
        self.assertNotIn("Mantendo esse ritmo", texto)  # nos 14 dias o criador ainda não tem número para projetar

    def test_janela_de_graduacao_vira_destaque_depois_do_d30(self):
        _r, texto = self._inicio(self.u_grad)
        for trecho in ["Nível 1", "Você já passou da marca do Nível 2 neste mês", "Graduação", "regra do TikTok", "80.000 💎 em um mês",
                       "50.000 / 80.000", "Faltam 30.000 💎 neste mês. Seu ritmo: 2.174 💎 por dia.",
                       "A janela vai até 16/11: 3 meses, contando este."]:
            self.assertIn(trecho, texto)
        self.assertEqual(verificar_tom(texto), [])
        self.assertNotIn("Graduação", self._inicio(self.u_vet)[1])  # fora da janela não aparece

    def test_uma_campanha_so_na_tela_inicial(self):
        with system_context():
            for nome, dias in [("Campanha que fecha depois", 10), ("Campanha que fecha antes", 2)]:
                Campaign.objects.create(agency=self.ag, name=nome, source="interna", rules="Regras.", what_to_do="Abra LIVE e convide o seu público.",
                                        start=HOJE - dt.timedelta(days=1), end=HOJE + dt.timedelta(days=dias))
        _r, texto = self._inicio(self.u_vet)
        self.assertIn("Campanha do momento", texto)
        self.assertIn("Campanha que fecha antes", texto)
        self.assertIn("até 26/09", texto)
        self.assertNotIn("Campanha que fecha depois", texto)  # as outras ficam na tela Campanhas
        self.assertContains(self.client.get(reverse("campaigns") + "?aba=hera"), "Campanha que fecha depois")

    def test_meu_nivel_mostra_a_faixa_de_cada_nivel_e_os_grupos(self):
        self.client.force_login(self.u_vet)
        r = self.client.get(reverse("my_level"))
        texto = _texto(r)
        for trecho in ["Meu nível: 2", "pelo mês de agosto", "Próximo nível: Nível 3", "24.000 / 80.000 💎",
                       "Faltam 56.000 💎 neste mês. O nível muda no fechamento do mês.", "Faixa de cada nível", "até 39.999 💎",
                       "40.000 a 79.999 💎", "você está aqui", "Bronze", "Nível 1", "Prata", "Nível 2 a 3", "Diamante", "Nível 5 ou mais"]:
            self.assertIn(trecho, texto)
        self.assertNotIn("Tier", texto)
        self.assertEqual(verificar_tom(texto), [])
        self.assertContains(self.client.get(reverse("profile")), "NÍVEL")

    def test_enderecos_antigos_levam_para_as_telas_novas(self):
        self.client.force_login(self.u_vet)
        self.assertRedirects(self.client.get("/desempenho/"), "/#semanas", fetch_redirect_response=False)
        self.assertRedirects(self.client.get("/desempenho/?aba=historico"), "/#meses", fetch_redirect_response=False)
        self.assertRedirects(self.client.get("/meu-tier/"), "/meu-nivel/", fetch_redirect_response=False)
        barra = self.client.get("/").content.decode()
        self.assertNotIn("Desempenho", barra)
        self.assertIn(reverse("battles"), barra)  # Batalhas entrou na barra de baixo

    def test_semana_em_andamento_nao_e_comparada(self):
        with system_context():
            semanas = P.weeks_of_month(list(self.vet.snapshots.all()), HOJE)
        self.assertEqual([(s["iv"].diamonds, s["closed"], s["weak"]) for s in semanas],
                         [(2_000, False, False), (10_000, True, False), (2_000, True, True), (10_000, True, False)])
        with system_context():  # uma semana fechada só: nada a destacar
            self.assertFalse(any(s["weak"] for s in P.weeks_of_month(list(self.grad.snapshots.all()), HOJE)))

"""Regras da visão nas telas: sem palavras vetadas para o criador e sem ranking em nenhuma tela."""
import datetime as dt
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core.access import assign_manager
from core.rls import set_context, system_context
from data.engine import recalculate
from engage import defaults as D
from engage.models import BattleRequest, Campaign, FaqItem
from engage.tom import verificar_tom

from . import factories as F

TEMPLATES = Path(settings.BASE_DIR) / "templates"


def _texto_do_template(caminho):
    """Texto que a pessoa lê: tira tags e variáveis do Django e o <head>."""
    bruto = caminho.read_text(encoding="utf-8")
    bruto = re.sub(r"{%.*?%}|{{.*?}}|{#.*?#}", " ", bruto, flags=re.S)
    return re.sub(r"<head>.*?</head>", " ", bruto, flags=re.S)


def _texto_da_pagina(resposta):
    html = resposta.content.decode()
    html = re.sub(r"<head>.*?</head>|<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", html)


class VerificadorDeTomTests(SimpleTestCase):
    def test_barra_palavras_vetadas(self):
        for frase in ["Sua meta do mês", "Veja o relatório", "Sem cobrança", "O prazo acaba hoje", "Qual horário?",
                      "Ranking do Tier", "Fale com sua gestora", "Obrigada!", "Bora juntas", "Seja bem-vinda"]:
            self.assertTrue(verificar_tom(frase), frase)

    def test_aceita_texto_neutro(self):
        for frase in ["Metade do caminho", "Treino obrigatório", "Regra do TikTok", "Fale com a Hera", "Valeu!",
                      "Marque uma batalha entre 20h e 21h", "Boas-vindas"]:
            self.assertEqual(verificar_tom(frase), [], frase)


class TelasDoCriadorSemPalavrasVetadas(SimpleTestCase):
    def test_templates_do_criador(self):
        arquivos = sorted((TEMPLATES / "streamer").glob("*.html")) + sorted((TEMPLATES / "account").glob("*.html"))
        arquivos.append(TEMPLATES / "offline.html")
        self.assertGreater(len(arquivos), 15)
        for arq in arquivos:
            self.assertEqual(verificar_tom(_texto_do_template(arq)), [], arq.name)

    def test_textos_padrao_da_central_de_duvidas_e_dicas(self):
        for categoria, pergunta, resposta, _chaves in D.FAQ:
            self.assertEqual(verificar_tom(f"{categoria} {pergunta} {resposta}"), [], pergunta)
        for dica in D.TIPS:
            self.assertEqual(verificar_tom(dica), [], dica)

    def test_rotulos_do_pedido_de_batalha(self):
        for _valor, rotulo in BattleRequest.KINDS + BattleRequest.STATUS:
            self.assertEqual(verificar_tom(rotulo), [], rotulo)


class PaginasRenderizadasTests(TestCase):
    """Abre as telas com dados fictícios: novato nos 14 dias (missões e barras) e veterano."""

    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.gestao = F.user(role="gestora", ag=cls.ag, first_name="Ana")
        cls.admin = F.user(role="admin", ag=cls.ag)
        cls.u_vet, cls.u_novo = F.user(), F.user()
        today = dt.date.today()
        cls.vet = F.creator(cls.ag, username="vet.demo", streamer_user=cls.u_vet)
        cls.novo = F.creator(cls.ag, username="novo.demo", streamer_user=cls.u_novo)
        cls.novo.joined_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=5)
        cls.novo.save()
        for c in (cls.vet, cls.novo):
            assign_manager(c, cls.gestao)
            F.snapshot(c, today.replace(day=1), today, diamonds=3000, hours=4, valid_days=2, streams=3)
        cls.interna = Campaign.objects.create(
            agency=cls.ag, name="Maratona Teste", source="relampago", metric="hours", goal=4, rules="Some 4 horas de LIVE.",
            what_to_do="Some 4 horas de LIVE.", prizes="Sorteio", start=today - dt.timedelta(days=2), end=today + dt.timedelta(days=2))
        BattleRequest.objects.create(creator=cls.vet, kind="oficial", date=today + dt.timedelta(days=8), time=dt.time(20, 0),
                                     goal_diamonds=20000, status="outro_horario", manager_reply="Pode ser no sábado?")
        recalculate(cls.ag)
        cls.categorias = list(FaqItem.objects.filter(agency=cls.ag).values_list("category", flat=True).distinct())
        set_context()

    def tearDown(self):
        set_context()

    def test_paginas_do_criador(self):
        urls = ["/", reverse("my_level"),  # Desempenho foi unida ao Meu progresso (tela inicial)
                reverse("campaigns"), reverse("campaigns") + "?aba=hera", reverse("campaign", args=[self.interna.pk]),
                reverse("academy"), reverse("profile"), reverse("faq"), reverse("battles"), reverse("battle_new"),
                reverse("offers"), reverse("announcements"), reverse("notifications"), reverse("my_plan"),
                reverse("faq_search") + "?q=batalha", reverse("faq_search") + "?q=dia valido", reverse("faq_search") + "?q=xyzxyz"]
        urls += [reverse("faq") + f"?cat={c}" for c in self.categorias]
        for usuario in (self.u_vet, self.u_novo):
            self.client.force_login(usuario)
            for url in urls:
                r = self.client.get(url)
                self.assertEqual(r.status_code, 200, url)
                self.assertEqual(verificar_tom(_texto_da_pagina(r)), [], url)

    def test_mensagens_de_retorno_ao_criador(self):
        self.client.force_login(self.u_vet)
        d = (dt.date.today() + dt.timedelta(days=3)).isoformat()
        r = self.client.post(reverse("battle_new"), {"kind": "especial", "date": d, "time": "20:30", "duration_min": "60"}, follow=True)
        self.assertEqual(verificar_tom(_texto_da_pagina(r)), [])
        r = self.client.post(reverse("battle_new"), {"kind": "especial", "date": "x", "time": "20:30"})
        self.assertEqual(verificar_tom(_texto_da_pagina(r)), [])
        r = self.client.post(reverse("ask_manager"), {"question": "Como troco meu @?"})
        self.assertEqual(verificar_tom(_texto_da_pagina(r)), [])

    def test_telas_de_entrada_e_primeiro_acesso(self):
        for url in ["/accounts/login/", reverse("first_access")]:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertEqual(verificar_tom(_texto_da_pagina(r)), [], url)
        # mensagens de erro do primeiro acesso (código errado, senha curta, senhas diferentes)
        for dados in [{"handle": "@ninguem", "code": "AAAA-BBBB", "email": "x@teste.local", "password": "senha-boa-123", "password2": "senha-boa-123"},
                      {"handle": "@ninguem", "code": "AAAA-BBBB", "email": "x", "password": "123", "password2": "123"},
                      {"handle": "@ninguem", "code": "AAAA-BBBB", "email": "x@teste.local", "password": "senha-boa-123", "password2": "outra"}]:
            r = self.client.post(reverse("first_access"), dados)
            self.assertContains(r, "errorlist")
            self.assertEqual(verificar_tom(_texto_da_pagina(r)), [])

    def test_novato_ve_a_contagem_dos_14_dias_no_inicio(self):
        self.client.force_login(self.u_novo)
        r = self.client.get("/")
        self.assertContains(r, "Seus primeiros 14 dias")
        self.assertContains(r, "regra do TikTok")
        self.assertNotContains(r, "Missão da semana")
        self.client.force_login(self.u_vet)
        self.assertNotContains(self.client.get("/"), "Seus primeiros 14 dias")

    def test_nenhuma_tela_mostra_ranking(self):
        with system_context():
            self.assertTrue(self.interna.standings.exists())  # o progresso continua sendo calculado
        self.client.force_login(self.admin)
        for url in ["/gestao/", "/gestao/campanhas/", reverse("g_campaign", args=[self.interna.pk]),
                    reverse("g_creator", args=[self.vet.pk]), "/gestao/relatorios/"]:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
            texto = _texto_da_pagina(r)
            self.assertNotRegex(texto.lower(), r"ranking|posição|classificação geral", url)
            self.assertNotRegex(texto, r"\dº", url)
        self.client.force_login(self.u_vet)
        for url in ["/", reverse("campaigns") + "?aba=hera", reverse("campaign", args=[self.interna.pk])]:
            texto = _texto_da_pagina(self.client.get(url))
            self.assertNotRegex(texto.lower(), r"ranking|posição", url)
            self.assertNotRegex(texto, r"\dº", url)

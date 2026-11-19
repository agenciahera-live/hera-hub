"""Biblioteca de mensagens (passo 2.6): textos do Playbook, variações por trilha e "faz batalha", verificador de tom,
histórico de versões, e a semana sintética que alimenta a demonstração."""
import datetime as dt
from pathlib import Path

from django.conf import settings
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from core.access import assign_manager
from core.bootstrap import setup_agency
from core.models import Agency
from core.rls import set_context, system_context
from crm.models import Creator
from engage import playbook
from engage.library import sync_defaults
from engage.models import MessageTemplate, MessageVersion
from engage.services import outside_track, template_for
from engage.tom import verificar_tom_mensagem

from . import factories as F

# Os quatro textos do Playbook que o verificador barrava (SAI-01, RES-01, BAT-PEDIDO e BAT-ATUALIZA) foram revisados pela
# Mariana em 18/11 e não têm mais "prazo" nem "horário". A biblioteca padrão passa inteira no verificador.
EXCECOES_CONHECIDAS = {}
REVISADAS_18_11 = {"SAI-01", "RES-01", "BAT-PEDIDO", "BAT-ATUALIZA", "REG-14", "QUEDA-01", "REC-01", "CONVITE-APP",
                   "NR-24H-CASA", "NR-2D-CASA", "NR-3D-CASA"}


class VerificadorDeTomDasMensagensTests(SimpleTestCase):
    def test_barra_meta_cobranca_prazo_horario_e_texto_so_no_feminino(self):
        barradas = ["Faltam 2 dias pra bater a meta", "Sem cobrança, mas...", "O prazo acaba sexta", "Qual horário você consegue?",
                    "Seja bem-vinda à Hera!", "Você já tá pronta pra começar", "você tá super encaminhada", "o resto é só ser você mesma"]
        for texto in barradas:
            self.assertTrue(verificar_tom_mensagem(texto), texto)

    def test_aceita_forma_neutra_fuso_e_a_gestora_falando_de_si(self):
        aceitas = ["Seja bem-vindo(a) à Hera", "você tá super encaminhado(a)!", "O dia do TikTok vira às 21h (horário de Brasília)",
                   "obrigada por avisar", "eu mesma cuido de tudo por aqui", "toda pessoa recém-agenciada precisa ter 5 dias válidos",
                   "Não precisa estar perfeita", "Qual dia dessa semana fica bom pra você?"]
        for texto in aceitas:
            self.assertEqual(verificar_tom_mensagem(texto), [], texto)

    def test_biblioteca_padrao_passa_no_verificador_com_as_excecoes_que_vieram_do_playbook(self):
        barradas = {}
        for m in playbook.MESSAGES:
            problemas = verificar_tom_mensagem(m["body"])
            if problemas:
                barradas[m["code"]] = problemas
        self.assertEqual(barradas, EXCECOES_CONHECIDAS)

    def test_biblioteca_padrao_esta_coerente(self):
        chaves = [(m["code"], m["variant"]) for m in playbook.MESSAGES]
        self.assertEqual(len(chaves), len(set(chaves)))
        for m in playbook.MESSAGES:
            self.assertIn(m["source"], ("playbook", "roteiro", "provisorio", "agencia"))
            self.assertTrue(set(m["tracks"]) <= {"primeira_live", "outra_agencia", "nivel_publico"}, m["code"])
            if m["variant"]:  # toda variação tem um modelo geral com o mesmo código
                self.assertIn((m["code"], ""), chaves, m["code"])
        codigos = {m["code"] for m in playbook.MESSAGES}
        self.assertFalse(codigos & set(playbook.RETIRED))  # sem resumo de números pelo WhatsApp
        # as 4 provisórias ganharam o texto da Hera em 18/11, junto com a cadência para quem já é da casa
        self.assertEqual([m["code"] for m in playbook.MESSAGES if m["source"] == "provisorio"], [])
        self.assertEqual({m["code"] for m in playbook.MESSAGES if m["source"] == "agencia" and not m["code"].startswith("DUV-")},
                         {"REG-14", "QUEDA-01", "REC-01", "CONVITE-APP", "NR-24H-CASA", "NR-2D-CASA", "NR-3D-CASA"})
        # decisão 5: 23 dúvidas frequentes do roteiro na biblioteca, sem a graduação e sem repetir a BAT-PEDIDO
        duvidas = [m for m in playbook.MESSAGES if m["code"].startswith("DUV-")]
        self.assertEqual(len(duvidas), 23)
        self.assertFalse([m for m in duvidas if "gradua" in (m["title"] + m["body"]).lower()])
        self.assertTrue(all(m["stage"].startswith("Dúvidas frequentes · ") for m in duvidas))
        self.assertEqual(len(playbook.NICHE_GUIDE), 5)


class BibliotecaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.admin = F.user(role="admin", ag=cls.ag, first_name="Mariana")
        cls.gestora = F.user(role="gestora", ag=cls.ag)
        cls.conteudo = F.user(role="conteudo", ag=cls.ag)
        cls.c = F.creator(cls.ag, username="roteiro.demo")
        assign_manager(cls.c, cls.gestora)
        set_context()

    def tearDown(self):
        set_context()

    def _modelo(self, code, variant=""):
        with system_context():
            return MessageTemplate.objects.get(agency=self.ag, code=code, variant=variant)

    def _criador(self, **campos):
        with system_context():
            Creator.objects.filter(pk=self.c.pk).update(**campos)
            return Creator.objects.get(pk=self.c.pk)

    # ------------------------------------------------------------ carga
    def test_agencia_nova_recebe_a_biblioteca_do_playbook(self):
        with system_context():
            self.assertEqual(MessageTemplate.objects.filter(agency=self.ag).count(), len(playbook.MESSAGES))
            self.assertFalse(MessageTemplate.objects.filter(agency=self.ag, code__in=playbook.RETIRED).exists())
        regra = self._modelo("ONB-D2-04")
        self.assertIn("regra do próprio TikTok e não da Hera", regra.body)
        self.assertEqual(self._modelo("ONB-NL-D7").source, "playbook")
        self.assertIn("{dias_validos} dias válidos e {horas} horas", self._modelo("META-D10").body)  # [X dias / Y horas] virou variável

    def test_preparar_a_agencia_de_novo_nao_mexe_em_texto_editado_e_a_carga_guarda_a_versao(self):
        with system_context():
            MessageTemplate.objects.filter(agency=self.ag, code="ROD-PERG").update(body="Texto que a Hera editou")
            MessageTemplate.objects.filter(agency=self.ag, code="APO-06").delete()
            setup_agency(name="Agência Teste", slug="hera")  # roda em todo seed e em todo criar_admin
            self.assertEqual(self._modelo("ROD-PERG").body, "Texto que a Hera editou")
            self.assertTrue(MessageTemplate.objects.filter(agency=self.ag, code="APO-06").exists())  # só cria o que falta
            # carga de uma revisão do Playbook: troca o texto e guarda o anterior como versão
            sync_defaults(Agency.objects.get(pk=self.ag.pk), overwrite=True)
            rod = self._modelo("ROD-PERG")
            self.assertIn("Como estão as LIVEs por aí?", rod.body)
            self.assertEqual(list(rod.versions.values_list("body", flat=True)), ["Texto que a Hera editou"])

    # ------------------------------------------------------------ variação por trilha e por "faz batalha"
    def test_escolhe_a_variacao_pela_trilha_e_pelo_faz_batalha(self):
        casos = [
            ({}, "ONB-D1-01", ""),  # sem trilha definida: modelo geral (Primeira LIVE)
            ({"track_suggested": "outra_agencia"}, "ONB-D1-01", "outra-agencia"),  # vale a sugestão do cadastro enquanto a gestão não define
            ({"track": "nivel_publico", "track_suggested": "outra_agencia"}, "ONB-D1-01", "nivel-publico"),  # a trilha da gestão vence
            ({"track": "outra_agencia"}, "ONB-D2-04", "ja-faz-live"),
            ({"track": "nivel_publico"}, "ONB-D2-04", "ja-faz-live"),
            ({"track": "primeira_live"}, "ONB-D2-04", ""),
            ({"track": "primeira_live", "does_battles": "nao"}, "DES-D4-01", "sem-batalha"),
            ({"track": "primeira_live", "does_battles": "sim"}, "DES-D4-01", ""),
            ({"track": "nivel_publico", "does_battles": "nao"}, "EST-02", "sem-batalha"),
            ({"track": "outra_agencia"}, "APO-03", ""),  # sem variação: o mesmo para todos
        ]
        for campos, code, esperado in casos:
            c = self._criador(**{"track": "", "track_suggested": "", "does_battles": "", **campos})
            with system_context():
                self.assertEqual(template_for(self.ag, code, c).variant, esperado, (campos, code))
        # modelo que só existe para outra trilha: aparece, mas marcado
        c = self._criador(track="primeira_live", track_suggested="", does_battles="")
        with system_context():
            estrategia = template_for(self.ag, "EST-01", c)
            self.assertTrue(outside_track(estrategia, c))
            self.assertFalse(outside_track(template_for(self.ag, "DES-D2-01", c), c))

    def test_ficha_mostra_o_roteiro_na_versao_do_criador(self):
        self._criador(track="outra_agencia", niche="gamer", does_battles="nao")
        self.client.force_login(self.gestora)
        aba = self.client.get(reverse("g_creator", args=[self.c.pk]) + "?tab=mensagens")
        self.assertContains(aba, "Trilha: <b>Veio de outra agência</b>", html=False)
        self.assertContains(aba, "A Hera não fica com nenhuma parte dos seus ganhos")  # boas-vindas de quem veio de outra agência
        self.assertNotContains(aba, "Seja bem-vindo(a) à Hera Agency")  # e não a geral
        self.assertContains(aba, "chamar alguém como convidado(a) ou co-host")  # D4 de quem não faz batalha
        self.assertContains(aba, "Ajustes do nicho Gamer")
        self.assertContains(aba, "outra trilha")  # a estratégia de quem já tem nível e público aparece marcada
        # o "Enviei" grava a versão do criador
        self.client.post(reverse("g_sent", args=[self.c.pk, "ONB-D1-01"]))
        with system_context():
            self.assertIn("Como você já tem experiência com agência", self.c.contacts.get(template_code="ONB-D1-01").body)

    # ------------------------------------------------------------ tela da biblioteca
    def test_tela_lista_filtra_e_marca_provisorias_e_alertas(self):
        self.client.force_login(self.gestora)
        tela = self.client.get(reverse("g_messages"))
        for texto in ["Biblioteca de mensagens", "Cadência de não-resposta", "Entrou e ainda não abriu LIVE", "Ajustes por nicho",
                      "Ver detalhes e versões", "NR-24H-CASA", "depois do D15 (quem já é da casa)"]:
            self.assertContains(tela, texto)
        self.assertNotContains(tela, "tom: prazo")  # revisão de 18/11: nenhuma mensagem padrão com palavra vetada
        self.assertNotContains(tela, "Editar e ver versões")  # gestora sem o papel Conteúdo só lê
        provisorias = self.client.get(reverse("g_messages") + "?ver=provisorias")
        self.assertNotContains(provisorias, "REG-14")  # ganhou o texto da Hera
        self.assertNotContains(provisorias, "ONB-D1-02")
        busca = self.client.get(reverse("g_messages") + "?q=heart me")
        self.assertContains(busca, "DES-D3-HM")
        self.assertNotContains(busca, "ROD-PERG")
        so_t3 = self.client.get(reverse("g_messages") + "?trilha=nivel_publico")
        self.assertContains(so_t3, "EST-01")
        self.assertNotContains(so_t3, "DES-D5-02")  # o Desafio dos 5 dias não vale para quem já tem nível e público

    def test_so_socias_e_conteudo_editam_e_cada_mudanca_guarda_a_versao(self):
        t = self._modelo("ROD-PERG")
        url = reverse("g_message", args=[t.pk])
        original = t.body
        self.client.force_login(self.gestora)
        self.assertEqual(self.client.post(url, {"a": "save", "title": t.title, "body": "Mudei"}).status_code, 403)
        self.client.force_login(self.conteudo)
        self.assertContains(self.client.get(url), "Salvar")
        self.client.post(url, {"a": "save", "title": t.title, "body": "Oi {nome}! Como vai a semana por aí? 💜"})
        self.client.force_login(self.admin)
        self.client.post(url, {"a": "save", "title": "Pergunta aberta (nova)", "body": "Oi {nome}! Tudo certo com as LIVEs? 💜"})
        t = self._modelo("ROD-PERG")
        self.assertEqual((t.title, t.body), ("Pergunta aberta (nova)", "Oi {nome}! Tudo certo com as LIVEs? 💜"))
        with system_context():
            versoes = list(MessageVersion.objects.filter(template=t).order_by("saved_at", "id"))
        self.assertEqual([v.body for v in versoes], [original, "Oi {nome}! Como vai a semana por aí? 💜"])  # nada sobrescrito
        self.assertEqual([v.saved_by_id for v in versoes], [self.conteudo.pk, self.admin.pk])
        tela = self.client.get(url)
        self.assertContains(tela, "Histórico de versões")
        self.assertContains(tela, "trocada por Mariana")
        # restaurar a primeira versão
        self.client.post(url, {"a": "restore", "version": versoes[0].pk})
        self.assertEqual(self._modelo("ROD-PERG").body, original)
        with system_context():
            self.assertEqual(MessageVersion.objects.filter(template=t).count(), 3)

    def test_biblioteca_de_uma_agencia_nao_abre_para_outra_nem_para_o_criador(self):
        t = self._modelo("ROD-PERG")
        url = reverse("g_message", args=[t.pk])
        with system_context():
            outra = F.agency(slug="outra")
            de_fora = F.user(role="admin", ag=outra)
            streamer = F.user()
            F.creator(self.ag, username="streamer.demo", streamer_user=streamer)
        self.client.force_login(de_fora)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, {"a": "save", "title": "x", "body": "Texto de fora"}).status_code, 404)
        self.assertEqual(self._modelo("ROD-PERG").body, t.body)
        self.client.force_login(streamer)
        self.assertNotEqual(self.client.get(reverse("g_messages")).status_code, 200)
        self.assertNotEqual(self.client.get(url).status_code, 200)

    def test_verificador_de_tom_nao_deixa_salvar(self):
        t = self._modelo("ROD-PERG")
        url = reverse("g_message", args=[t.pk])
        self.client.force_login(self.admin)
        for ruim in ["Oi {nome}! Qual horário você consegue abrir LIVE?", "Oi {nome}, falta pouco pra bater a meta!", "Seja bem-vinda de volta!"]:
            r = self.client.post(url, {"a": "save", "title": t.title, "body": ruim})
            self.assertContains(r, "O verificador de tom barrou esta mensagem")
            self.assertContains(r, ruim.split("!")[0])  # o rascunho continua na tela para corrigir
        self.assertEqual(self._modelo("ROD-PERG").body, t.body)
        with system_context():
            self.assertEqual(MessageVersion.objects.filter(template=t).count(), 0)
        # texto já gravado que o verificador barraria (ex.: veio de uma revisão antiga): a tela avisa
        with system_context():
            MessageTemplate.objects.filter(pk=self._modelo("SAI-01").pk).update(body="Pode voltar quando quiser, sem prazo de espera.")
        self.assertContains(self.client.get(reverse("g_message", args=[self._modelo("SAI-01").pk])), "O verificador de tom barraria este texto")

    def test_revisao_pontual_troca_so_os_codigos_revisados(self):
        """A migração da revisão de 18/11 troca só as mensagens revisadas; o que a gestão editou nas outras fica."""
        from engage.library import sync_defaults

        with system_context():
            editada = self._modelo("ROD-PERG")
            MessageTemplate.objects.filter(pk=editada.pk).update(body="Texto editado pela Hera na tela")
            revisada = self._modelo("SAI-01")
            MessageTemplate.objects.filter(pk=revisada.pk).update(body="Texto antigo com prazo")
            MessageTemplate.objects.filter(agency=self.ag, code="NR-24H-CASA").delete()
            sync_defaults(self.ag, overwrite=True, only_codes=REVISADAS_18_11)
            self.assertEqual(self._modelo("ROD-PERG").body, "Texto editado pela Hera na tela")
            self.assertNotIn("prazo", self._modelo("SAI-01").body)
            self.assertTrue(MessageVersion.objects.filter(template=revisada, body="Texto antigo com prazo").exists())
            self.assertTrue(MessageTemplate.objects.filter(agency=self.ag, code="NR-24H-CASA").exists())


class SemanaSinteticaTests(TestCase):
    """A semana real fica fora do repositório. Para os testes existe uma semana inventada, no mesmo formato."""

    FIXTURE = Path(settings.BASE_DIR) / "tests" / "fixtures" / "semana-sintetica.json"

    def tearDown(self):
        set_context()

    def _carregar(self):
        from web.management.commands.demo_semana import Command

        cmd = Command()
        cmd.handle(arquivo=str(self.FIXTURE), ano=2026)
        return cmd

    def test_comando_carrega_a_semana_e_o_motor_bate_com_o_arquivo(self):
        cmd = self._carregar()
        self.assertEqual(cmd.diffs, [])  # estado, segmento e prioridade iguais aos do arquivo, para todos
        with system_context():
            ag = Agency.objects.get(slug="semana-demo")
            self.assertEqual(Creator.objects.filter(agency=ag).count(), 10)
            self.assertTrue(all(u.endswith(".demo") for u in Creator.objects.filter(agency=ag).values_list("username", flat=True)))
        # a fila roda em cima dela
        from web import services as S

        with system_context():
            q = S.action_queue(Creator.objects.filter(agency=ag), ag, today=dt.date(2026, 11, 9))
        self.assertIn("queda", [i.code for i in q])
        self.assertIn("regua_14", [i.code for i in q])
        # rodar de novo recria a agência de demonstração, sem duplicar
        self._carregar()
        with system_context():
            self.assertEqual(Agency.objects.filter(slug="semana-demo").count(), 1)

    @override_settings(IS_PRODUCTION=True)
    def test_logins_de_demonstracao_nao_nascem_em_producao(self):
        from django.core.management import call_command

        with self.assertRaises(CommandError):
            self._carregar()
        with self.assertRaises(CommandError):
            call_command("seed_demo", verbosity=0)
        with system_context():
            self.assertFalse(Agency.objects.filter(slug="semana-demo").exists())

    def test_app_nao_liga_em_producao_com_login_de_demonstracao_no_banco(self):
        from core.checks import demo_logins_check

        with override_settings(IS_PRODUCTION=True):
            self.assertEqual(demo_logins_check(None), [])  # banco limpo: liga
        self._carregar()  # cria admin@semana.demo e gestora.a@semana.demo até gestora.e
        self.assertEqual(demo_logins_check(None), [])  # no computador da Hera, tudo bem
        with override_settings(IS_PRODUCTION=True):
            self.assertEqual([e.id for e in demo_logins_check(None)], ["hera.E002"])

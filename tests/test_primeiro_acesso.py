"""Login do criador (decisão de 14/11/2026): código de acesso gerado pela gestão + e-mail e senha criados pelo criador."""
import datetime as dt

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.rls import set_context, system_context
from crm import first_access as FA
from crm.models import AccessCode, Contact, Creator

from . import factories as F

SENHA = "senha-boa-123"


class PrimeiroAcessoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.gx = F.user(role="gestora", ag=cls.ag)
        cls.gy = F.user(role="gestora", ag=cls.ag)
        cls.novo = F.creator(cls.ag, username="novo.demo", status="pendente")
        cls.outro = F.creator(cls.ag, username="outro.demo", status="pendente")
        assign_manager(cls.novo, cls.gx)
        assign_manager(cls.outro, cls.gy)
        set_context()

    def tearDown(self):
        set_context()

    # ------------------------------------------------------------ apoio
    def _gerar(self, creator=None, gestora=None):
        creator = creator or self.novo
        self.client.force_login(gestora or self.gx)
        self.client.post(reverse("g_access_code", args=[creator.pk]))
        self.client.logout()
        with system_context():
            return FA.active_code(creator)

    def _entrar(self, code, handle="@novo.demo", email="novo@teste.local", senha=SENHA, senha2=None):
        return self.client.post(reverse("first_access"), {"handle": handle, "code": code, "email": email,
                                                         "password": senha, "password2": senha if senha2 is None else senha2})

    def _creator(self, c=None):
        with system_context():
            return Creator.objects.select_related("user").get(pk=(c or self.novo).pk)

    # ------------------------------------------------------------ gestão
    def test_gestora_gera_codigo_e_ve_mensagem_pronta(self):
        ac = self._gerar()
        self.assertEqual(len(ac.code), 8)
        self.assertTrue(set(ac.code) <= set(AccessCode.ALPHABET))
        self.assertEqual(self._creator().status, "convidado")
        self.client.force_login(self.gx)
        ficha = self.client.get(reverse("g_creator", args=[self.novo.pk]))
        self.assertContains(ficha, ac.display)
        self.assertContains(ficha, "http://testserver/primeiro-acesso/")  # link do app dentro da mensagem pronta
        self.assertContains(ficha, "Copiar mensagem")
        self.assertContains(ficha, "Gerar outro código")
        # "Enviei" do convite registra o contato, com o código dentro da mensagem
        self.client.post(reverse("g_sent", args=[self.novo.pk, "CONVITE-APP"]))
        with system_context():
            contato = Contact.objects.get(creator=self.novo, template_code="CONVITE-APP")
        self.assertIn(ac.display, contato.body)
        self.assertNotIn("{", contato.body)  # nenhuma variável sem preencher

    def test_gerar_outro_codigo_cancela_o_anterior(self):
        primeiro = self._gerar()
        segundo = self._gerar()
        self.assertNotEqual(primeiro.code, segundo.code)
        self.assertContains(self._entrar(primeiro.display), "Confira o seu @ e o código")
        self.assertRedirects(self._entrar(segundo.display), "/boas-vindas/", fetch_redirect_response=False)

    def test_gestora_de_outra_carteira_nao_gera_nem_ve_codigo(self):
        self._gerar()
        self.client.force_login(self.gy)
        self.assertEqual(self.client.post(reverse("g_access_code", args=[self.novo.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("g_creator", args=[self.novo.pk])).status_code, 404)

    def test_quem_saiu_nao_recebe_codigo(self):
        with system_context():
            Creator.objects.filter(pk=self.novo.pk).update(status="saiu")
        self.assertIsNone(self._gerar())

    # ------------------------------------------------------------ criador
    def test_criador_cria_senha_com_o_codigo_e_depois_entra_com_email_e_senha(self):
        ac = self._gerar()
        # aceita o @ com maiúsculas e o código em minúsculas, com ou sem hífen
        r = self._entrar(ac.code.lower(), handle="  @Novo.Demo ", email="Novo@Teste.Local")
        self.assertRedirects(r, "/boas-vindas/", fetch_redirect_response=False)
        c = self._creator()
        self.assertEqual(c.user.email, "novo@teste.local")
        self.assertTrue(c.user.check_password(SENHA))
        self.assertEqual((c.status, c.confirmed_username), ("ativo", True))
        with system_context():
            self.assertIsNotNone(AccessCode.objects.get(pk=ac.pk).used_at)
            self.assertEqual(c.private.email, "novo@teste.local")
        # já está dentro: aceita o termo e pula a pergunta "É você?" (informou o @ junto com o código)
        self.assertRedirects(self.client.get("/"), "/boas-vindas/", fetch_redirect_response=False)
        r = self.client.post("/boas-vindas/", {"action": "consent", "accept": "on"})
        self.assertRedirects(r, "/boas-vindas/?s=c", fetch_redirect_response=False)  # segue para o cadastro (experiência e aniversário)
        self.assertEqual(self.client.get("/").status_code, 200)
        # o código vale uma vez
        self.client.logout()
        self.assertContains(self._entrar(ac.display, email="b@teste.local"), "Confira o seu @ e o código")
        # dali em diante: e-mail e senha
        r = self.client.post("/accounts/login/", {"login": "novo@teste.local", "password": SENHA})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get("/").status_code, 200)
        self.client.logout()
        r = self.client.post("/accounts/login/", {"login": "novo@teste.local", "password": "errada-123"})
        self.assertEqual(r.status_code, 200)

    def test_codigo_errado_cinco_vezes_cancela_o_codigo(self):
        ac = self._gerar()
        for _ in range(AccessCode.MAX_ATTEMPTS):
            self.assertContains(self._entrar("ZZZZ-ZZZZ"), "Confira o seu @ e o código")
        self.assertContains(self._entrar(ac.display), "Confira o seu @ e o código")
        self.assertIsNone(self._creator().user)

    def test_codigo_vencido_codigo_de_outro_e_arroba_errado(self):
        ac = self._gerar()
        do_outro = self._gerar(self.outro, self.gy)
        self.assertContains(self._entrar(do_outro.display), "Confira o seu @ e o código")  # código de outro criador
        self.assertContains(self._entrar(ac.display, handle="@nao.existe"), "Confira o seu @ e o código")
        with system_context():
            AccessCode.objects.filter(pk=ac.pk).update(expires_at=timezone.now() - dt.timedelta(minutes=1), failed_attempts=0)
        self.assertContains(self._entrar(ac.display), "Confira o seu @ e o código")
        self.assertIsNone(self._creator().user)

    def test_quem_saiu_depois_de_receber_o_codigo_nao_entra(self):
        ac = self._gerar()
        with system_context():
            Creator.objects.filter(pk=self.novo.pk).update(status="saiu")
        self.assertContains(self._entrar(ac.display), "Confira o seu @ e o código")

    def test_senha_fraca_ou_diferente_nao_gasta_o_codigo(self):
        ac = self._gerar()
        self.assertContains(self._entrar(ac.display, senha="123"), "muito curta")
        self.assertContains(self._entrar(ac.display, senha2="outra-senha-123"), "não são iguais")
        self.assertContains(self._entrar(ac.display, email="sem-arroba"), "e-mail válido")
        with system_context():
            self.assertEqual(AccessCode.objects.get(pk=ac.pk).failed_attempts, 0)
        self.assertRedirects(self._entrar(ac.display), "/boas-vindas/", fetch_redirect_response=False)

    def test_email_de_outra_pessoa_nao_pode_ser_usado(self):
        F.user(email="ocupado@teste.local")
        ac = self._gerar()
        self.assertContains(self._entrar(ac.display, email="ocupado@teste.local"), "já está em uso")
        self.assertRedirects(self._entrar(ac.display, email="livre@teste.local"), "/boas-vindas/", fetch_redirect_response=False)

    def test_codigo_novo_serve_para_criar_senha_nova(self):
        """Esqueceu a senha (ou entrou pelo convite antigo, sem senha): a gestão gera outro código."""
        antigo = F.user(email="antigo@teste.local")
        with system_context():
            Creator.objects.filter(pk=self.novo.pk).update(user=antigo, status="ativo")
        ac = self._gerar()
        self.assertRedirects(self._entrar(ac.display, email="antigo@teste.local", senha="senha-nova-456"), "/boas-vindas/",
                             fetch_redirect_response=False)
        c = self._creator()
        self.assertEqual(c.user.pk, antigo.pk)  # mesmo cadastro, senha nova
        self.assertTrue(c.user.check_password("senha-nova-456"))
        self.assertEqual(get_user_model().objects.filter(email="antigo@teste.local").count(), 1)

    # ------------------------------------------------------------ o e-mail nunca recupera acesso
    def test_nao_existe_recuperacao_por_email_nem_google(self):
        self.assertRedirects(self.client.get("/accounts/password/reset/"), "/primeiro-acesso/", fetch_redirect_response=False)
        self.assertRedirects(self.client.post("/accounts/password/reset/", {"email": "novo@teste.local"}), "/primeiro-acesso/",
                             fetch_redirect_response=False)
        for url in ["/accounts/login/code/", "/accounts/google/login/"]:
            self.assertNotEqual(self.client.get(url).status_code, 200, url)
        # cadastro aberto continua fechado: ninguém cria login sem o código da gestão
        self.client.post("/accounts/signup/", {"email": "intruso@teste.local", "password1": SENHA})
        self.assertFalse(get_user_model().objects.filter(email="intruso@teste.local").exists())
        entrar = self.client.get("/accounts/login/")
        self.assertContains(entrar, reverse("first_access"))
        self.assertNotContains(entrar, "Google")
        self.assertNotContains(entrar, "código por e-mail")

"""Coisas que só quebram em produção (encontradas na simulação de publicação de 18/11/2026)."""
import gc
import io

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.models.signals import post_save
from django.test import TestCase

from core.models import Membership
from core.rls import set_context


class AcessoDasSociasAosCadastrosTests(TestCase):
    def tearDown(self):
        set_context()

    def test_receptor_do_papel_nao_some_da_memoria(self):
        # Com referência fraca, o receptor era descartado e as sócias ficavam sem acesso aos cadastros em produção.
        gc.collect()
        self.assertTrue(post_save.has_listeners(Membership))

    def test_gestora_cadastrada_em_configuracoes_entra_com_email_e_senha(self):
        """Como a sócia cadastra pela tela Configurações: usuário (nome de usuário = e-mail), senha e e-mail; depois o papel."""
        from . import factories as F

        set_context(system=True)
        ag = F.agency()
        admin = get_user_model().objects.create_user(username="socia@teste.local", email="socia@teste.local", password="x")
        Membership.objects.create(user=admin, agency=ag, role="admin")
        set_context()
        self.client.force_login(get_user_model().objects.get(pk=admin.pk))
        r = self.client.post("/gestao/admin/auth/user/add/", {"username": "gestora.nova@teste.local", "password1": "Senha-Forte-2026-g",
                                                             "password2": "Senha-Forte-2026-g", "usable_password": "true"})
        self.assertEqual(r.status_code, 302, r.content[:2000])
        nova = get_user_model().objects.get(username="gestora.nova@teste.local")
        nova.email = "gestora.nova@teste.local"
        nova.save()
        r = self.client.post("/gestao/admin/core/membership/add/", {"user": nova.pk, "role": "gestora", "phone": "", "active": "on"})
        self.assertEqual(r.status_code, 302, r.content[:2000])
        self.client.logout()
        r = self.client.post("/accounts/login/", {"login": "gestora.nova@teste.local", "password": "Senha-Forte-2026-g"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get("/", follow=True).redirect_chain[-1][0], "/gestao/")

    def test_criar_admin_da_acesso_aos_cadastros(self):
        call_command("criar_admin", email="socia@teste.local", nome="Sócia", senha="Senha-Forte-2026-x", stdout=io.StringIO())
        set_context(system=True)
        u = get_user_model().objects.get(email="socia@teste.local")
        self.assertTrue(u.is_staff)
        self.assertTrue(u.is_superuser)

"""Prepara a agência e cria o primeiro Admin (ou troca a senha de um Admin que já existe).

    python manage.py criar_admin --email voce@hera.com.br --nome "Mariana" --agencia "Agência Hera"

Sem --senha, o comando cria uma senha provisória e mostra na tela.
"""
import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from allauth.account.models import EmailAddress
from core.bootstrap import ensure_permission_groups, setup_agency
from core.models import Membership
from core.rls import system_context


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--nome", default="")
        parser.add_argument("--agencia", default="Agência Hera")
        parser.add_argument("--slug", default="hera")
        parser.add_argument("--senha", default="", help="8 caracteres ou mais. Sem ela, o comando cria uma senha provisória.")

    def handle(self, *args, **o):
        senha = o["senha"] or secrets.token_urlsafe(9)
        try:
            validate_password(senha)
        except ValidationError as e:
            raise CommandError(" ".join(e.messages))
        with system_context():
            ag = setup_agency(name=o["agencia"], slug=o["slug"])
            ensure_permission_groups()
            User = get_user_model()
            email = o["email"].lower()
            u, _ = User.objects.get_or_create(username=email, defaults={"email": email, "first_name": o["nome"]})
            u.set_password(senha)
            u.save()
            EmailAddress.objects.get_or_create(user=u, email=email, defaults={"verified": True, "primary": True})
            Membership.objects.get_or_create(user=u, agency=ag, role="admin")
        aviso = "" if o["senha"] else f" Senha provisória: {senha} (troque em Configurações → Alterar senha)."
        self.stdout.write(self.style.SUCCESS(f"Pronto. Entre com {email} e a senha.{aviso}"))

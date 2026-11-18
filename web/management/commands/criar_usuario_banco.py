"""Cria o usuário de banco do app (sem superusuário), para que o RLS valha.

    python manage.py criar_usuario_banco --admin-url "postgresql://postgres:SENHA@HOST:PORTA/railway"

Mostra no final a DATABASE_URL que deve ser colada nas variáveis do app.
"""
import secrets
from urllib.parse import urlparse

import psycopg
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria o usuário hera_app no Postgres (sem superusuário, sem BYPASSRLS)."

    def add_arguments(self, parser):
        parser.add_argument("--admin-url", required=True, help="URL do banco com o usuário administrador (postgres)")
        parser.add_argument("--role", default="hera_app")

    def handle(self, *args, **o):
        url = urlparse(o["admin_url"])
        dbname = url.path.lstrip("/")
        pwd = secrets.token_urlsafe(24)
        role = o["role"]
        with psycopg.connect(o["admin_url"], autocommit=True) as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", [role])
            if cur.fetchone():
                cur.execute(f'ALTER ROLE "{role}" WITH LOGIN PASSWORD %s NOSUPERUSER NOBYPASSRLS', [pwd])
            else:
                cur.execute(f'CREATE ROLE "{role}" WITH LOGIN PASSWORD %s NOSUPERUSER NOBYPASSRLS NOCREATEROLE', [pwd])
            cur.execute(f'GRANT ALL PRIVILEGES ON DATABASE "{dbname}" TO "{role}"')
            cur.execute(f'GRANT ALL ON SCHEMA public TO "{role}"')
            cur.execute(f'ALTER SCHEMA public OWNER TO "{role}"')
        new = f"postgresql://{role}:{pwd}@{url.hostname}:{url.port}/{dbname}"
        self.stdout.write(self.style.SUCCESS("Usuário criado. Cole esta DATABASE_URL nas variáveis do app:"))
        self.stdout.write(new)

"""Cria o usuário de banco do app (sem superusuário), para que o RLS valha.

    python manage.py criar_usuario_banco --admin-url "postgresql://postgres:SENHA@HOST:PORTA/railway"

Mostra no final a DATABASE_URL que deve ser colada nas variáveis do app.
"""
import secrets
from urllib.parse import urlparse

import psycopg
from psycopg import sql
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
        # O Postgres não aceita parâmetro ($1) em CREATE/ALTER ROLE: a senha entra como literal montado com segurança.
        r, db = sql.Identifier(role), sql.Identifier(dbname)
        with psycopg.connect(o["admin_url"], autocommit=True) as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", [role])
            if cur.fetchone():
                cur.execute(sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {} NOSUPERUSER NOBYPASSRLS").format(r, sql.Literal(pwd)))
            else:
                cur.execute(sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD {} NOSUPERUSER NOBYPASSRLS NOCREATEROLE").format(r, sql.Literal(pwd)))
            cur.execute(sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(db, r))
            cur.execute(sql.SQL("GRANT ALL ON SCHEMA public TO {}").format(r))
            cur.execute(sql.SQL("ALTER SCHEMA public OWNER TO {}").format(r))
        new = f"postgresql://{role}:{pwd}@{url.hostname}:{url.port}/{dbname}"
        self.stdout.write(self.style.SUCCESS("Usuário criado. Cole esta DATABASE_URL nas variáveis do app:"))
        self.stdout.write(new)

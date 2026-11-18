"""Contexto de segurança no banco (Row-Level Security).

A cada requisição o app informa ao Postgres quem é o usuário logado
(`app.user_id`). As políticas de RLS (migração core/0002) usam esse valor.
Tarefas internas (importação por comando, cron, seeds) usam `system_context()`.
"""
from contextlib import contextmanager

from django.db import connection


def set_context(user_id=None, system=False):
    with connection.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.user_id', %s, false), set_config('app.system', %s, false)",
            [str(user_id) if user_id else "", "on" if system else "off"],
        )


def get_context():
    with connection.cursor() as cur:
        cur.execute("SELECT current_setting('app.user_id', true), current_setting('app.system', true)")
        return cur.fetchone()


@contextmanager
def system_context():
    prev = get_context()
    set_context(system=True)
    try:
        yield
    finally:
        set_context(user_id=prev[0] or None, system=(prev[1] == "on"))


@contextmanager
def as_user(user):
    prev = get_context()
    set_context(user_id=user.pk if user else None)
    try:
        yield
    finally:
        set_context(user_id=prev[0] or None, system=(prev[1] == "on"))

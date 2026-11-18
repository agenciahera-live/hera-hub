"""Segurança no banco para as tabelas novas da ficha (passo 2.2): respostas, motivo de quem parou, lembretes e
registro de batalhas. São tabelas INTERNAS, no mesmo padrão de web/0001_rls: só a gestão que enxerga o criador lê,
só quem edita o criador grava, e o próprio criador nunca vê."""
from django.db import migrations

TABLES = ["crm_reply", "crm_stopreason", "crm_reminder", "crm_battlerecord"]


def forward():
    sql = ""
    for t in TABLES:
        sql += f"""
ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {t} FORCE ROW LEVEL SECURITY;
CREATE POLICY {t}_select ON {t} FOR SELECT USING (hera_staff_can_view(creator_id));
CREATE POLICY {t}_insert ON {t} FOR INSERT WITH CHECK (hera_staff_can_edit(creator_id));
CREATE POLICY {t}_update ON {t} FOR UPDATE USING (hera_staff_can_edit(creator_id)) WITH CHECK (hera_staff_can_edit(creator_id));
CREATE POLICY {t}_delete ON {t} FOR DELETE USING (hera_staff_can_edit(creator_id));
"""
    return sql


def reverse():
    sql = ""
    for t in TABLES:
        for op in ("select", "insert", "update", "delete"):
            sql += f"DROP POLICY IF EXISTS {t}_{op} ON {t};\n"
        sql += f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY;\n"
    return sql


class Migration(migrations.Migration):
    dependencies = [("web", "0003_rls_codigo_acesso"), ("crm", "0004_ficha_do_criador")]
    operations = [migrations.RunSQL(forward(), reverse())]

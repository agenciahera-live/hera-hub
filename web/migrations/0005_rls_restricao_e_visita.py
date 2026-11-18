"""Segurança no banco para os casos de restrição ou banimento e para as visitas às LIVEs.
Tabelas INTERNAS, no padrão de web/0004: a gestão que enxerga o criador lê, quem edita grava, o criador nunca vê."""
from django.db import migrations

TABLES = ["crm_accountcase", "crm_visit"]


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
    dependencies = [("web", "0004_rls_ficha_do_criador"), ("crm", "0006_restricao_e_visita")]
    operations = [migrations.RunSQL(forward(), reverse())]

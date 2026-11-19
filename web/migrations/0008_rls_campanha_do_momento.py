"""Segurança no banco para a campanha do momento escolhida pela gestora (passo 3.4).

O criador lê a dele (o app precisa saber qual campanha mostrar), nunca a de outro criador.
Só quem edita o criador (sócias e a gestora da carteira) grava. Quem cobre a carteira não escolhe campanha.
A situação de cada criador nas campanhas (engage_campaignparticipant) já tinha RLS (0001_rls)."""
from django.db import migrations

TABLES = ["engage_campaignpick"]


def forward():
    sql = ""
    for t in TABLES:
        sql += f"""
ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {t} FORCE ROW LEVEL SECURITY;
CREATE POLICY {t}_select ON {t} FOR SELECT USING (hera_can_view(creator_id));
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
    dependencies = [("web", "0007_rls_hera_academy"), ("engage", "0021_campanhas_lidas_do_backstage")]
    operations = [migrations.RunSQL(forward(), reverse())]

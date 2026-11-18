"""Segurança no banco para a Hera Academy (passo 3.2): módulo liberado antes da hora e aula escolhida pela gestora.

O criador lê as dele (o app precisa saber o que abriu e qual aula mostrar), nunca as de outro criador.
Só quem edita o criador (sócias e a gestora da carteira) grava. Quem cobre a carteira não libera módulo."""
from django.db import migrations

TABLES = ["engage_modulerelease", "engage_lessonpick"]


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
    dependencies = [("web", "0006_rls_carteiras_e_ausencia"), ("engage", "0016_hera_academy_modulos")]
    operations = [migrations.RunSQL(forward(), reverse())]

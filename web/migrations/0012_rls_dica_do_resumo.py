"""Segurança no banco para a dica da Hera no resumo do mês (engage_monthtip). O criador lê a dele (o app mostra);
nunca a de outro criador. Só quem edita o criador (a gestora da carteira ou uma sócia) grava."""
from django.db import migrations

T = "engage_monthtip"
FORWARD = f"""
ALTER TABLE {T} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {T} FORCE ROW LEVEL SECURITY;
CREATE POLICY {T}_select ON {T} FOR SELECT USING (hera_can_view(creator_id));
CREATE POLICY {T}_insert ON {T} FOR INSERT WITH CHECK (hera_staff_can_edit(creator_id));
CREATE POLICY {T}_update ON {T} FOR UPDATE USING (hera_staff_can_edit(creator_id)) WITH CHECK (hera_staff_can_edit(creator_id));
CREATE POLICY {T}_delete ON {T} FOR DELETE USING (hera_staff_can_edit(creator_id));
"""
REVERSE = "".join(f"DROP POLICY IF EXISTS {T}_{op} ON {T};\n" for op in ("select", "insert", "update", "delete")) + \
    f"ALTER TABLE {T} DISABLE ROW LEVEL SECURITY;\n"


class Migration(migrations.Migration):
    dependencies = [("web", "0011_rls_sinais_de_risco"), ("engage", "0027_dica_do_resumo_do_mes")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]

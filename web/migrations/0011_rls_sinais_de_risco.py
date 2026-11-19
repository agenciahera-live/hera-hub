"""Segurança no banco para os sinais de risco marcados pela gestora (passo 4.3). Tabela interna: só a gestão que
enxerga o criador lê; só quem edita o criador (a gestora da carteira ou uma sócia) marca. O criador nunca lê."""
from django.db import migrations

T = "crm_risksignal"
FORWARD = f"""
ALTER TABLE {T} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {T} FORCE ROW LEVEL SECURITY;
CREATE POLICY {T}_select ON {T} FOR SELECT USING (hera_staff_can_view(creator_id));
CREATE POLICY {T}_insert ON {T} FOR INSERT WITH CHECK (hera_staff_can_edit(creator_id));
CREATE POLICY {T}_update ON {T} FOR UPDATE USING (hera_staff_can_edit(creator_id)) WITH CHECK (hera_staff_can_edit(creator_id));
CREATE POLICY {T}_delete ON {T} FOR DELETE USING (hera_staff_can_edit(creator_id));
"""
REVERSE = "".join(f"DROP POLICY IF EXISTS {T}_{op} ON {T};\n" for op in ("select", "insert", "update", "delete")) + \
    f"ALTER TABLE {T} DISABLE ROW LEVEL SECURITY;\n"


class Migration(migrations.Migration):
    dependencies = [("web", "0010_rls_painel_das_socias"), ("crm", "0013_sinais_de_risco")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]

"""Segurança no banco para a posição do criador nas campanhas (passo 4.5).

engage_campaignposition: a gestão que enxerga o criador lê (decisão da Mariana de 22/11/2026: a gestora vê a posição);
o criador nunca lê, nem a dele (no app do criador não existe posição nem ranking). Só a leitura do Backstage (sistema)
grava e apaga.
"""
from django.db import migrations

T = "engage_campaignposition"

FORWARD = f"""
ALTER TABLE {T} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {T} FORCE ROW LEVEL SECURITY;
CREATE POLICY {T}_select ON {T} FOR SELECT USING (hera_staff_can_view(creator_id));
CREATE POLICY {T}_insert ON {T} FOR INSERT WITH CHECK (hera_is_system());
CREATE POLICY {T}_update ON {T} FOR UPDATE USING (hera_is_system()) WITH CHECK (hera_is_system());
CREATE POLICY {T}_delete ON {T} FOR DELETE USING (hera_is_system());
"""

REVERSE = "".join(f"DROP POLICY IF EXISTS {T}_{op} ON {T};\n" for op in ("select", "insert", "update", "delete")) + \
    f"ALTER TABLE {T} DISABLE ROW LEVEL SECURITY;\n"


class Migration(migrations.Migration):
    dependencies = [("web", "0012_rls_dica_do_resumo"), ("engage", "0028_acompanhamento_de_campanhas")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]

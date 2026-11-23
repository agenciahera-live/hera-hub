"""Segurança no banco para o marco da primeira LIVE (etapa 5, passo 5.1).

As respostas são do criador: só ele grava (e a rotina, como sistema, para a LGPD). A gestão que vê o criador lê
(ficha e fila), mas nunca edita. Um criador nunca lê as respostas de outro. Mesmo modelo do Meu plano (0009)."""
from django.db import migrations

T = "engage_firstlivecheckin"
WR = "(hera_is_own(creator_id) OR hera_is_system())"
DL = ("(hera_is_own(creator_id) OR hera_is_system() OR EXISTS (SELECT 1 FROM crm_creator c "
      "WHERE c.id = creator_id AND hera_has_role(c.agency_id, ARRAY['admin'])))")

FORWARD = f"""
ALTER TABLE {T} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {T} FORCE ROW LEVEL SECURITY;
CREATE POLICY {T}_select ON {T} FOR SELECT USING (hera_can_view(creator_id));
CREATE POLICY {T}_insert ON {T} FOR INSERT WITH CHECK {WR};
CREATE POLICY {T}_update ON {T} FOR UPDATE USING {WR} WITH CHECK {WR};
CREATE POLICY {T}_delete ON {T} FOR DELETE USING {DL};
"""

REVERSE = "".join(f"DROP POLICY IF EXISTS {T}_{op} ON {T};\n" for op in ("select", "insert", "update", "delete")) + \
    f"ALTER TABLE {T} DISABLE ROW LEVEL SECURITY;\n"


class Migration(migrations.Migration):
    dependencies = [("web", "0016_rls_premiacoes"), ("engage", "0030_marco_da_primeira_live")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]

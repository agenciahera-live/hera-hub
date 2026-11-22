"""Segurança no banco para os dados do Pix (passo 4.7, parte 2; vale também para as premiações do passo 4.6).

crm_pixinfo: só o próprio criador grava e apaga; leem ele, as sócias e o financeiro. A gestora, a recrutadora, o
analista e os outros criadores não leem. A anonimização (rotina, sistema) apaga.
"""
from django.db import migrations

T = "crm_pixinfo"
MONEY = ("EXISTS (SELECT 1 FROM crm_creator c WHERE c.id = creator_id "
         "AND hera_has_role(c.agency_id, ARRAY['admin','financeiro']))")

FORWARD = f"""
ALTER TABLE {T} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {T} FORCE ROW LEVEL SECURITY;
CREATE POLICY {T}_select ON {T} FOR SELECT USING (hera_is_system() OR hera_is_own(creator_id) OR {MONEY});
CREATE POLICY {T}_insert ON {T} FOR INSERT WITH CHECK (hera_is_system() OR hera_is_own(creator_id));
CREATE POLICY {T}_update ON {T} FOR UPDATE USING (hera_is_system() OR hera_is_own(creator_id))
  WITH CHECK (hera_is_system() OR hera_is_own(creator_id));
CREATE POLICY {T}_delete ON {T} FOR DELETE USING (hera_is_system() OR hera_is_own(creator_id));
"""

REVERSE = "".join(f"DROP POLICY IF EXISTS {T}_{op} ON {T};\n" for op in ("select", "insert", "update", "delete")) + \
    f"ALTER TABLE {T} DISABLE ROW LEVEL SECURITY;\n"


class Migration(migrations.Migration):
    dependencies = [("web", "0014_rls_indique_e_ganhe"), ("crm", "0016_pix_e_recibo")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]

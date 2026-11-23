"""Segurança no banco para as premiações (passo 4.6).

crm_award: lê a gestão que enxerga o criador (inclusive o financeiro, que paga o Pix); o criador nunca. Registra quem
edita o criador (a gestora da carteira ou uma sócia). Atualiza quem edita o criador (entrega dos diamantes) e o
financeiro (Pix pago e recibo). Apagar: só as sócias. A aprovação fica no pedido às sócias (crm_approvalrequest), que
só elas decidem (web/migrations/0010).
"""
from django.db import migrations

T = "crm_award"
FIN = "hera_has_role(agency_id, ARRAY['financeiro'])"

FORWARD = f"""
ALTER TABLE {T} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {T} FORCE ROW LEVEL SECURITY;
CREATE POLICY {T}_select ON {T} FOR SELECT USING (hera_staff_can_view(creator_id));
CREATE POLICY {T}_insert ON {T} FOR INSERT WITH CHECK (hera_staff_can_edit(creator_id));
CREATE POLICY {T}_update ON {T} FOR UPDATE USING (hera_staff_can_edit(creator_id) OR {FIN})
  WITH CHECK (hera_staff_can_edit(creator_id) OR {FIN});
CREATE POLICY {T}_delete ON {T} FOR DELETE USING (hera_is_system() OR hera_has_role(agency_id, ARRAY['admin']));
"""

REVERSE = "".join(f"DROP POLICY IF EXISTS {T}_{op} ON {T};\n" for op in ("select", "insert", "update", "delete")) + \
    f"ALTER TABLE {T} DISABLE ROW LEVEL SECURITY;\n"


class Migration(migrations.Migration):
    dependencies = [("web", "0015_rls_pix"), ("crm", "0017_premiacoes")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]

"""Segurança no banco para o painel das sócias (passo 4.1).

- Pedidos de decisão (crm_approvalrequest): a gestão que enxerga o criador lê o pedido dele; quem edita o criador
  (a gestora da carteira ou uma sócia) pede; só as sócias decidem (update) e apagam. O criador nunca lê.
- Sorteio de envios (crm_sentcheck) e retrato da fila (crm_queueday): só as sócias e a rotina (sistema).
"""
from django.db import migrations

ADMIN = "(hera_is_system() OR hera_has_role(agency_id, ARRAY['admin']))"

FORWARD = f"""
ALTER TABLE crm_approvalrequest ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_approvalrequest FORCE ROW LEVEL SECURITY;
CREATE POLICY crm_approvalrequest_select ON crm_approvalrequest FOR SELECT
  USING ({ADMIN} OR (creator_id IS NOT NULL AND hera_staff_can_view(creator_id)));
CREATE POLICY crm_approvalrequest_insert ON crm_approvalrequest FOR INSERT
  WITH CHECK ({ADMIN} OR (creator_id IS NOT NULL AND hera_staff_can_edit(creator_id)));
CREATE POLICY crm_approvalrequest_update ON crm_approvalrequest FOR UPDATE USING {ADMIN} WITH CHECK {ADMIN};
CREATE POLICY crm_approvalrequest_delete ON crm_approvalrequest FOR DELETE USING {ADMIN};
"""
for t in ("crm_sentcheck", "crm_queueday"):
    FORWARD += f"""
ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {t} FORCE ROW LEVEL SECURITY;
CREATE POLICY {t}_all ON {t} FOR ALL USING {ADMIN} WITH CHECK {ADMIN};
"""

REVERSE = """
DROP POLICY IF EXISTS crm_approvalrequest_select ON crm_approvalrequest;
DROP POLICY IF EXISTS crm_approvalrequest_insert ON crm_approvalrequest;
DROP POLICY IF EXISTS crm_approvalrequest_update ON crm_approvalrequest;
DROP POLICY IF EXISTS crm_approvalrequest_delete ON crm_approvalrequest;
ALTER TABLE crm_approvalrequest DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS crm_sentcheck_all ON crm_sentcheck;
ALTER TABLE crm_sentcheck DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS crm_queueday_all ON crm_queueday;
ALTER TABLE crm_queueday DISABLE ROW LEVEL SECURITY;
"""


class Migration(migrations.Migration):
    dependencies = [("web", "0009_rls_meu_plano"), ("crm", "0011_painel_das_socias")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]

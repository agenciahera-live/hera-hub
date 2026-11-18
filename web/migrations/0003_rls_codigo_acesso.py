"""Segurança no banco para o código de acesso ao app (crm_accesscode).

Mais restrita que as outras tabelas internas: só lê e grava quem pode EDITAR o criador
(sócias e a gestora da carteira vigente) e as tarefas do sistema (a ativação em crm/first_access.py).
Recrutadora, analista, financeiro e o próprio criador nunca leem o código pelo banco."""
from django.db import migrations

FORWARD = """
ALTER TABLE crm_accesscode ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_accesscode FORCE ROW LEVEL SECURITY;
CREATE POLICY crm_accesscode_select ON crm_accesscode FOR SELECT USING (hera_staff_can_edit(creator_id));
CREATE POLICY crm_accesscode_insert ON crm_accesscode FOR INSERT WITH CHECK (hera_staff_can_edit(creator_id));
CREATE POLICY crm_accesscode_update ON crm_accesscode FOR UPDATE USING (hera_staff_can_edit(creator_id)) WITH CHECK (hera_staff_can_edit(creator_id));
CREATE POLICY crm_accesscode_delete ON crm_accesscode FOR DELETE USING (hera_staff_can_edit(creator_id));
"""
REVERSE = """
DROP POLICY IF EXISTS crm_accesscode_select ON crm_accesscode;
DROP POLICY IF EXISTS crm_accesscode_insert ON crm_accesscode;
DROP POLICY IF EXISTS crm_accesscode_update ON crm_accesscode;
DROP POLICY IF EXISTS crm_accesscode_delete ON crm_accesscode;
ALTER TABLE crm_accesscode DISABLE ROW LEVEL SECURITY;
"""


class Migration(migrations.Migration):
    dependencies = [("web", "0002_importacao_pela_gestao"), ("crm", "0003_acesso_por_codigo")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]

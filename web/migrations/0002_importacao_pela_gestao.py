"""Importação diária do Backstage pela gestão ou pelas sócias: a gestora passa a poder ler e gravar
as linhas de importação no banco (antes, só admin e financeiro). A tela confere qual tipo de arquivo cada papel envia."""
from django.db import migrations


def policy(roles):
    cond = ("EXISTS (SELECT 1 FROM data_importbatch b WHERE b.id = batch_id "
            f"AND (hera_is_system() OR hera_has_role(b.agency_id, ARRAY[{roles}])))")
    return f"""
DROP POLICY IF EXISTS importrow_all ON data_importrow;
CREATE POLICY importrow_all ON data_importrow FOR ALL USING ({cond}) WITH CHECK ({cond});
"""


class Migration(migrations.Migration):
    dependencies = [("web", "0001_rls")]
    operations = [migrations.RunSQL(policy("'admin','financeiro','gestora'"), policy("'admin','financeiro'"))]

"""Importação diária: quem ainda estava com o alerta antigo (8 dias, da importação semanal) passa para 2 dias."""
from django.db import migrations


def atualizar(apps, schema_editor):
    apps.get_model("core", "AgencySettings").objects.filter(stale_data_days=8).update(stale_data_days=2)


class Migration(migrations.Migration):
    dependencies = [("core", "0002_importacao_diaria")]
    operations = [migrations.RunPython(atualizar, migrations.RunPython.noop)]

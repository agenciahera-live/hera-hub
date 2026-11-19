"""Passo 4.3 (19/11/2026): mensagens provisórias dos itens do mês na fila (resumo do mês, nível novo, quase lá e módulo
concluído). Só cria o que falta; não mexe em nenhuma mensagem existente. Os textos esperam a revisão da Mariana."""
from django.db import migrations


def carregar(apps, schema_editor):
    from engage.library import sync_defaults

    Agency = apps.get_model("core", "Agency")
    MessageTemplate = apps.get_model("engage", "MessageTemplate")
    MessageVersion = apps.get_model("engage", "MessageVersion")
    for ag in Agency.objects.all():
        sync_defaults(ag, MessageTemplate=MessageTemplate, MessageVersion=MessageVersion)


class Migration(migrations.Migration):
    dependencies = [("engage", "0025_teste_do_app")]
    operations = [migrations.RunPython(carregar, migrations.RunPython.noop)]

"""Carrega a biblioteca de mensagens do Playbook (revisão de novembro/2026) nas agências que já existem.

- Os modelos passam a ter o texto do Playbook, palavra por palavra. O texto que estava antes fica guardado
  como versão anterior (dá para restaurar pela tela Mensagens).
- Entram as variações por trilha e por "faz batalha" e as mensagens novas.
- Saem REL-MES e LEMBRETE-SEMANA (a Hera não envia mais resumo de números pelo WhatsApp) e o provisório ONB-NL-D3.

Agência nova recebe a biblioteca pelo setup_agency."""
from django.db import migrations


def carregar(apps, schema_editor):
    from engage.library import sync_defaults

    Agency = apps.get_model("core", "Agency")
    MessageTemplate = apps.get_model("engage", "MessageTemplate")
    MessageVersion = apps.get_model("engage", "MessageVersion")
    for ag in Agency.objects.all():
        sync_defaults(ag, overwrite=True, MessageTemplate=MessageTemplate, MessageVersion=MessageVersion)


class Migration(migrations.Migration):
    dependencies = [("engage", "0014_biblioteca_de_mensagens"), ("core", "0001_initial")]
    operations = [migrations.RunPython(carregar, migrations.RunPython.noop)]

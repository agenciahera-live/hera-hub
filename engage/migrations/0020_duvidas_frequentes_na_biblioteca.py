"""Decisão 5 da revisão de 18/11/2026: as dúvidas frequentes do roteiro online entram na biblioteca de mensagens
(códigos DUV-*), com os textos revisados pela Mariana. Só cria o que falta; não mexe em nenhuma mensagem existente.
(Elas também vão para a central de dúvidas do app, adaptadas para o criador ler, em outra etapa.)"""
from django.db import migrations


def carregar(apps, schema_editor):
    from engage.library import sync_defaults

    Agency = apps.get_model("core", "Agency")
    MessageTemplate = apps.get_model("engage", "MessageTemplate")
    MessageVersion = apps.get_model("engage", "MessageVersion")
    for ag in Agency.objects.all():
        sync_defaults(ag, MessageTemplate=MessageTemplate, MessageVersion=MessageVersion)


class Migration(migrations.Migration):
    dependencies = [("engage", "0019_revisao_mensagens_18_11")]
    operations = [migrations.RunPython(carregar, migrations.RunPython.noop)]

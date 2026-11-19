"""Revisão das mensagens pela Mariana (18/11/2026, arquivo "Mensagens - decisões 1 a 5"):

1. Sem "prazo" e "horário": SAI-01, RES-01, BAT-PEDIDO e BAT-ATUALIZA.
2. Provisórias com texto da Hera: REG-14, QUEDA-01 (a gestora completa o trecho entre colchetes), REC-01 e CONVITE-APP.
3. Cadência depois do D15 para quem já é da casa: NR-24H-CASA, NR-2D-CASA e NR-3D-CASA (novas; o +5 dias é o mesmo).
4. Mural de batalhas fica sem o bloco de destaques (sem mudança).

Só esses códigos são trocados; o texto anterior fica guardado como versão. As outras mensagens, que a gestão pode ter
editado pela tela, não mudam."""
from django.db import migrations

CODES = {"SAI-01", "RES-01", "BAT-PEDIDO", "BAT-ATUALIZA", "REG-14", "QUEDA-01", "REC-01", "CONVITE-APP",
         "NR-24H-CASA", "NR-2D-CASA", "NR-3D-CASA"}


def carregar(apps, schema_editor):
    from engage.library import sync_defaults

    Agency = apps.get_model("core", "Agency")
    MessageTemplate = apps.get_model("engage", "MessageTemplate")
    MessageVersion = apps.get_model("engage", "MessageVersion")
    for ag in Agency.objects.all():
        sync_defaults(ag, overwrite=True, MessageTemplate=MessageTemplate, MessageVersion=MessageVersion, only_codes=CODES)


class Migration(migrations.Migration):
    dependencies = [("engage", "0018_batalha_oficial")]
    operations = [migrations.RunPython(carregar, migrations.RunPython.noop)]

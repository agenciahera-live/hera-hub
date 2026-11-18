"""Pedido de batalha com um tipo só ("Batalha agendada") e a resposta da central de dúvidas correspondente."""
from django.db import migrations, models

PERGUNTA_ANTIGA = "Como peço uma batalha especial?"
PERGUNTA = "Como peço uma batalha?"
RESPOSTA = ("No Início, toque em \"Pedir batalha\" e escolha o dia e a hora. A Hera busca alguém do seu mesmo nível "
            "e avisa no seu grupo e no app quando a batalha estiver confirmada.")


def atualizar(apps, schema_editor):
    FaqItem = apps.get_model("engage", "FaqItem")
    schema_editor.execute("SELECT set_config('app.system', 'on', false)")
    FaqItem.objects.filter(question__in=[PERGUNTA_ANTIGA, PERGUNTA]).update(question=PERGUNTA, answer=RESPOSTA)
    schema_editor.execute("SELECT set_config('app.system', 'off', false)")


class Migration(migrations.Migration):
    dependencies = [("engage", "0005_textos_neutros")]
    operations = [
        migrations.AlterField(
            model_name="battlerequest",
            name="kind",
            field=models.CharField(
                choices=[("oficial", "Batalha agendada"), ("especial", "Batalha especial"), ("pk", "PK agendada"),
                         ("cohost", "Cohost"), ("tematica", "LIVE temática")],
                max_length=20, verbose_name="tipo"),
        ),
        migrations.RunPython(atualizar, migrations.RunPython.noop),
    ]

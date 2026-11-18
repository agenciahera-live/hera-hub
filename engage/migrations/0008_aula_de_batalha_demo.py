"""Marca a aula de demonstração sobre batalha, para o botão da tela Pedir batalha já aparecer.

Com dados reais, a marcação é feita no cadastro da aula ("explica a batalha oficial")."""
from django.db import migrations


def marcar(apps, schema_editor):
    Lesson = apps.get_model("engage", "Lesson")
    schema_editor.execute("SELECT set_config('app.system', 'on', false)")
    if not Lesson.objects.filter(about_battles=True).exists():
        Lesson.objects.filter(title="Sua primeira batalha em 8 minutos").update(about_battles=True)
    schema_editor.execute("SELECT set_config('app.system', 'off', false)")


class Migration(migrations.Migration):
    dependencies = [("engage", "0007_batalha_opcoes_rounds_aula")]
    operations = [migrations.RunPython(marcar, migrations.RunPython.noop)]

"""Central de dúvidas: os números atualizam todo dia, e a gestão pode combinar um número de diamantes para o mês."""
from django.db import migrations

RESPOSTAS = {
    "Quando meus números atualizam?":
        "A Hera atualiza os dados do TikTok todo dia. A data da última atualização aparece no topo do Início.",
    "De onde vem o número de diamantes do meu mês?":
        "Ele vem do próprio TikTok (Backstage): é a referência que a plataforma calcula para você. A gestão da Hera "
        "também pode combinar com você um número para o mês. Quando não há nenhum dos dois, o app mostra quanto falta "
        "para o próximo Tier.",
}


def atualizar(apps, schema_editor):
    FaqItem = apps.get_model("engage", "FaqItem")
    schema_editor.execute("SELECT set_config('app.system', 'on', false)")
    for pergunta, resposta in RESPOSTAS.items():
        FaqItem.objects.filter(question=pergunta).update(answer=resposta)
    schema_editor.execute("SELECT set_config('app.system', 'off', false)")


class Migration(migrations.Migration):
    dependencies = [("engage", "0008_aula_de_batalha_demo")]
    operations = [migrations.RunPython(atualizar, migrations.RunPython.noop)]

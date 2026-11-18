"""Central de dúvidas: a resposta sobre os grupos passa a citar as faixas da visão (Bronze T1, Prata T2–T3, Ouro T4, Diamante T5+)."""
from django.db import migrations

PERGUNTA = "O que são os grupos Bronze, Prata, Ouro e Diamante?"
RESPOSTA = ("Quem chega fica no Primeiro Mês. Depois, o grupo segue o Tier: Bronze (Tier 1), Prata (Tier 2 e 3), "
            "Ouro (Tier 4) e Diamante (Tier 5 ou mais).")


def atualizar(apps, schema_editor):
    FaqItem = apps.get_model("engage", "FaqItem")
    schema_editor.execute("SELECT set_config('app.system', 'on', false)")
    FaqItem.objects.filter(question=PERGUNTA).update(answer=RESPOSTA)
    schema_editor.execute("SELECT set_config('app.system', 'off', false)")


class Migration(migrations.Migration):
    dependencies = [("engage", "0010_sem_meta_individual_e_convite_por_codigo")]
    operations = [migrations.RunPython(atualizar, migrations.RunPython.noop)]

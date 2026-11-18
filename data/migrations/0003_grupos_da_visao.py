"""Grupos por nível da visão: Bronze T1, Prata T2–T3, Ouro T4, Diamante T5 ou mais.

Só troca os grupos que ainda estão com as faixas antigas do padrão (1–2, 3–4, 5–7, 8–10).
Faixas que a agência já editou em Configurações ficam como estão.
O grupo de cada criador é refeito no próximo recálculo (importação ou rotina diária)."""
from django.db import migrations

ANTIGO_PARA_NOVO = {("Bronze", 1, 2): (1, 1), ("Prata", 3, 4): (2, 3), ("Ouro", 5, 7): (4, 4), ("Diamante", 8, 10): (5, 10)}


def trocar(apps, schema_editor):
    GroupRule = apps.get_model("data", "GroupRule")
    for (nome, tmin, tmax), (novo_min, novo_max) in ANTIGO_PARA_NOVO.items():
        GroupRule.objects.filter(name=nome, tier_min=tmin, tier_max=tmax).update(tier_min=novo_min, tier_max=novo_max)


def voltar(apps, schema_editor):
    GroupRule = apps.get_model("data", "GroupRule")
    for (nome, tmin, tmax), (novo_min, novo_max) in ANTIGO_PARA_NOVO.items():
        GroupRule.objects.filter(name=nome, tier_min=novo_min, tier_max=novo_max).update(tier_min=tmin, tier_max=tmax)


class Migration(migrations.Migration):
    dependencies = [("data", "0002_porta_de_importacao")]
    operations = [migrations.RunPython(trocar, voltar)]

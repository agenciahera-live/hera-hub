"""Atualiza as perguntas da central de dúvidas e as dicas já gravadas no banco
para os textos novos (sem palavras vetadas, sem ranking, linguagem neutra).

Só mexe nos itens que vieram do padrão do app, reconhecidos pela pergunta ou pelo texto antigo.
"""
from django.db import migrations

PERGUNTAS_RENOMEADAS = {
    "Qual é a meta dos meus primeiros 14 dias?": "Qual é a regra dos meus primeiros 14 dias?",
    "Qual é a meta mínima do mês?": "Qual é o mínimo do mês?",
    "De onde vem a minha meta de diamantes?": "De onde vem o número de diamantes do meu mês?",
    "Quais são os marcos de novato?": "Quais são os marcos de quem está começando?",
}
DICAS_TROCADAS = {
    "Constância primeiro: 3–4 dias por semana no mesmo horário ajudam o público a te achar.":
        "Constância primeiro: 3–4 dias por semana, sempre na mesma hora, ajudam o público a te achar.",
}


def atualizar(apps, schema_editor):
    from engage import defaults as D

    FaqItem = apps.get_model("engage", "FaqItem")
    Tip = apps.get_model("engage", "Tip")
    schema_editor.execute("SELECT set_config('app.system', 'on', false)")
    antigas = {nova: antiga for antiga, nova in PERGUNTAS_RENOMEADAS.items()}
    for categoria, pergunta, resposta, _chaves in D.FAQ:
        nomes = [pergunta] + ([antigas[pergunta]] if pergunta in antigas else [])
        FaqItem.objects.filter(question__in=nomes).update(category=categoria, question=pergunta, answer=resposta)
    for antiga, nova in DICAS_TROCADAS.items():
        Tip.objects.filter(text=antiga).update(text=nova)
    schema_editor.execute("SELECT set_config('app.system', 'off', false)")


class Migration(migrations.Migration):
    dependencies = [("engage", "0004_sem_ranking_e_tom")]
    operations = [migrations.RunPython(atualizar, migrations.RunPython.noop)]

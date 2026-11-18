"""(Sem efeito desde 14/11/2026.) Criava os modelos provisórios da fila do dia nas agências que já existiam.
A biblioteca inteira passou a ser carregada do Playbook pela migração 0015, que substitui esta."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("engage", "0011_duvida_grupos_da_visao"), ("core", "0001_initial")]
    operations = []

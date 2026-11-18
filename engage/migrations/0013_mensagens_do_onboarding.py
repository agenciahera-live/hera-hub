"""(Sem efeito desde 14/11/2026.) Criava os modelos provisórios de quem entrou e não abriu LIVE.
Os textos do Playbook entram pela migração 0015, que substitui esta."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("engage", "0012_mensagens_da_fila_do_dia")]
    operations = []

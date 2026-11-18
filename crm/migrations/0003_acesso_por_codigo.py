"""Decisões da Mariana de 14/11/2026: saem a meta individual (Goal) e o disparo assistido (Contact.batch);
entra o código de acesso ao app (AccessCode). A regra de segurança da tabela nova está em web/0003.

Depende de web/0001_rls porque aquela migração cria as regras de crm_goal: em banco novo, a tabela
precisa existir até lá e só depois é apagada."""
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0002_destaque_e_grupo'),
        ('web', '0001_rls'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='contact',
            name='batch',
        ),
        migrations.CreateModel(
            name='AccessCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=12)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('expires_at', models.DateTimeField()),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('revoked_at', models.DateTimeField(blank=True, null=True, verbose_name='cancelado em')),
                ('failed_attempts', models.PositiveSmallIntegerField(default=0)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='access_codes', to='crm.creator')),
            ],
            options={
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.DeleteModel(
            name='Goal',
        ),
    ]

"""Textos já gravados no banco, depois das decisões de 14/11/2026:
- central de dúvidas: a gestão não combina mais um número de diamantes com o criador (meta individual removida);
- modelo "Convite para o app": o acesso passa a ser pelo código enviado no grupo, não por convite no e-mail.

O modelo de convite só é trocado se ainda estiver com o texto antigo do padrão (texto editado pela agência é mantido).
"""
from django.db import migrations

PERGUNTA = "De onde vem o número de diamantes do meu mês?"
RESPOSTA = ("Ele vem do próprio TikTok (Backstage): é a referência que a plataforma calcula para você. "
            "Quando o TikTok não informa essa referência, o app mostra quanto falta para o próximo Tier.")

CONVITE_ANTIGO = ("Oi {nome}! 💜 A Hera agora tem um app só pra você acompanhar suas lives, suas metas e as campanhas. "
                  "Te mandei um convite no e-mail — é só abrir o link e entrar. Qualquer dúvida me chama!")
CONVITE_NOVO = ("Oi {nome}! 💜 A Hera tem um app só seu, pra você acompanhar suas LIVEs, seu progresso e as campanhas.\n\n"
                "Pra entrar pela primeira vez:\n1. Abra {link_app}\n2. Informe o seu @ do TikTok e este código: {codigo_acesso}\n"
                "3. Cadastre o seu e-mail e crie uma senha\n\nO código vale até {codigo_validade}. "
                "Depois é só entrar com o e-mail e a senha. Qualquer dúvida, me chama aqui!")


def atualizar(apps, schema_editor):
    FaqItem = apps.get_model("engage", "FaqItem")
    MessageTemplate = apps.get_model("engage", "MessageTemplate")
    schema_editor.execute("SELECT set_config('app.system', 'on', false)")
    FaqItem.objects.filter(question=PERGUNTA).update(answer=RESPOSTA)
    MessageTemplate.objects.filter(code="CONVITE-APP", body=CONVITE_ANTIGO).update(body=CONVITE_NOVO)
    schema_editor.execute("SELECT set_config('app.system', 'off', false)")


class Migration(migrations.Migration):
    dependencies = [("engage", "0009_duvidas_importacao_diaria")]
    operations = [migrations.RunPython(atualizar, migrations.RunPython.noop)]

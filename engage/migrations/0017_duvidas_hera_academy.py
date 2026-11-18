"""Central de dúvidas: a categoria "Academy" passa a se chamar "Hera Academy" (decisão da Mariana de 18/11/2026)
e entra a pergunta sobre os módulos que ainda não abriram (passo 3.2)."""
from django.db import migrations

ANTIGA = "As gravações ficam disponíveis por 7 dias; peça o link à Hera. Os treinos principais estão na Academy do app."
NOVA = "As gravações ficam disponíveis por 7 dias; peça o link à Hera. As aulas principais estão na Hera Academy, no app."
PERGUNTA = "Por que um módulo ainda não abriu?"
RESPOSTA = ("Os módulos da Hera Academy abrem conforme você avança: alguns no primeiro acesso, outros depois da sua 1ª LIVE, "
            "no fim dos seus primeiros 14 dias ou quando você chega a um nível. Cada módulo fechado mostra quando abre. "
            "Se quiser ver um antes, fale com a Hera.")
CHAVES = "modulo, fechado, bloqueado, nao abre, academy, curso, aula"


def atualizar(apps, schema_editor):
    FaqItem = apps.get_model("engage", "FaqItem")
    Agency = apps.get_model("core", "Agency")
    schema_editor.execute("SELECT set_config('app.system', 'on', false)")
    FaqItem.objects.filter(category="Academy").update(category="Hera Academy")
    FaqItem.objects.filter(answer=ANTIGA).update(answer=NOVA)
    for ag in Agency.objects.all():
        if FaqItem.objects.filter(agency=ag).exists() and not FaqItem.objects.filter(agency=ag, question=PERGUNTA).exists():
            FaqItem.objects.create(agency=ag, category="Hera Academy", question=PERGUNTA, answer=RESPOSTA, keywords=CHAVES)
    schema_editor.execute("SELECT set_config('app.system', 'off', false)")


class Migration(migrations.Migration):
    dependencies = [("engage", "0016_hera_academy_modulos"), ("core", "0011_academy_nivel_que_abre_tudo")]
    operations = [migrations.RunPython(atualizar, migrations.RunPython.noop)]

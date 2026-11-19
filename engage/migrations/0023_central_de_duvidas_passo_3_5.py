"""Central de dúvidas, revisão do passo 3.5 (18/11/2026): "Tier" vira "Nível", saem as frases que sugerem horas, dias ou
horário, e entram as dúvidas frequentes do roteiro online (revisadas pela Mariana), adaptadas para o criador ler.
Também as dicas do dia que sugeriam hora e dias de LIVE.

Só troca o que está igual ao texto padrão antigo: o que a gestão editou pela tela fica como está (só a categoria
"Tier" vira "Nível" e "Regras da plataforma" vira "Regras do TikTok"). Pergunta nova entra se ainda não existir."""
from django.db import migrations

# Textos padrão de antes desta revisão (pergunta → resposta), para saber o que a gestão não editou.
OLD = {
    "O que é um dia válido?": "É o dia em que você faz pelo menos 60 minutos de LIVE. LIVEs com menos de 30 minutos não contam. Se precisar, dá pra fazer duas LIVEs de 35 minutos no mesmo dia. Neste mês você tem {dias_validos_mes} dias válidos.",
    "Que horas o dia do TikTok vira?": "O TikTok conta o dia pelo fuso UTC: ele começa às 21h e termina às 20h59, pela hora de Brasília. Uma LIVE que passa das 21h divide as horas entre dois dias. Termine antes das 21h para validar o dia.",
    "Qual é a regra dos meus primeiros 14 dias?": "É uma regra do TikTok: 5 dias válidos e 15 horas de LIVE nos primeiros 14 dias. Uma rotina de 1–2h por dia, 3–4 dias por semana, já resolve.",
    "Qual é o mínimo do mês?": "5 dias válidos e 15 horas de LIVE por mês. Faltam {falta_dias_min} dias válidos e {falta_horas_min}h para você chegar lá este mês.",
    "De onde vem o número de diamantes do meu mês?": "Ele vem do próprio TikTok (Backstage): é a referência que a plataforma calcula para você. Quando o TikTok não informa essa referência, o app mostra quanto falta para o próximo Tier.",
    "O que é Tier?": "É o seu nível na Hera, de 1 a 10, pelos diamantes do mês fechado. Tier 1 vai até 39.999, Tier 2 de 40 mil a 79.999, Tier 3 a partir de 80 mil, e assim por diante. Você está no Tier {tier}.",
    "Quando meu Tier muda?": "No fechamento do mês. Durante o mês você vê a barra de quanto falta para o próximo Tier.",
    "O que são os grupos Bronze, Prata, Ouro e Diamante?": "Quem chega fica no Primeiro Mês. Depois, o grupo segue o Tier: Bronze (Tier 1), Prata (Tier 2 e 3), Ouro (Tier 4) e Diamante (Tier 5 ou mais).",
    "O que é graduação?": "É uma regra do TikTok para quem está começando: fazer 80 mil diamantes em um mês, dentro dos seus 3 primeiros meses. Dá para graduar até 3 vezes, uma por mês nesse período.",
    "Por que fazer batalhas (PK)?": "Batalha é a principal alavanca de audiência e diamantes. O melhor momento costuma ser entre 20h e 21h, e nos fins de semana. Você pode pedir uma batalha pelo app.",
    "Como peço uma batalha?": "No Início, toque em \"Pedir batalha\" e escolha o dia e a hora. A Hera busca alguém do seu mesmo nível e avisa no seu grupo e no app quando a batalha estiver confirmada.",
    "Como funcionam as campanhas?": "As campanhas em destaque aparecem no app com um resumo do que fazer, os prêmios e até quando vão. O card abre a campanha direto no TikTok. Cada campanha tem regras próprias.",
    "O que não pode fazer em LIVE?": "Não pode: LIVE sem interação ou de má qualidade, menores de idade, conteúdo sexual ou nudez, LIVE em veículos, drogas ou cigarro, divulgar outras plataformas, bullying ou preconceito, mostrar documentos, exibir TV/notebook/celular, filmes ou músicas de terceiros, usar máscara, mostrar só parte do corpo, ficar ausente mais de 5 minutos, fazer LIVE na cama. Assista ao treino \"Xô Restrições e Banimentos\".",
    "Minha conta foi restrita ou banida. E agora?": "Fale com a Hera pelo botão \"Falar com a Hera\". A gente te ajuda com o suporte do TikTok.",
    "Como faço para sair da agência?": "Nos primeiros 15 dias, basta avisar a Hera, que remove você da agência. Depois disso, a saída é pelo aviso prévio no app do TikTok e leva até 30 dias. Quem sai perde as premiações do mês.",
    "A Hera cobra alguma coisa de mim?": "Não. O TikTok paga a comissão da agência separadamente; você fica com 100% do que ganha.",
}
CATEGORY_RENAMES = {"Tier": "Nível", "Regras da plataforma": "Regras do TikTok"}


def aplicar(apps, schema_editor):
    from engage import defaults as D

    FaqItem = apps.get_model("engage", "FaqItem")
    Tip = apps.get_model("engage", "Tip")
    Agency = apps.get_model("core", "Agency")
    schema_editor.execute("SELECT set_config('app.system', 'on', false)")
    for old, new in CATEGORY_RENAMES.items():
        FaqItem.objects.filter(category=old).update(category=new)
    for ag in Agency.objects.all():
        items = list(FaqItem.objects.filter(agency=ag))
        if not items:
            continue  # agência sem central (recebe a nova no setup_agency)
        by_q = {i.question: i for i in items}
        for cat, q, a, k in D.FAQ:
            old_q = D.FAQ_RENAMED.get(q, q)
            row = by_q.get(q) or by_q.get(old_q)
            if row is None:
                FaqItem.objects.create(agency=ag, category=cat, question=q, answer=a, keywords=k)
            elif row.answer == OLD.get(row.question, a):  # texto padrão, sem edição da gestão (o que não mudou, compara com ele mesmo)
                row.category, row.question, row.answer, row.keywords = cat, q, a, k
                row.save()
        for q in D.FAQ_RETIRED:
            row = by_q.get(q)
            if row is not None and row.answer == OLD.get(q):
                row.active = False
                row.save()
    for old, new in D.TIPS_RETIRED.items():
        Tip.objects.filter(text=old).update(text=new)
    schema_editor.execute("SELECT set_config('app.system', 'off', false)")


class Migration(migrations.Migration):
    dependencies = [("engage", "0022_pedidos_da_ajuda")]
    operations = [migrations.RunPython(aplicar, migrations.RunPython.noop)]

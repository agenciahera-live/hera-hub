"""Conteúdo inicial da agência (níveis, grupos, itens do onboarding, central de dúvidas e dicas),
tirado do Playbook do Gestor e do Manual da Agência Hera.

As mensagens da gestão ficam em engage/playbook.py.
"""

TIERS = [
    (1, 0, "Aprender e criar hábito"),
    (2, 40_000, "Aprender e criar hábito"),
    (3, 80_000, "Criar consistência"),
    (4, 150_000, "Criar consistência"),
    (5, 250_000, "Desenvolver performance"),
    (6, 350_000, "Desenvolver performance"),
    (7, 500_000, "Desenvolver performance"),
    (8, 800_000, "Escalar com maturidade"),
    (9, 1_200_000, "Escalar com maturidade"),
    (10, 1_600_000, "Escalar com maturidade"),
]

# Grupos da visão: Bronze T1, Prata T2–T3, Ouro T4, Diamante T5 ou mais (antes: 1–2, 3–4, 5–7, 8–10).
GROUPS = [("Bronze", 1, 1), ("Prata", 2, 3), ("Ouro", 4, 4), ("Diamante", 5, 10)]

ONBOARDING = [
    # code, label, anchor, day, auto_rule
    ("boas_vindas", "Boas-vindas enviada", "entrada", 1, ""),
    ("video_basico", "Vídeo básico enviado", "entrada", 1, ""),
    ("resumo_regras", "Resumo das regras enviado", "entrada", 1, ""),
    ("confirmou_leitura", "Confirmou leitura", "entrada", 2, ""),
    ("live_agendada", "LIVE agendada", "entrada", 2, ""),
    ("setup_aprovado", "Setup aprovado", "entrada", 2, ""),
    ("live_1", "1ª LIVE realizada", "primeira_live", 1, "streams>=1"),
    ("live_2", "2ª LIVE realizada", "primeira_live", 2, "streams>=2"),
    ("live_3", "3ª LIVE realizada", "primeira_live", 3, "streams>=3"),
    ("batalha", "Batalha testada", "primeira_live", 4, "battles>=1"),
    ("desafio_5", "Desafio 5 dias fechado", "primeira_live", 5, "streams>=5"),
    ("rotina_fixa", "Rotina fixa combinada", "entrada", 8, ""),
    ("check_d10", "Check preventivo da meta (D10)", "entrada", 10, ""),
    ("meta_14", "Meta 5 dias/15h cumprida", "entrada", 14, "meta_onboarding"),
    ("checkpoint_d15", "1:1 checkpoint de Tier (D15)", "entrada", 15, ""),
]

# As mensagens da gestão saíram daqui: a biblioteca padrão fica em engage/playbook.py (gerada do Playbook)
# e é carregada por engage/library.py.

FAQ = [
    ("Dia válido", "O que é um dia válido?", "É o dia em que você faz pelo menos 60 minutos de LIVE. LIVEs com menos de 30 minutos não contam. Se precisar, dá pra fazer duas LIVEs de 35 minutos no mesmo dia. Neste mês você tem {dias_validos_mes} dias válidos.", "dia valido, validar, validou, contar dia, 1 hora"),
    ("Dia válido", "Que horas o dia do TikTok vira?", "O TikTok conta o dia pelo fuso UTC: ele começa às 21h e termina às 20h59, pela hora de Brasília. Uma LIVE que passa das 21h divide as horas entre dois dias. Termine antes das 21h para validar o dia.", "21h, horario, fuso, utc, virar o dia, meia noite"),
    ("Regras da plataforma", "Qual é a regra dos meus primeiros 14 dias?", "É uma regra do TikTok: 5 dias válidos e 15 horas de LIVE nos primeiros 14 dias. Uma rotina de 1–2h por dia, 3–4 dias por semana, já resolve.", "meta, 14 dias, novato, comeco, inicio, 15 horas"),
    ("Regras da plataforma", "Qual é o mínimo do mês?", "5 dias válidos e 15 horas de LIVE por mês. Faltam {falta_dias_min} dias válidos e {falta_horas_min}h para você chegar lá este mês.", "meta minima, mes, minimo, obrigatorio"),
    ("Regras da plataforma", "De onde vem o número de diamantes do meu mês?", "Ele vem do próprio TikTok (Backstage): é a referência que a plataforma calcula para você. Quando o TikTok não informa essa referência, o app mostra quanto falta para o próximo Tier.", "meta diamantes, objetivo, alvo"),
    ("Tier", "O que é Tier?", "É o seu nível na Hera, de 1 a 10, pelos diamantes do mês fechado. Tier 1 vai até 39.999, Tier 2 de 40 mil a 79.999, Tier 3 a partir de 80 mil, e assim por diante. Você está no Tier {tier}.", "nivel, tier, subir de nivel, level"),
    ("Tier", "Quando meu Tier muda?", "No fechamento do mês. Durante o mês você vê a barra de quanto falta para o próximo Tier.", "mudar tier, atualiza, fechamento"),
    ("Tier", "O que são os grupos Bronze, Prata, Ouro e Diamante?", "Quem chega fica no Primeiro Mês. Depois, o grupo segue o Tier: Bronze (Tier 1), Prata (Tier 2 e 3), Ouro (Tier 4) e Diamante (Tier 5 ou mais).", "grupo, bronze, prata, ouro, diamante, primeiro mes"),
    ("Tier", "O que é graduação?", "É uma regra do TikTok para quem está começando: fazer 80 mil diamantes em um mês, dentro dos seus 3 primeiros meses. Dá para graduar até 3 vezes, uma por mês nesse período.", "graduar, graduacao, 80 mil, 80k"),
    ("Batalhas", "Por que fazer batalhas (PK)?", "Batalha é a principal alavanca de audiência e diamantes. O melhor momento costuma ser entre 20h e 21h, e nos fins de semana. Você pode pedir uma batalha pelo app.", "pk, batalha, match, versus, duelo"),
    ("Batalhas", "Como peço uma batalha?", "No Início, toque em \"Pedir batalha\" e escolha o dia e a hora. A Hera busca alguém do seu mesmo nível e avisa no seu grupo e no app quando a batalha estiver confirmada.", "marcar batalha, agendar pk, pedir batalha"),
    ("Campanhas", "Como funcionam as campanhas?", "As campanhas em destaque aparecem no app com um resumo do que fazer, os prêmios e até quando vão. O card abre a campanha direto no TikTok. Cada campanha tem regras próprias.", "campanha, competicao, premio, premiacao, ranking"),
    ("Campanhas", "Quando meus números atualizam?", "A Hera atualiza os dados do TikTok todo dia. A data da última atualização aparece no topo do Início.", "atualizar, atualizacao, dados, numeros errados, desatualizado"),
    ("Campanhas", "Quais são os marcos de quem está começando?", "Há prêmios nos marcos de 25 mil, 50 mil e 150 mil diamantes para quem está começando.", "marco, 25k, 50k, 150k, premio novato"),
    ("Regras de LIVE", "O que não pode fazer em LIVE?", "Não pode: LIVE sem interação ou de má qualidade, menores de idade, conteúdo sexual ou nudez, LIVE em veículos, drogas ou cigarro, divulgar outras plataformas, bullying ou preconceito, mostrar documentos, exibir TV/notebook/celular, filmes ou músicas de terceiros, usar máscara, mostrar só parte do corpo, ficar ausente mais de 5 minutos, fazer LIVE na cama. Assista ao treino \"Xô Restrições e Banimentos\".", "proibido, pode, nao pode, regra, restricao, banimento, ban"),
    ("Regras de LIVE", "Minha conta foi restrita ou banida. E agora?", "Fale com a Hera pelo botão \"Falar com a Hera\". A gente te ajuda com o suporte do TikTok.", "banido, restrita, bloqueada, suspensa, punicao"),
    ("Saída", "Como faço para sair da agência?", "Nos primeiros 15 dias, basta avisar a Hera, que remove você da agência. Depois disso, a saída é pelo aviso prévio no app do TikTok e leva até 30 dias. Quem sai perde as premiações do mês.", "sair, saida, desligar, cancelar, aviso previo"),
    ("Saída", "Posso voltar depois de sair?", "Se saiu nos primeiros 15 dias, pode voltar quando quiser. Se saiu depois, o retorno é possível após 90 dias.", "voltar, retorno, carencia, 90 dias"),
    ("Suporte", "Quanto tempo leva para responderem?", "A Hera responde em até 24h nos dias úteis. Nos fins de semana, só casos urgentes.", "resposta, demora, atendimento, suporte, horario de atendimento"),
    ("Benefícios", "A Hera cobra alguma coisa de mim?", "Não. O TikTok paga a comissão da agência separadamente; você fica com 100% do que ganha.", "cobra, taxa, porcentagem, comissao, pagar"),
    ("Benefícios", "Quais aulas de idioma existem?", "Inglês (segundas 14h–15h e terças 20h–21h) e Espanhol (quintas 20h–21h), pelo Zoom. As gravações ficam no Drive.", "ingles, espanhol, idioma, aula de idiomas, zoom"),
    ("Benefícios", "Onde vejo cupons e parcerias?", "Na tela Benefícios: cupons de desconto e produtos recomendados para melhorar sua LIVE.", "cupom, desconto, parceria, produto, iluminacao"),
    ("Hera Academy", "Perdi uma aula ao vivo. E agora?", "As gravações ficam disponíveis por 7 dias; peça o link à Hera. As aulas principais estão na Hera Academy, no app.", "aula, gravacao, treinamento, perdi, academy"),
    ("Hera Academy", "Por que um módulo ainda não abriu?", "Os módulos da Hera Academy abrem conforme você avança: alguns no primeiro acesso, outros depois da sua 1ª LIVE, no fim dos seus primeiros 14 dias ou quando você chega a um nível. Cada módulo fechado mostra quando abre. Se quiser ver um antes, fale com a Hera.", "modulo, fechado, bloqueado, nao abre, academy, curso, aula"),
]

TIPS = [
    "Termine suas LIVEs antes das 21h: é quando o dia do TikTok vira.",
    "Chame quem entra pelo nome. Interação constrói audiência, mesmo com pouca gente.",
    "Batalhas entre 20h e 21h costumam trazer mais audiência.",
    "Constância primeiro: 3–4 dias por semana, sempre na mesma hora, ajudam o público a te achar.",
    "Luz de frente e celular na altura dos olhos já mudam muito a sua LIVE.",
]

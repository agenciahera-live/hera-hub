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

# Central de dúvidas (tela Ajuda do criador). Revisão do passo 3.5 (18/11/2026): "Tier" virou "Nível"; saíram as frases
# que sugerem horas, dias ou horário (regra do app); entraram as dúvidas frequentes do roteiro online revisadas pela
# Mariana (decisão 5: biblioteca de mensagens e central de dúvidas), adaptadas para o criador ler (sem "eu", sem "me manda").
# A migração engage/0023 leva esta revisão para as agências que já existem, sem mexer no que a gestão editou.
FAQ = [
    ("Dia válido", "O que é um dia válido?", "É um dia com pelo menos 1 hora de LIVE. Pode ser uma LIVE só ou várias somadas no mesmo dia (LIVEs com menos de 30 minutos não entram na soma). Neste mês você tem {dias_validos_mes} dias válidos.", "dia valido, validar, validou, contar dia, 1 hora"),
    ("Dia válido", "Que horas o dia do TikTok vira?", "O dia do TikTok vira às 21h de Brasília. Uma LIVE que passa das 21h conta uma parte em cada dia.", "21h, horario, fuso, utc, virar o dia, meia noite"),
    ("Dia válido", "Por que meu dia não contou como válido?", "Os motivos mais comuns são: a LIVE somou menos de 1h no dia, ou passou das 21h e o tempo ficou dividido entre dois dias. Se ainda ficar com dúvida, mande o dia e a hora da LIVE para a Hera no seu grupo: ela confere no painel da agência.", "nao contou, nao validou, dia invalido, perdi o dia"),
    ("Dia válido", "Quanto tempo de LIVE eu preciso fazer? É só abrir?", "É só abrir, sim! Para o dia contar como dia válido no TikTok, a LIVE precisa somar pelo menos 1 hora no dia. Se ficar mais tempo, melhor ainda: é quando mais gente te encontra. LIVEs com menos de 30 minutos não entram na soma.", "quanto tempo, so abrir, tempo de live, duracao"),
    ("Regras do TikTok", "Qual é a regra dos meus primeiros 14 dias?", "É regra do TikTok para toda conta recém-agenciada: 5 dias válidos e 15 horas de LIVE no total dentro dos primeiros 14 dias. Você escolhe os seus dias de LIVE, e a Hera te ajuda a montar a sua rotina.", "14 dias, novato, comeco, inicio, 15 horas, primeiros dias"),
    ("Regras do TikTok", "Qual é o mínimo do mês?", "5 dias válidos e 15 horas de LIVE por mês. Faltam {falta_dias_min} dias válidos e {falta_horas_min}h para você chegar lá este mês.", "minima, mes, minimo, obrigatorio"),
    ("Regras do TikTok", "O que é graduação?", "É uma regra do TikTok para quem está começando: fazer 80 mil diamantes em um mês, dentro dos seus 3 primeiros meses. Dá para graduar até 3 vezes, uma por mês nesse período.", "graduar, graduacao, 80 mil, 80k"),
    ("Nível", "O que é o Nível?", "É o seu nível na Hera, de 1 a 10, pelos diamantes do mês fechado. A faixa de diamantes de cada nível aparece em Início › Meu nível. Você está no Nível {tier}.", "nivel, tier, subir de nivel, level"),
    ("Nível", "Quando meu Nível muda?", "No fechamento do mês. Durante o mês, a barra mostra quanto falta para o próximo nível.", "mudar nivel, mudar tier, atualiza, fechamento"),
    ("Nível", "O que são os grupos Bronze, Prata, Ouro e Diamante?", "Quem chega fica no Primeiro Mês. Depois, o grupo segue o seu nível do mês fechado: Bronze, Prata, Ouro e Diamante. Os níveis de cada grupo aparecem em Início › Meu nível.", "grupo, bronze, prata, ouro, diamante, primeiro mes"),
    ("Batalhas", "O que é uma batalha?", "É quando duas LIVEs se juntam na mesma tela por alguns minutos e o público de cada lado manda presentes. Ganha quem somar mais pontos. Além de diamantes, a batalha leva seu perfil pra um público novo, que conhece você pela outra pessoa ⚔️", "pk, batalha, match, versus, duelo, o que e"),
    ("Batalhas", "Por que fazer batalhas (PK)?", "Batalha é uma das estratégias que mais trazem audiência e diamantes, porque leva o seu perfil para o público da outra pessoa. Mas não é obrigatória: tem muita gente que cresce com co-host, convidados e desafios com o chat.", "pk, batalha, vale a pena, por que"),
    ("Batalhas", "Como eu começo uma batalha?", "Durante a LIVE, toque no ícone de batalha (ou de convidar) e escolha entre chamar alguém que você segue ou uma batalha aleatória. Pra começar, o mais tranquilo é batalhar com alguém da Hera do seu nível: a Hera pode te indicar alguém.", "comecar batalha, iniciar pk, convidar, aleatoria"),
    ("Batalhas", "Como peço uma batalha oficial?", "Em Batalhas, toque em \"Pedir\": escolha duas datas, a hora, os rounds e quantos diamantes quer fazer. Peça com pelo menos 7 dias de antecedência. A Hera busca um oponente do seu nível e avisa no seu grupo e no app quando a batalha estiver confirmada.", "marcar batalha, agendar pk, pedir batalha, batalha oficial"),
    ("Batalhas", "Eu preciso fazer batalha?", "Não. Batalha é uma das estratégias que mais ajudam a crescer, mas não é obrigatória. Tem muita gente que cresce com co-host, convidados e desafios com o chat. A gente monta o caminho que combina com você.", "obrigatorio, preciso, nao gosto de batalha"),
    ("Batalhas", "Se eu perder a batalha, perco alguma coisa?", "Não perde nada do que ganhou. Os presentes que você recebeu durante a batalha continuam sendo seus.", "perder, perdi, derrota"),
    ("Campanhas", "Como funcionam as campanhas?", "São competições do TikTok ou da Hera com prêmios pra quem participa. Cada uma tem suas regras e um link oficial. Em Campanhas, no app, aparecem as campanhas em que você participa, com o resumo de como pontuar. O card abre a campanha no TikTok.", "campanha, competicao, premio, premiacao"),
    ("Campanhas", "Abrindo a LIVE eu já participo das campanhas?", "Depende da campanha. Algumas contam sozinhas pra quem faz LIVE no período; outras precisam de inscrição pelo link da campanha. No app, o card mostra se você pode se inscrever ou se a inscrição já foi feita.", "inscricao, inscrever, participar, entrar na campanha"),
    ("Campanhas", "Quando meus números atualizam?", "A Hera atualiza os dados do TikTok todo dia. A data da última atualização aparece no topo do Início.", "atualizar, atualizacao, dados, numeros errados, desatualizado"),
    ("Campanhas", "Quais são os marcos de quem está começando?", "Há prêmios nos marcos de 25 mil, 50 mil e 150 mil diamantes para quem está começando.", "marco, 25k, 50k, 150k, premio novato"),
    ("Público e fã-clube", "O que é o fã-clube e o Heart Me?", "O fã-clube é o grupo dos seus fãs mais próximos. Quem entra é o público: a pessoa toca no Heart Me, o coraçãozinho laranja na sua LIVE (custa 1 moeda), e ganha um selo que vale 24h. No dia seguinte ela pode ativar de novo, e cada fã novo e cada reativação contam. Quem está no fã-clube recebe aviso quando você entra ao vivo, então costuma voltar mais 💜", "fa clube, heart me, coracao, fas, selo"),
    ("Público e fã-clube", "Como eu faço o público voltar?", "Três coisas ajudam muito: fazer LIVE em dias parecidos (o público aprende quando te encontrar), lembrar do fã-clube durante a LIVE e postar cortes da LIVE nos vídeos, que trazem gente nova.", "publico, audiencia, voltar, seguidores, crescer"),
    ("Público e fã-clube", "Posso fazer LIVE fazendo outra coisa (limpando a casa, cozinhando)?", "Pode sim! LIVE fazendo uma atividade costuma funcionar bem, desde que você continue aparecendo e conversando com quem chega. Só evite ficar muito tempo fora da câmera ou em silêncio, porque o TikTok pode entender que a LIVE está parada.", "cozinhando, limpando, atividade, fazer outra coisa"),
    ("Público e fã-clube", "Posso cadastrar minhas LIVEs pra avisar o público?", "Pode! Você consegue criar eventos de live e de batalhas no seu perfil para seus amigos adicionarem e receberem um lembrete na hora que vai começar sua live.", "evento, agendar live, lembrete, avisar publico"),
    ("Dinheiro e saque", "Como eu saco o que ganhei nas LIVEs?", "É feito direto no app do TikTok 💜\n1. Vá no seu perfil, toque no menu (☰) e entre em Configurações e privacidade\n2. Entre em Saldo (às vezes aparece como Recompensas de LIVE)\n3. Toque em Sacar\n4. Escolha o método de pagamento (o app mostra as opções disponíveis, como Pix, conta bancária ou PayPal) e confirme o valor\n⚠️ Cuidado pra não tocar em Trocar: essa opção transforma o saldo em moedas pra presentear e não dá pra desfazer.\nSe não achar alguma tela, mande um print para a Hera no seu grupo.", "saque, sacar, dinheiro, receber, pix, saldo"),
    ("Dinheiro e saque", "Quanto tempo demora pra cair?", "Depois que você pede o saque, o próprio app mostra quanto tempo deve levar. Normalmente leva alguns dias úteis, dependendo do método escolhido. Se passar do tempo que o app mostrou, avise a Hera no seu grupo: ela ajuda a abrir um chamado no suporte.", "demora, cair, quando cai, saque atrasado"),
    ("Dinheiro e saque", "A Hera cobra alguma coisa de mim?", "Não. A Hera não fica com nenhuma parte dos seus ganhos. Quem paga a agência é o TikTok, separado do que você recebe. Com ou sem agência, você recebe a mesma coisa.", "cobra, taxa, porcentagem, comissao, pagar, parte"),
    ("Dinheiro e saque", "Preciso pagar imposto sobre o que ganho?", "O que você ganha nas LIVEs é renda, então entra na sua declaração. Como cada caso é diferente (pessoa física, MEI ou empresa), o ideal é conversar com um contador pra ver o melhor jeito pra você 💜", "imposto, declaracao, mei, contador, renda"),
    ("Regras de LIVE", "O que não pode fazer em LIVE?", "Não pode: LIVE sem interação ou de má qualidade, menores de idade, conteúdo sexual ou nudez, LIVE em veículos, drogas ou cigarro, divulgar outras plataformas, bullying ou preconceito, mostrar documentos, exibir TV/notebook/celular, filmes ou músicas de terceiros, usar máscara, mostrar só parte do corpo, ficar ausente mais de 5 minutos, fazer LIVE na cama. Assista ao treino \"Xô Restrições e Banimentos\". Na dúvida, pergunte para a Hera antes.", "proibido, pode, nao pode, regra, restricao, banimento, ban"),
    ("Regras de LIVE", "Minha conta foi restrita ou banida. E agora?", "Calma, a gente resolve junto. Em Ajuda, toque em \"Minha conta foi restringida ou banida\" e conte o que aconteceu: o aviso chega na frente das outras mensagens. Mande também um print da mensagem no seu grupo com a Hera.", "banido, restrita, bloqueada, suspensa, punicao, interrompida"),
    ("Regras de LIVE", "Posso fazer live de vendas (TikTok Shop)?", "A Hera trabalha com LIVEs de entretenimento e interação (bate-papo, desafios, jogos e batalhas). Live de vendas e TikTok Shop não fazem parte do nosso suporte.", "vendas, tiktok shop, loja, vender"),
    ("Saída", "Como faço para sair da agência?", "Nos primeiros 15 dias, é só avisar a Hera, que cuida de tudo. Depois disso, o pedido é feito no app do TikTok, por aviso prévio (regra do TikTok), e leva até 30 dias. Quem sai perde as premiações do mês. Veja tudo em Ajuda › Sair da agência.", "sair, saida, desligar, cancelar, aviso previo"),
    ("Saída", "Posso voltar depois de sair?", "Se saiu nos primeiros 15 dias, pode voltar quando quiser. Se saiu depois, o retorno é possível após 90 dias.", "voltar, retorno, carencia, 90 dias"),
    ("A Hera e os grupos", "Pra que serve cada grupo?", "📅 Grupo Primeiro Mês: onde a Hera acompanha de perto seus primeiros 30 dias.\n📢 Grupo de avisos: novidades, aulas ao vivo e campanhas pra todo mundo.\n💜 Grupo individual: o seu espaço com a Hera, pra conversar sobre a sua evolução.", "grupo, whatsapp, grupos, avisos, individual"),
    ("A Hera e os grupos", "Tenho que fazer LIVE numa hora certa?", "Não. Quem decide quando fazer LIVE é você. A gente pode te mostrar em que momentos o público costuma estar mais ativo, mas a escolha é sua.", "hora certa, que horas, quando fazer live, obrigatorio"),
    ("Suporte", "Quanto tempo leva para responderem?", "A Hera responde em até 24h nos dias úteis. Nos fins de semana, só casos urgentes.", "resposta, demora, atendimento, suporte"),
    ("Benefícios", "Quais aulas de idioma existem?", "Inglês (segundas 14h–15h e terças 20h–21h) e Espanhol (quintas 20h–21h), pelo Zoom. As gravações ficam no Drive.", "ingles, espanhol, idioma, aula de idiomas, zoom"),
    ("Benefícios", "Onde vejo cupons e parcerias?", "Na tela Benefícios: cupons de desconto e produtos recomendados para melhorar sua LIVE.", "cupom, desconto, parceria, produto, iluminacao"),
    ("Hera Academy", "Perdi uma aula ao vivo. E agora?", "As gravações ficam disponíveis por 7 dias; peça o link à Hera. As aulas principais estão na Hera Academy, no app.", "aula, gravacao, treinamento, perdi, academy"),
    ("Hera Academy", "Por que um módulo ainda não abriu?", "Os módulos da Hera Academy abrem conforme você avança: alguns no primeiro acesso, outros depois da sua 1ª LIVE, no fim dos seus primeiros 14 dias ou quando você chega a um nível. Cada módulo fechado mostra quando abre. Se quiser ver um antes, fale com a Hera.", "modulo, fechado, bloqueado, nao abre, academy, curso, aula"),
]
# Revisão de 18/11: pergunta nova → pergunta antiga que ela substitui (mesma linha no banco).
FAQ_RENAMED = {"O que é o Nível?": "O que é Tier?", "Quando meu Nível muda?": "Quando meu Tier muda?",
               "Como peço uma batalha oficial?": "Como peço uma batalha?"}
# Saíram da central: falava da referência de diamantes do TikTok, que o app não mostra mais.
FAQ_RETIRED = ["De onde vem o número de diamantes do meu mês?"]

# Dicas do dia na tela inicial. Revisão de 18/11: saíram as que sugeriam hora e dias de LIVE (regra do app).
TIPS = [
    "O dia do TikTok vira às 21h de Brasília: uma LIVE que passa desse ponto conta uma parte em cada dia.",
    "Chame quem entra pelo nome. Interação constrói audiência, mesmo com pouca gente.",
    "Batalha leva o seu perfil para o público da outra pessoa. Quer tentar uma? Peça em Batalhas.",
    "Fazer LIVE em dias parecidos ajuda o público a aprender quando te encontrar.",
    "Luz de frente e celular na altura dos olhos já mudam muito a sua LIVE.",
]
TIPS_RETIRED = {
    "Termine suas LIVEs antes das 21h: é quando o dia do TikTok vira.": TIPS[0],
    "Batalhas entre 20h e 21h costumam trazer mais audiência.": TIPS[2],
    "Constância primeiro: 3–4 dias por semana, sempre na mesma hora, ajudam o público a te achar.": TIPS[3],
}

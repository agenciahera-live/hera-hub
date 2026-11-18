"""Biblioteca padrão de mensagens da gestão.

GERADO a partir de docs/playbook-gestor-hera.md (revisão de novembro/2026) e do roteiro online de onboarding
(https://claude.ai/artifact/GcykwdtLRmVZKirbEXo3ef). Os textos foram extraídos direto dos dois, palavra por palavra.

- source "playbook": texto do Playbook. Os trechos [X], [Y], [N], [tema]... que o sistema sabe preencher viraram variáveis.
- source "roteiro": variações por trilha e por "faz batalha" e mensagens que só existem no roteiro online.
- source "provisorio": o Playbook não traz o texto; foi escrito para o sistema funcionar e espera revisão da Hera.

tracks vazio = vale para todas as trilhas. battles "" = vale para quem faz e para quem não faz batalha.
Trechos entre colchetes [assim] são para a gestora completar antes de enviar.

Depois de carregada no banco, a biblioteca é editada pela tela Mensagens (com histórico de versões e verificador de tom).
Este arquivo só define o ponto de partida e o que entra em agência nova.
"""

MESSAGES = [{'code': 'NR-24H',
  'variant': '',
  'stage': 'Cadência de não-resposta',
  'title': '+24h · não viu, a notificação passou batido',
  'body': 'Oi {nome}! Só confirmando que chegou tudo certinho aí pra você, o vídeo abriu sem problema? 👀',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'NR-2D',
  'variant': '',
  'stage': 'Cadência de não-resposta',
  'title': '+2 dias · viu, mas achou trabalhoso',
  'body': 'Oi {nome}! Imagino que a semana tá corrida. Se preferir, te resumo aqui mesmo em 3 linhas o essencial pra você já começar. Quer assim?',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'NR-3D',
  'variant': '',
  'stage': 'Cadência de não-resposta',
  'title': '+3 dias · no privado, pela própria gestora',
  'body': 'Oi {nome}! Tudo bem? Queria saber como você tá se sentindo nesse comecinho 💜',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'NR-5D',
  'variant': '',
  'stage': 'Cadência de não-resposta',
  'title': '+5 dias · sinal real de desengajamento (depois, acionar quem recrutou)',
  'body': 'Oi {nome}, tudo bom? Senti sua falta por aqui e queria entender como você está. Se o momento mudou, tudo bem também, só me conta 💜',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ONB-D1-01',
  'variant': '',
  'stage': 'Dia 1 · Boas-vindas, materiais e grupo',
  'title': '1.1 Boas-vindas + primeiro passo',
  'body': '✨ Seja bem-vindo(a) à Hera Agency ✨ Esse é o seu grupo individual comigo 💜 A partir de agora, eu vou te acompanhar de perto e te ajudar a '
          'evoluir nas suas lives 🚀\n'
          '\n'
          'Antes de falar de live, vou te guiar em 3 passos rapidinho:\n'
          '\n'
          '1️⃣ preparei 1 vídeo curto com o básico que você precisa saber pra começar bem (te mando já na sequência)\n'
          '\n'
          '2️⃣ Um resumo rápido das regras do que pode e não pode em live (a aula completa fica salva pra você ver depois)\n'
          '\n'
          '3️⃣ Aí sim a gente combina sua primeira live — sem pressa, só quando você já tiver visto o essencial\n'
          '\n'
          'Quero que você comece preparado(a), não só rápido. 💜\n'
          '\n'
          'Quando terminar os dois materiais, me chama aqui! 🚀',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ONB-D1-01',
  'variant': 'outra-agencia',
  'stage': 'Dia 1 · Boas-vindas, materiais e grupo',
  'title': '1.1 Boas-vindas · veio de outra agência',
  'body': '✨ Seja bem-vindo(a) à Hera, {nome}! ✨ Esse é o seu grupo individual comigo 💜\n'
          '\n'
          'Como você já tem experiência com agência, quero deixar claro desde já como a gente trabalha aqui:\n'
          '\n'
          '💰 A Hera não fica com nenhuma parte dos seus ganhos. Quem paga a agência é o TikTok, à parte do que você recebe.\n'
          '📄 Não existe contrato nem taxa. Nos primeiros 15 dias você pode sair quando quiser, sem nenhuma espera pra voltar.\n'
          '🤝 Sua conta e seu jeito de fazer LIVE continuam seus. A gente entra com estratégia, campanhas, batalhas e suporte junto ao TikTok.\n'
          '\n'
          'Pra eu te ajudar do jeito certo: o que funcionava bem pra você antes e o que você sentia falta? 💜',
  'tracks': ['outra_agencia'],
  'battles': '',
  'source': 'roteiro'},
 {'code': 'ONB-D1-01',
  'variant': 'nivel-publico',
  'stage': 'Dia 1 · Boas-vindas, materiais e grupo',
  'title': '1.1 Boas-vindas · já tem nível e público',
  'body': '✨ Seja bem-vindo(a) à Hera, {nome}! ✨ Esse é o seu grupo individual comigo 💜\n'
          '\n'
          'Vi que você já tem uma caminhada bonita nas LIVEs, então não vou te encher de material básico. Quero entender seu momento e montar com '
          'você a estratégia daqui pra frente: batalhas, campanhas do TikTok e os próximos níveis.\n'
          '\n'
          'Topa uma conversa rápida de 20 minutinhos essa semana? Me diz o dia que fica melhor pra você 💜',
  'tracks': ['nivel_publico'],
  'battles': '',
  'source': 'roteiro'},
 {'code': 'ONB-D1-02',
  'variant': '',
  'stage': 'Dia 1 · Boas-vindas, materiais e grupo',
  'title': 'Mensagem 1 · envio do vídeo curto',
  'body': 'Aqui vai o vídeo, {nome}! 🎬 Com o essencial pra você já começar bem: [vídeo]\n'
          '\n'
          'Quando assistir, me avisa aqui que eu te mando o próximo material!',
  'tracks': ['primeira_live', 'outra_agencia'],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ONB-D1-03',
  'variant': '',
  'stage': 'Dia 1 · Boas-vindas, materiais e grupo',
  'title': 'Mensagem 2 · imagem com as regras mais importantes',
  'body': 'Show! 💜 Agora essa imagem é um resumo do que pode e do que não pode fazer em live, importante pra você não correr risco de restrição na '
          'conta: [imagem]\n'
          '\n'
          'Dá uma lida com calma e deixa salva pra sempre que precisar ver de novo. Qualquer dúvida, só perguntar que estou por aqui.',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ONB-D1-03',
  'variant': 'nivel-publico',
  'stage': 'Dia 1 · Boas-vindas, materiais e grupo',
  'title': 'Mensagem 2 · resumo de regras para quem já tem público',
  'body': 'Uma coisa que mando pra todo mundo, mesmo pra quem já tem experiência: esse resumo das regras de LIVE do TikTok, que mudam de tempos em '
          'tempos [imagem]. Vale uma olhada rápida pra conta ficar protegida 💜',
  'tracks': ['nivel_publico'],
  'battles': '',
  'source': 'roteiro'},
 {'code': 'ONB-D1-04',
  'variant': '',
  'stage': 'Dia 1 · Boas-vindas, materiais e grupo',
  'title': 'Mensagem 3 · confirmação e transição para o Dia 2',
  'body': 'Oie, conseguiu ver o material que te mandei? Responda com um SIM ou NÃO pra gente passar pra próxima fase do seu início.',
  'tracks': ['primeira_live', 'outra_agencia'],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ONB-D2-01',
  'variant': '',
  'stage': 'Dia 2 · Primeira LIVE combinada, setup e regra do TikTok',
  'title': '2.1 Confirmação de leitura (se ainda não veio)',
  'body': 'Oie, conseguiu ver o material que te mandei? Responde com SIM que a gente já parte pra próxima fase! 💜',
  'tracks': ['primeira_live', 'outra_agencia'],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ONB-D2-02',
  'variant': '',
  'stage': 'Dia 2 · Primeira LIVE combinada, setup e regra do TikTok',
  'title': '2.2 Combinar a primeira LIVE + pedir setup + bônus da campanha',
  'body': 'Perfeito! Acho que você já tem tudo que precisa pra começar 🚀 Bora combinar sua primeira live? Não precisa estar perfeita — o importante '
          'agora é entrar e ganhar prática. Qual dia dessa semana fica bom pra você?\n'
          '\n'
          'E antes de ir ao vivo, me manda um print ou vídeo rapidinho de como ficou a luz/enquadramento aí no seu espaço? Assim eu já te devolvo um '
          'ok ou um ajuste antes de você começar. 📸\n'
          '\n'
          'Ah, e um bônus: assim que você fizer essa primeira live, você já entra automaticamente na nossa competição interna de iniciantes 🎁 Os '
          'detalhes vão aparecer certinho no seu aplicativo — é só mais um benefício de já estar com a gente. Qualquer dúvida me avisa.',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ONB-D2-02',
  'variant': 'ja-faz-live',
  'stage': 'Dia 2 · Primeira LIVE combinada, setup e regra do TikTok',
  'title': '2.2 Combinar a primeira LIVE · já faz LIVE',
  'body': 'Bora fazer sua primeira LIVE como Hera, {nome}? 🚀 Me conta qual dia dessa semana você pretende entrar, que eu fico de olho e já te mando '
          'o retorno depois.\n'
          '\n'
          'Se quiser, me manda um print de como está seu espaço hoje (luz e enquadramento). Às vezes um ajuste pequeno muda bastante a retenção 📸\n'
          '\n'
          'E assim que fizer essa primeira LIVE agenciada, você já entra na nossa competição de iniciantes 🎁 Os detalhes aparecem no seu aplicativo.',
  'tracks': ['outra_agencia', 'nivel_publico'],
  'battles': '',
  'source': 'roteiro'},
 {'code': 'ONB-D2-03',
  'variant': '',
  'stage': 'Dia 2 · Primeira LIVE combinada, setup e regra do TikTok',
  'title': '2.3 Resposta ao setup enviado',
  'body': 'Ficou bom! Só um ajuste: [comentário técnico específico — ex: “a luz tá vindo de trás, tenta virar de frente pra janela”]. Com isso, já '
          'tá tudo certo pra sua primeira live!',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ONB-D2-04',
  'variant': '',
  'stage': 'Dia 2 · Primeira LIVE combinada, setup e regra do TikTok',
  'title': '2.4 Regra do TikTok para os primeiros 14 dias (até o D2, para todos)',
  'body': '{nome}, uma informação importante, que é regra do próprio TikTok e não da Hera: toda pessoa recém-agenciada precisa ter 5 dias válidos e '
          '15 horas de LIVE no total dentro dos primeiros 14 dias. Dia válido = pelo menos 1 hora de LIVE no mesmo dia (pode somar mais de uma LIVE; '
          'LIVEs com menos de 30 minutos não entram na soma). O dia do TikTok vira às 21h (horário de Brasília). Dá pra fazer numa rotina tranquila, '
          'tipo 1 a 2 horas por dia, uns 3 ou 4 dias na semana. Qualquer dúvida, me chama!',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ONB-D2-04',
  'variant': 'ja-faz-live',
  'stage': 'Dia 2 · Primeira LIVE combinada, setup e regra do TikTok',
  'title': '2.4 Regra do TikTok · já faz LIVE',
  'body': '{nome}, só pra deixar registrado, porque é regra do TikTok pra toda conta recém-agenciada: são 5 dias válidos e 15 horas de LIVE nos '
          'primeiros 14 dias (dia válido = 1h ou mais no mesmo dia, e o dia do TikTok vira às 21h de Brasília).\n'
          '\n'
          'Pra quem já faz LIVE como você, isso acontece naturalmente. Te aviso por aqui se eu ver alguma coisa estranha na contagem 💜',
  'tracks': ['outra_agencia', 'nivel_publico'],
  'battles': '',
  'source': 'roteiro'},
 {'code': 'DES-D1-01',
  'variant': '',
  'stage': 'Desafio dos 5 dias (a partir da 1ª LIVE)',
  'title': 'D1.1 Manhã · kit de quebra-gelo',
  'body': 'Bom dia, {nome}! Hoje é o dia 🎉 O foco de hoje não é ter audiência e live lotada nem fazer tudo certo — é só ver como você se sente ao '
          'vivo. Ninguém nasce sabendo, viu?\n'
          '\n'
          'Separei 3 ganchos pra você puxar se bater aquele branco assim que entrar:\n'
          '1. “Oi gente, que bom ter vocês aqui comigo, de onde vocês são? Tô começando agora”\n'
          '2. Perguntar algo simples: “de onde vocês são?” ou “como foi seu dia?”\n'
          '3. Comentar sobre o clima ou o que a pessoa disse, sempre em tom positivo (“Nossa, que legal, sei que aí é super bacana!”)\n'
          '\n'
          'Vou estar de olho, torcendo daqui! 💜',
  'tracks': ['primeira_live', 'outra_agencia'],
  'battles': '',
  'source': 'playbook'},
 {'code': 'DES-D1-01',
  'variant': 'sem-batalha',
  'stage': 'Desafio dos 5 dias (a partir da 1ª LIVE)',
  'title': 'D1.1 Manhã · gamer ou quem não batalha',
  'body': 'Bom dia, {nome}! Hoje é o dia 🎉 O foco é só ver como você se sente jogando ao vivo.\n'
          '\n'
          'Três jeitos de trazer o chat pro jogo:\n'
          '1. “Chegou agora? Me ajuda a decidir: vou pela esquerda ou pela direita?”\n'
          '2. Narre o que você está pensando, mesmo quando ninguém comenta\n'
          '3. Agradeça quem chega pelo nome, mesmo no meio da partida\n'
          '\n'
          'Vou estar torcendo daqui! 💜',
  'tracks': ['primeira_live', 'outra_agencia'],
  'battles': 'nao',
  'source': 'roteiro'},
 {'code': 'DES-D1-02',
  'variant': '',
  'stage': 'Desafio dos 5 dias (a partir da 1ª LIVE)',
  'title': 'D1.2 Horas antes',
  'body': 'Sua live é hoje, viu? Lembra: luz de frente, celular na altura dos olhos, e o resto é só ser você. Relaxa, respira — hoje o objetivo é só '
          'começar. Você já tem tudo pra isso.',
  'tracks': ['primeira_live'],
  'battles': '',
  'source': 'playbook'},
 {'code': 'DES-D1-03',
  'variant': '',
  'stage': 'Desafio dos 5 dias (a partir da 1ª LIVE)',
  'title': 'D1.3 Checkpoint pós-LIVE (até 24h)',
  'body': 'Você conseguiu, {nome}! Vi um trecho: [ponto positivo específico — ex: “você ficou super à vontade cumprimentando quem entrava”]. Uma '
          'coisa só pra ajustar na próxima: [1 dica]. Como você se sentiu?',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'DES-D1-03',
  'variant': 'nivel-publico',
  'stage': 'Desafio dos 5 dias (a partir da 1ª LIVE)',
  'title': 'D1.3 Retorno pós-LIVE · já tem nível e público',
  'body': 'Que estreia, {nome}! 🚀 Vi que [dado do Backstage: espectadores, tempo médio ou diamantes]. Pra próxima, uma ideia: [1 sugestão de '
          'estratégia: batalha, campanha ou momento da LIVE]. O que você achou?',
  'tracks': ['nivel_publico'],
  'battles': '',
  'source': 'roteiro'},
 {'code': 'DES-D1-04',
  'variant': '',
  'stage': 'Desafio dos 5 dias (a partir da 1ª LIVE)',
  'title': 'D1.4 A LIVE não aconteceu no dia combinado (mensagem de apoio)',
  'body': 'Oi {nome}! Vi que não rolou hoje — tudo bem, sem problema nenhum. Aconteceu algum imprevisto ou ficou alguma insegurança? Quando quiser '
          'tentar de novo, me avisa que eu fico por aqui 💜',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'DES-D1-05',
  'variant': '',
  'stage': 'Desafio dos 5 dias (a partir da 1ª LIVE)',
  'title': 'D1.5 Sem resposta nem à contingência',
  'body': 'Oi {nome}, está tudo bem?',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'DES-D2-01',
  'variant': '',
  'stage': 'Desafio dos 5 dias (a partir da 1ª LIVE)',
  'title': 'D2.1 Manhã · testar formato',
  'body': 'Dia 2 do nosso desafio! 🎯 Hoje o foco é testar um formato diferente — pode ser conversar mais sobre um assunto específico, fazer alguma '
          'atividade ao vivo (arrumar algo, cozinhar, mostrar um hobby), qualquer coisa que você curta. A ideia é descobrir o que combina com seu '
          'jeito.',
  'tracks': ['primeira_live', 'outra_agencia'],
  'battles': '',
  'source': 'playbook'},
 {'code': 'DES-D2-02',
  'variant': '',
  'stage': 'Desafio dos 5 dias (a partir da 1ª LIVE)',
  'title': 'D2.2 Convite à aula gravada',
  'body': '{nome}, agora que você já deu os primeiros passos nas suas lives, tem uma coisa que acho que vai te ajudar bastante: no grupo de avisos a '
          'gente divulga aulas ao vivo todo dia, mas tem uma aula gravada específica pra quem tá começando que é show de bola — vai te dar muitas '
          'estratégias pra praticar nas lives.\n'
          '\n'
          'Vou deixar salva na descrição do seu grupo. Quando der, me conta o que você achou, tenho certeza que você vai adorar! 💜',
  'tracks': ['primeira_live', 'outra_agencia'],
  'battles': '',
  'source': 'playbook'},
 {'code': 'DES-D2-03',
  'variant': '',
  'stage': 'Desafio dos 5 dias (a partir da 1ª LIVE)',
  'title': 'D2.3 Checkpoint pós-LIVE',
  'body': 'Gostei do que vi hoje! [observação específica]. Achou diferença no seu conforto de ontem pra hoje?',
  'tracks': ['primeira_live', 'outra_agencia'],
  'battles': '',
  'source': 'playbook'},
 {'code': 'DES-D3-01',
  'variant': '',
  'stage': 'Desafio dos 5 dias (a partir da 1ª LIVE)',
  'title': 'D3.1 Manhã · interação',
  'body': 'Dia 3! 🎯 Hoje o foco é interação: chame quem entrar pelo nome (ou nome de usuário), faça perguntas, comente o que eles escrevem no chat. '
          'Mesmo quando tiver pouca gente, continue interagindo — isso é o que constrói audiência com o tempo, não o contrário.',
  'tracks': ['primeira_live', 'outra_agencia'],
  'battles': '',
  'source': 'playbook'},
 {'code': 'DES-D3-02',
  'variant': '',
  'stage': 'Desafio dos 5 dias (a partir da 1ª LIVE)',
  'title': 'D3.2 Checkpoint + marco de 3 LIVEs em 3 dias',
  'body': 'Como foi chamar a galera pelo nome hoje? Sentiu diferença no clima da live?\n'
          '\n'
          '{nome}, olha só: você já fez 3 lives em 3 dias! Isso já é mais consistência do que muita gente consegue no começo. Vamos pros últimos 2 '
          'dias do desafio? 🔥',
  'tracks': ['primeira_live', 'outra_agencia'],
  'battles': '',
  'source': 'playbook'},
 {'code': 'DES-D3-HM',
  'variant': '',
  'stage': 'Desafio dos 5 dias (a partir da 1ª LIVE)',
  'title': 'D3 Fã-clube com Heart Me',
  'body': '🧡 Foco de hoje: ativar seu fã-clube com o Heart Me!\n'
          '\n'
          'O Heart Me é o coraçãozinho laranja que aparece pro seu público na LIVE. Quem toca nele (custa 1 moeda) entra no seu fã-clube e ganha um '
          'selo que vale 24h. No dia seguinte a pessoa pode ativar de novo, e é isso que cria o hábito de voltar.\n'
          '\n'
          'Quem manda é o público, não você. Sua parte na LIVE de hoje:\n'
          '1. Mostrar onde fica o coração laranja (print abaixo).\n'
          '2. Convidar: “Bora ativar o heart, gente!”.\n'
          '3. Comemorar cada Heart Me e ler o nome de quem mandou.\n'
          '\n'
          'Dica: se sua LIVE tem perguntas e respostas, você pode responder primeiro quem ativou o Heart Me 💜',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'DES-D4-01',
  'variant': '',
  'stage': 'Desafio dos 5 dias (a partir da 1ª LIVE)',
  'title': 'D4.1 Manhã · convite à batalha',
  'body': 'Oi {nome}, tô vendo que você já fez {lives} lives 👏 Hoje preparei mais um vídeo de 8 minutos com o essencial pra sua primeira live de '
          'batalha. Não precisa saber tudo, só isso já é suficiente pra começar. Se quiser, te conecto com alguém da Hera do mesmo nível pra essa '
          'estreia 💜',
  'tracks': ['primeira_live', 'outra_agencia'],
  'battles': '',
  'source': 'playbook'},
 {'code': 'DES-D4-01',
  'variant': 'sem-batalha',
  'stage': 'Desafio dos 5 dias (a partir da 1ª LIVE)',
  'title': 'D4.1 Manhã · no lugar da batalha (co-host ou convidado)',
  'body': 'Oi, {nome}! Já são {lives} LIVEs 👏 Hoje a ideia é trazer outra pessoa pra sua LIVE de um jeito que combine com você: chamar alguém como '
          'convidado(a) ou co-host pra jogar junto, conversar ou fazer um desafio com o chat. Isso ajuda o público de um a conhecer o outro. Quer '
          'que eu te indique alguém da Hera que curte o mesmo estilo?',
  'tracks': ['primeira_live', 'outra_agencia'],
  'battles': 'nao',
  'source': 'roteiro'},
 {'code': 'DES-D4-02',
  'variant': '',
  'stage': 'Desafio dos 5 dias (a partir da 1ª LIVE)',
  'title': 'D4.2 Checkpoint + bônus da campanha',
  'body': 'E aí, curtiu a batalha? Isso ajuda bastante tanto em audiência quanto em diamantes.\n'
          '\n'
          'Aliás, você já ativou a competição no app — agora é só pontuar! 🎁 Quer repetir a batalha amanhã?',
  'tracks': ['primeira_live', 'outra_agencia'],
  'battles': '',
  'source': 'playbook'},
 {'code': 'DES-D5-01',
  'variant': '',
  'stage': 'Desafio dos 5 dias (a partir da 1ª LIVE)',
  'title': 'D5.1 Manhã · repetir o que funcionou',
  'body': 'Último dia do desafio! 🎯 Pega o que funcionou melhor nesses 4 dias e repete hoje.',
  'tracks': ['primeira_live', 'outra_agencia'],
  'battles': '',
  'source': 'playbook'},
 {'code': 'DES-D5-02',
  'variant': '',
  'stage': 'Desafio dos 5 dias (a partir da 1ª LIVE)',
  'title': 'D5.2 Fechamento do desafio',
  'body': 'Fechamos os 5 dias! O que você achou que funcionou melhor pra você — o momento do dia, o formato, a interação ou a batalha? Vamos usar '
          'isso pra você organizar sua semana do seu jeito.',
  'tracks': ['primeira_live', 'outra_agencia'],
  'battles': '',
  'source': 'playbook'},
 {'code': 'EST-01',
  'variant': '',
  'stage': 'Estratégia · quem já tem nível e público',
  'title': 'Conversa de estratégia',
  'body': 'Oi, {nome}! Pra nossa conversa, separei 3 pontos:\n'
          '\n'
          '1️⃣ Seu momento: o que mais funciona nas suas LIVEs hoje e onde você quer chegar\n'
          '2️⃣ Batalhas: com quem e em que momento faz mais sentido pra você\n'
          '3️⃣ Campanhas do TikTok abertas agora que combinam com seu perfil\n'
          '\n'
          'Se tiver algum print do seu painel que queira me mostrar, pode trazer 💜',
  'tracks': ['nivel_publico'],
  'battles': '',
  'source': 'roteiro'},
 {'code': 'EST-02',
  'variant': '',
  'stage': 'Estratégia · quem já tem nível e público',
  'title': 'Campanhas e batalhas da semana',
  'body': '{nome}, olha o que está aberto agora e combina com você: [campanha + link oficial]. Pra pontuar, [resumo da regra].\n'
          '\n'
          'Pra batalhas, separei [nomes] da Hera, do seu nível, que aceitam convite. Quer que eu faça a ponte?',
  'tracks': ['nivel_publico'],
  'battles': '',
  'source': 'roteiro'},
 {'code': 'EST-02',
  'variant': 'sem-batalha',
  'stage': 'Estratégia · quem já tem nível e público',
  'title': 'Campanhas da semana · não faz batalha',
  'body': '{nome}, olha o que está aberto agora e combina com o seu estilo de LIVE: [campanha + link oficial]. Pra pontuar, [resumo da regra].\n'
          '\n'
          'Se quiser trazer público novo sem batalhar, [nomes] da Hera fazem LIVE parecida e topam co-host. Quer que eu faça a ponte?',
  'tracks': ['nivel_publico'],
  'battles': 'nao',
  'source': 'roteiro'},
 {'code': 'EST-03',
  'variant': '',
  'stage': 'Estratégia · quem já tem nível e público',
  'title': 'Janela de graduação',
  'body': '{nome}, uma oportunidade que vale ter no radar: o TikTok gradua quem faz 80 mil diamantes dentro de um mês, nos 3 primeiros meses de '
          'agência. Pelo seu ritmo, [mês] parece um bom mês pra isso.\n'
          '\n'
          'Se fizer sentido pra você, a gente pensa junto em campanhas e batalhas que ajudam nesse mês 💜',
  'tracks': ['nivel_publico'],
  'battles': '',
  'source': 'roteiro'},
 {'code': 'ROT-01',
  'variant': '',
  'stage': 'D5 a D10 · Do teste para a rotina',
  'title': '1.8 Organizar a semana do jeito do criador (D6 e D7)',
  'body': '{nome}, pelo que você testou, quais dias da semana combinam mais com você pra fazer LIVE? Muita gente acha que fica mais fácil quando o '
          'público já sabe em que dias te encontrar. Se quiser, eu cadastro esses dias no TikTok pra seus seguidores receberem lembrete 💜',
  'tracks': ['primeira_live', 'outra_agencia'],
  'battles': '',
  'source': 'playbook'},
 {'code': 'META-D10',
  'variant': '',
  'stage': 'D5 a D10 · Do teste para a rotina',
  'title': 'D10 Checkpoint dos dias válidos · no caminho',
  'body': '{nome}, só um check rápido: você já tá com {dias_validos} dias válidos e {horas} horas das suas lives. Faltam poucos dias pra completar '
          'os 14, e você tá super encaminhado(a)!',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'META-D10-RISCO',
  'variant': '',
  'stage': 'D5 a D10 · Do teste para a rotina',
  'title': 'D10 Se faltarem dias · uma ajudinha com a contagem',
  'body': '{nome}, uma ajudinha com a contagem do TikTok: até agora aparecem {dias_validos} dias válidos e {horas} horas no painel, e a regra da '
          'plataforma pede 5 dias e 15 horas nos primeiros 14 dias. Se quiser, a gente olha junto quais dias dessa semana encaixam melhor pra você 💜',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'META-D12',
  'variant': '',
  'stage': 'D10 a D15 · Fechamento dos 14 dias',
  'title': 'D12 e D13 Reforço se estiver em risco',
  'body': '{nome}, faltam {dias_restantes} dias pro fim dos 14 dias da regra do TikTok, e aparecem {dias_validos} dias válidos e {horas} horas até '
          'agora. Ainda dá tempo, viu? Se tiver alguma coisa atrapalhando, me conta que a gente pensa junto 💜',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'META-D12-TRANSP',
  'variant': '',
  'stage': 'D10 a D15 · Fechamento dos 14 dias',
  'title': 'D12 Transparência (0 a 2 dias válidos e sem LIVE desde o D10, ou sem resposta)',
  'body': '{nome}, queria te falar com carinho e com transparência 💜 Pela regra do TikTok, toda conta recém-agenciada precisa de 5 dias válidos e 15 '
          'horas de LIVE nos primeiros 14 dias, e até agora aparecem {dias_validos} dias no painel. Se esse não for o seu momento, tudo bem: se a '
          'gente encerrar antes do 15º dia, você pode voltar pra Hera quando quiser, sem nenhuma espera. Me conta o que faz mais sentido pra você?',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'META-D14',
  'variant': '',
  'stage': 'D10 a D15 · Fechamento dos 14 dias',
  'title': 'D14 Fechou os 14 dias',
  'body': '{nome}, você fechou os 14 dias da regra do TikTok! 🎉 {dias_validos} dias válidos e {horas} horas. Isso mostra que você já pegou o ritmo — '
          'parabéns de verdade.',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'META-D14-NAO',
  'variant': '',
  'stage': 'D10 a D15 · Fechamento dos 14 dias',
  'title': 'D14 Não completou · acolhimento, sem cobrança',
  'body': '{nome}, os 14 dias da regra do TikTok terminaram hoje. Como você tá se sentindo com as LIVEs até aqui? Quero entender o que funcionou e o '
          'que pesou, pra gente ver o melhor caminho daqui pra frente 💜',
  'tracks': [],
  'battles': '',
  'source': 'roteiro'},
 {'code': 'ONB-D15-ENC',
  'variant': '',
  'stage': 'D10 a D15 · Fechamento dos 14 dias',
  'title': 'D15 Encerramento (não fechou 5 dias válidos e 15h)',
  'body': '{nome}, como te contei, o TikTok pede 5 dias válidos e 15 horas nos primeiros 14 dias, e esse padrão não fechou dessa vez. Por isso '
          'encerrei sua entrada na Hera por enquanto 💜 Foi muito bom te conhecer. Quando quiser voltar às LIVEs, me chama que eu te explico o '
          'caminho de volta.',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'TIER-D15',
  'variant': '',
  'stage': 'D10 a D15 · Fechamento dos 14 dias',
  'title': '1.9 Reconhecimento de evolução (D15)',
  'body': 'Vamos dar uma olhada em como você começou? [compartilhar print/resumo do Backstage: dias de live, horas, diamantes]. Isso já mostra sua '
          'evolução desde o Dia 1. Você já está no Tier {tier} — e olha que já faz só 15 dias!',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ONB-NL-D5',
  'variant': '',
  'stage': 'Entrou e ainda não abriu LIVE (do aceite ao D14)',
  'title': 'D5 Entender o motivo (no privado)',
  'body': 'Oi {nome}! Passando pra saber de você 💜 Vi que a primeira LIVE ainda não rolou, e tá tudo bem. Me conta o que tá pegando? Se for '
          'vergonha, alguma coisa técnica ou falta de tempo, a gente resolve junto.',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ONB-NL-D7',
  'variant': '',
  'stage': 'Entrou e ainda não abriu LIVE (do aceite ao D14)',
  'title': 'D7 Transparência sobre a contagem do TikTok',
  'body': '{nome}, quero te deixar por dentro da contagem do TikTok 💜 A regra da plataforma pede 5 dias válidos e 15 horas de LIVE nos primeiros 14 '
          'dias, e hoje é o seu 7º dia. Ainda dá tempo de fechar se você começar essa semana. E se esse não for o seu momento, tudo bem também: '
          'saindo antes do 15º dia, você pode voltar pra Hera quando quiser, sem nenhuma espera. Me conta o que faz mais sentido pra você?',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ONB-NL-D10',
  'variant': '',
  'stage': 'Entrou e ainda não abriu LIVE (do aceite ao D14)',
  'title': 'D10 Último dia viável (grupo e privado)',
  'body': '{nome}, falando com carinho e com transparência 💜 Pela regra do TikTok, hoje é o último dia em que ainda dá pra fechar os 5 dias válidos '
          'dentro dos 14 dias. Se você quiser começar, eu tô aqui pra te ajudar hoje mesmo. Se preferir deixar pra outro momento, eu encerro sua '
          'entrada por enquanto e você volta quando quiser, sem nenhuma espera. O que você prefere?',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ONB-NL-ENC',
  'variant': '',
  'stage': 'Entrou e ainda não abriu LIVE (do aceite ao D14)',
  'title': 'Até o D14 Encerramento de quem nunca abriu LIVE',
  'body': '{nome}, como a primeira LIVE não aconteceu nesses primeiros dias, encerrei sua entrada na Hera por enquanto 💜 Fiz isso antes do 15º dia '
          'justamente pra você não ficar com nenhuma espera: quando quiser começar, é só me chamar que a gente refaz o convite. Foi muito bom te '
          'conhecer e a porta fica aberta.',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'SAI-ANTECIPADA',
  'variant': '',
  'stage': 'Entrou e ainda não abriu LIVE (do aceite ao D14)',
  'title': 'Antes do D15 Saída antecipada (a pessoa escolheu sair)',
  'body': '{nome}, como combinamos, encerrei sua entrada na Hera por enquanto 💜 Isso não te prende a nada: quando quiser voltar às LIVEs, é só me '
          'chamar que a gente refaz o convite, sem nenhuma espera. Foi muito bom te conhecer e a porta fica aberta.',
  'tracks': [],
  'battles': '',
  'source': 'roteiro'},
 {'code': 'APO-01',
  'variant': '',
  'stage': 'Situações específicas · apoio',
  'title': '2.1 “Não sei o que falar”',
  'body': 'Isso é super comum! Vou te sugerir 10 formas de iniciar um assunto em live, pode manter essa lista ao seu lado pra você puxar assunto '
          'quando bater aquele branco. Quer que eu te mande agora?',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'APO-02',
  'variant': '',
  'stage': 'Situações específicas · apoio',
  'title': '2.2 “Não tenho audiência”',
  'body': 'No começo é assim mesmo pra todo mundo. Lembra sempre que uma live cheia não significa que é uma live bem monetizada. Nosso foco agora '
          'não é ter muito público, mas sim pegar ritmo. A audiência vem com consistência, não com a primeira live.',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'APO-03',
  'variant': '',
  'stage': 'Situações específicas · apoio',
  'title': '2.3 Queda de frequência',
  'body': 'Notei que suas lives diminuíram nas últimas semanas. Antes de mais nada: tá tudo bem com você? Quero entender o que mudou pra gente '
          'ajustar junto.',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'APO-04',
  'variant': '',
  'stage': 'Situações específicas · apoio',
  'title': '2.4 Criador que quer desistir',
  'body': 'Entendo, {nome}. Antes de qualquer coisa: obrigado(a) por avisar. Posso te perguntar o que pesou nessa decisão?',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'APO-05',
  'variant': '',
  'stage': 'Situações específicas · apoio',
  'title': '2.5 Mês com mais LIVE e menos diamantes',
  'body': '{nome}, vi que esse mês você fez mais LIVE e os diamantes não acompanharam. Sei que isso desanima, e quero te dizer que o seu esforço '
          'apareceu: [dado concreto — ex: “você teve mais gente assistindo e mais comentários”]. Vamos olhar com calma o que mudou? 💜',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'APO-06',
  'variant': '',
  'stage': 'Situações específicas · apoio',
  'title': '2.6 Perdeu uma campanha por pouco',
  'body': '{nome}, você chegou muito perto na [campanha]! Foi bonito de ver. Na próxima que abrir e combinar com você, eu te aviso logo no começo '
          'pra gente pensar junto 💜',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'REG-04',
  'variant': '',
  'stage': 'Sem LIVE depois do D15 · régua de 4, 14, 21 e 30 dias',
  'title': '4 dias sem LIVE · pergunta aberta',
  'body': 'Oi {nome}! Senti sua falta nas LIVEs esses dias 💜 Tá tudo bem por aí? Me conta como você tá, sem pressa.',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'REG-VOLTA',
  'variant': '',
  'stage': 'Sem LIVE depois do D15 · régua de 4, 14, 21 e 30 dias',
  'title': 'Boas-vindas de volta (na data que o criador informou)',
  'body': '{nome}, que bom te ver de volta! 💜 Como foi [a viagem / esses dias]? Quando quiser retomar as LIVEs, me chama que eu te conto o que tem '
          'de novo.',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'REG-14',
  'variant': '',
  'stage': 'Sem LIVE depois do D15 · régua de 4, 14, 21 e 30 dias',
  'title': '14 dias sem LIVE · no privado, com oferta de conversa curta',
  'body': 'Oi {nome}, tudo bem? Faz um tempinho que a gente não se fala. Como estão as coisas? Se quiser, a gente conversa rapidinho, do jeito que '
          'for melhor pra você 💜',
  'tracks': [],
  'battles': '',
  'source': 'provisorio'},
 {'code': 'REG-21',
  'variant': '',
  'stage': 'Sem LIVE depois do D15 · régua de 4, 14, 21 e 30 dias',
  'title': '21 dias sem LIVE · alinhamento (privado ou ligação)',
  'body': '{nome}, sentimos sua falta nas LIVEs 💜 Queria entender como está seu momento. Pra ser transparente: quando uma conta fica 30 dias sem '
          'LIVE, a Hera encerra a parceria, e a porta fica aberta pra quando você quiser voltar. Se tiver algo que eu possa fazer pra te ajudar a '
          'voltar, me conta?',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'REG-30',
  'variant': '',
  'stage': 'Sem LIVE depois do D15 · régua de 4, 14, 21 e 30 dias',
  'title': '30 dias sem LIVE · encerramento',
  'body': '{nome}, como te contei, depois de 30 dias sem LIVE a gente encerra a parceria, então hoje encerrei sua conta na Hera 💜 Obrigada por tudo '
          'o que construímos juntos. Quando quiser voltar às LIVEs, me chama que eu te explico o caminho de volta.',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'QUEDA-01',
  'variant': '',
  'stage': 'Leitura da semana',
  'title': 'Queda com horas e dias mantidos',
  'body': 'Oi {nome}! Vi que você manteve o ritmo de LIVEs e, mesmo assim, os diamantes da semana vieram abaixo do seu normal. Isso acontece. Quer '
          'que eu assista a uma LIVE sua pra gente achar o que ajustar?',
  'tracks': [],
  'battles': '',
  'source': 'provisorio'},
 {'code': 'REC-01',
  'variant': '',
  'stage': 'Leitura da semana',
  'title': 'Reconhecimento · semana subindo',
  'body': '{nome}, que semana! 🚀 Seus diamantes ficaram bem acima do seu normal. O que você fez de diferente? Vale repetir o que funcionou.',
  'tracks': [],
  'battles': '',
  'source': 'provisorio'},
 {'code': 'ROD-APP',
  'variant': '',
  'stage': 'Rodízio · 4 dias sem contato',
  'title': 'Novidade no app (quando o criador tem o app)',
  'body': '{nome}, seu progresso foi atualizado no app 💜 Dá uma olhada em “Meu progresso” e me conta o que achou. Se quiser conversar sobre os '
          'próximos passos, é só me chamar.',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ROD-AULA',
  'variant': '',
  'stage': 'Rodízio · 4 dias sem contato',
  'title': 'Jornada de cursos',
  'body': '{nome}, saiu um vídeo novo que tem a sua cara: {proxima_aula}. É rapidinho e tem umas ideias boas pra testar na LIVE. Depois me conta o '
          'que achou 💜',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ROD-CAMP',
  'variant': '',
  'stage': 'Rodízio · 4 dias sem contato',
  'title': 'Campanha aberta que vale para o criador',
  'body': '{nome}, abriu a {campanha} e ela combina com o seu jeito de fazer LIVE. Pra pontuar, {campanha_regra}. O link é esse: {campanha_link}. '
          'Quer que eu te explique melhor?',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ROD-BAT',
  'variant': '',
  'stage': 'Rodízio · 4 dias sem contato',
  'title': 'Vaga de batalha',
  'body': '{nome}, tem vaga de batalha oficial essa semana no mural. Lembrei de você! Se quiser uma, me fala o dia que fica melhor 💜',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ROD-PERG',
  'variant': '',
  'stage': 'Rodízio · 4 dias sem contato',
  'title': 'Pergunta aberta (quando não há novidade)',
  'body': 'Oi {nome}! Como estão as LIVEs por aí? Tem alguma coisa em que eu possa te ajudar essa semana? 💜',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ANIV-DIA',
  'variant': '',
  'stage': 'Aniversário',
  'title': 'No dia',
  'body': 'Feliz aniversário, {nome}! 🎂💜 Que seu novo ano seja cheio de LIVEs boas e gente querida do seu lado. É uma alegria ter você na Hera!',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'ANIV-30',
  'variant': '',
  'stage': 'Aniversário',
  'title': '30 dias antes · batalha oficial ou LIVE de aniversário',
  'body': '{nome}, seu aniversário tá chegando! 🎉 Que tal a gente preparar uma batalha oficial ou uma LIVE especial de aniversário? Seu público '
          'costuma amar. Se você curtir a ideia, me conta e eu já começo a organizar 💜',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'BAT-PEDIDO',
  'variant': '',
  'stage': 'Batalha oficial',
  'title': 'O que é e como pedir (formulário do pedido)',
  'body': 'É uma batalha marcada pela Hera: você escolhe o dia, o horário, quantos rounds e quantos diamantes quer fazer, e a gente busca um '
          'oponente do seu nível, da Hera ou de outra agência. Como os dois lados se preparam e avisam o público antes, costuma render bem mais que '
          'a aleatória.\n'
          '\n'
          'Pra pedir, é só me mandar preenchido:\n'
          '\n'
          '⚔️ PEDIDO DE BATALHA OFICIAL\n'
          '👤 Seu @:\n'
          '📆 Duas opções de data:\n'
          '⏰ Horário:\n'
          '🥊 Rounds: 1 / 3 / tanto faz\n'
          '💎 Quantos diamantes você quer fazer nessa batalha (se não souber, a gente sugere pelo seu histórico):\n'
          '🤝 Pode ser com criador de outra agência? sim / não\n'
          '🖼️ Quer ajuda com o banner? sim / não\n'
          '\n'
          'Peça com pelo menos 7 dias de antecedência 💜',
  'tracks': [],
  'battles': '',
  'source': 'roteiro'},
 {'code': 'BAT-CONF',
  'variant': '',
  'stage': 'Batalha oficial',
  'title': 'Confirmação',
  'body': '✅ BATALHA OFICIAL CONFIRMADA\n'
          '\n'
          '📆 Data: [dd/mm] · ⏰ [hora] (Brasília)\n'
          '🥊 Rounds: [1 ou 3]\n'
          '💎 Diamantes esperados para você: [faixa]\n'
          '👤 @[criador] 🆚 @[oponente]\n'
          '\n'
          'Antes:\n'
          '▫️ Seguir o oponente e divulgar nos vídeos até o dia\n'
          '▫️ Testar luz, áudio e internet\n'
          '▫️ Separar as ferramentas (luva, névoa)\n'
          'No dia:\n'
          '▫️ Abrir a LIVE 30 min antes e já chamar o público\n'
          '▫️ Desativar o evento, se tiver criado, e conferir o controle de público +18\n'
          '▫️ Não encerrar logo depois: a entrega da LIVE costuma subir',
  'tracks': [],
  'battles': '',
  'source': 'roteiro'},
 {'code': 'BAT-ATUALIZA',
  'variant': '',
  'stage': 'Batalha oficial',
  'title': 'Atualização (algo mudou)',
  'body': '⚠️ ATUALIZAÇÃO DA SUA BATALHA\n'
          '\n'
          'Mudou: [o que mudou, ex.: o oponente agora é @nome / o horário passou para 20h].\n'
          'O resto continua igual ao que combinamos 💜',
  'tracks': [],
  'battles': '',
  'source': 'roteiro'},
 {'code': 'BAT-4D',
  'variant': '',
  'stage': 'Batalha oficial',
  'title': '4 dias antes da batalha',
  'body': '{nome}, faltam 4 dias pra sua batalha oficial com @[oponente]! ⚔️ Três coisas que ajudam muito daqui até lá:\n'
          '1. Já ir juntando as luvas e as ferramentas.\n'
          '2. Postar todo dia nos vídeos e nos stories e avisar seu público nas LIVEs.\n'
          '3. Seguir @[oponente] e conferir se a sua LIVE está aberta pra todos. Qualquer dúvida, me chama 💜',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'BAT-DIA',
  'variant': '',
  'stage': 'Batalha oficial',
  'title': 'Dia da batalha',
  'body': 'É hoje, {nome}! ⚔️ Lembra de seguir @[oponente], abrir a LIVE uns 30 minutos antes pra já chamar seu público e desativar o evento, se '
          'tiver criado. Vou estar torcendo daqui 💜',
  'tracks': [],
  'battles': '',
  'source': 'roteiro'},
 {'code': 'BAT-MURAL',
  'variant': '',
  'stage': 'Batalha oficial',
  'title': 'Mural da semana (grupo de avisos, toda segunda)',
  'body': '⚔️ MURAL DE BATALHAS DA SEMANA · [dd/mm a dd/mm]\n'
          '\n'
          'Vagas abertas pra batalha oficial:\n'
          '📆 [dia dd/mm] · ⏰ [hora] · 🥊 [1 ou 3] rounds\n'
          '📆 [dia dd/mm] · ⏰ [hora] · 🥊 [1 ou 3] rounds\n'
          '📆 [dia dd/mm] · ⏰ [hora] · 🥊 [1 ou 3] rounds\n'
          '\n'
          'Quer uma? Responde aqui com seu @ e a data 💜\n'
          'Eu te chamo no seu grupo pra combinar o resto.',
  'tracks': [],
  'battles': '',
  'source': 'roteiro'},
 {'code': 'CAMP-POS',
  'variant': '',
  'stage': 'Acompanhamento de campanha',
  'title': 'Posição do criador (sem citar outro criador)',
  'body': '{nome}, olhei a [campanha] agora e você está em [X]º lugar! 👏 Faltam [Y] pontos pra próxima posição. Você tem falado da campanha na LIVE? '
          'Um vídeo sobre ela também ajuda bastante.',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'RES-01',
  'variant': '',
  'stage': 'Restrição ou banimento',
  'title': 'Primeira resposta',
  'body': 'Calma, {nome}, a gente resolve junto 💜 Me manda um print da mensagem que apareceu e me conta o horário em que aconteceu. Você já fez o '
          'recurso pelo app? Se não, eu te mostro o caminho.',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'PIX-01',
  'variant': '',
  'stage': 'Premiação em dinheiro (Pix)',
  'title': 'Pedir os dados pelo formulário (no privado)',
  'body': 'Parabéns, {nome}! 🎉 Você ganhou [prêmio] na [campanha] 💜 Pra eu enviar sua premiação por Pix, preenche esse formulário rapidinho (leva 1 '
          'minuto): https://docs.google.com/forms/d/e/1FAIpQLScoxBXvHRaBFvA14HZXs9ze_i2PbdILmqnHRdpzsyD5fYd-8g/viewform Seus dados ficam guardados '
          'só com o financeiro da Hera. Assim que enviar, te aviso por aqui!',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'PIX-02',
  'variant': '',
  'stage': 'Premiação em dinheiro (Pix)',
  'title': 'Depois do envio',
  'body': 'Prêmio enviado, {nome}! ✅ [valor] via Pix, referente à [campanha]. Parabéns de novo, você mereceu demais 💜',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'SAI-01',
  'variant': '',
  'stage': 'Saída',
  'title': 'Saída pedida antes de 15 dias',
  'body': 'Entendo, {nome}. Antes de qualquer coisa: obrigada por avisar — isso já ajuda demais.\n'
          '\n'
          'Como você ainda tá nos seus primeiros 15 dias, é bem simples: só preciso entender o que pesou nessa decisão, pra ver se rolou algo que a '
          'gente consiga ajustar. Se mesmo assim não for o momento, sem problema nenhum — eu mesma cuido de tudo por aqui, e você fica livre pra '
          'voltar quando quiser, sem prazo de espera nenhum.',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'SAI-02',
  'variant': '',
  'stage': 'Saída',
  'title': 'Saída pedida após 15 dias · parte 1 (esperar a resposta)',
  'body': 'Entendo, {nome}. Antes de qualquer coisa: obrigada por avisar.\n'
          '\n'
          'Posso te perguntar o que pesou nessa decisão? Quero entender se tem algo que a gente ainda consegue resolver.',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'SAI-03',
  'variant': '',
  'stage': 'Saída',
  'title': 'Saída pedida após 15 dias · parte 2 (se insistir na saída)',
  'body': 'Se decidir mesmo seguir com a saída, um detalhe importante pra você saber antes: como você já passou dos 15 dias, o pedido precisa ser '
          'feito direto no app, por aviso prévio — isso é um processo da própria plataforma, não é algo que a Hera decide. E uma regra real do '
          'TikTok: depois desse pedido, você fica 90 dias sem poder ser agenciado(a) por nenhuma agência. Quero que você tenha essa informação antes '
          'de decidir, pra não ter surpresa depois.',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'SAI-04',
  'variant': '',
  'stage': 'Saída',
  'title': 'Saída · casos de inelegibilidade para agenciamento (regra do TikTok)',
  'body': 'Mais uma coisa que eu prefiro te contar agora: o TikTok tem regras próprias pra liberar um perfil pra outra agência. Quem somou mais de '
          '300 mil diamantes nos últimos 6 meses, tem mais de uma conta ou tem violações no perfil pode ficar sem agência depois de sair. Não é uma '
          'regra da Hera, e o TikTok não deixa tudo isso muito claro, então vale pensar com calma 💜',
  'tracks': [],
  'battles': '',
  'source': 'playbook'},
 {'code': 'CONVITE-APP',
  'variant': '',
  'stage': 'Acesso ao app',
  'title': 'Convite para o primeiro acesso (com o código)',
  'body': 'Oi {nome}! 💜 A Hera tem um app só seu, pra você acompanhar suas LIVEs, seu progresso e as campanhas.\n'
          '\n'
          'Pra entrar pela primeira vez:\n'
          '1. Abra {link_app}\n'
          '2. Informe o seu @ do TikTok e este código: {codigo_acesso}\n'
          '3. Cadastre o seu e-mail e crie uma senha\n'
          '\n'
          'O código vale até {codigo_validade}. Depois é só entrar com o e-mail e a senha. Qualquer dúvida, me chama aqui!',
  'tracks': [],
  'battles': '',
  'source': 'provisorio'}]

# Modelos que saíram da biblioteca (resumo de números pelo WhatsApp e provisórios trocados pelos textos do Playbook)
RETIRED = ["REL-MES", "LEMBRETE-SEMANA", "ONB-NL-D3"]

# Ajustes por nicho (aba Nichos do roteiro): o roteiro é o mesmo; mudam o teste do D2, o que entra no lugar da batalha no D4 e os ganchos.
NICHE_GUIDE = [{'code': 'gamer',
  'name': 'Gamer',
  'who': 'Joga ao vivo, costuma não batalhar e fica longos períodos em LIVE.',
  'd2': 'Testar jogos diferentes ou o mesmo jogo com um desafio do chat ("se chegar a 10 curtidas eu troco de personagem").',
  'd4': 'Co-host ou convidado jogando junto, ou partida contra o chat. Batalha fica como opção, sem insistência.',
  'ganchos': 'Pedir pro chat decidir jogadas, narrar o que está pensando, agradecer quem chega pelo nome no meio da partida.',
  'obs': 'Costuma bater os dias válidos com facilidade. O ponto de atenção é a interação: jogo concentrado vira LIVE silenciosa.'},
 {'code': 'bate_papo',
  'name': 'Bate-papo e lifestyle',
  'who': 'Conversa, rotina, maquiagem, cozinha, arrumação ao vivo.',
  'd2': 'Uma atividade com as mãos enquanto conversa (cozinhar, arrumar, se maquiar).',
  'd4': 'Batalha leve com alguém do mesmo nível, ou co-host conversando sobre um tema em comum.',
  'ganchos': 'Perguntas de opinião ("qual vocês escolheriam?"), contar uma história do dia, enquetes rápidas.',
  'obs': 'É o perfil que mais se beneficia de batalhas.'},
 {'code': 'musica',
  'name': 'Música e talento',
  'who': 'Canta, toca, dança ou faz arte ao vivo.',
  'd2': 'Pedidos do chat ("me manda a música que eu toco").',
  'd4': 'Batalha de talento ou dueto como co-host.',
  'ganchos': 'Pedidos de música, dedicatórias, contar a história por trás de uma música ou peça.',
  'obs': 'Conferir com o criador se as músicas usadas estão liberadas nas regras de LIVE do TikTok.'},
 {'code': 'fe_educacao',
  'name': 'Fé, educação e conteúdo de nicho',
  'who': 'LIVEs de oração, estudo, aulas, conselhos, terapia de conversa.',
  'd2': 'Um tema por LIVE, anunciado antes nos vídeos.',
  'd4': 'Co-host com outro criador do mesmo tema. Batalha só se o criador quiser.',
  'ganchos': 'Perguntas do público como pauta, momentos fixos dentro da LIVE (uma oração, uma dica, um quadro).',
  'obs': 'Público fiel e menor no começo. Valorizar retenção e fã-clube mais do que espectadores.'},
 {'code': 'sem_aparecer',
  'name': 'Quem não quer aparecer muito',
  'who': 'Prefere LIVE com tela, jogo, desenho ou só voz e mãos.',
  'd2': 'Testar formatos com a câmera nas mãos ou na tela (desenho, unboxing, jogo).',
  'd4': 'Convidado que aparece mais, enquanto o criador conduz a conversa.',
  'ganchos': 'Mostrar o processo do que está fazendo e pedir opinião do chat.',
  'obs': 'Conferir na imagem de regras o que é permitido em LIVE sem rosto.'}]

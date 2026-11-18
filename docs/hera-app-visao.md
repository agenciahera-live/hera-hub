# Hera App — visão do aplicativo e site (versão final)

Nov 11, 2026 · @Mariana

Esta versão incorpora as decisões da Mariana de 11/11/2026 as de 12/11/2026 (rotina diária e agenda do mês) e as de 14/11/2026 (conteúdo por nível, tela inicial, campanhas e fonte única de dados). A aba "Rascunho com notas" guarda a primeira versão, as notas dela e as respostas.

## Resumo

A Hera precisa de um sistema só, com duas portas: o app do criador e o site da gestão. Os dois usam os mesmos dados do Backstage. Cada criador está sempre em uma fase, e a fase decide o que ele vê em destaque no app e o que a gestão envia para ele naquele dia.

O problema de hoje não é falta de conteúdo. O Playbook, o roteiro por trilha e nicho e as regras de prioridade já existem e funcionam. O que falta é tirar o trabalho manual da rotina da Anna e saber se a conversa de fato aconteceu.

As cinco apostas do produto:

1. **Uma fila do dia, não um painel.** A Anna abre o site e vê quem precisa de contato hoje, por quê, e a mensagem pronta para copiar e colar no grupo individual.
2. **O sistema fecha o ciclo com o dado.** O Claude lê o Backstage todo dia e envia os números ao sistema. O passo seguinte só aparece quando o dado confirma o anterior.
3. **A página educacional é a tela principal do criador.** Todos os vídeos e cursos ficam abertos para todos, organizados do "como abrir uma LIVE" em diante. Junto dela, o criador acompanha o próprio nível, a contagem dos 14 dias e a janela de graduação.
4. **O tom de parceria faz parte do produto.** Regras do TikTok aparecem como regras da plataforma. Objetivos são escolhidos pelo criador. Nada de meta, cobrança ou horário pedido pela Hera, e nenhum ranking.
5. **Feito para várias gestoras e vários grupos.** Cada gestora tem a sua carteira. As gestoras de Lunow e Impulse podem ter login próprio para usar o método com os criadores delas, sem as campanhas internas da Hera.

## Diagnóstico: o que já fazemos e onde trava

A Hera já tem o método. O que trava é a execução manual: páginas separadas, leitura do Backstage duas vezes por semana e registro feito à mão.

| O que existe hoje | O que funciona | Onde trava |
| --- | --- | --- |
| Playbook do Gestor e roteiro online | Scripts do D1 ao D15, três trilhas, ajustes por nicho, situações e dúvidas frequentes | A Anna copia de uma página e cola no WhatsApp, trocando nome e números à mão |
| Acompanhamento Semanal (Plano da semana, Onboarding, Desempenho) | Status e prioridade calculados por criador; uma mensagem por dia; etapa do onboarding pela data | Lê o Backstage só na segunda e na quinta |
| Radar de graduação (80 mil no mês) | Ritmo por dia, projeção do mês e aviso do último mês da janela | Atualiza uma vez por semana; a janela de graduação se decide dia a dia |
| Registro ("Enviei", "Respondeu", notas, 1:1) | Histórico por criador, salvo todo mês | Depende de a Anna marcar; não confirma envio nem resposta |
| Material educacional | Vídeo curto, imagem de regras, aula de batalha, aula gravada para iniciantes | Enviado peça por peça no grupo; não há um lugar único para o criador assistir |
| Campanhas por tier e mural de batalhas | Grupos Bronze, Prata, Ouro e Diamante e Primeiro Mês | Campanhas novas são cadastradas à mão |
| Batalha oficial | Modelo de pedido e de confirmação | Pedido por texto no WhatsApp; busca de oponente sem agenda |
| Indique e ganhe | Link próprio de cada criador no app do TikTok; contagem de indicações no Backstage | Os criadores perdem o link e pedem de novo à gestão |
| Premiação em dinheiro | Formulário na conta Google da Hera | Fora do fluxo; sem ligação com a campanha que gerou o prêmio |
| Resumo do mês e estudo de fechamento | Visão da conta inteira e só da Hera | Montado a cada mês; não há painel contínuo para as sócias |

### O que o registro de outubro mostra

Entre 15 e 28 de outubro foram registradas 100 mensagens para 33 criadores, 0 respostas e 0 conversas 1:1. Em pelo menos seis criadores, de 4 a 8 passos do onboarding foram marcados em poucos minutos.

Há duas leituras possíveis: as mensagens saíram em bloco, ou o registro foi preenchido depois. Nas duas, o sistema atual mede cliques, não conversas. Ele não sabe se a mensagem saiu no dia certo nem se o criador respondeu.

Esse é o principal ponto a resolver. O Playbook depende de ritmo (uma mensagem por dia, o passo seguinte só depois da LIVE anterior) e de retorno humano em até 24 horas depois da LIVE.

## Princípios do produto

Nove regras decidem o que entra e o que fica de fora.

1. **Fase primeiro.** Todo criador tem uma fase, e a fase define o que aparece em destaque no app e o que chega na fila da gestão.
2. **Conteúdo que abre por nível.** Os módulos básicos abrem no primeiro acesso. Os avançados abrem conforme o criador sobe de nível ou fecha um marco, e a gestão pode liberar qualquer módulo antes da hora.
3. **Dado antes de mensagem.** A mensagem do dia seguinte só aparece depois que a LIVE anterior consta no Backstage.
4. **A gestora envia, o sistema prepara.** Nenhuma mensagem sai sozinha. O sistema escreve o rascunho, e a gestora copia, ajusta se quiser e cola no grupo.
5. **Uma mensagem por dia por criador.** O que não cabe vai para o próximo dia livre.
6. **Primeiro cai a LIVE, depois cai o diamante.** Toda leitura de queda começa por dias e horas, nunca por receita.
7. **Parceria entre autônomos.** No app do criador não existem as palavras meta, relatório, cobrança, prazo ou horário, e não existe ranking. Regras do TikTok são sempre apresentadas como regras da plataforma. A linguagem é neutra.
8. **Nada é sobrescrito.** Cada envio, resposta, nota e 1:1 vira uma linha nova na ficha, com data e autor.
9. **Decisões sensíveis passam pelas sócias.** Campanha nova, premiação e a decisão de manter ou encerrar um criador precisam da aprovação das sócias antes de valer.

## Quem usa e o que cada perfil acessa

São cinco perfis sobre a mesma base de dados. Cada um vê só o que precisa para agir.

| Perfil | Quem | O que vê | O que faz |
| --- | --- | --- | --- |
| Criador | Cada pessoa agenciada | A página educacional inteira, os próprios números e as campanhas em que participa | Assiste aos conteúdos, acompanha o nível, pede batalha oficial, pede conversa, guarda o link do Indique e ganhe |
| Gestão | Anna e as gestoras que a Hera vier a contratar | Os criadores da própria carteira | Trabalha a fila do dia, copia e cola as mensagens, registra 1:1, confirma batalhas |
| Recrutamento | Fernanda e Adrielly | Quem cada uma trouxe, até o D15 | Cadastra o link do grupo individual e o contexto do criador; é acionada quando ele some |
| Sócias | Mariana e Aline | Tudo, mais premiações e fechamento | Aprovam campanhas e premiações, decidem manter ou encerrar, acompanham indicadores e compra de moedas |
| Gestora parceira | Lunow e Impulse, se quiserem | Só os próprios criadores | Usa a fila, as mensagens e a página educacional; campanhas internas, premiações e Indique e ganhe da Hera não valem para esses grupos |

A ficha de cada criador nasce da leitura do Backstage, assim que a pessoa entra na agência. O primeiro acesso ao app completa a ficha e ativa o login: o criador entra com e-mail e senha, informa o @ e o código de acesso que a gestora envia no grupo individual. Só entra quem consta na base da Hera no Backstage, e o acesso é bloqueado quando o criador sai da agência. A base atual entra pelo que já temos exportado.

Assim, quem ainda não abriu o app também aparece na fila da gestão.

## O motor de fases

O criador passa por seis fases. Cada fase muda o que aparece em destaque no app e o tipo de tarefa que chega na fila da gestão. A fase vem da data de entrada e dos dados do Backstage; ninguém precisa marcar.

&#91;embedded content: fases do criador · 5 em sequência, 1 desvio\]

As cinco fases seguem em linha. A pausa e a saída podem acontecer a partir de qualquer uma delas depois da chegada.

| Fase | Quando | O criador vê em destaque | A gestão recebe na fila | Muda de fase quando |
| --- | --- | --- | --- | --- |
| Chegada | Do aceite no Backstage ao primeiro contato | Boas-vindas, primeiro módulo da página educacional, resumo do que pode e não pode, para que serve cada grupo | Trilha sugerida pelo formulário para a gestão confirmar, nicho e se faz batalha; boas-vindas no grupo individual | Viu o material e combinou a 1ª LIVE |
| Novato | D1 a D14 | Contagem da regra do TikTok (dias válidos e horas, com o dia virando às 21h de Brasília), Desafio dos 5 dias, kit de quebra-gelo, checagem de luz e enquadramento | Mensagem do dia do roteiro; conferências no D3, D7, D10, D12 e D14; cadência de não-resposta | Fecha 5 dias válidos e 15 horas, ou chega ao D15 |
| Primeiro mês | D15 a D30 | Nível atual, evolução desde o dia 1, dias de LIVE que escolheu, campanha Primeiro Mês | Conversa de evolução do D15, montagem da rotina, retorno sobre a LIVE em até 24 horas | Completa 30 dias |
| Graduação | Até o fim do 3º mês | Quanto falta para 80 mil no mês, ritmo por dia, projeção e meses que restam na janela | Radar diário (no ritmo, precisa acelerar, último mês), 1:1 mensal para quem tem potencial, batalhas com criadores maiores | A janela fecha |
| Veterano | Depois da janela | Nível e faixa do próximo nível, campanhas em que participa, batalhas | Estado da semana e ação sugerida | Segue até sair |
| Pausa e saída | 4, 14, 21 e 30 dias sem LIVE, ou pedido de saída | Regras de saída explicadas com transparência e convite para voltar | Régua de reativação, decisão de manter ou encerrar aprovada pelas sócias, motivo de saída sempre registrado | Volta a fazer LIVE ou é removido |

A janela de graduação começa a contar na entrada e corre junto com as fases de novato e de primeiro mês. Cada mês com 80 mil dentro dos três primeiros meses vale uma graduação. Por isso o radar aparece para a gestão desde o primeiro dia e vira o destaque do criador depois do D30.

### Trilhas e nichos

A resposta do formulário de cadastro só sugere a trilha (Primeira LIVE, Veio de outra agência, Já tem nível e público). Quem define é a gestão, porque muita gente diz ter experiência sem ter. O histórico do Backstage (horas, nível, seguidores) ajuda a conferir.

A trilha e o nicho mudam o roteiro de mensagens e o que o app destaca. Eles não bloqueiam conteúdo: todos os vídeos ficam abertos para todos.

### Veteranos: o foco muda com o nível

| Grupo | Nível | Foco do criador | O que a gestão acompanha |
| --- | --- | --- | --- |
| Bronze | T1 (até 40 mil no mês) | Criar hábito e testar formatos | Frequência e dias válidos |
| Prata | T2 e T3 (40 mil a 149.999) | Aumentar a comunidade e repetir o que funciona | Regularidade, fã-clube e primeiras batalhas |
| Ouro | T4 (150 mil a 249.999) | Segurar a audiência | Retenção e batalhas no horário de pico |
| Diamante | T5 ou mais (250 mil ou mais) | Estratégia de conteúdo, networking e campanhas da plataforma | Previsibilidade e batalhas oficiais |

Os criadores Diamante têm 1:1 todo mês. O mesmo vale para quem tem potencial de graduação, enquanto a janela estiver aberta.

### Estado da semana e sinais

Além da fase, cada criador carrega um estado calculado toda semana: Queda, Subindo, Sem LIVE, Horas sem retorno, Irregular, Novo ou Estável. Três sinais completam a leitura: quase sem batalhas, fã-clube parado e sem vídeos. Fase, estado e sinais juntos definem a prioridade (1 a 3) e a mensagem sugerida. Essas regras já existem na automação semanal e entram no sistema como estão.

## Área do criador (app)

A tela principal do app é a página educacional da Hera. Em volta dela ficam o progresso do criador, as campanhas, as batalhas, o Indique e ganhe e a ajuda.

### Página educacional

É o material educacional da Hera em um só lugar, com os primeiros módulos abertos no primeiro acesso e os avançados abrindo conforme o criador avança. Precisa de um nome forte; sugestões: Academia Hera ou Escola Hera.

A ordem segue as dúvidas que aparecem em cada fase. O que decide a abertura é o nível e o marco alcançado, não o tempo de casa: quem chega de outra agência já no Nível 3 ou acima abre tudo no primeiro acesso, e quem começa do zero abre os módulos conforme avança. Assim o conteúdo de nível alto não fica disponível para quem entra e sai na primeira semana.

A gestão libera qualquer módulo antes da hora para um criador específico. O que ainda não abriu aparece como "abre no Nível X" ou "abre depois da sua 1ª LIVE", nunca como cadeado sem explicação: o que não abriu funciona como próximo passo, não como porta fechada.

| Módulo | Conteúdo | Quando abre |
| --- | --- | --- |
| 1. Começar | Como abrir uma LIVE, luz e enquadramento, o que pode e o que não pode | Primeiro acesso |
| 2. Primeiros 14 dias | O que é dia válido, a regra do TikTok, Desafio dos 5 dias | Primeiro acesso |
| 3. Interação | Ganchos de conversa, chamar pelo nome, Heart Me e fã-clube | Primeiro acesso |
| 4. Batalhas | Primeira batalha, co-host e convidados, batalha oficial | Depois da 1ª LIVE |
| 5. Rotina e crescimento | Dias de LIVE, vídeos e cortes, comunidade | Ao fechar os 14 dias, ou no D15 |
| 6. Nível e monetização | Presentes, campanhas, graduação e próximos níveis | Ao fechar os 14 dias, ou no D15 |
| 7. Estratégia avançada | Campanhas da plataforma, networking, planejamento de LIVE, batalha oficial de alto nível | Nível 3 (80 mil no mês) |
| Cursos extras | Temas por nicho e outros cursos que a Hera quiser oferecer, como organização financeira | Liberação da gestão |

Cada vídeo marca "assistido" para o próprio criador. A gestão vê na ficha o que já foi visto, e isso substitui a pergunta "conseguiu ver o material?".

### Meu progresso: a tela inicial do app

O app abre nesta tela. É a que o criador procura, porque entra para ver como está o mês, e por isso é também o caminho para o que ele não abriria sozinho: a página educacional, a campanha do momento, o Indique e ganhe e o pedido de batalha. Cada botão aparece logo depois do que o motiva, e não todos juntos no fim.

A página educacional continua sendo o conteúdo mais importante do app, mas como destino: quem chega nela vem daqui, pela aula recomendada ou pelo próximo módulo.

1. **Topo, que muda com a fase.** Na Chegada e no Novato (D1 a D14), a contagem dos 14 dias do TikTok, o próximo passo e o módulo Começar, porque o criador ainda não tem número para mostrar. Do Primeiro mês em diante, o nível atual, quanto falta para o próximo e os diamantes do mês.
2. **A frase do mês.** Uma linha só, escolhida pelos números.
3. **No seu ritmo.** "Mantendo esse ritmo, você fecha o mês em torno de X 💎."
4. **Simulador.** O criador mexe nos dias de LIVE que pretende fazer e vê onde pode chegar. Começa no ritmo atual e vai até o melhor mês dele, para explorar sem a Hera sugerir número.
5. **Campanha do momento.** Uma campanha só, a que o sistema escolheu para ele, com o prazo e o que falta para pontuar.
6. **Botão: pedir batalha oficial.** Logo depois, porque a batalha é a alavanca que mais muda o número.
7. **Semanas deste mês.** Diamantes, horas e dias por semana, com a semana mais fraca destacada e uma sugestão concreta ao lado, nunca só o número.
8. **Banner: aula recomendada.** Entra logo depois da semana fraca, ligado ao ponto que caiu.
9. **Meses desde a entrada.** Diamantes e nível de cada mês, para ver a evolução.
10. **Botão: Indique e ganhe.** Fecha a tela como o caminho de renda extra.

A frase do mês tem três versões:

| Situação | Frase |
| --- | --- |
| No ritmo de subir de nível | "No seu ritmo, você chega ao Nível X este mês. Parabéns pela constância!" |
| Perto, faltando pouco | "Você está a X 💎 do Nível Y. Dá pra chegar." |
| Abaixo do mês passado | O fato e um convite: "Suas horas de LIVE estão abaixo do mês passado. Quer ver a aula sobre rotina?" |

Nunca "você vai subir de nível": a projeção é estimativa e vem com o texto "estimativa pelo seu histórico, não é garantia". A frase nunca pede horas, dias ou horário.

**Aula recomendada.** O app sugere pelo ponto mais fraco do mês: poucos dias de LIVE, pouca interação, poucas batalhas ou co-host, fã-clube parado. A gestora pode trocar a aula na ficha do criador, e a escolha dela vence a sugestão automática.

**Push.** No máximo um por semana vindo desta tela, nunca entre 22h e 9h, e só quando há algo novo: nível novo, aula trocada pela gestora, campanha fechando. O criador pode desligar.

**De onde vem o número.** Todos os números desta tela saem de Dados do criador, que fecha no dia anterior, e a tela mostra "dados até ontem" com a hora da última atualização. Os pontos de campanha são a única exceção, porque vêm da tela de campanhas e podem atrasar de 2 a 3 horas.

**Nunca aparece aqui:** ranking, comparação com outro criador, a palavra relatório e a palavra meta.

### As outras áreas

| Área | O que tem | Por que importa |
| --- | --- | --- |
| Início | É a tela Meu progresso, descrita acima: o app abre nela | Uma tela só para o criador voltar; no começo mostra a contagem dos 14 dias, não os números |
| Meu progresso | Diamantes do mês, dias válidos, horas, "Meu nível" e "Próximo nível" com a faixa de diamantes, últimas 5 semanas; na janela de graduação, quanto falta para 80 mil e o ritmo por dia | Torna o avanço visível e tira da gestão as perguntas de contagem |
| Meu plano | Dias de LIVE que o criador escolhe, objetivos que ele mesmo define e lembretes que ele liga ou desliga | Rotina sem imposição |
| Batalhas | Pedido de batalha oficial em formulário, mural de vagas da semana, confirmação com oponente e checklist do dia, histórico | Substitui o modelo de texto no WhatsApp e dá os 7 dias de antecedência à gestão |
| Campanhas | Lista das campanhas em que o criador participa, internas da Hera e do TikTok, com a regra resumida e um botão que abre a campanha no app do TikTok; botão "Solicitar premiação" quando a gestão confirma o resultado | O criador sabe em que está; posição e ranking ficam só no TikTok |
| Indique e ganhe | Regras do programa, "meu link" (o criador cola o link do app do TikTok e ele fica guardado), indicações válidas, em andamento e não validadas, quanto já ganhou e formulário de Pix | Acaba com os pedidos de link à gestão e dá transparência sobre cada indicação; vale só para criadores da Hera |
| Ajuda | Dúvidas frequentes (saque, dias válidos, batalhas, fã-clube, conta e segurança, grupos), pedido de conversa com a gestão, aviso de restrição ou banimento na conta com pedido de auxílio e recurso via agência | Responde o repetitivo; o aviso de conta chega à gestão como prioridade 1 |
| Conquistas e prêmios | Marcos (1ª LIVE, 5 dias, 14 dias fechados, nível novo, graduação, 1 mês e 3 meses de Hera) e prêmios ganhos com a situação da entrega | Reconhecimento ligado a dado concreto |

O regulamento do Indique e ganhe será enviado pela Mariana. Ele define o que é indicação válida e quando o prêmio é devido.

Detalhes que fazem diferença no dia a dia:

- **Marco da primeira LIVE.** Na manhã seguinte à leitura do Backstage, o app mostra um cartão: "Sua primeira LIVE durou X e contou (ou não contou) como dia válido, pela regra do TikTok". Junto vêm três perguntas opcionais, de um toque: o que foi mais difícil (saber o que falar, vergonha, parte técnica, pouca gente, nada), como você se sentiu (três opções) e com o que você quer ajuda agora. As respostas vão para a ficha. O retorno depois da LIVE continua no grupo individual, com a gestora.
- **Calculadora "Onde posso chegar".** Fica em Meu progresso. A base são os diamantes por dia de LIVE do próprio criador, pela mediana das últimas 8 semanas. O criador escolhe quantos dias pretende fazer LIVE até o fim do mês, e o app mostra uma faixa de diamantes e o nível em que ela cai. Três referências ficam fixas: o ritmo atual, o melhor mês dele e quanto falta para o próximo nível. Para novatos, só aparece depois de 3 semanas de dados. O texto diz "estimativa pelo seu histórico, não é garantia", sempre em diamantes. O número de dias vem do criador, nunca da Hera.
- **Setup fica no grupo.** A foto ou o vídeo de luz e enquadramento continua sendo enviado no grupo individual, como parte do onboarding. O app tem só o vídeo que ensina.
- **Nomes que protegem a relação.** "Meu progresso" no lugar de relatório, "meus objetivos" no lugar de metas, "meu nível" e "próximo nível" como no TikTok. Tudo o que é regra aparece com o selo "regra do TikTok".
- **Saída sem surpresa.** As regras de saída (antes e depois de 15 dias, espera de 90 dias da plataforma) ficam escritas na Ajuda, no mesmo tom do Playbook. A Ajuda também explica que, depois de sair, o TikTok pode não liberar o perfil para outra agência em três casos: soma de 300 mil diamantes nos últimos 6 meses, contas múltiplas e violações no perfil. O TikTok não divulga um número exato de violações; a Hera consulta caso a caso.

## Área da gestão (site)

A tela inicial da gestora é a fila do dia: uma lista curta, em ordem de prioridade, com a mensagem pronta para cada criador. O resto do site existe para alimentar essa fila ou para aprofundar um caso.

### Fila do dia

Cada item traz o criador, o motivo ("D10 com 2 dias válidos", "queda de 40% com as horas mantidas") e a mensagem já preenchida com nome e números. São dois toques: "Copiar mensagem" e "Abrir grupo", que leva ao grupo individual pelo link guardado na ficha. A gestora cola e envia. Vale a regra de uma mensagem por dia por criador.

A fila guarda as datas fixas que já usamos: D10, D12, D14 e D15; régua de 4, 14, 21 e 30 dias sem LIVE; mural de batalhas na segunda; campanhas na véspera do fechamento. O que não tem data segue o ritmo atual: quedas na segunda e terça, quem está subindo ou irregular na quarta e quinta, batalhas de fim de semana na sexta.

Um item só sai da fila quando acontece uma de três coisas: a gestora marcou que enviou, adiou com motivo, ou o dado mudou (o criador abriu LIVE, por exemplo).

### Rotina diária e agenda do mês

Incluído em 12/11/2026. A Mariana recebeu o modelo de gestão de outra agência; estes são os itens que entram na fila, adaptados às regras da Hera. A fila continua organizada pela fase de cada criador, e estes itens entram como blocos fixos ou com data.

| Item na fila | Quando aparece | O que a gestora faz |
| --- | --- | --- |
| Suporte | Todo dia, primeiro bloco da fila | Responde as mensagens pendentes dos grupos individuais antes das mensagens do plano |
| Restrição ou banimento | Todo dia, enquanto houver caso aberto | Pede o print da restrição e da negativa do recurso, orienta o recurso, abre o chamado no TikTok e atualiza a situação na ficha; no 4º dia sem solução, o caso sobe para as sócias |
| Aniversário | No dia, e 30 dias antes | No dia, parabéns no grupo; 30 dias antes, oferece uma batalha oficial ou um evento de aniversário |
| Batalha oficial próxima | 4 dias antes da batalha | Checklist: ferramentas (luvas), divulgação diária nos vídeos e nas LIVEs, confirmação com a agência oponente, seguir o oponente e LIVE aberta para todos |
| Sugestão de visita | Todo dia, no máximo 3 | Visita a próxima LIVE do criador sugerido, marca "Visitei" com nota de 1 a 3 e manda o retorno |
| Acompanhamento de campanha | Dia seguinte à abertura, metade, véspera do fechamento e dia seguinte ao fim | Olha o ranking da campanha no TikTok e avisa, no grupo individual, quem está perto de prêmio |
| Rodada de batalhas oficiais | Dia 8 de cada mês | Oferece as batalhas oficiais do mês seguinte a criadores Ouro e Diamante |
| Resumo do mês | Dias 1 a 7 | Fala primeiro com quem foi menos constante (dias 1 a 5) e depois com os constantes; mensagem de parabéns ou de apoio, conforme o mês de cada um |
| Quase lá | Última semana do mês | Contato prioritário com quem está perto do próximo nível, dos 80 mil da graduação ou de um prêmio de campanha |

Como cada item funciona:

- **Aniversário.** O app pede dia e mês de nascimento no primeiro acesso. O ano não é pedido.
- **Sugestão de visita.** A Anna já visita as LIVEs; o sistema só indica por onde começar. Entram, nesta ordem: queda de prioridade 1, novato nos 5 primeiros dias de LIVE, criadores Diamante, quem tem potencial de graduação e quem está há 14 dias ou mais sem visita registrada. Cada sugestão mostra o motivo ("caiu 48% na semana"). A avaliação cobre cenário, câmera, áudio, interação, batalha e respeito às diretrizes.
- **Acompanhamento de campanha.** O sistema sabe quais campanhas estão no ar e monta a agenda pela duração de cada uma. Campanhas de até 3 dias têm só abertura e véspera; campanhas com ranking diário têm duas olhadas por semana. O item mostra a campanha, o link, os criadores da Hera que podem participar e a mensagem para preencher ("você está em Xº, faltam Y pontos"), sem citar o nome de outro criador. O ranking continua só no TikTok.
- **Mensagem de apoio.** Para quem fez mais horas e recebeu menos diamantes, ou perdeu uma campanha por pouco. Frases como "vários criadores ganharam menos" e explicações de sazonalidade só entram quando os números da Hera confirmam.
- **Projeção.** O texto é "no seu ritmo atual, você fecha o mês em X; faltam Y para o próximo nível". O sistema não sugere número de horas ou de dias.
- **Motivo de quem parou.** Campo de escolha na ficha, usado na régua de reativação e na saída: sem tempo, desanimou, problema técnico, viagem, não sabe o que fazer, problema pessoal, outra agência, outro.

O que não entra, do modelo da outra agência: apresentar ou aumentar meta, incentivo pago por dias e horas cumpridos, visita obrigatória a 100% da carteira por semana e radar de queda com dia fixo no mês (o da Hera é semanal e por criador).

Dependência: a agenda de campanhas precisa da lista de campanhas abertas. A leitura diária do Backstage passa a trazer essa lista, e as campanhas novas entram na agenda depois da aprovação das sócias.

### Regras de contato da carteira

Incluído em 12/11/2026. Hoje só o onboarding tem agenda; o resto da carteira anda pela demanda. Estas regras dão agenda para todos. Onde este trecho divergir de outro ponto do documento, vale este.

**Relógio de contato.** Cada criador tem um contador de dias desde a última mensagem individual registrada. O limite é de 4 dias para todos, contados de segunda a sábado. No domingo a fila não traz envios. Post no grupo de avisos não zera o contador. O limite fica na tela de configuração.

**Ordem da fila do dia:**

1. Suporte e restrições.
2. O que tem data: onboarding do dia, D10 a D15, régua de sem LIVE, batalha oficial em 4 dias, aniversário, campanha.
3. O que vem do dado: queda, subida, nível novo, módulo de curso concluído.
4. Rodízio: quem chegou ao limite de 4 dias sem contato e não entrou nos itens acima.

**Mensagem de rodízio.** O sistema escolhe pelo que há de novo para aquele criador, nesta ordem: novidade no app (progresso atualizado), próximo vídeo da jornada de cursos, campanha aberta que vale para ele, vaga de batalha, pergunta aberta. O mesmo modelo não se repete duas vezes seguidas. Com o app, a Hera não envia mais resumo de números pelo WhatsApp: a gestora avisa que há informação nova no app.

**Teto do dia.** Começa em 30 mensagens individuais por gestora, a calibrar com a Anna depois de duas semanas. O que passa do teto vai para o dia seguinte, começando pelo rodízio, e aparece no painel das sócias.

**Sem LIVE há 4 dias.** Vale para quem fez LIVE nos últimos 14 dias. No 4º dia sem LIVE, o criador entra na fila com uma pergunta aberta, sem cobrança. A resposta vira motivo na ficha: viagem, saúde (só a categoria, sem detalhes), trabalho ou estudo, problema técnico, desmotivou, problema pessoal, outra agência, não respondeu. "Desmotivou" pede o porquê: poucos diamantes, pouco público, não sabe o que fazer na LIVE, vergonha, outro. Se o criador informar a data de volta, o alerta fica em silêncio até lá e depois entra uma mensagem de boas-vindas de volta. Problema técnico vai para o suporte, "desmotivou" vira conversa curta e "outra agência" sobe para as sócias. A régua de quem está parado passa a ser 4, 14, 21 e 30 dias.

**Entrou e ainda não abriu LIVE.** Um terceiro relógio conta os dias desde o aceite sem a 1ª LIVE:

| Dia | Situação | O que a gestora faz |
| --- | --- | --- |
| D2 | Sempre | Combina a data da 1ª LIVE e envia a regra dos 14 dias, mesmo sem resposta do criador; a data fica na ficha |
| Data combinada | A LIVE não aconteceu | Mensagem de apoio no mesmo dia; no dia seguinte, "tá tudo bem?" |
| D3 | Sem LIVE e sem data combinada | Apoio e oferta de combinar a data |
| D5 | Sem LIVE | Entende o motivo e registra; aciona quem recrutou |
| D7 | Sem LIVE | Mensagem transparente: faltam 7 dias e a regra do TikTok pede 5 dias válidos; pode começar nesta semana ou sair agora e voltar sem espera |
| D10 | Sem LIVE | Último dia em que ainda dá para fechar os 5 dias válidos; mensagem de transparência e aviso às sócias |
| Até o D14 | Nunca abriu LIVE | Encerramento até o D14, com aprovação das sócias, para o criador poder voltar sem espera |

**Travas do onboarding.** Os 14 dias contam do aceite no Backstage; o Desafio dos 5 dias conta da 1ª LIVE. O passo que depende de resposta só aparece depois de "Respondeu"; o que depende de LIVE, só depois de o dado confirmar; sem resposta, entra a cadência de não-resposta. No D1, a gestora convida para o primeiro acesso ao app; antes da 1ª LIVE, lembra do módulo Começar.

**Ausência da gestora.** A gestora tem o botão "Hoje não trabalho". Os itens do dia passam para o dia seguinte, na ordem da fila. Os itens que não podem esperar (D10, D12, D14, encerramento, batalha oficial e restrição) vão para quem cobre: uma das sócias ou uma recrutadora. O painel das sócias mostra quantos dias foram pulados no mês.

**Anotações e lembretes.** Na ficha, a gestora registra "o criador me escreveu", anota pontos importantes e cria lembrete com data ("retorno prometido até dia 15"). O lembrete entra na fila no dia marcado.

**Conferência por sorteio.** Toda semana o painel das sócias sorteia 5 envios marcados como "Enviei" para conferência no grupo individual.

**Diagnóstico de queda.** Quando os diamantes caem, a fila mostra a primeira resposta "sim" desta ordem, com a mensagem certa para ela: caíram as horas ou os dias válidos; caíram as impressões ou os espectadores; caiu o tempo médio assistindo; caiu a taxa de presentes; caíram os diamantes por pessoa que presenteou; caíram as batalhas; caíram os fãs novos ou os vídeos. Se nada disso explicar, a gestora assiste à gravação de uma LIVE e dá nota de 1 a 3.

**Sinais de risco dos criadores Diamante.** O sistema calcula: queda de 30% ou mais, horas ou dias abaixo do normal, batalhas em queda forte, nenhum fã novo com 5 horas ou mais de LIVE. A gestora marca na ficha: demorou a responder, mudou o tom, falou de outra agência, reclamou de algo. Um sinal acende um aviso na ficha; dois ou mais viram item na fila em até 48 horas e entram na lista das sócias.

### Campanhas: o que a gestora acompanha

Conferido no Backstage em 14/11/2026. A tela Campanhas › Campanhas da plataforma já tem tudo o que a gestora precisa, em dois cortes, e é de onde a leitura diária passa a tirar os dados de campanha.

- **Por campanha:** período, nível recomendado, tipo (classificação, missão, recompensas), participantes sobre elegíveis e diamantes gerados. Hoje são 37 campanhas na conta.
- **Por criador:** a situação de cada criador em cada campanha, nas quatro etapas que o Backstage usa: Qualifica-se, Inscrito, Em andamento e Encerrada.
- **Tabela de classificação:** dentro de cada campanha, a posição e os pontos de cada criador, com filtro por gerente.

Com isso o painel monta sozinho três listas, e cada uma vira um item na fila do dia:

| Lista | O que é | Item na fila |
| --- | --- | --- |
| Qualificado e não inscrito | O criador pode entrar numa campanha aberta e ainda não se inscreveu | Mensagem com o link e o resumo da regra, antes de a inscrição fechar |
| Perto de prêmio | Está na faixa premiada ou a poucos pontos dela | Aviso individual com a posição e quantos pontos faltam |
| Pode perder posição | Caiu na classificação desde a leitura anterior | Aviso individual, sem citar quem passou |

**O que a conferência de hoje mostrou:** 3 campanhas estão abertas para inscrição, 64 criadores se qualificam e 19 se inscreveram. Os outros 45 ficam de fora sem ninguém perceber. Essa é a primeira lista a rodar quando o painel existir, e dá para fazer à mão antes disso.

**Campanhas da agência.** Na aba Campanhas dirigidas pela Agência aparecem as campanhas em que a Hera se inscreve como agência, com prazo próprio de inscrição. A inscrição é decisão das sócias e entra na lista de aprovações do painel.

**Atraso dos dados.** O próprio Backstage avisa que os dados de campanha podem atrasar de 2 a 3 horas. Por isso o aviso de "perto de prêmio" não vale para as últimas horas de uma campanha, e a véspera do fechamento continua sendo o momento de falar.

#### Uma campanha de cada vez por criador

O Backstage lista tudo junto, e hoje são 37 campanhas, várias delas válidas para o mesmo criador. O criador não sabe onde focar, e a gestora acaba mandando campanha nova quase todo dia, às vezes com prêmio que não interessa para aquela pessoa. A regra passa a ser outra: o sistema escolhe uma campanha por criador, e a gestora só envia essa.

A nota de cada campanha para cada criador sai de quatro contas:

| Conta | O que mede | De onde vem |
| --- | --- | --- |
| Encaixe | A mecânica da campanha bate com o que o criador já faz | Etiqueta da campanha × perfil das últimas 4 semanas |
| Chance | Quantos participam contra até que posição ganha | Participantes sobre elegíveis × faixa de prêmio |
| Prêmio | O prêmio comparado ao que o criador costuma fazer no mês | Prêmio da campanha × diamantes do mês dele |
| Esforço | Quanto falta para entrar na faixa, no ritmo atual | Pontos atuais × ritmo do criador |

O encaixe pesa mais que o prêmio: uma campanha de batalha para quem não batalha não motiva, por maior que seja o prêmio. E uma campanha com 2 participantes que premia até o 40º lugar vale mais do que uma com 78 participantes que premia o Top 3, mesmo pagando menos.

**Etiqueta de mecânica.** Cada campanha recebe uma etiqueta só: batalha, horas e constância, fã-clube, presentes e galeria, convidados e co-host, ou vídeos. O perfil do criador vem da leitura diária: batalhas por semana, dias e horas, fãs novos, co-host e vídeos.

**Quando troca.** A campanha do criador só muda quando ela termina, quando ele já garantiu a faixa de prêmio, ou quando entra outra com nota bem maior. Assim ele não recebe campanha nova toda semana.

**O que a gestora vê.** Um criador por linha, com uma campanha e o motivo em uma frase: "Duelo de Batalhas, porque ela faz 12 batalhas por semana e só 4 criadores participam". Ela pode trocar, tirar, ou marcar uma campanha como "não oferecer" quando o prêmio não compensa, e isso vale para todos.

**Para a agência.** A mesma conta mostra onde a Hera tem muitos qualificados e poucos participantes. Aí vale uma ação coletiva no grupo de avisos, em vez de mensagem um a um.

#### O que precisa de mão humana

As regras de cada campanha abrem como imagem de divulgação no Backstage, não como dado. A classificação não é automática: quando a campanha é cadastrada, alguém preenche quatro campos — mecânica principal, até que posição ganha, prêmio e nível recomendado. O Claude lê a imagem e propõe; as sócias confirmam junto com a aprovação de campanha que já fazem. São poucas campanhas novas por semana, e daí em diante a nota sai sozinha.

Dois limites: uma campanha com vários rankings dentro (a Coração da LIVE tem sete) entra com a mecânica principal, não com todas; e se o TikTok mudar o formato das regras, quebra a classificação, não o resto do sistema.

### As outras telas

| Tela | O que tem |
| --- | --- |
| Ficha do criador | Fase, trilha, nicho, nível, 5 semanas de números, sinais, quem recrutou, link do grupo individual, dia e mês de aniversário, vídeos assistidos, linha do tempo de tudo o que foi enviado e respondido, notas e o registro de cada 1:1 com print da conversa |
| Onboarding | Quadro por dia (chegada, D1 a D15) calculado pela data; alertas do D3, D7, D10, D12, D14 e D15; a cadência de não-resposta (+1, +2, +3 no privado, +5 dias) entra sozinha na fila, com a mensagem pronta para copiar e colar |
| Radar de graduação | Quem está na janela, diamantes do mês, ritmo por dia, quanto precisa por dia, projeção e aviso do último mês; por criador, a frequência de mensagens (último contato e total no mês) e a agenda de gestão (próximo 1:1 e próximo contato previsto) |
| Batalhas | Pedidos recebidos, sugestão de oponente do mesmo nível dentro da Hera, agenda, confirmação e atualização no modelo oficial, mural de vagas da semana |
| Campanhas | Cadastro com aprovação das sócias e o link da campanha no TikTok, quem participa de cada uma, o que fecha hoje, pedidos de premiação e premiação a entregar |
| 1:1 | Agenda, data da última 1:1 de cada criador com aviso ao passar de 30 dias, pauta de 7 blocos já preenchida com os números, plano com 2 a 3 ações e próximo encontro marcado; frequência de uma por mês para criadores Diamante e com potencial de graduação |
| Indique e ganhe | Indicações por criador, situação de cada uma pela regra do regulamento e prêmios a pagar |
| Biblioteca de mensagens | Todos os scripts do Playbook com variáveis, por trilha e nicho, com histórico de versões e um verificador de tom que barra meta, cobrança, prazo, horário e texto só no feminino |
| Pausas e saídas | Régua de reativação, criadores no D15 sem fechar a regra, pedido de decisão às sócias (manter ou encerrar) e motivo de saída como campo obrigatório |
| Grupo de avisos | Posts programados: mural de batalhas, campanhas que fecham e aulas |
| Carteiras | Divisão dos criadores entre as gestoras; a troca de carteira leva o histórico junto |

### Template do registro de 1:1

Sem registro, o 1:1 não conta. O registro fica só na área da gestão e não aparece no app do criador.

| Campo | O que registrar |
| --- | --- |
| Cabeçalho | Criador, data, canal (ligação, vídeo, áudio ou mensagem) e quem conduziu |
| Print da conversa | Imagem da conversa ou da tela da chamada, anexada |
| 1. Performance | Horas de LIVE, diamantes e média de espectadores, comparados ao mês anterior (preenchido pelo sistema) |
| 2. Constância | Dias com LIVE e o que atrapalhou a rotina |
| 3. Qualidade | Cenário, áudio, interação e retenção, com retorno técnico objetivo |
| 4. Monetização | Presentes, campanhas ativas e oportunidades |
| 5. Dificuldades | Técnicas, emocionais ou de agenda, e a solução conversada |
| 6. Plano | 2 a 3 ações combinadas, com quem faz cada uma |
| 7. Próximo 1:1 | Data já marcada |
| Anotações | O que foi falado e não coube nos blocos |

### Onde a inteligência artificial ajuda

- Preenche o trecho específico da mensagem ("você fez 3 LIVEs em 3 dias") a partir dos dados, para a gestora só revisar.
- Resume a ficha antes de um 1:1 e transforma as anotações em plano de ação.
- Sugere oponentes de batalha pelo histórico de diamantes.
- Nunca envia mensagem.

## Painel das sócias

O painel mostra, sem ninguém montar nada, se o método está sendo aplicado e se está dando resultado. Ele abre pelos totais da conta inteira, que é sobre o que o TikTok paga, e depois separa a Hera de Lunow e Impulse.

| Bloco | Indicadores | Referência que já usamos |
| --- | --- | --- |
| Resultado do mês | Diamantes da conta e só da Hera, comparados ao mês anterior; projeção do fechamento | Números de Receita › Incentivos, que incluem o dia de hoje |
| Fechamento | Incentivos da agência, graduações e simulação da compra de moedas | Estudo mensal, pronto antes do último dia |
| Funil do onboarding | Por mês de entrada: entrou, fez a 1ª LIVE, fechou 5 dias e 15 horas, ficou depois do D15, graduou | Regra do TikTok nos primeiros 14 dias |
| Retenção | Taxa de saída nos 15 primeiros dias; removidos por 30 dias sem LIVE; motivos de saída | Abaixo de 10% é bom, acima de 20% é ruim |
| Graduação | Quem bateu 80 mil no mês, quem está no ritmo, quem está no último mês da janela | 80 mil num mês, dentro dos 3 primeiros meses |
| Base por nível | Quantos criadores em cada grupo e quem subiu ou desceu | Bronze T1, Prata T2 e T3, Ouro T4, Diamante T5 ou mais |
| Execução da gestão | Itens da fila concluídos por dia e por gestora, tempo até o primeiro contato com o novato, respostas registradas, 1:1 feitos | 1:1 mensal com criadores Diamante e com potencial de graduação, sempre com registro |
| Página educacional | Quantos criadores assistiram a cada módulo; novatos que viram o módulo Começar antes da 1ª LIVE | Indicador novo |
| Batalhas | Batalhas por semana, batalhas oficiais marcadas e efeito em diamantes | 6 ou mais por semana é bom, menos de 3 é ruim |
| Premiações e indicações | Custo por campanha, pedidos de premiação, prêmios a entregar, moedas a comprar, indicações válidas do Indique e ganhe | Prêmio em diamantes na LIVE; Pix só de vez em quando |
| Recrutamento | Por recrutadora: quantos entraram, quantos fecharam os 14 dias, quantos graduaram | Qualidade de quem entra, não só quantidade |

As aprovações viram uma lista no painel: campanha nova, premiação, manter ou encerrar um criador. Qualquer uma das sócias resolve de onde estiver, e a decisão fica registrada na ficha.

### Como usar antes de o sistema existir

O painel pode começar já como uma página única, no mesmo formato do Acompanhamento Semanal, alimentada pela mesma leitura do Backstage. Ninguém precisa rodar nada: é só abrir o link, e a página atualiza quando a leitura agendada roda. No sistema final, ele vira uma página do site no login das sócias.

## Mensagens e automações

Toda mensagem nasce de um gatilho (uma data ou um dado), passa por uma regra e chega pronta para a gestora. Nenhuma mensagem é enviada sozinha: o sistema não tem conexão com o WhatsApp, e a API oficial não será usada.

1. **Gatilho.** Data de entrada, dia da 1ª LIVE, leitura diária do Backstage, pedido feito no app.
2. **Regra.** As do Playbook e da automação semanal, sem mudança: fase, trilha, nicho, estado da semana, sinais.
3. **Mensagem pronta.** Script certo, com nome e números preenchidos, checado pelo verificador de tom.
4. **Envio pela gestora.** Ela copia a mensagem, abre o grupo individual pelo link da ficha, cola e envia.
5. **Confirmação.** A gestora marca "Enviei" e, quando houver, "Respondeu", com um toque. O dado completa a leitura: houve LIVE, o criador respondeu ao marco da primeira LIVE no app, ou nada aconteceu.
6. **Próximo passo.** Segue o roteiro, ou a cadência de não-resposta entra na fila.

### Quem envia cada tipo

| Tipo | Exemplos | Quem envia |
| --- | --- | --- |
| Informativo | Campanha fecha hoje, batalha amanhã, contagem dos 14 dias atualizada, vídeo novo na página educacional | O app, por notificação, se o criador deixou ligado |
| Relacionamento | Boas-vindas, retorno depois da LIVE, reconhecimento, apoio, queda, reativação | A gestora, com a mensagem pronta para copiar e colar |
| Decisão | Encerramento no D15 ou aos 30 dias, campanha nova, premiação | A gestora, depois da aprovação das sócias |

### O canal

- **WhatsApp, no grupo individual.** O link de cada grupo fica guardado na ficha, cadastrado por quem cria o grupo. Pelo que sei, link de grupo abre o grupo mas não leva texto pronto, por isso o fluxo tem dois toques: copiar e abrir.
- **Notificações do próprio app.** Levam o informativo para fora do WhatsApp e deixam a conversa humana mais leve.

## Dados e integrações

O Backstage é a única fonte dos números. Não existe API, então a leitura continua sendo feita pelo Claude, que envia o arquivo pronto para o sistema.

### Backstage

- **Como funciona.** O Claude lê o Backstage com o login da agência, monta o arquivo de dados (como já faz para o Acompanhamento Semanal) e o envia ao sistema por uma porta de importação.
- **Agenda.** Leitura automática todo dia de manhã. O dia do TikTok vira às 21h de Brasília, então de manhã o dia anterior já está fechado.
- **Plano B.** Se a leitura automática falhar, o sistema avisa e a gestora sobe a planilha exportada do Backstage. Se a planilha virar o caminho principal, a frequência é de segunda a sexta.
- **O que o criador vê.** A planilha de Dados do criador tem um dia de atraso, então o app mostra sempre "dados até ontem" e a hora da última atualização.
- **Qual número vale no fechamento.** Diamantes de Receita › Incentivos, que incluem o dia de hoje, para as decisões das sócias.
- **Campos lidos.** Diamantes, duração de LIVE, dias válidos, batalhas, novos membros do fã-clube, vídeos novos, data de entrada, última LIVE, seguidores, situação de graduação e nível. Para o Indique e ganhe, falta confirmar que a tela de indicações pode entrar na leitura.
- **Ponto de atenção.** A leitura depende do computador da Mariana ligado com o app do Claude aberto. Com criadores olhando o app todo dia, uma leitura perdida deixa os números parados; por isso o aviso na tela e o plano B.

**Uma fonte só para o que o criador e a gestão veem.** Todos os números do app e do painel saem de Dados do criador, que fecha no dia anterior. Receita › Incentivos, que inclui o dia de hoje, fica só para o fechamento do mês e as decisões de compra das sócias. Assim nenhuma tela mistura dois cortes de data, e a planilha de Dados do criador, que é a mesma que já exportamos, pode ser subida todo dia no app como plano B.

### Leitura detalhada por criador

Conferido no Backstage em 12/11/2026. A página de cada criador (Gerenciar criadores, clicando no criador) tem mais dados do que a lista geral, e eles entram na leitura.

| Onde | O que mostra |
| --- | --- |
| Desempenho da LIVE, por dia | Diamantes, impressões, público alcançado, visualizações, espectadores, taxa de toques, duração da LIVE, tempo médio assistindo, novos seguidores, presentes, pessoas que presentearam, taxa de presentes, comentadores, taxa de comentários; comparação com o período anterior |
| Origens de tráfego | Feed de LIVE, Para Você, Seguindo e outros, em porcentagem |
| Transmissões de LIVE, por LIVE | Início e fim, duração, impressões, espectadores, pico de pessoas ao mesmo tempo, média de pessoas ao mesmo tempo, tempo médio assistindo, comentadores, novos seguidores, diamantes, presentes, tipo (normal, co-host, batalha) e gravação disponível |
| Análise de uma LIVE | Linha do tempo de presentes, espectadores e interações, com os períodos de batalha marcados; parte dos diamantes que veio de seguidores |

- **Frequência.** Todo dia para quem está na fila (novatos, criadores Diamante, potencial de graduação e quedas); uma vez por semana para o resto da carteira.
- **Para que serve.** Preenche o bloco de performance do 1:1, alimenta o marco da primeira LIVE, torna o diagnóstico de queda preciso e personaliza o retorno depois da LIVE ("ontem você teve pico de 82 pessoas e 91 comentaram").
- **Cuidados.** Os horários do Backstage estão em UTC. A tela não mostra quem presenteou, só quantas pessoas. A coleta automática dessa página ainda precisa ser montada e testada.

### De onde nasce a ficha

A ficha nasce da leitura do Backstage, assim que a pessoa entra na agência. No primeiro acesso ao app, o criador informa o @, o sistema confere com o Backstage, e a ficha é completada com as respostas do cadastro. A base atual é carregada de uma vez com o que já temos exportado.

### As outras ligações

| Sistema | O que entra ou sai | Observação |
| --- | --- | --- |
| Formulário de cadastro | Primeira tela do app; a resposta sobre experiência com LIVE sugere a trilha | A gestão confirma ou troca a trilha |
| Formulário de Pix | Dentro do Indique e ganhe e no botão "Solicitar premiação" de uma campanha ganha | Dados visíveis só para o financeiro; o botão aparece depois que a gestão confirma o resultado |
| WhatsApp | Link do grupo individual guardado na ficha | Sem API; a gestora copia e cola |
| TikTok | Link de cada campanha e link pessoal do Indique e ganhe | O app só guarda e abre os links |
| Agenda | 1:1 e batalhas oficiais com lembrete | Conta Google da Hera |
| Histórico atual | Registros desde outubro de 2026 e as regras da automação semanal | Migram como estão |

O Argus fica fora do sistema.

### Formato do produto

Um só sistema na web, que abre bem no celular e pode ser instalado na tela inicial sem passar pelas lojas. O criador usa no celular, a gestão no computador.

## Cuidados

Três riscos precisam ser tratados no desenho, antes de qualquer tela: o trabalhista, o de dados pessoais e o de dependência do TikTok. Não sou advogado; os dois primeiros pedem revisão jurídica antes do lançamento.

### Risco trabalhista

Um app que mostra horas, dias e lembretes pode ser lido como controle de jornada. O cuidado que a Hera já tem com as palavras precisa virar regra do produto.

- Os números são do criador e aparecem como o negócio dele, não como acompanhamento da Hera.
- Dias de LIVE e objetivos são escolhidos por ele e podem ser mudados ou apagados a qualquer momento.
- Lembretes são opcionais e vêm desligados.
- Nada no app gera punição por parte da Hera. O que tem consequência (14 dias, graduação, espera de 90 dias) aparece como regra do TikTok.
- O app não tem ranking. Posição em campanha só existe no app do TikTok.
- O verificador de tom vale para as telas, não só para as mensagens.
- O termo de uso deixa clara a relação entre autônomos, sem exclusividade e sem obrigação de horário.
- O regulamento do Indique e ganhe passa pela mesma revisão, por envolver pagamento.

### Dados pessoais

- Cada criador vê só os próprios dados. No Indique e ganhe, quem indica vê só a situação de cada indicação, não os números da pessoa indicada.
- Dados de Pix ficam separados, com acesso só do financeiro.
- Prints de conversa do 1:1 ficam só na área da gestão.
- O cadastro pede consentimento e explica o que é lido do Backstage.
- Quem sai pode pedir a exclusão dos dados.
- Cada gestora vê só a própria carteira. As gestoras de Lunow e Impulse veem só os criadores delas, e a gestão da Hera não vê os dessas agências além dos totais da conta.

### Dependência do TikTok

- A leitura do Backstage acontece uma vez por dia e tem o plano B da planilha.
- O login da agência no Backstage fica com pouquíssimas pessoas.
- Regras do TikTok mudam. Níveis, regra dos 14 dias e graduação ficam em uma tela de configuração, não escritos no código.

### Dependência de uma pessoa

Hoje a Anna cuida sozinha de toda a base. O sistema trabalha com carteiras por gestora, sem limite de pessoas: a Hera pode contratar uma segunda, terceira ou quarta gestora, e a troca de carteira leva o histórico completo de cada criador.

## O que eu faria como CEO da Hera

Eu melhoraria o app que a Hera já tem, em etapas. Primeiro o que tira trabalho da gestão e confirma que o método está sendo aplicado; logo em seguida, a página educacional para o criador.

### A ordem de construção

1. **Mapear o app atual.** Antes de qualquer mudança, comparar o que existe com este documento: o que já está pronto, o que precisa mudar e o que falta. O Claude Code faz isso lendo o código.
2. **Base e fila do dia.** Importação diária do arquivo do Backstage, fichas da base atual, fila do dia com "Copiar mensagem" e "Abrir grupo", quadro de onboarding, biblioteca de mensagens e carteiras por gestora. As regras atuais entram sem mudança.
3. **App do criador.** Página educacional como tela principal, Meu progresso com nível e contagens, pedido de batalha oficial e campanhas com link para o TikTok. Teste com cerca de 10 criadores antes de abrir para todos.
4. **Gestão completa.** Batalhas com agenda, campanhas com aprovação das sócias, 1:1 com o template, pedidos de premiação, Indique e ganhe (depois do regulamento) e painel das sócias.
5. **Crescimento do criador.** Conquistas, marco da primeira LIVE, calculadora "Onde posso chegar", cursos extras e apoio de inteligência artificial nos rascunhos.
6. **Outros grupos.** Login para as gestoras de Lunow e Impulse.

Cada etapa só começa quando a anterior está em uso de verdade. O painel das sócias pode começar antes, como página única alimentada pela leitura que já existe.

### O que só a Hera tem

Ferramentas de mercado já mostram números do Backstage ao criador ([Devign Agency Suite](https://www.muzahim.devignlb.com/) é um exemplo). O que diferencia o app da Hera é o motor de fases com o Playbook dentro, as regras de tom e a página educacional própria. É nisso que o esforço deve se concentrar.

### O que eu não faria

- **Reescrever o app do zero.** Melhorar o que existe, etapa por etapa.
- **Chat próprio para substituir o WhatsApp.** O criador já está lá, e a relação também.
- **Mensagens enviadas sozinhas.** O Playbook pede gente no retorno depois da LIVE.
- **App nas lojas logo de início.** Custa caro e atrasa o teste.
- **Qualquer ranking.** Nem no app, nem nos grupos. O ranking fica só no app do TikTok.
- **Qualquer mecânica com punição.** Perder pontos ou status por não fazer LIVE contradiz a parceria e aumenta o risco trabalhista.
- **Mudar o método junto com a ferramenta.** Primeiro o sistema reproduz o que já funciona; os ajustes vêm depois, com dado.

### Como saber se deu certo

| Indicador | Hoje | Onde quero chegar |
| --- | --- | --- |
| Novatos que fecham 5 dias e 15 horas em 14 dias | Não medido por mês de entrada | Medido todo mês e em alta |
| Saída nos 15 primeiros dias | Não medido | Abaixo de 10% |
| Graduações por mês | Acompanhadas no radar semanal | Em alta, com radar diário |
| Fila do dia concluída | Sem medida confiável | Acima de 90% dos itens no dia |
| Respostas e 1:1 registrados | 0 e 0 na segunda quinzena de outubro | 1:1 mensal com todos os criadores Diamante e com potencial de graduação |
| Novatos que veem o módulo Começar antes da 1ª LIVE | Não existe | Maioria dos novatos |
| Criadores ativos que abrem o app na semana | Não medido | Maioria da base ativa |
| Tempo da gestão em tarefas manuais | Alto, sem medida | Metade do atual, medido pela Anna |

Os alvos sem número de referência no Playbook são proposta minha e precisam ser validados com a Anna.

## Decisões

### Tomadas pela Mariana em 11/11/2026

- O sistema melhora o app que a Hera já tem, com o Claude Code.
- A página educacional é a tela principal do app, com todos os vídeos e cursos abertos para todos.
- Sem ranking no app e nos grupos; as campanhas abrem no app do TikTok.
- Sem API do WhatsApp; a gestora copia a mensagem e cola no grupo individual, pelo link guardado na ficha.
- A leitura do Backstage continua sendo feita pelo Claude, que envia o arquivo ao sistema; a planilha exportada é o plano B.
- O Argus fica fora do sistema.
- A trilha é definida pela gestão; o formulário só sugere.
- Campanhas, premiações e a decisão de manter ou encerrar um criador têm aprovação das sócias.
- 1:1 mensal com os criadores Diamante e com quem tem potencial de graduação.
- A leitura de principais apoiadores sai do sistema.
- O Indique e ganhe entra no app, só para criadores da Hera.
- As gestoras de Lunow e Impulse podem ter login para usar o método com os criadores delas, sem as campanhas internas da Hera.
- O sistema aceita várias gestoras, cada uma com a sua carteira.
- O motivo de saída é sempre registrado.
- No app, o criador vê "Meu nível" e "Próximo nível".

### Tomadas pela Mariana em 12/11/2026

- O app pede dia e mês de aniversário no primeiro acesso; a fila avisa no dia e 30 dias antes.
- A visita às LIVEs não vira obrigação semanal; a fila sugere até 3 visitas por dia.
- A posição em campanha é acompanhada pela gestora, com agenda por campanha e aviso individual; o app e os grupos continuam sem ranking.
- Entram na fila: suporte como primeiro bloco, restrições com aviso às sócias no 4º dia, checklist de batalha oficial 4 dias antes, rodada de batalhas oficiais no dia 8, lista "Quase lá" na última semana e motivo de quem parou.
- Não entram: meta apresentada ao criador e incentivo por dias e horas.

* Limite de 4 dias sem mensagem individual para todos, de segunda a sábado; domingo sem envios.
* Sem LIVE há 4 dias: a gestora entende e registra o motivo; a régua passa a ser 4, 14, 21 e 30 dias.
* Quem entrou e nunca abriu LIVE é encerrado até o D14.
* Login com e-mail, senha e código de acesso enviado pela gestora; só criadores da Hera entram.
* O check-in depois da LIVE e o envio de setup saem do app; entram o marco da primeira LIVE e a calculadora "Onde posso chegar".
* A Ajuda explica os casos de inelegibilidade para agenciamento depois da saída.
* A ausência da gestora é coberta por uma sócia ou recrutadora; a gestora pode pular um dia.
* Sorteio semanal de 5 envios para conferência das sócias.
* A leitura do Backstage passa a incluir a página de cada criador e as LIVEs dele.

### Tomadas pela Mariana em 14/11/2026

- O conteúdo da página educacional passa a abrir por nível e por marco, em vez de ficar todo aberto desde o primeiro acesso. Quem entra no Nível 3 ou acima abre tudo; a gestão pode liberar qualquer módulo antes da hora.
- Módulo novo "7. Estratégia avançada", que abre no Nível 3.
- Meu progresso passa a ser a tela inicial do app, juntando o que era Início. A página educacional continua sendo o conteúdo mais importante, mas como destino.
- No Novato, o topo da tela inicial mostra a contagem dos 14 dias em vez dos números do mês.
- A gestora escolhe na ficha qual aula aparece para cada criador, e essa escolha vence a sugestão automática.
- O acompanhamento de campanhas entra no painel da gestão com três listas próprias: qualificado e não inscrito, perto de prêmio e pode perder posição.
- A leitura diária do Backstage passa a trazer também as campanhas: situação de cada criador e posição na classificação.
- Cada criador recebe uma campanha de cada vez, escolhida pelo sistema por encaixe, chance, prêmio e esforço, com o motivo em uma frase para a gestora. A campanha do momento aparece na tela inicial do criador.
- Cada campanha cadastrada recebe uma etiqueta de mecânica e a faixa de prêmio, propostas pelo Claude e confirmadas pelas sócias.
- Fonte única de dados: o app e o painel usam Dados do criador (fecha no dia anterior). Receita › Incentivos fica só para o fechamento e as decisões de compra das sócias.

### Em aberto

- [ ] Regulamento do Indique e ganhe: a Mariana envia, com a regra de indicação válida e de pagamento.
- [ ] Confirmar que a tela de indicações do Backstage pode entrar na leitura.
- [ ] Página educacional: nome, ordem dos vídeos e quem grava.
- [ ] O que o app atual já tem: resultado do mapeamento pelo Claude Code.
- [ ] Acesso das gestoras de Lunow e Impulse: cortesia ou cobrado?
- [ ] Revisão jurídica (trabalhista e dados pessoais): quem faz, e antes de qual etapa?
- [ ] Quais criadores testam primeiro o app?
- [ ] O que a Anna acha da fila do dia?

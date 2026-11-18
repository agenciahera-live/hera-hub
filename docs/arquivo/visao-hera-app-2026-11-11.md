> **Versão arquivada em 14/11/2026. Não vale mais.** Foi substituída por `docs/hera-app-visao.md` (versão final, com as decisões de 11, 12 e 14/11). Vários pontos daqui foram revogados: ranking nas campanhas, API do WhatsApp, ligação com o Argus, leitura em servidor, check-in e envio de setup pelo app, principais apoiadores e régua de 7 dias sem LIVE.

# Hera App — visão do aplicativo e site para gestão e criadores

Nov 11, 2026 · @Mariana

## Resumo

A Hera precisa de um sistema só, com duas portas: o app do criador e o site da gestão. Os dois leem os mesmos dados do Backstage. Cada criador está sempre em uma fase, e a fase decide o que ele vê no app e o que a Anna envia para ele naquele dia.

O problema de hoje não é falta de conteúdo. O Playbook, o roteiro por trilha e nicho e as regras de prioridade já existem e funcionam. O que falta é tirar o copiar e colar da rotina da Anna e saber se a conversa de fato aconteceu.

As cinco apostas do produto:

1. **Uma fila do dia, não um painel.** A Anna abre o site e vê quem precisa de contato hoje, por quê, e a mensagem pronta. Ela não monta nada.
2. **O sistema fecha o ciclo sozinho.** LIVE feita, dias válidos e horas vêm do Backstage todo dia. O passo seguinte só aparece quando o dado confirma o anterior.
3. **O criador enxerga o próprio caminho.** Contagem dos 14 dias, janela de graduação, tier, campanhas e batalhas ficam no app. Menos dúvidas no WhatsApp, mais autonomia.
4. **O tom de parceria faz parte do produto.** Regras do TikTok aparecem como regras da plataforma. Objetivos são escolhidos pelo criador. Nada de meta, cobrança ou horário pedido pela Hera.
5. **Feito para mais de uma agência desde o início.** Lunow e Impulse já dividem o Backstage com a Hera. A mesma estrutura permite vender o sistema para outras agências depois, ao lado do Argus.

## Diagnóstico: o que já fazemos e onde trava

A Hera já tem o método. O que trava é a execução manual: páginas separadas, leitura do Backstage duas vezes por semana e registro feito à mão.

| O que existe hoje | O que funciona | Onde trava |
| --- | --- | --- |
| Playbook do Gestor e roteiro online | Scripts do D1 ao D15, três trilhas, ajustes por nicho, situações e dúvidas frequentes | A Anna copia de uma página e cola no WhatsApp, trocando nome e números à mão |
| Acompanhamento Semanal (Plano da semana, Onboarding, Desempenho) | Status e prioridade calculados por criador; uma mensagem por dia; etapa do onboarding pela data | Lê o Backstage só na segunda e na quinta e depende do computador da Mariana ligado com o app aberto |
| Radar de graduação (80 mil no mês) | Ritmo por dia, projeção do mês e aviso do último mês da janela | Atualiza uma vez por semana; a janela de graduação se decide dia a dia |
| Registro ("Enviei", "Respondeu", notas, 1:1) | Histórico por criador, salvo todo mês | Depende de a Anna marcar; não confirma envio nem resposta |
| Campanhas por tier, rankings e mural de batalhas | Grupos Bronze, Prata, Ouro e Diamante e Primeiro Mês | Campanhas novas são cadastradas à mão; rankings montados no grupo |
| Batalha oficial | Modelo de pedido e de confirmação | Pedido por texto no WhatsApp; busca de oponente sem agenda |
| Premiação em dinheiro | Formulário na conta Google da Hera | Fora do fluxo; sem ligação com a campanha que gerou o prêmio |
| Resumo do mês e estudo de fechamento | Visão da conta inteira e só da Hera | Montado a cada mês; não há painel contínuo para as sócias |

### O que o registro de outubro mostra

Entre 15 e 28 de outubro foram registradas 100 mensagens para 33 criadores, 0 respostas e 0 conversas 1:1. Em pelo menos seis criadores, de 4 a 8 passos do onboarding foram marcados em poucos minutos.

Há duas leituras possíveis: as mensagens saíram em bloco, ou o registro foi preenchido depois. Nas duas, o sistema atual mede cliques, não conversas. Ele não sabe se a mensagem saiu no dia certo nem se o criador respondeu.

Esse é o principal ponto a resolver. O Playbook depende de ritmo (uma mensagem por dia, o passo seguinte só depois da LIVE anterior) e de resposta humana em até 24 horas depois da LIVE. Sem confirmar essas duas coisas, não dá para saber se o método está sendo aplicado.

## Princípios do produto

Oito regras decidem o que entra e o que fica de fora. Todas vêm do que já foi combinado neste projeto.

1. **Fase primeiro.** Todo criador tem uma fase, e a fase define telas, conteúdos e mensagens. Ninguém recebe tudo de uma vez.
2. **Dado antes de mensagem.** A mensagem do dia seguinte só aparece depois que a LIVE anterior consta no Backstage. O sistema confere antes de sugerir.
3. **A gestora decide, o sistema prepara.** Reconhecimento, apoio e conversa difícil são sempre humanos. O sistema escreve o rascunho e a Anna aprova e envia.
4. **Uma mensagem por dia por criador.** O que não cabe vai para o próximo dia livre.
5. **Primeiro cai a LIVE, depois cai o diamante.** Toda leitura de queda começa por dias e horas, nunca por receita.
6. **Parceria entre autônomos.** No app do criador não existem as palavras meta, relatório, cobrança, prazo ou horário. Regras do TikTok são sempre apresentadas como regras da plataforma. A linguagem é neutra.
7. **Nada é sobrescrito.** Cada envio, resposta, nota e 1:1 vira uma linha nova na ficha, com data e autor.
8. **Decisões sensíveis passam pela Mariana.** Campanha nova, encerramento fora da regra e premiação precisam de aprovação antes de valer.

## Quem usa e o que cada perfil acessa

São cinco perfis sobre a mesma base de dados. Cada um vê só o que precisa para agir.

| Perfil | Quem | O que vê | O que faz |
| --- | --- | --- | --- |
| Criador | Cada pessoa agenciada | Só os próprios números, as campanhas do seu grupo e os conteúdos da sua fase | Acompanha o progresso, pede batalha oficial, pede conversa, escolhe objetivos e dias de LIVE |
| Gestão | Anna | Toda a base da Hera | Trabalha a fila do dia, envia mensagens, registra 1:1, confirma batalhas |
| Recrutamento | Fernanda e Adrielly | Quem cada uma trouxe, até o D15 | Passa o bastão (trilha, nicho, contexto) e é acionada quando o criador some |
| Sócias | Mariana e Aline | Tudo, mais premiações e fechamento | Aprovam campanhas, decidem manter ou encerrar, acompanham indicadores e compra de moedas |
| Agência parceira | Lunow e Impulse | Só os próprios criadores | Ficam fora das campanhas e premiações da Hera |

O criador entra por um link de convite enviado no grupo individual e confirma pelo WhatsApp, sem senha. O convite já carrega o @ do TikTok, a trilha e quem recrutou.

## O motor de fases

O criador passa por seis fases. Cada fase muda a tela inicial do app e o tipo de tarefa que chega na fila da Anna. A fase vem da data de entrada e dos dados do Backstage; ninguém precisa marcar.

&#91;embedded content: fases do criador · 5 em sequência, 1 desvio\]

As cinco fases seguem em linha. A pausa e a saída podem acontecer a partir de qualquer uma delas depois da chegada.

| Fase | Quando | O criador vê no app | A gestão recebe na fila | Muda de fase quando |
| --- | --- | --- | --- | --- |
| Chegada | Do aceite no Backstage ao primeiro contato | Boas-vindas, vídeo curto, resumo do que pode e não pode, para que serve cada grupo | Passagem do recrutamento com trilha, nicho e se faz batalha; boas-vindas no grupo individual | Viu o material e combinou a 1ª LIVE |
| Novato | D1 a D14 | Contagem da regra do TikTok (dias válidos e horas, com o dia virando às 21h de Brasília), Desafio dos 5 dias, kit de quebra-gelo, checagem de luz e enquadramento | Mensagem do dia do roteiro; conferências no D3, D7, D10, D12 e D14; cadência de não-resposta | Fecha 5 dias válidos e 15 horas, ou chega ao D15 |
| Primeiro mês | D15 a D30 | Tier atual, evolução desde o dia 1, dias de LIVE que escolheu, campanha Primeiro Mês | Conversa de evolução do D15, montagem da rotina, retorno sobre a LIVE em até 24 horas | Completa 30 dias |
| Graduação | Até o fim do 3º mês | Quanto falta para 80 mil no mês, ritmo por dia, projeção e meses que restam na janela | Radar diário (no ritmo, precisa acelerar, último mês), 1:1 a cada 30 dias, batalhas com criadores maiores | A janela fecha |
| Veterano | Depois da janela | Tier e faixa do próximo, campanhas do grupo, batalhas, principais apoiadores | Estado da semana e ação sugerida | Segue até sair |
| Pausa e saída | 7, 14, 21 e 30 dias sem LIVE, ou pedido de saída | Regras de saída explicadas com transparência e convite para voltar | Régua de reativação, decisão de manter ou encerrar com a Mariana, motivo registrado | Volta a fazer LIVE ou é removido |

A janela de graduação começa a contar na entrada e corre junto com as fases de novato e de primeiro mês. Cada mês com 80 mil dentro dos três primeiros meses vale uma graduação. Por isso o radar aparece para a gestão desde o primeiro dia e vira a tela principal do criador depois do D30.

### As três trilhas e os nichos continuam valendo

A trilha (Primeira LIVE, Veio de outra agência, Já tem nível e público) vem do formulário de cadastro e muda o roteiro da chegada e do novato. O nicho troca o teste de formato do D2, a alternativa à batalha no D4 e os ganchos de conversa. O app usa os dois para escolher o conteúdo; a Anna não precisa lembrar.

### Veteranos: o foco muda com o tier

| Grupo | Tier | Foco do criador | O que a gestão acompanha |
| --- | --- | --- | --- |
| Bronze | T1 (até 40 mil no mês) | Criar hábito e testar formatos | Frequência e dias válidos |
| Prata | T2 e T3 (40 mil a 149.999) | Aumentar a comunidade e repetir o que funciona | Regularidade, fã-clube e primeiras batalhas |
| Ouro | T4 (150 mil a 249.999) | Segurar a audiência | Retenção e batalhas no horário de pico |
| Diamante | T5 ou mais (250 mil ou mais) | Estratégia de conteúdo, networking e campanhas da plataforma | Previsibilidade, principais apoiadores e batalhas oficiais |

Os principais têm tratamento próprio: os 4 maiores das últimas 4 semanas com potencial de subir, mais quem pode bater 80 mil na janela. Eles têm 1:1 a cada 30 dias, e a leitura de audiência e de apoiadores cobre cerca de 10 criadores.

### Estado da semana e sinais

Além da fase, cada criador carrega um estado calculado toda semana: Queda, Subindo, Sem LIVE, Horas sem retorno, Irregular, Novo ou Estável. Três sinais completam a leitura: quase sem batalhas, fã-clube parado e sem vídeos. Fase, estado e sinais juntos definem a prioridade (1 a 3) e a mensagem sugerida. Essas regras já existem na automação semanal e entram no sistema como estão.

## Área do criador (app)

O app responde três perguntas do criador sem ele precisar chamar ninguém: como estou, o que posso fazer agora e como peço ajuda. São oito áreas, e a tela inicial muda conforme a fase.

| Área | O que tem | Por que importa |
| --- | --- | --- |
| Início | O próximo passo da fase, a contagem em andamento, campanhas que fecham hoje e a próxima batalha marcada | Uma tela, uma ação; evita sobrecarga no começo |
| Meu progresso | Diamantes do mês, dias válidos, horas, tier atual e faixa do próximo, últimas 5 semanas; na janela de graduação, quanto falta para 80 mil e o ritmo por dia | Torna o avanço visível e tira da Anna as perguntas de contagem |
| Meu plano | Dias de LIVE que o criador escolhe, objetivos que ele mesmo define e lembretes que ele liga ou desliga | Rotina sem imposição; os dias escolhidos podem ir para Adicionar programação no Backstage |
| Batalhas | Pedido de batalha oficial em formulário, mural de vagas da semana, confirmação com oponente e checklist do dia, histórico | Substitui o modelo de texto no WhatsApp e dá os 7 dias de antecedência à gestão |
| Campanhas | Campanhas do grupo de tier, regras, posição no ranking e prêmios; competição de iniciantes no primeiro mês | O criador sabe em que está e o que falta, sem depender do grupo de avisos |
| Aprender | Conteúdo curto liberado por fase, trilha e nicho: vídeo do básico, imagem do que pode e não pode, aula de batalha, Heart Me, lista de ganchos de conversa, aula gravada para iniciantes | Aprendizado na hora em que faz sentido, depois da prática |
| Ajuda | Dúvidas frequentes (saque, dias válidos, batalhas, fã-clube, conta e segurança, grupos), pedido de conversa com a gestão, aviso de restrição na conta | Responde o repetitivo e deixa para a Anna o que precisa de gente |
| Conquistas e prêmios | Marcos (1ª LIVE, 5 dias, 14 dias fechados, tier novo, graduação, 1 mês e 3 meses de Hera) e prêmios ganhos com situação do pagamento | Reconhecimento ligado a dado concreto; dados de Pix pedidos só quando há prêmio em dinheiro |

Quatro detalhes que fazem diferença no dia a dia:

- **Check-in de um toque depois da LIVE.** "Como você se sentiu?" com três opções. A resposta chega na ficha e orienta o retorno da Anna.
- **Envio do setup.** O novato manda foto ou vídeo de luz e enquadramento pelo app, e a Anna devolve o ajuste.
- **Nomes que protegem a relação.** "Meu progresso" no lugar de relatório, "meus objetivos" no lugar de metas. Tudo o que é regra aparece com o selo "regra do TikTok".
- **Saída sem surpresa.** As regras de saída (antes e depois de 15 dias, espera de 90 dias da plataforma) ficam escritas na Ajuda, no mesmo tom do Playbook.

## Área da gestão (site)

A tela inicial da Anna é a fila do dia: uma lista curta, em ordem de prioridade, com a mensagem pronta para cada criador. O resto do site existe para alimentar essa fila ou para aprofundar um caso.

### Fila do dia

Cada item traz o criador, o motivo ("D10 com 2 dias válidos", "queda de 40% com as horas mantidas"), a mensagem já preenchida com nome e números e um botão que abre a conversa no WhatsApp. Vale a regra de uma mensagem por dia por criador.

A fila guarda as datas fixas que já usamos: D10, D12, D14 e D15; régua de 7, 14, 21 e 30 dias sem LIVE; mural de batalhas na segunda; campanhas na véspera do fechamento. O que não tem data segue o ritmo atual: quedas na segunda e terça, quem está subindo ou irregular na quarta e quinta, batalhas de fim de semana na sexta.

Um item só sai da fila quando acontece uma de três coisas: a Anna enviou, a Anna adiou com motivo, ou o dado mudou (o criador abriu LIVE, por exemplo).

### As outras telas

| Tela | O que tem |
| --- | --- |
| Ficha do criador | Fase, trilha, nicho, tier, 5 semanas de números, sinais, quem recrutou, linha do tempo de tudo o que foi enviado e respondido, notas, plano do último 1:1, principais apoiadores |
| Onboarding | Quadro por dia (chegada, D1 a D15) calculado pela data; alertas do D3, D7, D10, D12, D14 e D15; cadência de não-resposta (+1, +2, +3 no privado, +5 dias) disparada sozinha |
| Radar de graduação | Quem está na janela, diamantes do mês até hoje, ritmo por dia, quanto precisa por dia, projeção e aviso do último mês |
| Batalhas | Pedidos recebidos, sugestão de oponente do mesmo nível dentro da Hera, agenda, confirmação e atualização no modelo oficial, mural da semana gerado, resultado registrado |
| Campanhas | Cadastro com aprovação da Mariana, quem participa de cada uma, o que fecha hoje, ranking por grupo de tier, premiação a entregar |
| 1:1 | Agenda, pauta de 7 blocos já preenchida com os números do criador, plano com 2 a 3 ações, próximo encontro marcado; sem registro, o 1:1 não conta |
| Biblioteca de mensagens | Todos os scripts do Playbook com variáveis, por trilha e nicho, com histórico de versões e um verificador de tom que barra meta, cobrança, prazo, horário e texto só no feminino |
| Pausas e saídas | Régua de reativação, criadores no D15 sem fechar a regra, pedido de decisão à Mariana (manter ou encerrar), motivo de saída |
| Grupo de avisos | Posts programados: mural de batalhas, campanhas que fecham, aulas, destaques da semana |

### Onde a inteligência artificial ajuda

- Preenche o trecho específico da mensagem ("você fez 3 LIVEs em 3 dias") a partir dos dados, para a Anna só revisar.
- Resume a ficha antes de um 1:1 e transforma as anotações em plano de ação.
- Sugere oponentes de batalha pelo histórico de diamantes.
- Nunca envia mensagem de relacionamento sozinha.

## Painel das sócias

O painel mostra, sem ninguém montar nada, se o método está sendo aplicado e se está dando resultado. Ele abre pelos totais da conta inteira, que é sobre o que o TikTok paga, e depois separa a Hera de Lunow e Impulse.

| Bloco | Indicadores | Referência que já usamos |
| --- | --- | --- |
| Resultado do mês | Diamantes da conta e só da Hera até hoje, comparados ao mês anterior; projeção do fechamento | Números de Receita › Incentivos, que incluem o dia de hoje |
| Fechamento | Incentivos da agência, graduações e simulação da compra de moedas | Estudo mensal, pronto antes do último dia |
| Funil do onboarding | Por mês de entrada: entrou, fez a 1ª LIVE, fechou 5 dias e 15 horas, ficou depois do D15, graduou | Regra do TikTok nos primeiros 14 dias |
| Retenção | Taxa de saída nos 15 primeiros dias; removidos por 30 dias sem LIVE; motivos de saída | Abaixo de 10% é bom, acima de 20% é ruim |
| Graduação | Quem bateu 80 mil no mês, quem está no ritmo, quem está no último mês da janela | 80 mil num mês, dentro dos 3 primeiros meses |
| Base por tier | Quantos criadores em cada grupo e quem subiu ou desceu | Bronze T1, Prata T2 e T3, Ouro T4, Diamante T5 ou mais |
| Execução da gestão | Itens da fila concluídos por dia, tempo até o primeiro contato com o novato, respostas recebidas, 1:1 feitos com os principais | 1:1 a cada 30 dias com os principais, sempre com registro |
| Batalhas | Batalhas por semana, batalhas oficiais marcadas e efeito em diamantes | 6 ou mais por semana é bom, menos de 3 é ruim |
| Premiações | Custo por campanha, prêmios a entregar e moedas a comprar | Prêmio em diamantes na LIVE; Pix só de vez em quando |
| Recrutamento | Por recrutadora: quantos entraram, quantos fecharam os 14 dias, quantos graduaram | Qualidade de quem entra, não só quantidade |

As decisões que hoje chegam por mensagem viram uma lista no painel: aprovar campanha, manter ou encerrar um criador no D15, autorizar premiação. A Mariana resolve de onde estiver, e a decisão fica registrada na ficha.

## Mensagens e automações

Toda mensagem nasce de um gatilho (uma data ou um dado), passa por uma regra e chega pronta para a Anna aprovar. Depois do envio, o sistema observa o que aconteceu e só então libera o próximo passo.

1. **Gatilho.** Data de entrada, dia da 1ª LIVE, leitura diária do Backstage, pedido feito no app.
2. **Regra.** As do Playbook e da automação semanal, sem mudança: fase, trilha, nicho, estado da semana, sinais.
3. **Mensagem pronta.** Script certo, com nome e números preenchidos, checado pelo verificador de tom.
4. **Envio pela Anna.** Um toque abre o WhatsApp com o texto. Ela ajusta se quiser.
5. **Confirmação.** O sistema registra o envio e acompanha o resultado: houve LIVE, o criador respondeu no app, ou nada aconteceu.
6. **Próximo passo.** Segue o roteiro, ou entra a cadência de não-resposta.

### O que pode ser automático e o que não pode

| Tipo | Exemplos | Quem envia |
| --- | --- | --- |
| Informativo | Campanha fecha hoje, batalha amanhã, contagem dos 14 dias atualizada, aula nova | O app, por notificação, se o criador deixou ligado |
| Relacionamento | Boas-vindas, retorno depois da LIVE, reconhecimento, apoio, queda, reativação | A Anna, com rascunho pronto |
| Decisão | Encerramento no D15 ou aos 30 dias, mudança de campanha | A Anna, depois do ok da Mariana quando foge da regra |

### O canal: WhatsApp continua, com três níveis

- **Botão que abre a conversa com o texto pronto.** Usa o número e os grupos individuais de hoje. É o mais simples e não muda a relação. O sistema registra o clique, não a entrega.
- **Notificações do próprio app.** Levam o informativo para fora do WhatsApp e deixam a conversa humana mais leve.
- **API oficial do WhatsApp Business.** Permitiria detectar respostas automaticamente. Fora da janela de 24 horas aberta pelo contato, só dá para enviar modelos aprovados pela Meta, e desde 1º de outubro de 2026 as mensagens livres passaram a ser cobradas acima de uma franquia mensal ([Digisac](https://digisac.com.br/blog/janela-de-24-horas-whatsapp)). Também mudaria o formato dos grupos individuais.

Minha recomendação é começar pelos dois primeiros. A confirmação de que a conversa andou vem do dado (a LIVE apareceu) e do check-in do criador no app. A API fica para uma segunda etapa, se ainda fizer falta.

## Dados e integrações

O Backstage é a única fonte dos números, e a leitura dele é a parte mais frágil do sistema. O resto (WhatsApp, Argus, formulários, agenda) se liga em volta.

### Backstage

- **Como lemos hoje.** Dois coletores rodam no navegador com o login da agência e um script monta a semana. Funciona, mas só com o computador da Mariana ligado.
- **Como deve ser.** Leitura diária em um servidor, sem depender de ninguém. Os campos são os que já usamos: diamantes, duração de LIVE, dias válidos, batalhas, novos membros do fã-clube, vídeos novos, data de entrada, última LIVE, seguidores, situação de graduação e tier.
- **Qual número vale.** Diamantes vêm de Receita › Incentivos, que inclui o dia de hoje. "Gerenciar criadores" fica um dia atrás e serve para dias válidos e histórico.
- **O risco.** Não encontrei API pública do TikTok para os dados do Backstage. Um fornecedor de dados de LIVE afirma que o TikTok não oferece API pública para dados de transmissão ([TikTool](https://tik.tools/tiktok-live-api)). A leitura pelo navegador pode quebrar quando a tela mudar.
- **A proteção.** A camada de leitura fica separada do resto e tem um plano B: subir a planilha exportada do Backstage. Vale perguntar ao contato da Hera no TikTok se existe exportação oficial para agências.

### As outras ligações

| Sistema | O que entra ou sai | Observação |
| --- | --- | --- |
| Argus | Quando o recrutamento fecha com alguém, a ficha nasce com @, trilha, nicho e quem recrutou | A trava de 90 dias continua sendo checada antes do convite |
| Formulário de cadastro | A pergunta de experiência com LIVE define a trilha | Passa a ser a primeira tela do app |
| Formulário de Pix | Dados de pagamento só quando há prêmio em dinheiro | Acesso restrito ao financeiro, na conta da Hera |
| WhatsApp | Botão com texto pronto; link de convite do app no grupo individual | API oficial só em uma segunda etapa |
| Agenda | 1:1 e batalhas oficiais com lembrete | Conta Google da Hera |
| Histórico atual | Registros desde outubro de 2026 e as regras da automação semanal | Migram como estão, para não perder o que já foi feito |

### Formato do produto

Um só sistema na web, que abre bem no celular e pode ser instalado na tela inicial sem passar pelas lojas. O criador usa no celular, a gestão no computador. App nas lojas só depois que o uso justificar o custo.

## Cuidados

Três riscos precisam ser tratados no desenho, antes de qualquer tela: o trabalhista, o de dados pessoais e o de dependência do TikTok. Não sou advogado; os dois primeiros pedem revisão jurídica antes do lançamento.

### Risco trabalhista

Um app que mostra horas, dias e lembretes pode ser lido como controle de jornada. O cuidado que a Hera já tem com as palavras precisa virar regra do produto.

- Os números são do criador e aparecem como o negócio dele, não como acompanhamento da Hera.
- Dias de LIVE e objetivos são escolhidos por ele e podem ser mudados ou apagados a qualquer momento.
- Lembretes são opcionais e vêm desligados.
- Nada no app gera punição por parte da Hera. O que tem consequência (14 dias, graduação, espera de 90 dias) aparece como regra do TikTok.
- O verificador de tom vale para as telas, não só para as mensagens.
- O termo de uso deixa clara a relação entre autônomos, sem exclusividade e sem obrigação de horário.

### Dados pessoais

- Cada criador vê só os próprios dados. Rankings mostram apenas o que já é divulgado nos grupos de tier.
- Dados de Pix ficam separados, com acesso só do financeiro, e são pedidos apenas quando há prêmio em dinheiro.
- O cadastro pede consentimento e explica o que é lido do Backstage.
- Quem sai pode pedir a exclusão dos dados.
- Criadores de Lunow e Impulse nunca aparecem para a gestão da Hera além dos totais da conta.

### Dependência do TikTok

- A leitura automatizada do Backstage precisa ser discreta (uma vez por dia) e ter o plano B da planilha.
- O login da agência no Backstage fica guardado com segurança e acesso de pouquíssimas pessoas.
- Regras do TikTok mudam. Tiers, regra dos 14 dias e graduação ficam em uma tela de configuração, não escritos no código.

### Dependência de uma pessoa

Hoje a Anna cuida sozinha de toda a base. O sistema deve permitir dividir a carteira com uma segunda pessoa e passar o histórico completo de um criador sem perda.

## O que eu faria como CEO da Hera

Eu construiria primeiro o que tira trabalho da Anna e confirma que o método está sendo aplicado, e só depois o que encanta o criador. O gargalo da Hera hoje é uma gestora para a base inteira, não a falta de recursos para quem cria.

### A ordem de construção

1. **Base e fila do dia.** Leitura diária do Backstage em servidor, ficha do criador, fila do dia com botão de WhatsApp, quadro de onboarding e biblioteca de mensagens. As regras atuais entram sem mudança. Resultado: a Anna para de copiar e colar, e a Mariana deixa de depender do próprio computador.
2. **App do criador, versão mínima.** Três coisas: Meu progresso (contagem dos 14 dias e janela de 80 mil), pedido de batalha oficial e campanhas do grupo. Entrada por link no grupo individual. Teste com cerca de 10 criadores antes de abrir para todos.
3. **Gestão completa.** Batalhas com agenda e sugestão de oponente, campanhas com aprovação e ranking, 1:1 com pauta e plano, painel das sócias e fechamento do mês.
4. **Crescimento do criador.** Área Aprender por fase e nicho, conquistas, check-in depois da LIVE, apoio de inteligência artificial nos rascunhos.
5. **Produto para outras agências.** Marca neutra, configuração de regras por agência e venda junto com o Argus.

Cada etapa só começa quando a anterior está em uso de verdade pela Anna.

### Construir ou contratar

Já existe no mercado ferramenta que se conecta ao Backstage da agência e dá ao criador uma visão própria, com níveis e assistente de IA ([Devign Agency Suite](https://www.muzahim.devignlb.com/)). Antes de programar, vale comparar a etapa 1 com o que o OGerente e ferramentas desse tipo já entregam.

O que justifica construir é o que só a Hera tem: o motor de fases com o Playbook dentro, as regras de tom, a passagem direta do Argus e o plano de vender o conjunto. Se a ideia fosse apenas ver números do Backstage, contratar sairia mais barato.

### O que eu não faria

- **Chat próprio para substituir o WhatsApp.** O criador já está lá, e a relação também.
- **Mensagens de relacionamento enviadas sozinhas.** O Playbook pede gente no retorno depois da LIVE. Automatizar isso derruba a confiança.
- **App nas lojas logo de início.** Custa caro e atrasa o teste.
- **Ranking geral expondo quem está embaixo.** Rankings ficam dentro do grupo de tier, como hoje.
- **Qualquer mecânica com punição.** Perder pontos ou status por não fazer LIVE contradiz a parceria e aumenta o risco trabalhista.
- **Mudar o método junto com a ferramenta.** Primeiro o sistema reproduz o que já funciona; os ajustes vêm depois, com dado.

### Como saber se deu certo

| Indicador | Hoje | Onde quero chegar |
| --- | --- | --- |
| Novatos que fecham 5 dias e 15 horas em 14 dias | Não medido por mês de entrada | Medido todo mês e em alta |
| Saída nos 15 primeiros dias | Não medido | Abaixo de 10% |
| Graduações por mês | Acompanhadas no radar semanal | Em alta, com radar diário |
| Fila do dia concluída | Sem medida confiável | Acima de 90% dos itens no dia |
| Respostas e 1:1 registrados | 0 e 0 na segunda quinzena de outubro | 1:1 a cada 30 dias com todos os principais |
| Criadores ativos que abrem o app na semana | Não existe | Maioria da base ativa |
| Tempo da Anna em tarefas manuais | Alto, sem medida | Metade do atual, medido por ela |

Os alvos sem número de referência no Playbook são proposta minha e precisam ser validados com a Anna.

## Decisões em aberto

Oito decisões são da Mariana e mudam o desenho ou a ordem de construção.

- [ ] Quem desenvolve: o mesmo desenvolvedor do Argus ou outra pessoa, e com que orçamento?
- [ ] Construir ou contratar: o que o teste do OGerente mostrou sobre a etapa 1?
- [ ] WhatsApp: manter os grupos individuais com botão de texto pronto, ou testar a API oficial já na primeira etapa?
- [ ] Criadores de Lunow e Impulse entram no app, ou só os da Hera?
- [ ] Nome e marca: app da Hera ou marca neutra, pensando na venda para outras agências?
- [ ] Revisão jurídica (trabalhista e dados pessoais): quem faz, e antes de qual etapa?
- [ ] Quais criadores testam primeiro a versão mínima do app?
- [ ] O que a Anna acha da fila do dia? Vale mostrar este documento a ela antes de fechar a etapa 1.

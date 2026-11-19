# Status, custos, riscos e próximos passos

Situação em 18/11/2026: MVP construído; passos 1 a 3 da visão feitos em 11/11; mapeamento do app contra a visão final feito em 14/11; etapa 2 com os passos 2.1 a 2.7 feitos; etapa 3 (app do criador) começada em 15/11, com os passos 3.1 e 3.2 feitos (aguardando aprovação). Falta publicar e fazer o piloto com dados reais.

> **18/11/2026: próximos passos pausados para publicar.** A Mariana pediu para publicar o que já existe, para a gestão começar o teste com dados reais enquanto o app do criador é terminado. O passo a passo está em `docs/COMO_RODAR_E_PUBLICAR.md` (parte B para publicar, parte C para o teste da gestão). Na preparação foi corrigido um defeito que só aparecia em produção: quem tinha papel de sócia ou Conteúdo ficava sem acesso a Configurações e cadastros (`core/apps.py`, teste em `tests/test_publicacao.py`). Durante o teste, nenhum criador recebe código de acesso, e só se envia versão nova ao GitHub quando os testes passam.
>
> **18/11/2026: publicado (parte B concluída).** Endereço: https://hera-hub-production.up.railway.app. Projeto Railway `wonderful-creation` com 3 serviços: `Postgres`, `hera-hub` (o app, conexão interna `postgres.railway.internal`, usuário `hera_app`) e `rotina-diaria` (cron `0 9 * * *` UTC = 6h de Brasília, variáveis por referência ao app). Acesso público do banco desligado depois do `criar_admin`. Conta Admin criada e login conferido. Corrigido no caminho: `criar_usuario_banco` falhava no Postgres real (senha como parâmetro `$1` em `CREATE ROLE`; agora usa `psycopg.sql.Literal`). Próximo: parte C (cadastrar a equipe, importar os dados, carteiras).
>
> **18/11/2026: parte C, passos 1 a 5 feitos.** Primeira gestora cadastrada e entrou; outubro completo e novembro (1 a 17) importados sem erro; carteiras divididas; 5 criadores conferidos contra o Backstage. Falta: rotina de importação diária combinada com a equipe; conferir em 19/11 se o serviço `rotina-diaria` rodou às 6h.

> **19/11/2026: publicada a etapa 3** (passos 3.3 a 3.7, commit `0e4435e`). Deploy no Railway com sucesso; as 13 migrações rodaram sem erro (de `core.0012` a `web.0009`). O serviço `rotina-diaria` mostra "Last run succeeded" e a leitura automática do Backstage chegou às 12h30. O Dashboard de produção abriu com o menu novo "Teste do app". Ninguém recebeu código de acesso; a trava do teste está desligada até as sócias configurarem o teste. Avisos do `check --deploy` que já existiam e não impedem o app de ligar: HSTS e redirecionamento para HTTPS (o Railway já serve por HTTPS).

> **19/11/2026: publicados os passos 4.1 e 4.2** (commit `d1ef474`). Deploy com sucesso; as 3 migrações rodaram sem erro (`crm.0011`, `crm.0012`, `web.0010`). Em produção, o Painel das sócias abriu em menos de 1 segundo com todas as seções, e a tela 1:1 abriu com 7 criadores que precisam de 1:1 todo mês e ainda não têm 1:1 completo.

> ⚠️ **Os logins de demonstração (`@hera.demo` e `@semana.demo`, senha `hera-demo-2026`) não podem existir em produção.** Detalhes na seção 0, "Logins de demonstração não podem existir em produção".

## 0. Plano atual (visão final de 14/11/2026)

A especificação é `docs/hera-app-visao.md`. A versão de 11/11 foi arquivada em `docs/arquivo/`. As regras que valem para tudo estão em `CLAUDE.md`. Cada etapa e cada passo só começa com aprovação da Mariana.

### Etapas da visão

| Etapa | Situação |
| --- | --- |
| 1. Mapear o app atual | ✅ 14/11 (resultado resumido abaixo) |
| 2. Base e fila do dia | Em andamento: passos 1 a 3 de 11/11 feitos; correções e decisões de 14/11 feitas; passos 2.1 a 2.7 feitos (aguardando aprovação) |
| 3. App do criador (Meu progresso como tela inicial, página educacional, pedir batalha, campanha do momento; teste com ~10 criadores) | Em andamento desde 15/11: passos 3.1 e 3.2 feitos (plano dos passos abaixo, em "Etapa 3") |
| 4. Gestão completa (batalhas com agenda, campanhas com aprovação, 1:1 com template novo, premiações, Indique e ganhe, painel das sócias) | Em andamento desde 19/11: passo 4.1 feito (plano dos passos abaixo, em "Etapa 4") |
| 5. Crescimento do criador (conquistas, marco da 1ª LIVE, calculadora "Onde posso chegar", cursos extras, IA nos rascunhos) | A fazer |
| 6. Login para as gestoras de Lunow e Impulse | A fazer |

### Correções feitas em 14/11 (erros encontrados no mapeamento)

| Correção | O que mudou | Como testar |
| --- | --- | --- |
| Quem sai perde o acesso ao app | Antes, o criador com status "saiu" continuava entrando até a anonimização (180 dias). Agora o app mostra "Seu acesso foi encerrado" assim que a saída é registrada (pela ficha ou detectada na importação). Quem está em aviso prévio continua entrando. | Registre a saída de um criador com até 15 dias de casa e entre com o usuário dele |
| Graduação pela regra certa | Antes, a fila somava diamantes de 90 dias (68 a 80 mil). Agora conta os diamantes do mês corrente, só para quem está nos 3 primeiros meses de casa. Os valores (80 mil e 90 dias) ficaram em Configurações da agência. | Fila de ação: aparece "Perto de graduar" para quem está na janela com 85% ou mais de 80 mil no mês |
| Contato só conta com "Enviei" | Antes, clicar no botão do WhatsApp já registrava um contato (o problema de "medir cliques" do diagnóstico de outubro). Agora os botões são "Copiar mensagem", "Abrir grupo" (o grupo individual da ficha; sem link, abre o WhatsApp) e "Enviei". Só o "Enviei" grava o contato e avança a cadência. Depois do "Enviei", o item sai da fila do dia. | Fila de ação e aba Mensagens da ficha |

### Decisões da Mariana em 14/11 (depois do mapeamento) e o que mudou

| Decisão | O que mudou no app | Como testar |
| --- | --- | --- |
| **Remover** a meta individual, a missão da semana e o disparo assistido | Saíram: o quadro "Meta individual" da ficha (o número do criador volta a ser só a referência do TikTok ou, sem ela, o próximo Tier); a tela e o cartão "Missão da semana" do app; o menu "Disparos" da gestão. No lugar da missão, quem está nos primeiros 14 dias vê no Início o cartão "Seus primeiros 14 dias" (regra do TikTok), que abre a tela do Tier. A central de dúvidas não diz mais que a gestão combina um número com o criador. | Entre como `streamer01@hera.demo` e como `gestora1@hera.demo`: os três itens não aparecem mais |
| **Login novo:** código de acesso + e-mail e senha | Na ficha, quadro "Acesso ao app": botão **Gerar código de acesso**. Aparece o código (ex.: `ABCD-2345`), a validade e a mensagem pronta, com "Copiar mensagem", "Abrir grupo" e "Enviei". O criador abre o app, toca em **Primeiro acesso ou senha nova**, informa o @, o código e o e-mail e cria a senha. Depois entra com e-mail e senha. Esqueceu a senha: a gestora gera outro código. Saíram o convite por e-mail, o código por e-mail e o login com Google. | Ficha de um criador sem acesso → Gerar código → abrir `/primeiro-acesso/` em uma janela anônima |
| **Painel das sócias pode mostrar bônus, receita e moedas** | Só documentação por enquanto: a regra do `CLAUDE.md` agora diz que esses valores existem só no painel das sócias (papel Admin: Mariana e Aline). O painel é da etapa 4; até lá as colunas de bônus da planilha Task continuam ignoradas. | — |

**Regras do código de acesso:** vale uma vez; vence em 7 dias (Configurações → Configurações da agência → "validade do código de acesso"); gerar outro cancela o anterior; 5 erros seguidos cancelam o código; quem saiu da agência não recebe código nem entra. Só as sócias e a gestora da carteira veem o código (regra também no banco).

**Decisões pequenas desta rodada:**

| Decisão | Motivo |
| --- | --- |
| O e-mail do criador não é conferido e nunca recupera o acesso (sem código por e-mail, sem "esqueci a senha" por e-mail, sem Google) | Quem informa o e-mail é o próprio criador. Se ele digitar errado, o dono daquele e-mail não pode conseguir entrar no lugar dele. A recuperação é sempre o código enviado pela gestora no grupo |
| A equipe (sócias, gestoras) também entra só com e-mail e senha | Uma tela de entrada só. A senha da equipe é cadastrada pelas sócias em Configurações → Usuários; a da sócia, pelo comando `criar_admin --senha` |
| O app não envia mais nenhum e-mail | O serviço de e-mail (Resend) deixa de ser necessário para publicar (passo 6 do guia) |
| O código fica guardado em texto no banco, em tabela própria com regra de leitura restrita | A mensagem pronta precisa mostrar o código para a gestora copiar; ele vale uma vez e vence |
| Senha com 8 caracteres ou mais, e não pode ser das mais comuns | Antes não havia regra de senha, porque o acesso do criador era por código no e-mail |
| O cartão "Seus primeiros 14 dias" entrou no Início no lugar da missão | Sem a missão, o novato perderia a única contagem da regra do TikTok na tela inicial. Na etapa 3 ele vira o topo do "Meu progresso" |
| A coluna "disparo assistido" dos contatos e a tabela de metas individuais foram apagadas do banco | Não havia nenhum registro nelas |
| Quem entrou pelo código não vê a pergunta "É você? @..." | Já informou o próprio @ junto com o código |

### Etapa 2: passos que faltam

Os passos de 11/11 (4 a 8) foram refeitos com as decisões de 12/11 e 14/11. A etapa 2 traz as regras atuais sem mudar o método.

| Passo | O que entra | Situação |
| --- | --- | --- |
| 2.1 Porta de importação | Endereço para o Claude enviar o arquivo da leitura diária (com chave própria); aviso quando a leitura do dia não chegou; a planilha pela tela continua como plano B | ✅ 14/11, aguardando aprovação (detalhes abaixo) |
| 2.2 Ficha do criador | Fase, trilha (sugerida pelo cadastro, confirmada pela gestão), nicho, dia e mês de aniversário (pedido no primeiro acesso, junto com a pergunta de experiência com LIVE), motivo de quem parou (lista fixa), lembretes com data, "o criador me escreveu", linha do tempo única; "Respondeu" e cada marcação viram linhas novas (nada sobrescrito) | ✅ 14/11, aguardando aprovação (detalhes abaixo; a fase entra no 2.3) |
| 2.3 Motor de fases | Chegada, Novato, Primeiro mês, Graduação, Veterano, Pausa e saída; estado da semana (Queda, Subindo, Sem LIVE, Horas sem retorno, Irregular, Novo, Estável) e os 3 sinais, como na automação semanal; grupos novos (Bronze T1, Prata T2–T3, Ouro T4, Diamante T5+); radar de graduação diário | ✅ 14/11, aguardando aprovação (detalhes abaixo, com o complemento do estado da semana) |
| 2.4 Fila do dia | Ordem em 4 blocos (suporte e restrições → o que tem data → o que vem do dado → rodízio); uma mensagem por dia por criador; relógio de 4 dias sem contato (segunda a sábado); teto de 30 por gestora; domingo sem envios; régua sem LIVE 4, 14, 21 e 30 dias; "Adiar com motivo" no lugar de "dispensar por 7 dias" | ✅ 14/11, aguardando aprovação (detalhes abaixo) |
| 2.5 Quadro de onboarding | Alertas do D3 e do D7; relógio "entrou e não abriu LIVE" (D2, data combinada, D3, D5, D7, D10, D14); travas (passo só depois de "Respondeu" ou do dado); cadência de não-resposta entra sozinha na fila | ✅ 14/11, aguardando aprovação (detalhes abaixo) |
| 2.6 Biblioteca de mensagens | Textos do Playbook palavra por palavra, por trilha e nicho; histórico de versões; verificador de tom aplicado às mensagens; saem os modelos de resumo de números (REL-MES e LEMBRETE-SEMANA) | ✅ 14/11, aguardando aprovação (detalhes abaixo) |
| 2.7 Carteiras | Tela de divisão dos criadores entre gestoras; "Hoje não trabalho" com cobertura por uma sócia ou recrutadora | ✅ 15/11, aguardando aprovação (detalhes abaixo) |

### Passo 2.1, o que mudou (porta de importação)

- **Endereço novo, sem login:** `POST /api/importacao/backstage/`, com a chave no cabeçalho (`Authorization: Bearer hera_...`) e a planilha "Dados do criador" no campo `file`. Responde em JSON: `"ok": true` quando os dados entraram (ou o arquivo era repetido); `"ok": false` com o motivo em `"mensagem"` quando não gravou.
- **Mesmo importador da tela.** A porta usa `data/importer.py`: mesma validação, mesmo "desfazer", mesmo recálculo. O lote fica marcado como "leitura automática" no histórico.
- **Chave por agência, gerada só pelas sócias** em Importar dados → Leitura automática. O texto aparece uma vez; o banco guarda só o resumo. Gerar outra cancela a anterior; "Desligar" cancela sem gerar outra.
- **A porta só grava sozinha leitura limpa.** Com linha com erro, mais de 5 saídas de uma vez, nenhuma linha válida ou período no futuro, o lote fica em pré-visualização, as sócias e as gestoras são avisadas no sininho e o Dashboard mostra "Conferir e gravar". Arquivo ilegível, formato desconhecido ou planilha Task: recusado, com aviso.
- **Aviso de que a leitura não chegou:** com a leitura automática ligada, o Dashboard diz "ainda não chegou (esperada até as 10h)" e, depois das 10h, "não chegou até as 10h. Plano B: suba a planilha".
- **Defeito antigo corrigido no importador:** arquivo só com criadores novos ficava sem período na pré-visualização ("período None a None").

**Como testar o passo 2.1:** entre como `admin@hera.demo` → Importar dados → **Ligar: gerar chave** → copie as instruções. No PowerShell, rode o comando `curl.exe` das instruções apontando para um arquivo da pasta `seeds/`. Um arquivo já importado responde "repetido"; um arquivo novo aparece no Histórico como "leitura automática".

**Decisões pequenas do passo 2.1:**

| Decisão | Motivo |
| --- | --- |
| A chave fica no banco (só o resumo), gerada pela tela, e não em variável do servidor | As sócias trocam a chave sozinhas, sem mexer no Railway; e cada agência tem a sua |
| Leitura com problema fica esperando conferência, em vez de gravar o que der | Na tela, alguém olha a pré-visualização antes de gravar; na porta, ninguém olha. Saída detectada bloqueia o acesso do criador, então várias saídas de uma vez pedem um olho humano |
| Limite de 5 saídas e hora-limite das 10h, os dois em Configurações da agência | Valores de partida, para calibrar com o uso |
| A planilha Task não entra pela porta | O fechamento continua com as sócias e o financeiro |
| O aviso de "não chegou" aparece no Dashboard, sem notificação no sininho | A rotina que cria notificações roda às 6h, antes da leitura; o Dashboard é a tela inicial da gestora. O aviso de 2 dias sem importar continua valendo |
| Avisos de leitura recusada ou em conferência não se repetem no mesmo dia enquanto não forem lidos | Se o envio for repetido várias vezes com o mesmo problema, o sininho não enche |

**O que falta fora do app para a leitura automática funcionar:** a rotina do Claude que abre o Backstage todo dia, exporta "Dados do criador" e envia para a porta (é a rotina que hoje alimenta o Acompanhamento Semanal). E o app publicado: enquanto ele roda só neste computador, a porta só existe com o app ligado aqui.

### Passo 2.2, o que mudou (ficha do criador)

- **Quadro "Cadastro":** trilha (o cadastro do criador sugere, a gestão define), nicho, recrutadora (lista de quem tem o papel Recrutadora: hoje Fernanda e Adrielly), "indicado por" (@ de um criador da Hera, mesmo de outra carteira) e aniversário (dia e mês). Cada troca vira uma nota na linha do tempo. A ficha de quem indicou mostra "Indicou: @...".
- **Primeiro acesso do criador:** depois do termo, uma tela pergunta se já fez LIVE (sugere a trilha) e o dia e mês do aniversário (opcional, sem ano).
- **Linha do tempo única** no lugar de "Notas" e "Contatos recentes": envios, respostas, notas, 1:1, motivos, lembretes, batalhas, saídas e códigos de acesso, com data e autor.
- **"Respondeu" e "O criador me escreveu"** viram linhas novas, com um resumo opcional. Nada é escrito por cima.
- **Lembretes com data:** entram na fila de ação no dia marcado e saem com "Feito".
- **"Parou de fazer LIVE?":** motivo em lista fixa (viagem, saúde, trabalho ou estudo, problema técnico, desmotivou com o porquê, problema pessoal, outra agência, não respondeu, outro), data de volta e observação.
- **Saída:** o motivo da lista passou a ser obrigatório.
- **Aba "Batalhas" (pedido da Mariana em 14/11):** a gestora registra data, oponente, rounds, resultado, diamantes dos dois lados e uma observação para as próximas. Mostra o placar do histórico e os pedidos feitos pelo app. O criador não vê.
- **Defeito antigo corrigido:** os botões da ficha que voltavam para uma aba ("Respondeu", cadência, onboarding) caíam em página de erro; agora voltam para a aba certa.

**Como testar:** entre como `gestora1@hera.demo` → Creators → abra um criador. Para a recrutadora aparecer na lista, a pessoa precisa ter o papel Recrutadora em Configurações → Papéis.

**Decisões pequenas do passo 2.2:**

| Decisão | Motivo |
| --- | --- |
| A fase do criador ainda não aparece na ficha | Ela é calculada pelo motor de fases (passo 2.3) e entra junto com ele |
| Nicho é texto livre por enquanto | A lista de nichos está no Playbook novo e entra no passo 2.6 |
| "Indicado por" aceita criador de outra carteira e mostra só o @ | A indicação cruza carteiras; o @ é público, os dados do outro criador continuam fechados |
| A data de volta fica registrada, mas ainda não silencia alertas | O silêncio até a volta e a mensagem de boas-vindas entram com a régua de 4, 14, 21 e 30 dias (passo 2.4) |
| Marcações do onboarding continuam podendo ser desmarcadas | Cada clique fica no registro de ações (Configurações → Audit logs); o quadro novo é o passo 2.5 |
| O bônus do Indique e ganhe não é calculado | Depende do regulamento (etapa 4); o campo "indicado por" já guarda o dado |

### Passo 2.3, o que mudou (fases, grupos e radar de graduação)

- **Motor de fases** (`data/phases.py`): Chegada, Novato, Primeiro mês, Graduação, Veterano, Pausa e Saída. A fase é calculada na hora, pela data de entrada e pelos dados do Backstage; ninguém marca. Aparece no topo da ficha e na lista de Creators (coluna, filtro e CSV).
  - Chegada: até o D14, enquanto não há nenhum "Enviei" registrado nem LIVE.
  - Novato: até fechar 5 dias válidos e 15h, ou até o D14.
  - Primeiro mês: até o D30. Graduação: até o fim da janela (90 dias). Veterano: depois.
  - Pausa: 4 dias sem LIVE para quem já fez LIVE, quem nunca abriu LIVE depois do D14, ou aviso prévio. A ficha mostra a fase anterior ("antes: Veterano").
- **Grupos da visão:** Bronze T1, Prata T2–T3, Ouro T4, Diamante T5 ou mais. A tela "Meu Tier" do criador e a central de dúvidas leem as faixas de Configurações. O grupo de cada criador é refeito na próxima importação.
- **Radar de graduação** (menu 🚀 Graduação): quem está na janela, diamantes do mês, quanto falta, ritmo por dia, quanto precisa por dia, projeção, aviso de último mês da janela, graduações anteriores, última mensagem e total no mês, próximo 1:1. Atualiza a cada importação. A ficha mostra o mesmo resumo.
- **Não feito: estado da semana, sinais e prioridade.** A visão manda trazer as regras da automação semanal "como estão", e elas não estão neste computador. Entram quando a Mariana trouxer as regras.

**Como testar:** entre como `gestora1@hera.demo` → Creators (coluna e filtro Fase) → abra um criador → menu Graduação.

**Decisões pequenas do passo 2.3:**

| Decisão | Motivo |
| --- | --- |
| A fase não é gravada no banco, é calculada a cada tela | Nunca fica desatualizada e não precisa de rotina |
| "Primeiro contato" da Chegada = primeiro "Enviei" registrado | É o único sinal de contato que o sistema tem |
| A Pausa vale também durante o Novato | A visão diz "de qualquer fase depois da chegada"; os alertas do D10 ao D14 continuam na fila |
| Limite da Pausa (4 dias) em Configurações da agência | Regra de contato da visão; pode mudar |
| A janela de graduação conta 90 dias corridos da entrada | Já era assim na fila; "3 primeiros meses" da visão |
| O alerta "sem LIVE" da fila continua em 7 dias | A régua de 4, 14, 21 e 30 dias é o passo 2.4 |

### Passo 2.3, complemento (estado da semana, segmento, prioridade e sinais)

As regras chegaram em `docs/regras-estado-prioridade.md` (extraídas do script do Acompanhamento Semanal) e entraram como estão, em `data/states.py`:

- **Estado da semana**, na ordem do script: Inativo 30d+, Sem LIVE, Queda, Subindo, Novo, Horas sem retorno, Irregular, Estável.
- **Segmento** (Top, Médio, Desenvolvimento, Base), pelo maior entre o mês anterior e a projeção do mês. **Não é o grupo** (Bronze, Prata, Ouro, Diamante): o segmento prioriza a fila, o grupo serve às campanhas internas.
- **Prioridade 1, 2 e 3** e os **sinais** (quase sem batalhas, fã-clube parado, N dias válidos).
- **Faixas de graduação** do script no radar: Conferir graduação, Bateu a marca, No ritmo, Precisa acelerar, Difícil no mês, No radar, Em formação. **Potencial de graduação** (1:1 mensal) = No ritmo e Precisa acelerar.
- Aparecem na ficha (linha "Semana / Segmento / Prioridade / sinais") e em cada item da fila.

| Diferença para o script | Motivo |
| --- | --- |
| O sinal "Sem vídeos" não é calculado | A exportação "Dados do criador" não traz a coluna de vídeos novos |
| "Dias sem LIVE" sai do último dia com LIVE nos dados importados | O app não recebe a data da última LIVE |
| As semanas saem da diferença entre importações | Com importação diária, fica igual ao script; com buracos de vários dias, os dias do buraco caem na semana em que a importação voltou |

### Passo 2.4, o que mudou (fila do dia)

- **Ordem em 4 blocos:** 1. suporte e pedidos; 2. o que tem data; 3. o que vem do dado; 4. rodízio.
- **Uma mensagem por dia por criador.** Vale a primeira pela ordem da fila; as outras esperam o próximo dia livre. Quem já recebeu um "Enviei" hoje não aparece de novo.
- **Rodízio:** quem fica 4 dias (segunda a sábado) sem mensagem individual entra na fila. A mensagem é escolhida pelo que há de novo (app, próxima aula, campanha aberta, pergunta aberta), sem repetir o modelo da última vez. Novatos (até o D14) e quem está na régua sem LIVE ficam fora do rodízio.
- **Teto de 30 mensagens por gestora por dia.** O que passa fica para amanhã, começando pelo rodízio; o painel mostra quantas ficaram.
- **Domingo sem envios:** ficam só dúvidas e pedidos.
- **Régua sem LIVE em 4, 14, 21 e 30 dias** (no lugar do alerta de 7 dias). No 4º dia, pergunta aberta; no 30º, pedido de decisão às sócias. Se o criador informou data de volta, silêncio até lá; chegou a data sem LIVE, mensagem de boas-vindas de volta.
- **Do dado:** Queda (desde segunda, com o diagnóstico "caíram as horas ou os dias" antes de qualquer outra coisa), Subindo e Irregular (a partir de quarta).
- **Com data:** regra dos 14 dias em risco, cadência de não-resposta, aniversário (no dia e 30 dias antes), batalha oficial em até 4 dias (checklist), lembretes, 1:1 atrasado.
- **"Adiar com motivo"** no lugar de "dispensar por 7 dias": motivo obrigatório, volta na data escolhida e fica na linha do tempo.
- **13 modelos de mensagem novos**, com textos provisórios até o Playbook entrar: régua (4), boas-vindas de volta, queda com horas mantidas, reconhecimento, aniversário (2) e rodízio (4). **No passo 2.6 entraram os textos do Playbook; continuam provisórios só o de 14 dias sem LIVE, o de queda e o de reconhecimento.**

**Como testar:** entre como `gestora1@hera.demo` → Dashboard. Com os dados de demonstração (até setembro) quase todos aparecem como inativos; a fila fica realista depois de uma importação atual.

**Decisões pequenas dos passos 2.3 (complemento) e 2.4:**

| Decisão | Motivo |
| --- | --- |
| "Caíram as horas ou os dias" = semana 30% abaixo da mediana das 3 anteriores | Mesmo corte de 30% da queda de diamantes; o script não define esse número |
| O convite de aniversário fica na fila de 30 a 24 dias antes | Se a gestora não enviar no dia exato, o item não se perde |
| Limites (4 dias, teto de 30, régua 4/14/21/30) em Configurações da agência | A visão manda calibrar o teto com a Anna depois de duas semanas |
| O teto conta por gestora da carteira | Cada gestora tem o seu limite |
| Itens de mensagem sem "Enviei" continuam na fila nos dias seguintes | Regra da visão: só sai com "Enviei", adiamento ou mudança no dado |

**Não entrou no 2.4 (itens da "Rotina diária e agenda do mês" que dependem de outras partes):** restrição ou banimento (depende do aviso no app, etapa 3), sugestão de visita, acompanhamento de campanha e véspera do fechamento (dependem da leitura de campanhas), rodada de batalhas do dia 8, resumo do mês, lista "Quase lá", nível novo e módulo de curso concluído. O relógio de "entrou e não abriu LIVE" é o passo 2.5. A cobertura de ausência ("Hoje não trabalho") é o passo 2.7.

### Ajustes de 14/11 à noite (regras v2, tabela de tipos, restrição, visita) e passo 2.5

**Regras v2.** `docs/regras-estado-prioridade.md` foi substituído pela versão com os cortes do diagnóstico de queda. No código: horas caíram = abaixo de 0,7 × a **média** das 3 semanas anteriores; dias caíram = 2 dias válidos a menos que a média; basta um dos dois. Diamantes continuam com **mediana**, de propósito.

**Conferência com a semana real.** O comando `python manage.py demo_semana --arquivo "..\exemplo-semana.json"` carrega a semana de 02 a 08/11 (81 criadores, números reais, nomes trocados) numa agência de demonstração separada (`semana-demo`, logins `admin@semana.demo` e `gestora.a@semana.demo` até `gestora.e@semana.demo`, senha `hera-demo-2026`). O arquivo fica **fora** do repositório, em `HERA\creator-hub\`. Resultado: estado, segmento e prioridade do app iguais aos do script em **80 de 81** criadores. A diferença é um criador que abriu uma LIVE sem horas registradas: o script sabe pela data da última LIVE, que o app não recebe.

**Fila com a semana real (segunda 09/11, sem nenhum contato registrado antes):** 72 mensagens (29 da régua sem LIVE, 31 do rodízio, 5 quedas, 7 de onboarding) e 13 sugestões de visita. Com as carteiras do arquivo, a maior gestora fica com 26, abaixo do teto de 30. Se uma gestora só cuidasse dos 81, 42 passariam do teto no primeiro dia e o acumulado levaria 3 dias para zerar. Depois do primeiro ciclo, o rodízio espalha os contatos (81 criadores ÷ 4 dias ≈ 20 por dia).

**Tabela de tipos da fila.** `web/services.py:ITEM_TYPES` declara todos os tipos de item, com o bloco de cada um, inclusive os que ainda não geram nada (campanha, rodada do dia 8, resumo do mês, Quase lá, nível novo, módulo concluído). `COLLECTORS` diz quem gera cada tipo. Tipo novo = uma linha em cada tabela; ordenação, teto, domingo e "uma por dia" não mudam.

**Restrição ou banimento.** Quadro na ficha para abrir e encerrar o caso. Com o caso aberto, o criador fica no bloco 1 da fila todo dia (também no domingo), com os passos e o número do dia. No 4º dia sem solução (configurável), a rotina diária avisa as sócias e a ficha mostra "com as sócias".

**Sugestão de visita.** Até 3 por gestora por dia, nesta ordem: queda de prioridade 1, novato nos 5 primeiros dias de LIVE, grupo Diamante, potencial de graduação, 14 dias ou mais sem visita. Sempre com o motivo. "Visitei" na ficha, com nota de 1 a 3. É tarefa, não gasta a mensagem do dia. Quem está sem LIVE não é sugerido; quem recebeu visita nos últimos 7 dias também não.

**Passo 2.5 (quadro de onboarding).** Entrou como o tipo "onboarding" da fila:
- **Entrou e ainda não abriu LIVE:** D1 boas-vindas e convite para o app; D2 regra dos 14 dias (sempre) e combinar a data, que fica na ficha; data combinada que passou sem LIVE (apoio e, no dia seguinte, "tá tudo bem?"); D3 apoio; D5 entender o motivo, com aviso a quem recrutou; D7 mensagem transparente; D10 último dia possível, com aviso às sócias; D11 a D14 pedido de encerramento às sócias.
- **Quem já abriu LIVE:** conferências do D3 e do D7, regra em risco do D10 ao D14, reconhecimento ao fechar a regra, conversa de evolução no D15.
- **Trava da não-resposta:** mensagem sem "Respondeu" e sem LIVE depois dela puxa a cadência (+24h, +2d, +3d, +5d) sozinha. "Respondeu" ou uma LIVE encerram.
- **Quadro de Onboarding:** nova coluna "Próximo passo" e a situação da 1ª LIVE (feita, combinada ou sem LIVE).
- 4 modelos novos para quem não abriu LIVE (D3, D5, D7, D10), com texto provisório. **Trocados pelos textos do Playbook no passo 2.6.**

**Decisões pequenas:**

| Decisão | Motivo |
| --- | --- |
| A semana real fica fora do repositório e numa agência separada | Regra do projeto: nenhum dado real no código; e nada se mistura com os dados principais |
| Os nomes das gestoras do arquivo viram "Gestora A" a "Gestora E" | São nomes reais |
| Visita: quem foi visitado há menos de 7 dias não é sugerido de novo | A visão não define; evita sugerir a mesma pessoa todo dia |
| O roteiro do D1 ao D15 mostra um passo por dia, o mais adiantado ainda não enviado | Regra de uma mensagem por dia; o roteiro completo por trilha e nicho vem do Playbook (2.6) |
| ~~A cadência automática vale só no onboarding (até o D15)~~ **Mudou no 2.6:** vale para a carteira inteira | Decisão da Mariana: depois do D15 a cadência é acionada pela régua de sem LIVE (ver o passo 2.6) |
| O aviso do D10 "no caminho" não existe como item separado | Pelo motor, no D10 quem não fechou a regra já está em risco |

### Passo 2.6, o que mudou (biblioteca de mensagens)

O Playbook do Gestor (revisão de novembro de 2026) está em `docs/playbook-gestor-hera.md`. É a fonte dos textos.

- **Biblioteca com 88 mensagens** (79 scripts e 9 variações), palavra por palavra: 65 do Playbook, 19 do roteiro online (as variações por trilha e por "faz batalha", a estratégia de quem já tem nível e público e as mensagens de batalha oficial) e 4 **provisórias**, que o Playbook não traz.
- **Tela nova: Gestão → 💬 Mensagens.** Mostra tudo por etapa, com busca, filtro por trilha, as variações, as variáveis de cada texto e o guia de ajustes por nicho (5 nichos). Toda a equipe lê. **Só as sócias e quem tem o papel Conteúdo editam.**
- **Histórico de versões.** Cada mudança guarda o texto anterior, com data e quem trocou. Dá para restaurar uma versão antiga. Nada é sobrescrito.
- **Verificador de tom nas mensagens.** Não deixa salvar texto com "meta", "cobrança", "prazo", "horário" (menos "horário de Brasília") ou escrito só no feminino ("bem-vinda", "pronta").
- **Variação certa para cada criador.** A ficha ganhou "Nicho" (lista dos 5 do Playbook) e "Faz batalha?". A fila e a aba Mensagens da ficha escolhem sozinhas a versão da trilha do criador e a versão "sem batalha". A aba Mensagens virou "Roteiro deste criador": mostra a trilha, os ajustes do nicho e marca o que é de outra trilha.
- **Saíram** os modelos de resumo de números pelo WhatsApp (REL-MES e LEMBRETE-SEMANA) e a mensagem provisória do D3.
- **As 4 provisórias de "Entrou e ainda não abriu LIVE"** foram trocadas pelos textos do Playbook (D5, D7, D10 e encerramento até o D14). O D3 usa a mensagem de apoio do roteiro.
- **Roteiro do D10 ao D15 como no Playbook:** D10 "no caminho" (3 dias válidos ou mais) ou "uma ajudinha com a contagem" (0 a 2); D12 e D13 reforço, ou transparência com 0 a 2 dias válidos e sem LIVE desde o D10; D14 reconhecimento ou acolhimento; D15 conversa de evolução ou encerramento com aprovação das sócias.
- **Cadência de não-resposta na carteira inteira.** No onboarding ela entra depois de qualquer mensagem do roteiro sem resposta. Depois do D15, entra depois da pergunta aberta do 4º dia sem LIVE (e do contato dos 14 dias): +24h, +2 dias, +3 dias no privado, +5 dias. Depois do +5 dias sem resposta, a fila pede para a gestora acionar quem recrutou, e a rotina diária avisa a recrutadora. "Respondeu" ou uma LIVE encerram.
- **Visita, as duas pontas:** quem recebeu visita há menos de 7 dias não é sugerido; quem está há 14 dias ou mais sem visita registrada entra na lista. Agora com teste.
- **Semana sintética para os testes:** `tests/fixtures/semana-sintetica.json`, 10 criadores inventados, um de cada estado. Os testes não dependem mais de arquivo de fora. A semana real continua fora do repositório.

**Como testar:** entre como `admin@hera.demo` → 💬 Mensagens → abra uma mensagem, mude o texto, salve e veja o histórico. Tente salvar um texto com "horário": a tela barra. Na ficha de um criador, mude a trilha e o "Faz batalha?" e abra a aba Mensagens.

**Conferência depois da mudança (15/11):** 168 testes passando e 1 pulado (o da tela do criador em 375px, que precisa do Playwright instalado; já era pulado antes). As telas novas foram conferidas pelos testes, não abertas no navegador. Semana real recarregada: 80 de 81 criadores iguais ao script (a mesma diferença de antes). Fila da segunda 09/11: 73 mensagens e 13 sugestões de visita; todas as mensagens com texto pronto e nenhuma variável sem preencher; maior carteira com 27, abaixo do teto de 30.

**Decisões pequenas do 2.6:**

| Decisão | Motivo |
| --- | --- |
| A trilha "Primeira LIVE" usa o modelo geral; as outras trilhas têm variação só onde o roteiro muda o texto | É assim que o Playbook e o roteiro estão escritos |
| Sem trilha definida pela gestão, vale a trilha sugerida pelo cadastro | A gestora não fica sem roteiro enquanto não confirma a trilha |
| Texto editado pela Hera nunca é trocado ao preparar a agência de novo; só a carga de uma revisão do Playbook troca, e guarda a versão anterior | Edição da Hera não pode se perder |
| Os textos do Playbook que o verificador barraria entraram como estão, marcados com alerta na tela | Fidelidade ao Playbook; a decisão de mudar o texto é da Mariana (lista abaixo) |
| Fora do onboarding, o item da cadência avisa "ajuste antes de enviar" | Os textos da cadência falam com quem está chegando ("o vídeo abriu?") |
| Depois do +5 dias, "acionar quem recrutou" é tarefa na fila (do dia seguinte até 6 dias depois), não mensagem ao criador | A conversa é entre a gestora e a recrutadora |
| O app não liga em produção se achar login de demonstração no banco (trava `hera.E002`) | A senha desses logins é pública |

### Passo 2.7, o que mudou (carteiras e "Hoje não trabalho")

**Tela nova: Gestão → 🗂️ Carteiras (só as sócias).**

- **Uma linha por gestora:** tamanho da carteira, quantos estão em onboarding, mensagens na fila de hoje (e quantas passaram do teto), quem cobre, se trabalha hoje e os dias sem trabalhar no mês.
- **Mover criadores:** filtre por carteira (ou "Sem gestora"), marque os criadores, escolha o destino e clique em Mover. Dá para mover vários de uma vez, e também tirar da carteira ("Sem gestora").
- **A troca leva o histórico junto.** Mensagens, respostas, notas e 1:1 pertencem ao criador: a nova gestora passa a ver tudo e a anterior deixa de ver, na tela e no banco. A troca aparece na linha do tempo da ficha, com quem fez. As duas gestoras recebem um aviso no app.
- **Quem cobre:** as sócias escolhem, para cada gestora, uma sócia ou uma recrutadora. Sem escolha, cobrem as sócias.
- **Últimas trocas:** lista com data, quem moveu, quantos e de onde vieram.

**"Hoje não trabalho" (no Dashboard da gestora).**

- A gestora confirma e a fila dela sai da tela. **Os itens passam para o dia seguinte, na mesma ordem.** Nada é perdido: um item só sai com "Enviei", adiamento ou mudança no dado.
- **O que não pode esperar vai para quem cobre:** D10, D12, D14, encerramento, batalha oficial e restrição. Aparece no Dashboard de quem cobre, no quadro "Cobertura de hoje".
- **Quem cobre** envia a mensagem, marca "Enviei", registra a resposta e anota. Não edita cadastro, não registra saída, não adia item e não vê o código de acesso ao app. Enxerga a carteira **só naquele dia**; no dia seguinte o acesso some sozinho.
- **As sócias** são avisadas, veem o quadro de cobertura mesmo quando quem cobre é a recrutadora, e podem marcar ou desfazer a ausência de uma gestora na tela Carteiras (para hoje ou para um dia que ainda vai chegar).
- **"Voltei: vou trabalhar hoje"** desfaz o aviso e encerra a cobertura na hora. O registro fica guardado.
- **Dias sem trabalhar no mês** aparecem na tela Carteiras, por gestora. Ausência desfeita não conta.

**Como testar** (agência `hera.demo`): entre como `admin@hera.demo` → 🗂️ Carteiras → em "Quem cobre" da Ana Gestora, escolha Rita Recrutadora e salve. Entre como `gestora1@hera.demo` → Dashboard → "Hoje não trabalho" → confirmar. Entre como `recrutadora@hera.demo`: o quadro "Cobertura de hoje" aparece no Dashboard. Volte como `gestora1@hera.demo` e clique em "Voltei".

**Conferência (15/11):** 180 testes passando e 1 pulado (o mesmo de antes). As telas novas abriram no servidor local com os logins de demonstração; os cliques (mover, avisar ausência, cobrir) foram conferidos pelos testes, não à mão no navegador.

**Decisões pequenas do 2.7:**

| Decisão | Motivo |
| --- | --- |
| Quem escolhe quem cobre são as sócias, não a gestora | É essa escolha que dá acesso à carteira. A regra vale também no banco: a gestora só consegue marcar a própria ausência de hoje, com quem as sócias definiram |
| Quem cobre enxerga a carteira inteira da gestora ausente naquele dia, mas o Dashboard mostra só o que não pode esperar | Os itens urgentes mudam ao longo do dia (uma restrição nova, uma leitura nova). Travar o acesso só nos criadores urgentes faria quem cobre perder a ficha logo depois do "Enviei" |
| Quem cobre só registra contato (Enviei, Respondeu, nota) | O mínimo para cumprir o item. Cadastro, saída, adiamento e código de acesso continuam com a gestora e as sócias |
| "Encerramento" que não pode esperar é o do onboarding (até o D14 e o D15) | É onde um dia faz diferença: até o D14 o criador pode voltar sem espera. O encerramento dos 30 dias sem LIVE espera a gestora voltar |
| O reconhecimento de quem fechou a regra só é urgente a partir do D14 | Antes disso, um dia de espera não muda nada |
| Batalha oficial urgente = batalha aprovada nos próximos 4 dias (o checklist) | O pedido de batalha ainda pendente espera a gestora |
| Quem cobre é sócia ou recrutadora; outra gestora não cobre | É o que a visão diz. Se a Hera quiser, é uma linha de configuração |
| A ausência é por dia. Para ausência longa, as sócias passam os criadores para outra carteira | A visão fala em "pular um dia"; em vários dias seguidos os itens comuns se acumulariam sem ninguém cuidar |
| O "dia" da ausência é o dia de Brasília | É o dia de trabalho da gestora. A fila continua contando pelo dia do TikTok, que vira às 21h |
| A ausência marcada no domingo conta como dia sem trabalhar | A fila de domingo já não traz envios; o botão continua disponível para os pedidos e as restrições |
| Na ficha, o quadro Carteira só lista gestoras com o papel ativo | Não dá para mandar criador para quem não é mais gestora |

### Etapa 3: app do criador (plano dos passos)

Pedida pela Mariana em 15/11. A visão diz que cada etapa começa quando a anterior está em uso de verdade; a etapa 2 ainda não foi publicada, então a etapa 3 está sendo construída em paralelo e o teste com cerca de 10 criadores fica para depois da publicação.

| Passo | O que entra | Situação |
| --- | --- | --- |
| 3.1 Meu progresso | A tela inicial do app: topo que muda com a fase (contagem dos 14 dias ou Meu nível), frase do mês, "No seu ritmo", graduação, campanha do momento, pedir batalha, semanas do mês com a mais fraca destacada, aula recomendada e meses desde a entrada. "Tier" vira "Nível" no app. Saem "Acelerar" e "precisa/dia" | ✅ 15/11, aguardando aprovação (detalhes abaixo) |
| 3.2 Página educacional (Hera Academy) | Módulos 1 a 7 que abrem por nível e por marco ("abre no Nível 3", "abre depois da sua 1ª LIVE"), liberação antes da hora pela gestão, sem "obrigatória", aula recomendada pelo ponto mais fraco do mês e a escolha da gestora na ficha | ✅ 18/11, aguardando aprovação (detalhes abaixo) |
| 3.3 Batalha oficial | Pedido pelo modelo oficial, com os 7 dias de antecedência; confirmação e checklist do dia no app; histórico | ✅ 18/11, aguardando aprovação (detalhes abaixo) |
| 3.4 Campanhas | Lista só das campanhas em que o criador participa, com a regra resumida e o botão para o TikTok; campanha do momento escolhida por criador (a nota por encaixe, chance, prêmio e esforço depende da leitura de campanhas) | ✅ 18/11, aguardando aprovação (detalhes abaixo); falta ligar a leitura automática no Claude |
| 3.5 Ajuda | Dúvidas com as palavras novas (Nível), pedido de conversa, aviso de restrição ou banimento (abre o caso e vai para o topo da fila), regras de saída e os casos de inelegibilidade | ✅ 18/11, aguardando aprovação (detalhes abaixo; textos da central em revisão pela Mariana) |
| 3.6 Meu plano | Dias de LIVE que o criador escolhe, objetivos dele e lembretes desligados por padrão | ✅ 19/11, acesso pelo cartão da tela inicial e pelo Perfil (decisão da Mariana) (detalhes abaixo) |
| 3.7 Teste com 5 criadores | Lista de quem testa, roteiro do teste e a medida de quem abriu o app na semana | ✅ 19/11 no app; roteiro em revisão pela Mariana; o teste em si depende da publicação e dos vídeos (detalhes abaixo) |

Ficam para as etapas seguintes, como diz a visão: simulador "Onde posso chegar", marco da 1ª LIVE e conquistas (etapa 5); Indique e ganhe, premiação e mural de vagas de batalha (etapa 4); notificação push.

### Passo 3.1, o que mudou (Meu progresso, a tela inicial)

O app agora abre em **Meu progresso**. A tela Desempenho foi unida a ela (o endereço antigo leva para lá).

De cima para baixo:

1. **Topo, que muda com a fase.** Do D1 ao D14, sem a regra fechada: a contagem dos 14 dias (dias válidos e tempo de LIVE), com o selo "regra do TikTok", a data em que a contagem termina e o próximo passo. Daí em diante: **Meu nível**, o próximo nível com a faixa de diamantes, quanto falta e os números do mês.
2. **A frase do mês**, uma linha só, nas três versões da visão: no ritmo de subir de nível; perto, faltando pouco; abaixo do mês passado (o fato e o convite para a aula).
3. **No seu ritmo:** "Mantendo esse ritmo, você fecha o mês em torno de X 💎", sempre com "Estimativa pelo seu histórico, não é garantia".
4. **Graduação** (depois do D30, com a janela aberta): diamantes do mês contra os 80 mil, quanto falta, o ritmo por dia e quantos meses restam, com o selo "regra do TikTok".
5. **Campanha do momento:** uma só. Abre no TikTok.
6. **Pedir batalha oficial.**
7. **Semanas deste mês**, com a mais fraca destacada e o motivo ao lado ("menos dias de LIVE que na sua melhor semana"). A semana em andamento não é comparada.
8. **Aula recomendada.**
9. **Meses desde a entrada**, com os diamantes e o nível de cada mês e o melhor mês em dourado.

Também mudou:

- **"Tier" virou "Nível" em todo o app do criador.** A tela "Meu nível" mostra a faixa de diamantes de cada nível e os grupos. Na gestão continua "Tier".
- **Saíram** "Acelerar", "precisa/dia", a porcentagem "do caminho" e as barras de horas e de dias com alvo. A tela mostra fatos; a única projeção é a do ritmo, como estimativa.
- **"Dados até dd/mm"** e a hora da última atualização no alto da tela.
- **Barra de baixo:** Início, Academy, Campanhas, Batalhas e Dúvidas. Avisos, Benefícios e Pesquisa ficaram no fim da tela inicial.

**Como testar:** entre como `streamer01@hera.demo`. Para ver a contagem dos 14 dias, use um criador que entrou há menos de 14 dias.

**Conferência (15/11):** 191 testes passando e 1 pulado (o mesmo de antes). A tela foi montada, sem erro e sem palavra vetada, para os 442 criadores do banco local (430 com o nível no topo, 12 com a contagem; 69 com o quadro de graduação). Não foi aberta no navegador nem conferida em 375px: o servidor local foi desligado pelo sistema por falta de memória e o teste de largura precisa do Playwright.

**Conferência no navegador (18/11):** aberta no Chrome como `streamer01@hera.demo`, com a página limitada a 375px de largura: nada passa da borda, os cartões aparecem certos (Meu nível, Pedir batalha oficial, Aula recomendada, Meses desde a entrada, Avisos e Benefícios) e a barra de baixo cabe inteira. Não foi conferida a contagem dos 14 dias nem o quadro de graduação no navegador. Na mesma data foi corrigido o "modo aplicativo" (PWA): ele guardava o arquivo de estilos para sempre e mostrava telas sem o visual depois de uma atualização; agora busca sempre o arquivo novo e só usa a cópia guardada sem internet (`web/views_streamer.py`, `SW`, cache `hera-v2`).

**Decisões pequenas do 3.1:**

| Decisão | Motivo |
| --- | --- |
| "Perto, faltando pouco" = 85% ou mais da marca do próximo nível | Mesmo corte que a fila da gestão usa em "perto do próximo Tier" (configurável) |
| "Abaixo do mês passado" compara com o mesmo ponto do mês passado; olha as horas e depois os dias | Primeiro cai a LIVE, depois o diamante |
| Quem já passou da marca do próximo nível vê a faixa do grupo novo ("Seus diamantes deste mês já estão na faixa do grupo Ouro. A troca de grupo acontece no fechamento do mês.") ou, se o grupo não muda, a faixa do nível | Decisão da Mariana de 18/11: forma neutra, avisando a troca de grupo. É fato: os diamantes do mês só sobem até o fechamento |
| "No seu ritmo" só aparece a partir do 3º dia do mês e arredonda o número | Nos dois primeiros dias a conta não diz nada; "em torno de" não pode parecer conta exata |
| Nos 14 dias, a tela não mostra frase do mês nem projeção | A visão: o criador ainda não tem número para mostrar |
| A campanha do momento é, por enquanto, a que fecha primeiro entre as que valem para o criador | A escolha por encaixe, chance, prêmio e esforço depende da leitura de campanhas, que ainda não chega |
| A aula recomendada é, por enquanto, a próxima aula não assistida | A escolha pelo ponto mais fraco e a troca pela gestora entram no passo 3.2 |
| Avisos, Benefícios, Pesquisa e a dica do dia continuam, no fim da tela | Não estão na visão, mas já existem; tirar é decisão da Mariana |
| O simulador e o botão Indique e ganhe não entraram | São das etapas 5 e 4 da visão |

### Passo 3.2, o que mudou (Hera Academy, a página educacional)

O nome escolhido pela Mariana em 18/11 é **Hera Academy**. A página mostra os módulos na ordem e cada um abre por nível ou por marco, como na tabela da visão:

| Quando abre (`Course.opens_on`) | Módulos na demonstração |
| --- | --- |
| No primeiro acesso | 1. Começar · 2. Primeiros 14 dias · 3. Interação |
| Depois da 1ª LIVE | 4. Batalhas |
| Ao fechar os 14 dias, ou no D15 | 5. Rotina e crescimento · 6. Nível e monetização |
| Ao chegar a um nível | 7. Estratégia avançada (Nível 3) |
| Só com liberação da gestão | Cursos extras |

- **Quem chega ao Nível 3 abre tudo**, inclusive quem vem de outra agência (o nível pode ser configurado em Configurações da agência, "Hera Academy: nível que abre todos os módulos"). Cursos extras continuam só com liberação.
- **O que não abriu diz quando abre:** "Abre depois da sua 1ª LIVE.", "Abre quando os seus primeiros 14 dias terminarem.", "Abre no Nível 3." Uma aula fechada aberta por um link (de uma dúvida, por exemplo) volta para a Hera Academy com o motivo.
- **Saiu "obrigatória"** do app, da ficha e do cadastro das aulas. A tela de boas-vindas diz "Sua primeira aula".
- **Na ficha (aba Visão), quadro "Hera Academy":** a aula que aparece no app (com o motivo da sugestão), a escolha da gestora, os módulos com a situação de cada um e o botão **Liberar agora** (e **Desfazer**), e as aulas assistidas. Liberar ou escolher aula vira nota na linha do tempo e manda um aviso para o criador no app.
- **Aula recomendada**, nesta ordem: a escolha da gestora; o ponto mais fraco do mês comparado com o mesmo ponto do mês passado (rotina, batalhas ou, com a rotina mantida, interação); a próxima aula aberta que ainda não foi vista. Cada aula diz qual ponto ajuda (campo "ponto que a aula ajuda", no cadastro da aula).
- O botão "Entenda a batalha oficial" da tela Pedir batalha só aparece quando a aula já abriu para o criador.
- Central de dúvidas: a categoria "Academy" virou "Hera Academy" e entrou a pergunta "Por que um módulo ainda não abriu?".

**Onde cadastrar:** menu **Hera Academy** da gestão (cada módulo tem "quando abre" e, se for por nível, "nível que abre"; cada aula tem "ponto que a aula ajuda").

**Como testar:** entre como `streamer01@hera.demo` e abra Academy na barra de baixo (o módulo 7 aparece com "Abre no Nível 3."). Depois entre como `gestora2@hera.demo`, abra a ficha de @bia.show001.demo, quadro "Hera Academy", e use **Liberar agora** ou escolha uma aula.

**Conferência (18/11):** 210 testes passando e 1 pulado (o mesmo de antes), 18 deles novos (`tests/test_academy.py`, com isolamento no banco). A Hera Academy e a tela inicial abriram sem erro e sem palavra vetada para os 13 criadores de demonstração com acesso. Aberta no Chrome com 375px de largura: nada passa da borda. A ficha foi aberta como gestora. O botão Liberar foi testado pelos testes automáticos, não clicado no navegador.

**Decisões pequenas do 3.2:**

| Decisão | Motivo |
| --- | --- |
| Na barra de baixo o nome fica "Academy"; o título da página é "Hera Academy" | "Hera Academy" quebra em duas linhas em 375px e desalinha a barra |
| O nível que abre módulo é o maior entre o mês fechado e o mês corrente | A visão diz "Nível 3 (80 mil no mês)": quem bate 80 mil no mês abre na hora, sem esperar o fechamento. Não muda o Tier oficial, que continua sendo o do mês fechado |
| A 1ª LIVE conta pelo dado (algum tempo de LIVE ou dia válido no Backstage) | Mesma fonte única do resto do app |
| Curso extra sem liberação não aparece para o criador | É por nicho; mostrar "só com liberação" para todos pareceria porta fechada |
| A gestora só escolhe aula de módulo que já abriu para o criador | Para indicar aula de módulo fechado, libera o módulo antes. Assim o app nunca mostra uma aula que o criador não consegue abrir |
| Quem cobre a carteira ("Hoje não trabalho") não libera módulo nem escolhe aula | Quem cobre só registra contato (regra do passo 2.7) |
| Fã-clube ainda não entra no "ponto mais fraco" | O mês fechado não guarda fãs novos. Aulas de fã-clube aparecem pela escolha da gestora ou como próxima aula |
| Os módulos antigos de demonstração ("Comece por aqui" e "Crescer com constância") viraram os 7 módulos da visão | As aulas mudaram de módulo sem perder o que já foi assistido |

**Falta (depende da Hera):** os vídeos de verdade. Os links da demonstração são `example.com`. A ordem dos vídeos e quem grava estão nos itens "Em aberto" da visão.

### Passo 3.3, o que mudou (Batalha oficial)

**No app do criador:**

- **Pedir batalha oficial** segue o modelo oficial do roteiro (BAT-PEDIDO): 1ª e 2ª opção de data, a hora em que começa, rounds (1, 3 ou tanto faz), quantos diamantes quer fazer (em branco, a Hera sugere pelo histórico), se pode ser com criador de outra agência, se quer ajuda com o banner e observações.
- **7 dias de antecedência:** as datas começam em hoje + 7. O número fica em Configurações da agência ("batalha oficial: antecedência mínima do pedido").
- **Minhas batalhas:** a próxima batalha confirmada (quando, hora, rounds, "@criador 🆚 @oponente", diamantes esperados, recado da Hera e o aviso de quando a batalha passa das 21h), o **checklist da batalha** (os 6 itens da BAT-CONF, "Antes" e "No dia", marcados um a um), os pedidos em aberto, os que não deram e o **histórico** (data e oponente).
- **Tela inicial:** com batalha confirmada, aparece "Sua batalha oficial: dd/mm às hh:mm" acima do botão de pedir.
- **Saíram** o "Pico de audiência: 20h–21h" e a hora já preenchida com 20:00 (o app não sugere hora; quem escolhe é o criador).

**Na gestão (menu Batalhas):**

- **Pedidos para responder**, com tudo o que o criador informou, e o formulário **Confirmar batalha**: escolher uma das datas do criador (ou outra), 1 ou 3 rounds, o oponente e a faixa de diamantes. A opção que não foi usada fica guardada.
- **Confirmadas**, com o texto da BAT-CONF já preenchido (**Copiar confirmação**, **Abrir grupo**, **Enviei**), quantos itens do checklist o criador marcou e **Atualizar a batalha** (o criador recebe "Sua batalha oficial mudou"; o modelo BAT-ATUALIZA aparece ao lado).
- **Sugerir outro dia ou hora, ou recusar**, com recado.
- A situação "Confirmada" só vale pelo formulário de confirmação, com o oponente.
- **Fila do dia** (decisão da Mariana de 18/11): do 4º ao 1º dia antes da batalha, a fila traz a mensagem "4 dias antes da batalha" (BAT-4D) até a gestora marcar "Enviei"; no dia, a mensagem "Dia da batalha" (BAT-DIA). O @ do oponente já entra no texto. Como são mensagens, seguem as regras da fila (uma por dia por criador, teto, domingo sem envios); a do dia tem prioridade 1.

**Como testar:** entre como `streamer01@hera.demo` e abra Batalhas na barra de baixo (há uma batalha confirmada de demonstração, um pedido e uma do histórico). Marque itens do checklist. Depois, entre como `gestora2@hera.demo` e abra o menu Batalhas.

**Conferência (18/11):** todos os testes passando (os novos estão em `tests/test_batalha_oficial.py`: regra dos 7 dias, as duas datas, confirmação, texto preenchido, checklist, histórico sem resultado, fila dos 4 dias e do dia, e isolamento entre criadores e entre carteiras). Telas abertas no Chrome: a do criador em 375px sem nada passando da borda, o clique no checklist funcionando, e a da gestão.

**Decisões pequenas do 3.3:**

| Decisão | Motivo |
| --- | --- |
| Duas datas obrigatórias e uma hora só | É o modelo oficial do roteiro ("Duas opções de data", "Horário") |
| A data mais cedo vira a 1ª opção | A gestão lê os pedidos em ordem de data |
| "Tanto faz" nos rounds no pedido; na confirmação, 1 ou 3 | O modelo oficial tem "tanto faz"; a batalha precisa de um número |
| Status "Aprovada" virou "Confirmada" e "Não aprovada" virou "Não deu desta vez" | Mesma palavra da mensagem BAT-CONF; recusa sem tom de reprovação |
| O histórico do criador mostra só data e oponente | O registro de resultado e diamantes (aba Batalhas da ficha) é interno e serve para a gestão escolher o próximo oponente; mostrar vitória e derrota viraria comparação |
| O checklist é o da BAT-CONF, palavra por palavra | É o que o criador já recebe no grupo |
| Mensagem dos 4 dias e do dia na fila, como mensagem (não tarefa) | Decisão da Mariana de 18/11. Depois do "Enviei", o item sai da fila |

**Fica para a etapa 4 (gestão completa):** sugestão de oponente do mesmo nível, agenda das batalhas e mural de vagas da semana.

### Passo 3.4, o que mudou (Campanhas)

Decisão da Mariana de 18/11: **as campanhas não são cadastradas no app.** O Claude lê no Backstage, junto com a leitura diária, a tela Operações › Campanhas, e a gestão só escolhe o foco. Conferido no Backstage em 18/11 (só olhando, sem mudar nada): "Por campanha" traz situação, período, nível recomendado, tipo (tabela de classificação, desafio de batalha ou missão), participantes/elegíveis e total de diamantes; "Por criador" traz a situação de cada criador (qualifica-se, inscrito, em andamento, encerrada); o link fica em Regras › Compartilhar › Link (`https://www.tiktok.com/t/...`); as campanhas da Hera ficam em "Campanhas dirigidas pela Agência" e chegam pela mesma leitura.

**Leitura de campanhas** (`POST /api/importacao/campanhas/`, mesma chave da leitura diária; regras em `engage/campaigns.py:receive_reading`): JSON com as campanhas e a situação de cada criador. Reenviar não duplica (a campanha é achada pelo ID do Backstage ou pelo nome com a data de início). O que a gestão decide (foco, "não oferecer", mecânica e "premia até" conferidos) nunca é sobrescrito. A situação de cada criador é trocada inteira a cada leitura; a inclusão manual da gestão fica. @ que não é da agência é ignorado e contado. Campanha nova avisa a gestão no sininho. As instruções para o Claude (com o formato) aparecem em Importar dados › Leitura automática, junto com a chave.

**Na gestão:**
- **Campanhas › Lidas do Backstage:** cada campanha com aba, tipo, nível, mecânica, participantes, quantos da carteira podem se inscrever, estão inscritos ou participam, e os botões **Foco**, **Não oferecer** e **Conferir os dados** (mecânica, premia até, resumo, prêmios e link).
- **Ficha › Campanha do momento:** a sugestão do app com o motivo em uma frase ("faz 8 batalhas por semana e só 3 participantes e premia até o 10º"), e a escolha da gestora entre as campanhas em que o criador participa (inclusive fora do foco, só para ele), "nenhuma por enquanto" ou a sugestão do app. A escolha vence a sugestão, vira nota na linha do tempo e avisa o criador.

**No app do criador:** uma lista só (saíram as abas "Destaques TikTok" e "Da Hera"), com as campanhas de foco em que ele participa, a situação dele ("Você pode se inscrever", "Inscrição feita", "Valendo agora"), o resumo e o botão para o TikTok. A campanha do momento vem primeiro e aparece na tela inicial. Sem posição e sem ranking. O rodízio da fila (ROD-CAMP) usa a campanha do momento.

**Campanha do momento (sugestão):** encaixe da mecânica com o que o criador fez nas últimas 4 semanas (batalhas, dias válidos, fãs novos, co-host), que pesa o dobro, mais a chance (participantes e até que posição premia, quando a leitura traz). Vídeos ainda não chegam na leitura diária. Prêmio comparado ao mês do criador e esforço ficam para quando o prêmio vier em número.

**Como testar:** `tests/test_campanhas.py` (porta, foco, lista do criador, sugestão, escolha da gestora, permissões e isolamento no banco). No computador da Hera há uma leitura de demonstração: entre como `streamer01@hera.demo` (Campanhas e tela inicial) e como `gestora2@hera.demo` (Campanhas e a ficha de @bia.show001.demo).

**Falta para funcionar no dia a dia:** ligar a leitura de campanhas no Claude que faz a leitura diária (copiar as instruções novas em Importar dados). A leitura roda no computador da Hera, com o Backstage logado no Chrome.

**Decisões pequenas do 3.4:**

| Decisão | Motivo |
| --- | --- |
| Do TikTok, o criador vê só as campanhas de foco (ou a escolhida para ele) | A visão pede uma campanha de cada vez; o Backstage lista dezenas |
| Campanha lida sem ninguém da Hera listado não aparece para ninguém | A leitura diz quem se qualifica; o público por Tier vale só para as campanhas antigas, cadastradas à mão |
| "Encerrada" não conta como "participa" | O criador não tem mais o que fazer nela |
| Quem pode marcar foco: sócias, gestoras e Conteúdo | Pedido da Mariana: a gestora escolhe as de foco |
| O link é aceito só se começar com `https://` (na leitura, só links do TikTok) | Evita link quebrado ou de fora no card do criador |

### Passo 3.5, o que mudou (Ajuda)

**A tela Dúvidas virou Ajuda** (na barra de baixo também). De cima para baixo: a busca; **Minha conta foi restringida ou banida**; **Falar com a Hera**; as dúvidas por tema; e **Sair da agência**.

- **Falar com a Hera:** "Tenho uma dúvida" ou "Quero conversar com a Hera" (pedido de conversa, com o assunto e o melhor jeito de falar, se o criador quiser contar). Entra na fila do dia no bloco de suporte ("Pedido de conversa pelo app") e avisa a gestora.
- **Minha conta foi restringida ou banida:** o criador conta o tipo, quando aconteceu, o que apareceu e se já fez o recurso. O aviso **abre o caso da conta** (ou completa o caso aberto), que vai para o topo da fila, e avisa a gestora (sem gestora, as sócias). O caso continua interno: o criador só vê que já avisou. A gravação do caso roda no serviço `crm/account_report.py`, como sistema, nunca na view (mesmo padrão do primeiro acesso). Encerrar o caso na ficha também fecha o aviso.
- **Sair da agência:** as regras pela data de entrada do criador ("é o seu caso"): nos primeiros 15 dias, é só avisar a Hera e dá para voltar quando quiser; depois, aviso prévio no app do TikTok e 90 dias sem agência (regra do TikTok); e os casos de inelegibilidade (mais de 300 mil diamantes em 6 meses, mais de uma conta, violações), com o texto do Playbook (SAI-03 e SAI-04). Botão **Quero conversar com a Hera**, que entra na fila como "Quer conversar sobre sair da agência". Os números 15 e 90 vêm de Configurações da agência.
- **Central de dúvidas revisada** (`engage/defaults.py`, migração `engage/0023`): "Tier" virou "Nível" (tema e respostas; a faixa de cada nível fica em Meu nível, não no texto); saíram as frases que sugeriam horas, dias ou horário ("1–2h por dia, 3–4 dias por semana", "entre 20h e 21h", "termine antes das 21h"); entraram 17 dúvidas do roteiro online (decisão 5), adaptadas para o criador ler; temas novos: Dinheiro e saque, Público e fã-clube, A Hera e os grupos. Saiu "De onde vem o número de diamantes do meu mês?". A migração só troca o texto que a gestão não editou.
- **Dicas do dia:** saíram as três que sugeriam hora e dias de LIVE, trocadas por fatos.
- **Gestão:** a tela Dúvidas mostra o tipo de cada pedido (dúvida, conversa, aviso de restrição, saída).

**Para a Mariana revisar:** `HERA\creator-hub\Central de duvidas - revisao do passo 3.5 (para revisar).txt`, com cada pergunta marcada como nova, mudou ou igual, o texto de antes e 4 pontos de atenção (mínimo do mês; "leva até 30 dias" e "perde as premiações"; graduação; a pergunta que saiu). Ele substitui o arquivo antigo de 11/11.

**Como testar:** `tests/test_ajuda.py`. No computador da Hera, entre como `streamer01@hera.demo` e toque em Ajuda.

**Decisões pequenas do 3.5:**

| Decisão | Motivo |
| --- | --- |
| O aviso de conta fica no topo da Ajuda, antes dos temas | É o caso urgente; com 13 temas, lá embaixo ninguém acharia |
| O criador não manda print pelo app; a tela pede o print no grupo | Os arquivos enviados se perdem a cada versão no Railway (até existir armazenamento) |
| O aviso de conta não aparece duas vezes na fila | O caso já tem o próprio item ("Restrição na conta: dia N") |
| "Regras da plataforma" virou "Regras do TikTok" | Mesmo selo que o app usa ("regra do TikTok") |

### Passo 3.6, o que mudou (Meu plano)

Decisões da Mariana de 19/11: (1) os lembretes chegam no sininho do app até existir notificação no celular; (2) a gestão vê o plano; (3) onde fica o acesso ela decide depois de ver a tela.

**No app do criador, tela nova "Meu plano"** (`/meu-plano/`; regras em `engage/plan.py`):
- **Meus dias de LIVE:** sete botões (seg a dom). Sem hora, sem sugestão de quantos dias. Desmarcar tudo também vale.
- **Meus objetivos:** até 3 em aberto. "Chegar a um nível" (o app mostra, com os dados de ontem, onde o Nível começa e quantos diamantes o criador tem no mês; quem já está no nível vê "Você já está no Nível X") ou "Do meu jeito" (texto livre). Botões **Consegui** (vai para "Consegui 🎉", com Desfazer) e **Apagar**.
- **Lembretes, todos desligados no começo:** "Hoje é um dos meus dias de LIVE", "Minha batalha oficial é amanhã", "Campanha que fecha hoje" e "Módulo novo na Hera Academy". Chegam no sininho, pela rotina diária. O mesmo lembrete não se repete no mesmo dia.
- No fim da tela: "A Hera vê o seu plano para combinar visitas e batalhas com você."
- **Acesso, por enquanto:** cartão "Meu plano" na tela inicial (logo depois de "Pedir batalha oficial"), com os dias e o primeiro objetivo, ou "Monte seu plano, se quiser"; e um atalho no Perfil. A barra de baixo não mudou.

**Na gestão:** ficha › Visão geral, quadro "Meu plano · escolhido pelo criador": dias, objetivos em aberto e os que ele conseguiu, e a data da última mudança. Só leitura.

**Segurança:** tabelas `engage_creatorplan` e `engage_creatorgoal` com RLS (`web/migrations/0009_rls_meu_plano.py`): o criador lê e grava o dele; a gestão da carteira e as sócias leem; ninguém da gestão grava (a sócia só apaga junto quando exclui o criador). A anonimização da LGPD apaga o plano e os objetivos.

**Como testar:** `tests/test_meu_plano.py` (14 testes). No computador da Hera, entre como `streamer01@hera.demo` e toque no cartão "Meu plano" da tela inicial. Para ver a ficha, entre como `gestora2@hera.demo` e abra @bia.show001.demo.

**Conferência (19/11):** 250 testes passando e 1 pulado (o mesmo de antes). A tela e o cartão foram abertos no Chrome como streamer01 (com um plano de exemplo: seg, qua e sex, "Chegar ao Nível 2", "Fazer minha primeira batalha oficial" e dois lembretes ligados). A ficha da gestão foi conferida pelos testes, não aberta no navegador. Os lembretes foram conferidos pelos testes; a rotina diária ainda não rodou com eles no Railway.

**Decisões pequenas do 3.6:**

| Decisão | Motivo |
| --- | --- |
| Os lembretes são criados pela rotina diária, às 6h | É a rotina que já roda todo dia. No sininho a hora não incomoda ninguém; quando houver notificação no celular, o envio respeita a janela da visão (nunca entre 22h e 9h) |
| Até 3 objetivos em aberto | Foi o que a Mariana aprovou no plano; os que ele conseguiu não contam |
| Objetivo de nível mostra fato, não ritmo nem "quanto precisa por dia" | Regra da tela inicial: nada de "precisa/dia" |
| Os níveis da lista são os acima do nível atual | Escolher o próprio nível não faz sentido como objetivo |
| O aviso de módulo novo só começa depois da primeira rodada da rotina | Na primeira vez a rotina só guarda o que já estava aberto; assim ninguém recebe aviso de tudo de uma vez |
| A gestão vê dias e objetivos, mas não quais lembretes estão ligados | Lembrete é do celular do criador; não ajuda a gestão a combinar visita ou batalha |
| A tela avisa que a Hera vê o plano | Transparência sobre os dados (LGPD) |

**Acesso (decisão da Mariana de 19/11):** fica como está, pelo cartão da tela inicial e pelo atalho no Perfil. A barra de baixo não muda.

### Passo 3.7, o que mudou (teste do app com poucos criadores)

Decisões da Mariana de 19/11: **5 criadores**, escolhidos por ela depois; os **vídeos** da Hera Academy ela cadastra no sistema; o teste dura **de 2 semanas a 1 mês**; a **pesquisa do fim é identificada**.

**Gestão › 🧪 Teste do app (só as sócias)** (`/gestao/teste-do-app/`; regras em `web/app_test.py`):
- **Datas:** início e fim, com a situação (sem datas, começa em, em andamento, terminou).
- **Trava do código de acesso:** "Só quem participa do teste recebe código de acesso". Ligada, a ficha de quem não participa mostra o aviso no lugar do botão, e o serviço `crm/first_access.py:new_code` recusa (vale também para quem tentar pelo endereço direto).
- **Quem participa:** colocar pelo @ e "Tirar do teste". Cada mudança fica no registro de ações (Audit logs). A ficha mostra "no teste do app".
- **Uma linha por criador:** gestora, situação do acesso (sem código, código gerado em, entrou em), dias com o app aberto nesta semana e desde o início, última vez, áreas usadas (Meu progresso, Hera Academy, Campanhas, Batalhas, Ajuda, Meu plano) e se respondeu a pesquisa.
- **Pesquisa do fim:** botão "Criar a pesquisa": 5 perguntas, identificada, só para quem participa (campo novo `Survey.only_app_testers`), abre às 9h do último dia e fica 7 dias aberta. Aparece no fim da tela inicial do criador, como as outras pesquisas. Respostas em "Ver as respostas".

**Registro de uso do app:** cada tela do criador registra, uma vez por dia, que o app foi aberto (`app_open`, que antes só contava a tela inicial) e uma vez por dia cada área usada (`area:...`). Fica em `web/views_streamer.py:streamer_required`. O relatório que já existia ("abriram o app na semana") passa a contar qualquer tela.

**Roteiro do teste para a Mariana revisar:** `HERA\creator-hub\Roteiro do teste do app - passo 3.7 (para revisar).txt` (checklist antes de começar, convite, sugestões por semana, como a gestão acompanha, perguntas da pesquisa e como saber se deu certo, com 4 perguntas no fim).

**Como testar:** `tests/test_teste_do_app.py` (9 testes). No computador da Hera, entre como `admin@hera.demo` → Teste do app.

**Conferência (19/11):** 259 testes passando e 1 pulado (o mesmo de antes). A tela foi aberta no Chrome como admin, com um criador de exemplo e a trava ligada; depois o teste de exemplo foi desfeito no banco local (sem datas, trava desligada, ninguém no teste). Correção feita na conferência: com o teste ainda por começar, a linha "desde o início do teste" não aparece.

**Decisões pequenas do 3.7:**

| Decisão | Motivo |
| --- | --- |
| A trava vem desligada e é ligada pelas sócias na tela do teste | Ligada por padrão, a gestão não conseguiria gerar nenhum código até alguém configurar o teste |
| Não há limite de 5 na tela; ela só mostra "combinado: 5" | Se alguém sair do teste no meio, dá para colocar outro sem mexer em configuração |
| A trava não desliga sozinha no fim do teste | Abrir o app para todos é decisão das sócias, não da data |
| "Dia com o app aberto" = qualquer tela do criador aberta no dia (dia de Brasília) | É o que a visão chama de "abre o app na semana" |
| A área usada é registrada para todos os criadores, não só para quem testa | A mesma medida serve depois para o painel das sócias ("Página educacional": quem assistiu a cada módulo) |
| A pesquisa abre às 9h do último dia e fica 7 dias | Dá tempo de a gestora avisar no grupo e de o criador responder |
| A mensagem de convite ficou no roteiro, não na biblioteca de mensagens | Regra do projeto: texto novo de mensagem só entra com a aprovação da Mariana (pergunta 1 do roteiro) |

**Falta (fora do app):** publicar esta versão; cadastrar os vídeos (pelo menos os módulos 1 a 3); a Mariana escolher os 5 e revisar o roteiro.

### Etapa 4: gestão completa (plano dos passos)

Pedida pela Mariana em 19/11, com a ordem abaixo aprovada. Construída em paralelo ao teste da etapa 3 (que ainda não começou).

| Passo | O que entra | Situação |
| --- | --- | --- |
| 4.1 Painel das sócias | Números da visão, lista de aprovações (manter ou encerrar), sorteio semanal de 5 "Enviei" | ✅ 19/11, aguardando aprovação (detalhes abaixo) |
| 4.2 1:1 com o modelo novo | Canal e quem conduziu, bloco 1 automático, anotações, print, aviso de 30 dias, frequência mensal (Diamante e potencial) | ✅ 19/11, aguardando aprovação (detalhes abaixo) |
| 4.3 Itens do mês na fila | Resumo do mês, "Quase lá", nível novo, módulo concluído, sinais de risco dos Diamante | ✅ 19/11, aguardando aprovação; textos provisórios em revisão pela Mariana (detalhes abaixo) |
| 4.4 Batalhas | Agenda, sugestão de oponente por regra, mural de vagas, rodada do dia 8 | A fazer |
| 4.5 Campanhas | 3 listas, acompanhamento na fila, aprovação das campanhas da agência | A fazer (decisão: a gestora vê a posição do criador na campanha?) |
| 4.6 Premiações | "Solicitar premiação", Pix só para o financeiro, aprovação das sócias | A fazer (Pix e arquivos: decisão de armazenamento) |
| 4.7 Indique e ganhe | Link, indicações, quanto ganhou | A fazer (depende do regulamento) |

### Passo 4.1, o que mudou (Painel das sócias)

Decisões da Mariana de 19/11: **bônus, receita e a simulação de compra de moedas ficam fora do app** (as colunas de bônus da Task continuam ignoradas); **sorteio de 5 "Enviei" por semana no total, espalhados entre as gestoras**.

**Gestão › 👑 Painel das sócias** (`/gestao/painel/`, só Admin; regras em `web/panel.py`), nesta ordem:
- **Aprovações:** pedidos esperando, com "Manter" e "Encerrar" e uma observação; as últimas decisões. A decisão vai para a linha do tempo da ficha e a gestora recebe aviso.
- **Resultado do mês:** conta inteira, só a Hera e cada grupo parceiro: criadores, quem fez LIVE, diamantes do mês, comparação com o mesmo ponto do mês passado, projeção do fechamento e o mês passado.
- **Execução da gestão (últimos 7 dias), por gestora:** fila concluída (com a referência de 90%), mediana de dias até o 1º "Enviei" para o novato, Enviei e Respondeu da semana, 1:1 do mês com Diamante e potencial de graduação (e quem falta), dias sem trabalhar no mês.
- **Sorteio da semana:** 5 "Enviei" da semana anterior; "Conferi: estava lá" ou "Não encontrei", com observação; resumo das semanas anteriores.
- **Funil do onboarding** por mês de entrada (6 meses), **Retenção** (90 dias: saída nos 15 primeiros dias com a faixa de 10% e 20%, encerramentos decididos pelas sócias, motivos de saída), **Graduação** (bateram a marca, no ritmo, precisam acelerar, último mês da janela), **Base por nível** (grupos e quem subiu ou desceu de Tier), **Hera Academy** (quem assistiu a cada módulo; novatos que viram o 1º módulo antes da 1ª LIVE), **Batalhas** (por semana, com a faixa de 6 e 3; batalhas oficiais do mês), **Recrutamento** (por recrutadora: entraram, fecharam os 14 dias, saíram nos 15 primeiros dias, graduaram) e o espaço de **Premiações e indicações** (passos 4.6 e 4.7).

**Na fila do dia:** os itens de encerramento (até o D14, D15 e o último passo da régua sem LIVE) ganharam **"Pedir decisão às sócias"**, com observação. Depois do pedido, o item mostra "aguardando as sócias". Um pedido em aberto por criador. As sócias recebem aviso no sininho.

**Rotina das 6h:** tira o retrato da fila de cada gestora (`QueueDay`, só os criadores com mensagem) e, na segunda, faz o sorteio. O painel também sorteia ao abrir, se o da semana ainda não existir.

**Segurança:** `crm_approvalrequest` (a gestão que vê o criador lê o pedido; quem edita o criador pede; só as sócias decidem e apagam; o criador nunca lê), `crm_sentcheck` e `crm_queueday` (só as sócias e a rotina). Migração `web/0010_rls_painel_das_socias.py`.

**Como testar:** `tests/test_painel.py` (10 testes). No computador da Hera, entre como `admin@hera.demo` → Painel das sócias.

**Conferência (19/11):** 269 testes passando e 1 pulado (o mesmo de antes), já com a correção das batalhas. Aberto no Chrome com o banco local: o painel carregou em cerca de 5 segundos com 442 criadores. Duas correções feitas na conferência: o título do sorteio (agora "de 09/11 a 15/11") e as batalhas por semana. Elas pegavam semanas antigas e uma semana inflada quando o mês inteiro chegava numa importação só; agora entram só as 4 últimas semanas com leitura diária.

**Decisões pequenas do 4.1:**

| Decisão | Motivo |
| --- | --- |
| Fila concluída = mensagens da fila das 6h com "Enviei" ou "Adiar" no mesmo dia | "O dado mudou" (o criador abriu LIVE) não dá para medir no mesmo dia; os dias de ausência da gestora não entram |
| O retrato da fila guarda só os IDs dos criadores com mensagem | O necessário para a conta; o texto e o motivo continuam só na fila |
| Sorteio: uma gestora de cada vez, em ordem aleatória, até 5 | Decisão da Mariana: 5 no total, espalhados entre as gestoras |
| Projeção do fechamento = diamantes até ontem ÷ dias passados × dias do mês | A mesma conta do ritmo; diz "estimativa, não é garantia" |
| "Ficou depois do D15" conta só quem já passou do 15º dia | Quem ainda está nos 15 dias não pode contar como saída nem como permanência |
| Batalhas por semana só com semanas de leitura diária | Leitura que cobre mais de uma semana jogaria tudo numa semana só |
| O Relatórios continua para as gestoras | Cada gestora vê a própria carteira lá; o painel é das sócias |

### Passo 4.2, o que mudou (1:1 com o modelo novo)

Decisão da Mariana de 19/11: **o print não é enviado ao app.** A gestora guarda o print no drive dela e só marca no app "Guardei o print da conversa no meu drive". Assim não há armazenamento de arquivos nem custo novo.

**Registro do 1:1 (ficha › aba 1:1):** data, **canal** (ligação, vídeo, áudio ou mensagem), **quem conduziu** (vem quem registra; dá para trocar por outra gestora ou sócia), **bloco 1 preenchido pelo sistema** (diamantes, horas, dias válidos e batalhas até ontem; o mesmo ponto do mês passado, quando há leitura daquele dia; o mês passado fechado com o Tier), blocos 2 a 5, plano com quem faz e até quando, próximo 1:1, **anotações** e a marca do print. A média de espectadores fica de fora: só existe na leitura detalhada por criador, que ainda não chega. O texto antigo do bloco 1 falava em "% da meta" e saiu.

**Completo = canal, blocos 1 a 5, pelo menos 2 ações, próximo 1:1 marcado e o print guardado** (`OneOnOne.missing`). Ao salvar, a tela diz o que falta. O histórico mostra o canal, quem conduziu, o print, as anotações e o que falta.

**Tela nova Gestão › 🤝 1:1** (`/gestao/1a1/`, a carteira de quem vê; regras em `crm/one_on_one.py`): quem precisa de 1:1 todo mês (grupo Diamante e potencial de graduação), com o último 1:1 completo, o próximo marcado e a situação (em dia, passou de 30 dias, nunca teve 1:1 completo); os próximos marcados; os atrasados.

**Fila do dia:** item novo "1:1 do mês" (bloco 2, tarefa) para Diamante e potencial de graduação sem 1:1 completo há 30 dias ou mais e sem 1:1 marcado. O "1:1 atrasado" continua. O painel das sócias passou a contar só 1:1 completo.

**Como testar:** `tests/test_um_a_um.py` (7 testes). No computador da Hera, entre como `gestora1@hera.demo` → 🤝 1:1 e abra um criador.

**Conferência (19/11):** 276 testes passando e 1 pulado (o mesmo de antes). A agenda e o formulário foram abertos no Chrome com o banco local. Um teste antigo (`test_views`) foi atualizado para o modelo novo (canal, 2 ações e print).

**Decisões pequenas do 4.2:**

| Decisão | Motivo |
| --- | --- |
| Pelo menos 2 ações para o 1:1 contar | A visão pede "plano com 2 a 3 ações" |
| "No mesmo ponto do mês passado" só aparece com a leitura daquele dia do mês passado | É fato, não estimativa; com a leitura diária, passa a aparecer sempre a partir do mês seguinte |
| O "1:1 do mês" não entra para quem já tem 1:1 marcado | Já está combinado; se a data passar, entra o "1:1 atrasado" |
| Quem conduziu pode ser uma gestora ou uma sócia ativa | Às vezes a sócia conduz o 1:1 de um criador Diamante |
| O 1:1 continua só na gestão | Visão: o registro não aparece no app do criador |

### Passo 4.3, o que mudou (itens do mês na fila)

Decisões da Mariana de 19/11: **"menos constante" = menos dias válidos no mês que fechou do que no anterior**; **o sinal de risco marcado pela gestora vale 30 dias**. Regras em `web/month_items.py`.

- **Resumo do mês (dias 1 a 7):** do dia 1 ao 5, quem foi menos constante (MES-APOIO); nos dias 6 e 7, os constantes (MES-PARABENS). Quem fez mais LIVE (horas, dias ou batalhas) e recebeu menos diamantes recebe a 2.5 do Playbook (APO-05). Item sem "Enviei" segue até o dia 7. Fica de fora quem não fez LIVE no mês (a régua cuida) e quem está nos 14 dias (o roteiro cuida). Sem números no WhatsApp: a mensagem aponta para o app.
- **Nível novo (dias 1 a 7):** quem subiu de Tier no mês que fechou recebe NIVEL-NOVO no lugar do resumo.
- **Quase lá (últimos 7 dias do mês):** os avisos "perto do próximo Tier" e "perto de graduar" (85% ou mais) viram mensagem com prioridade 1 (QUASE-NIVEL, QUASE-GRAD), uma por semana. Fora da última semana, os avisos continuam como antes. "Perto de prêmio de campanha" entra no 4.5.
- **Módulo concluído:** quem terminou todas as aulas de um módulo nos últimos 3 dias (MODULO-OK, com a próxima aula aberta).
- **Sinais de risco dos criadores Diamante** (Playbook, seção 5): pelos números (queda de 30% ou mais; horas abaixo de 70% ou 2 dias válidos a menos que a média das 3 semanas anteriores; batalhas abaixo da metade da média, quando a média é 3 ou mais; nenhum fã novo com 5h ou mais de LIVE) e pela conversa (quadro novo na ficha: demorou a responder, mudou o tom, falou de outra agência, reclamou de algo; o mesmo tipo marcado duas vezes conta uma). Um sinal: aviso na ficha. Dois ou mais: item "Diamante com N sinais de risco" na fila (prioridade 1, conversa em até 48 horas), aviso às sócias pela rotina diária (um por criador a cada 7 dias) e a lista "Diamante em risco" no topo do painel das sócias. Os sinais marcados entram na linha do tempo.
- **6 mensagens provisórias** na biblioteca (etapa "Itens do mês"; migração `engage/0026`). Revisão: `HERA\creator-hub\Mensagens do passo 4.3 - itens do mes (para revisar).txt`.

**Segurança:** `crm_risksignal` (interna: a gestão que vê o criador lê; quem edita marca; o criador nunca lê). Migração `web/0011_rls_sinais_de_risco.py`.

**Como testar:** `tests/test_itens_do_mes.py` (9 testes). Dois testes antigos usavam 28/09 (última semana do mês) e foram atualizados para o "Quase lá" (`test_fila.py`, `test_fila_do_dia.py`).

**Conferência (19/11):** 286 testes passando e 1 pulado (o mesmo de antes). Não aberto no navegador; as telas (ficha com o quadro de sinais e o painel com a lista) foram conferidas pelos testes.

**Decisões pequenas do 4.3:**

| Decisão | Motivo |
| --- | --- |
| "Batalhas em queda forte" = menos da metade da média das 3 semanas anteriores, quando a média é 3 ou mais | O Playbook não define o número; com poucas batalhas, qualquer variação pareceria queda |
| "Horas ou dias abaixo do normal" usa o mesmo corte do diagnóstico de queda (70% das horas ou 2 dias válidos a menos) | Regras v2 do Acompanhamento Semanal |
| Quem é Diamante = Tier do mês fechado no grupo Diamante | Mesma regra do 1:1 mensal |
| O resumo do mês não entra para quem não fez LIVE no mês nem para quem está nos 14 dias | Esses criadores já têm roteiro próprio (régua e onboarding) |
| O aviso às sócias sai pela rotina das 6h, não na hora em que a gestora marca o sinal | A conta junta números da leitura diária e sinais da conversa; uma vez por dia basta para "conversa em até 48 horas" |

### Resumo do mês no app (pedido da Mariana de 19/11, entre os passos 4.3 e 4.4)

Decisões da Mariana de 19/11: o cartão fica no topo do Meu progresso **do dia 1 ao dia 10** e depois em "Meses desde a entrada"; as **dicas saem de um banco com regras** (provisório até a revisão dela); a **gestora pode escrever a própria dica** na ficha, que entra no lugar da primeira automática. Regras em `web/month_summary.py`.

- **Cartão "Seu mês de outubro 🎉"** (`templates/streamer/_month_summary.html`): a mudança de nível ("Você subiu do Nível 5 para o Nível 7 e segue no grupo Diamante 💎🚀"; mesmo nível ou abaixo: "Você fechou outubro no Nível 3, no grupo Prata 💜"; primeiro mês: "Seu primeiro mês fechado com a Hera"); **Onde você se superou** (até 3 números que mais melhoraram contra o mês anterior: diamantes em %, seguidores novos, fã-clube, batalhas, dias válidos, horas; sem melhora, vira "O seu mês" com o que ele fez); **Ideias para novembro, use o que fizer sentido para você** (2 dicas); "Conta com a Hera para o que precisar 🙌".
- **Tela de cada mês:** `/meu-mes/<ano>/<mês>/`, aberta pelo mês em "Meses desde a entrada".
- **Ficha › Visão › "Resumo do mês no app":** o que o criador vê e o campo "Dica da Hera para este criador" (passa pelo verificador de tom; em branco, apaga). Tabela `engage_monthtip` (o criador lê a dele; só quem edita o criador grava; `web/migrations/0012`).
- **Aviso no sininho** nos dias 2 e 3: "Seu resumo de outubro chegou 🎉" (um por mês; começa no dia 2 porque o último dia do mês chega com a leitura do dia 1).
- **Banco de 13 dicas** com a regra de cada uma, para revisão: `HERA\creator-hub\Dicas do resumo do mes no app (para revisar).txt`.
- **Ainda não entram:** "pessoas que mandaram presentes" e vídeos (só na leitura detalhada por criador, que ainda não existe).

**Como testar:** `tests/test_resumo_do_mes.py` (9 testes). No computador da Hera, entre como `streamer01@hera.demo` e toque em "ago/26" em "Meses desde a entrada".

**Conferência (19/11):** todos os testes passando e 1 pulado (o mesmo de antes). O cartão foi aberto no Chrome como streamer01; a demonstração só tinha dados para uma dica, e por isso entrou a 13ª dica (reserva), para todo criador ter 2.

### ⚠️ Logins de demonstração não podem existir em produção

Estes logins têm senha conhecida (`hera-demo-2026`) e servem só para demonstração no computador da Hera:

- `admin@semana.demo` e `gestora.a@semana.demo` até `gestora.e@semana.demo` (criados por `demo_semana`);
- todos os `@hera.demo`, como `admin@hera.demo`, `gestora1@hera.demo` e `streamer01@hera.demo` (criados por `seed_demo`).

Três proteções: os dois comandos se recusam a rodar em produção; o app não liga em produção se encontrar um desses e-mails no banco (erro `hera.E002` no log); e a regra está no guia de publicação. **Produção usa um banco novo. Nunca copie o banco de demonstração para produção.**

### Decisões pendentes da Mariana

- [x] **Nome da página educacional (passo 3.2):** **Hera Academy** (decisão de 18/11).
- [x] **Tela inicial (passo 3.1):** Avisos, Benefícios, Pesquisa e a dica do dia ficam no fim da tela: **manter** (decisão de 18/11).
- [x] **Frase de quem já passou da marca do próximo nível (passo 3.1):** trocada em 18/11 por uma forma neutra que avisa a troca de grupo: "Seus diamantes deste mês já estão na faixa do grupo Ouro. A troca de grupo acontece no fechamento do mês." Quando o grupo não muda (ex.: T2 → T3, os dois Prata) ou no Primeiro Mês: "Seus diamantes deste mês já estão na faixa do Nível 3. A mudança acontece no fechamento do mês." (`web/progress.py:reached_phrase`, testes em `tests/test_meu_progresso.py`).
- [x] **Decisões 1 a 4 das mensagens** (revisão da Mariana de 18/11, arquivo `HERA\creator-hub\Mensagens - decisoes 1 a 5 (para revisar).txt`), aplicadas pela migração `engage/0019_revisao_mensagens_18_11.py`, que troca só as mensagens revisadas e guarda o texto anterior como versão:
  1. SAI-01 sem o final "sem prazo de espera nenhum"; RES-01 "me conta quando aconteceu (o dia e a hora)"; BAT-PEDIDO "a hora" e "⏰ Hora:"; BAT-ATUALIZA "a batalha passou para as 20h". A biblioteca padrão não tem mais palavra vetada.
  2. REG-14, QUEDA-01, REC-01 e CONVITE-APP com o texto da Hera (origem "Criado pela agência"; nenhuma provisória). Em QUEDA-01, o trecho que a gestora completa ficou entre colchetes, como nas outras mensagens, e em forma neutra.
  3. Cadência depois do D15 com a versão para quem já é da casa: NR-24H-CASA, NR-2D-CASA e NR-3D-CASA (a fila escolhe sozinha pela fase; o +5 dias é o mesmo para todos).
  4. Mural de batalhas continua sem o bloco de destaques.
- [x] **Decisão 5 (dúvidas frequentes do roteiro), 18/11:** entram **nas duas**. Na biblioteca de mensagens já entraram 23 respostas (códigos DUV-*, etapa "Dúvidas frequentes", migração `engage/0020`), com os textos revisados; a graduação saiu e "O que é uma batalha oficial?" é a própria BAT-PEDIDO. O quadro de graduação do Meu progresso **fica** para os testes iniciais.
- [ ] **Dicas do resumo do mês no app:** 13 dicas com regra, em `HERA\creator-hub\Dicas do resumo do mes no app (para revisar).txt`, com 3 perguntas.
- [ ] **Mensagens do passo 4.3 (itens do mês):** 6 textos provisórios em `HERA\creator-hub\Mensagens do passo 4.3 - itens do mes (para revisar).txt`, com 2 perguntas (textos e o número de diamantes no "Quase lá").
- [ ] **Roteiro do teste do app (passo 3.7):** `HERA\creator-hub\Roteiro do teste do app - passo 3.7 (para revisar).txt`, com 4 perguntas.
- [ ] **Central de dúvidas (passo 3.5):** as respostas do roteiro entraram adaptadas para o criador, junto com a revisão "Tier → Nível". Falta a Mariana revisar `HERA\creator-hub\Central de duvidas - revisao do passo 3.5 (para revisar).txt` (substitui o arquivo antigo de 11/11), com 4 pontos de atenção.
- [ ] **Cobertura e quem cobre (passo 2.7) e a aprovação da etapa 2:** a Mariana decide depois do teste da gestão (18/11).
- [ ] **Cobertura (passo 2.7):** quem cobre enxerga a carteira inteira da gestora ausente, só naquele dia, e só registra contato. Confirmar se está bom assim, ou se o acesso deve ficar restrito aos criadores com item que não pode esperar.
- [ ] **Quem cobre cada gestora:** escolher na tela Carteiras (uma sócia, a Fernanda ou a Adrielly). Enquanto não escolher, cobrem as sócias.
- [x] Textos do Playbook com palavra vetada, 4 provisórias, cadência depois do D15 e mural de batalhas: decididos em 18/11 (ver "Decisões 1 a 4 das mensagens", acima).
- [x] Meta individual, missão da semana e disparo assistido: **remover** (feito em 14/11).
- [x] Login: **trocar pelo fluxo da visão** (feito em 14/11).
- [x] Painel das sócias: **pode mostrar bônus, receita e moedas**, só para Mariana e Aline (regra atualizada no `CLAUDE.md`; o painel é da etapa 4).
- [ ] Itens "Em aberto" da própria visão (regulamento do Indique e ganhe, nome da página educacional, revisão jurídica, criadores do teste, opinião da Anna sobre a fila).

### Resultado do mapeamento de 14/11 (resumo)

- **Já atende:** importação diária com plano B, regra dos 14 dias, dois relógios do onboarding, carteiras com histórico, isolamento de dados, link do grupo na ficha, sem ranking, verificador de tom nas telas, 1:1 com 7 blocos, cadência de não-resposta, aulas assistidas na ficha, central de dúvidas.
- **Precisa mudar:** tela inicial (vira Meu progresso), "Tier" (vira Meu nível) e grupos antigos, textos que sugerem número ou horário ("Acelerar", "precisa/dia", missões), Academy (abre por nível, sem "obrigatória"), campanhas (uma por criador), fila de ação (vira fila do dia), ficha, onboarding, 1:1 (canal, print, anotações), mensagens com palavras vetadas, saída (motivo em lista e aprovação das sócias), relatórios (viram painel das sócias), recrutadora até o D15.
- **Falta:** motor de fases, trilha e nicho, estado da semana, itens fixos da rotina diária, Meu plano, simulador, marco da 1ª LIVE, conquistas, Indique e ganhe, premiações e Pix, push, aniversário, aprovações e sorteio das sócias, campanhas por criador e as 3 listas.
- **Existe e a visão não prevê:** benefícios e cupons, pesquisas e NPS, disparo assistido, tags internas, meta individual, missão e dica do dia, `Outbox`, campanhas de pontos e relâmpago, perfil de comunidade, login pelo Google, anonimização automática em 180 dias.

## Histórico: passos 1 a 3 da visão de 11/11

| Passo | Situação |
| --- | --- |
| 1. Preparação (unificar as duas cópias, regras no `CLAUDE.md`) | ✅ 11/11 |
| 2. Regras nas telas que já existem (sem ranking, palavras vetadas, linguagem neutra) | ✅ 11/11, aguardando aprovação |
| 3. Importação diária (pela gestão ou pelas sócias) | ✅ 11/11, aguardando aprovação |
| 4 a 8 | Refeitos como passos 2.2 a 2.6 do plano atual |

**Passo 2, o que mudou:** não existe mais ranking em nenhuma tela (as colunas de posição saíram do banco; a campanha interna na gestão lista participantes em ordem alfabética, com valor e "chegou ao alvo"). Nas telas do criador saíram meta, relatório, cobrança, prazo e horário, e a linguagem ficou neutra ("Falar com a Hera", "Valeu!"). A central de dúvidas e as dicas foram reescritas, inclusive as já gravadas no banco (migração `engage/0005`).

**Como testar:** `python manage.py test tests` (63 testes). O teste `tests/test_tom.py` abre as telas do criador e falha se aparecer palavra vetada ou ranking. O verificador fica em `engage/tom.py`.

**Decisões pequenas do passo 2:**

| Decisão | Motivo |
| --- | --- |
| "Sua gestora" virou "a Hera" (botão "Falar com a Hera", "Seu contato na Hera") | Linguagem neutra sem inventar termo novo |
| "X% da meta" virou "X% do caminho"; "meta batida" virou "você chegou lá" | Tira a palavra sem mudar o cálculo |
| Categoria "Metas" da central de dúvidas virou "Regras da plataforma" | Regras do TikTok aparecem como regras da plataforma |
| O verificador também barra ranking, gestora, obrigada/o, juntas/os e bem-vinda/o | Cobre a linguagem neutra, além das cinco palavras da regra |
| As palavras-chave de busca da central de dúvidas continuam com "meta" e "horario" | Não aparecem na tela e ajudam quem busca por essas palavras |

**Pedir batalha (ajustes de 11/11, pedidos pela Mariana):** um tipo só ("Batalha agendada"); o criador pode oferecer até 3 outras opções de dia e hora; escolhe 1 ou 3 rounds; não escolhe oponente, não informa duração e não pede divulgação. A Hera busca alguém do mesmo nível e avisa no grupo e no app. Um botão no topo abre a aula marcada como "explica a batalha oficial" (cadastro da aula). No perfil saiu "Aceito convites de batalha".

**Passo 3, o que mudou:** a importação do Backstage ("Dados do criador") passa a ser diária e pode ser feita pela gestora ou pelas sócias (Admin); a planilha "Task" do fechamento continua com Admin e Financeiro. O painel avisa quando a importação de hoje ainda não foi feita, com o botão "Importar agora", e marca "atrasada" depois de 2 dias (configurável). As telas "semana a semana" somam os dias por semana (segunda a domingo). A missão "sem LIVE" passou a contar dias. Os textos do criador dizem que os números atualizam todo dia.

**Como testar o passo 3:** entre como `gestora1@hera.demo`, abra "Importar dados" e envie um arquivo "Dados do criador". Antes de gravar, o painel mostra o aviso; depois, mostra "Backstage importado hoje às HH:MM".

**Decisões pequenas do passo 3:**

| Decisão | Motivo |
| --- | --- |
| A pré-visualização da importação lê o banco como "sistema" (como a gravação já fazia) | O arquivo traz a agência inteira e a gestora só enxerga a própria carteira; sem isso, criadores de outra carteira apareceriam como "novos" |
| "Importação de hoje" = lote gravado hoje, no dia de São Paulo | É o que a pessoa que importa enxerga no relógio dela |
| Alerta de atraso passou de 8 para 2 dias sem importar | 8 dias era da importação semanal; 2 dias tolera um dia sem importar |
| ~~O número individual de diamantes continua sendo definido pela gestão~~ | Decisão de 11/11, **revogada em 14/11**: a meta individual foi removida |

**Pendências conhecidas:** as 42 mensagens do Playbook ainda têm palavras vetadas (passo 8); a tela "Meu Tier" e uma resposta da central ainda citam os grupos antigos (passo 5); os dados de demonstração terminam em setembro, então telas do mês corrente aparecem vazias até a primeira importação real.

## 1. O que foi implementado e o que falta

### MVP

| Função | Status | Observação |
| --- | --- | --- |
| Login com e-mail e senha, sessão de 90 dias | ✅ | Trocado em 14/11: saíram o código por e-mail e o Google |
| Primeiro acesso com código gerado pela gestão (@ + código + e-mail + senha) e termo LGPD | ✅ | Trocado em 14/11: saiu o convite por e-mail |
| Papéis (Admin, Gestora, Recrutadora, Conteúdo, Financeiro, Analista) e escopo por carteira | ✅ | Aplicado em 2 camadas: Django e RLS no Postgres |
| Banco multi-agência (`agency_id`) e grupos parceiros | ✅ | Acesso de streamer liberado por grupo parceiro |
| Importação: templates PT/EN, mapeamento, validação, pré-visualização, snapshot, desfazer | ✅ | Reconhece saídas ("O criador deixou a agência") pelo @ |
| Motor: referência do TikTok derivada, ritmo, previsão, Tier (mês fechado), grupo, Primeiro Mês | ✅ | Meta individual removida em 14/11 |
| Tela do streamer: Meu mês, contagem dos 14 dias, Tier, campanhas, dica, Academy, data dos dados | ✅ | Missão da semana removida em 14/11 |
| Desempenho (meses, semana a semana, melhor mês) | ✅ | |
| Dashboard com fila de ação (sem LIVE, queda > 30% com árvore de decisão, perto do Tier/graduação, onboarding em risco, cadência, 1:1 e planos vencidos, pedidos) | ✅ | Itens podem ser dispensados por 7 dias |
| CRM: tags, notas, 1:1 com 7 blocos, plano de ação, contatos, saída, histórico de @ e carteira | ✅ | |
| Onboarding D1–D15 com dois relógios e marcação automática | ✅ | |
| Mensagens do Playbook (42 modelos) com variáveis: copiar, abrir o grupo e "Enviei" | ✅ | Só o "Enviei" registra o contato (14/11) |
| Cadência de não-resposta (+24h, +2d, +3d, +5d) | ✅ | |
| ~~Disparo assistido por público (F2)~~ | Removido | Decisão de 14/11 |
| Avisos com público por grupo/Tier/parceira + notificações no app | ✅ | |
| Campanhas oficiais: só os destaques do mês, com resumo do que fazer, prêmios, botão para o TikTok e "Chamar minha gestora" | ✅ | Ajuste de 29/09 |
| Botão "Chamar minha gestora" ligado ao grupo individual do WhatsApp (link cadastrado por creator) | ✅ | Ajuste de 29/09 |
| Campanhas (destaques TikTok e da Hera): card com resumo e prêmios que abre direto no TikTok, sem ranking no app; acompanhamento interno só no painel | ✅ | |
| Academy com vídeos por link e progresso | ✅ | |
| Central de dúvidas: busca no Q&A (sem IA), sinônimos, respostas com os números do streamer, "perguntar para minha gestora" (F1) | ✅ | 23 perguntas iniciais do Manual e Playbook |
| Benefícios e cupons com cliques e "usei o cupom" (F4) | ✅ | |
| Pesquisas com uma pergunta por tela, NPS, anônimas (F5) | ✅ | |
| Pedido de batalha (oficial, especial, PK, cohost) com aviso das 21h (F6) | ✅ | Atalho na tela inicial |
| Atalhos na tela inicial: Tirar dúvida, Pedir batalha, Benefícios; botão "Ajuda" no topo | ✅ | Ajuste de 29/09 |
| Relatório mensal básico, CSV, métricas de sucesso | ✅ | |
| Rotina diária: avisos agendados, fim do aviso prévio, anonimização LGPD, alerta de importação atrasada | ✅ | Agendar no Railway |
| Log de ações administrativas | ✅ | Configurações → Audit logs |
| PWA instalável, funciona offline com página de aviso | ✅ | Ícone provisório; trocar pelo logo oficial |

### Ainda não feito (fora do MVP)

- **V2:** conquistas, badges e sequências de dias; Comunidade (F3); campanhas de pontos (tabela já existe); API oficial do WhatsApp (tabela `Outbox` já existe); acesso para gestores de parceiras (papel e regra no banco já existem); push; Google Sheets; fechamento por parceira; pareamento de batalhas; orçamento de prêmios; quiz pós-treino.
- **V3:** IA (resumo semanal, coach, risco), réguas automáticas, módulo de recrutadoras, venda para outras agências.
- **Faltou no MVP:** telas próprias de cadastro para Campanhas, Academy e Conteúdos. Hoje elas usam o painel de cadastros do Django: funciona, mas é menos bonito.

## 2. Decisões pequenas tomadas durante a construção

| Decisão | Motivo |
| --- | --- |
| "Meta em risco" = chegar ao Dia 10 sem 5 dias válidos e 15h | Regra do Playbook, simples de explicar |
| CSS próprio em vez de Tailwind | Nenhuma etapa de build: mais fácil de manter |
| Telas de cadastro de conteúdo no painel do Django | Economiza semanas; troca por telas próprias na V2 |
| ~~Senha opcional além do código por e-mail~~ | Trocado em 14/11: todos entram com e-mail e senha; o código por e-mail saiu |
| Recálculo roda como "sistema" logo após cada importação | Rankings e grupos precisam comparar creators |
| Ranking mostra só @ (público no TikTok), Tier e valor | Nada de dado pessoal para outros streamers |
| Notificações para outras pessoas criadas como "sistema" | O remetente não pode ler a notificação alheia (RLS) |
| Meta de diamantes sem meta do TikTok = mínimo do próximo Tier | Sempre existe uma meta a mostrar |
| Recrutadora vê os creators que recrutou, mas não edita | Segue a matriz de permissões aprovada |
| Campanha que não fecha com a data da importação (ex.: fim de semana) usa a importação mais próxima | Limite da importação semanal |
| Removido o `railway.json`; o comando de início e a rotina diária são configurados no painel do Railway (guia de publicação, passos 7 e 10) | O Railway descontinuou esse arquivo e o construtor NIXPACKS; além disso, o arquivo sobrescreveria o comando do serviço da rotina diária |
| O app só liga se passar na trava `hera.E001` (`check --deploy --database default`) | Antes, a verificação só rodava se alguém lembrasse de chamá-la, e sem `--database` ela nem era executada |
| Em produção, o app não liga sem `SECRET_KEY` | Evita publicar com a chave de desenvolvimento |
| `healthcheck.railway.app` sempre permitido em `ALLOWED_HOSTS` | Sem isso, a verificação de saúde do Railway falha e o deploy não completa |
| Banners de campanha não devem ser enviados até existir armazenamento de arquivos (R2) | O disco do Railway é apagado a cada nova versão |

## 3. Custos mensais estimados (hospedagem)

Preços do Railway por uso: memória ≈ US$ 10 por GB/mês, CPU ≈ US$ 20 por vCPU/mês, disco ≈ US$ 0,16 por GB/mês, plano Hobby com mínimo de US$ 5 ([railway.com/pricing](https://railway.com/pricing)). Câmbio de R$ 5,16. São estimativas: o consumo real aparece no painel do Railway depois do primeiro mês.

| Creators | App (web) | Banco | Rotinas / e-mail | Total estimado |
| --- | --- | --- | --- | --- |
| 150 | 0,35 GB, pouca CPU ≈ US$ 4–5 | 0,25 GB ≈ US$ 3 | e-mail grátis (Resend até 3 mil/mês) | **US$ 7–10 ≈ R$ 36–52** |
| 1.000 | 0,7 GB ≈ US$ 10 | 0,5 GB ≈ US$ 7 | e-mail grátis ou US$ 20 | **US$ 18–40 ≈ R$ 93–206** |
| 5.000 | 2 instâncias, 1,6 GB ≈ US$ 26 | 2 GB + 15 GB disco ≈ US$ 32 | worker de recálculo ≈ US$ 9 + e-mail US$ 20 | **US$ 80–100 ≈ R$ 413–516** |

Fora da hospedagem: domínio (≈ R$ 40/ano). A API oficial do WhatsApp, se ligada na V2, soma ≈ R$ 40–235/mês com 150 streamers.

## 4. Riscos e próximos passos recomendados

### Riscos

1. **Usuário do banco errado.** Se o app conectar como superusuário, as regras de segurança do banco deixam de valer. Mitigação: comando `criar_usuario_banco` e verificação automática `hera.E001`.
2. **Importação esquecida.** Com importação semanal, uma segunda sem importar deixa a tela do streamer com números velhos. Mitigação: data sempre visível e alerta para o Admin após 8 dias.
3. **Mudança no formato do Backstage.** O TikTok pode renomear colunas. Mitigação: mapeamento pela tela, salvo como modelo.
4. **Recálculo lento com muitos creators.** Hoje leva cerca de 30 ms por creator (5.000 creators ≈ 2–3 minutos por importação). Antes de passar de 1.000, mover o recálculo para uma fila em segundo plano.
5. **Conteúdo desatualizado no Q&A.** A central de dúvidas só é boa se as respostas forem mantidas. Mitigação: lista de buscas sem resposta e "não ajudou" na tela de Conteúdos.
6. **Regras divergentes nos documentos.** O Manual ainda fala em 4 meses de carência; o app usa 90 dias. Atualizar o Manual.
7. **Dados sensíveis.** WhatsApp e e-mail ficam numa tabela separada e são anonimizados depois da saída. Revisar o termo LGPD com um advogado antes de abrir para todos.

### Próximos passos

1. Publicar no Railway e criar o Admin (1 dia). **Em andamento (30/09):** configuração e guia (`docs/COMO_RODAR_E_PUBLICAR.md`, parte B) prontos. Falta: instalar Python e GitHub Desktop neste computador, rodar os testes e seguir os passos 1 a 10 do guia. Como testar: o deploy fica verde no Railway, `/accounts/login/` abre e o Admin entra com e-mail e senha.
2. Trocar o ícone pelo logo oficial e revisar os textos das 42 mensagens e das 23 perguntas do Q&A.
3. Importar os meses reais (julho a setembro) e conferir 5 creators contra o Backstage.
4. **Piloto de 2 semanas** com 1 gestora e cerca de 20 streamers diretos. Medir uso semanal, dúvidas sem resposta e tempo da gestora.
5. Liberar para toda a base Hera direta; depois, grupo parceiro por grupo parceiro.
6. ~~Depois de 2 meses de disparo assistido, decidir sobre a API oficial do WhatsApp.~~ Decidido em 11/11 e 14/11: sem API do WhatsApp e sem disparo assistido.
7. Começar a V2 pelas telas próprias de cadastro, pela Comunidade e pelas conquistas.

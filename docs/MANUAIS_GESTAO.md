# Manuais rápidos da gestão

Sete tarefas do dia a dia, em passos curtos. Onde aparece "Configurações", é o painel de cadastros (menu ⚙️, só Admin e Conteúdo).

## 1. Dados do Backstage: leitura automática e plano B

Os números entram todo dia por um de dois caminhos. Os dois usam o mesmo arquivo (a planilha **Dados do criador**) e dão o mesmo resultado.

### Caminho principal: leitura automática (o Claude envia)

1. O Claude lê o Backstage todo dia de manhã e envia a planilha para o app. Ninguém precisa subir arquivo.
2. Quando a leitura chega limpa, o app grava sozinho. O Dashboard mostra "Backstage importado hoje às HH:MM pela leitura automática".
3. **Se a leitura chegar com problema** (linha com erro, mais de 5 saídas de uma vez, período no futuro), o app **não grava sozinho**: avisa as sócias e as gestoras no sininho e mostra o botão **Conferir e gravar** no Dashboard. Abra, confira os números e clique em **Confirmar e gravar**, ou descarte e use o plano B.
4. **Se a leitura não chegar até as 10h**, o Dashboard avisa e pede o plano B.

**Ligar a leitura automática (só as sócias):** menu **⬆️ Importar dados** → quadro **Leitura automática** → **Ligar: gerar chave**. A tela mostra, uma única vez, as instruções prontas com a chave: clique em **Copiar instruções com a chave** e entregue ao Claude que faz a leitura. A chave é como uma senha da agência. Perdeu? Gere outra (a antiga para de funcionar). Para desligar, use **Desligar** no mesmo quadro.

A hora-limite (10h) e o limite de saídas (5) ficam em Configurações → Configurações da agência.

### Plano B: subir a planilha pela tela (gestão ou sócias)

1. No TikTok Backstage, exporte **Dados do criador** com o período do mês corrente (do dia 1 até ontem).
2. No app: menu **⬆️ Importar dados** → escolha o arquivo → **Pré-visualizar**.
3. Confira os números: novos (viram cadastro pendente), atualizados, saídas detectadas e erros. Linhas com erro não são gravadas.
4. Clique em **Confirmar e gravar**. O app recalcula níveis, grupos, alertas e a fila.
5. **Dia 1 de cada mês:** importe também o mês anterior completo. A planilha **Task** (fechamento) é sempre pela tela, pelas sócias ou pelo financeiro: ela não entra pela leitura automática.
6. **Errou?** Abra a importação no histórico e clique em **Desfazer importação**. Tudo volta ao estado anterior. Vale também para o que chegou pela leitura automática.

Dicas: reenviar o mesmo arquivo não duplica nada, por nenhum dos dois caminhos. Se o TikTok mudar o nome de alguma coluna, a leitura automática é recusada com aviso; suba a planilha pela tela, que pede para mapear as colunas e guarda o modelo para as próximas vezes.

## 2. Dar acesso ao app para um criador

1. Creators novos aparecem sozinhos depois da importação, com status **Cadastro pendente**. Nada é enviado sozinho.
2. **Cole o link do grupo individual** do criador (quadro "Grupo individual no WhatsApp", link `https://chat.whatsapp.com/...`). É para onde vão os botões **Abrir grupo** da gestão e **Falar com a Hera** do app. Sem o link, eles abrem o WhatsApp pelo número.
3. Abra o creator (menu **👥 Creators**) → quadro **Acesso ao app** → **Gerar código de acesso**. Aparecem o código (ex.: `ABCD-2345`), a validade e a mensagem pronta.
4. Clique em **Copiar mensagem** → **Abrir grupo** → cole e envie → marque **Enviei**.
5. O criador abre o link, toca em **Primeiro acesso ou senha nova**, informa o @ do TikTok, o código e o e-mail e cria a senha. Depois aceita o termo LGPD. Dali em diante entra com e-mail e senha.
6. **Esqueceu a senha?** Gere outro código no mesmo quadro ("Gerar código para senha nova") e envie no grupo. O criador preenche a mesma tela, com a senha nova.
7. O código vale **uma vez**, por 7 dias. Gerar outro cancela o anterior. Depois de 5 erros seguidos o código é cancelado: gere outro.
8. Criadores de grupos parceiros só acessam o app se o grupo estiver liberado em Configurações → Grupos parceiros. Quem saiu da agência não recebe código e perde o acesso.

**Acesso da equipe (gestoras e demais):** as sócias cadastram em Configurações → Usuários (e-mail e senha) e depois em Configurações → Papéis. Para trocar a senha de alguém da equipe, as sócias abrem o usuário em Configurações → Usuários.

## 3. Carteiras (só as sócias)

Menu **🗂️ Carteiras**. É onde as sócias dividem os criadores entre as gestoras.

**Passar criadores de uma carteira para outra:**

1. Em **Criadores**, escolha a carteira no filtro (ou "Sem gestora") e clique em **Filtrar**.
2. Marque os criadores. A caixa do cabeçalho marca todos.
3. Em "Passar os marcados para", escolha a gestora (ou "Sem gestora") e clique em **Mover**.

A gestora nova passa a ver os criadores na hora, e a anterior deixa de ver. **O histórico vai junto:** mensagens, respostas, notas e 1:1. A troca fica na linha do tempo da ficha, e as duas gestoras recebem um aviso no app. Para um criador só, também dá para usar o quadro **Carteira** da ficha.

**O que a tabela Gestoras mostra:** tamanho da carteira, quantos estão em onboarding, as mensagens na fila de hoje (e quantas passaram do teto e ficam para amanhã), quem cobre, se a gestora trabalha hoje e os dias sem trabalhar no mês. Use esses números para equilibrar as carteiras.

**Quem cobre:** escolha uma sócia ou uma recrutadora para cada gestora e clique em **Salvar**. Sem escolha, cobrem as sócias. Veja o item 3.1.

A coluna "Sugestão do Backstage" é o Agente da exportação. É só uma sugestão.

### 3.1 "Hoje não trabalho"

Quando a gestora não vai trabalhar no dia:

1. **A gestora** abre o Dashboard → **Hoje não trabalho** → **Confirmar**. A tela já diz quantos itens não podem esperar e para quem vão.
2. **Os itens do dia passam para amanhã**, na mesma ordem. Nada se perde.
3. **O que não pode esperar vai para quem cobre:** D10, D12, D14, encerramento, batalha oficial e restrição. Quem cobre vê o quadro **Cobertura de hoje** no próprio Dashboard, envia a mensagem e marca **Enviei**. Na ficha, pode registrar a resposta e uma nota. O resto da ficha fica só para leitura.
4. **As sócias** recebem um aviso e também veem o quadro de cobertura.
5. Voltou? **Voltei: vou trabalhar hoje**, no Dashboard. A cobertura termina na hora.

Se a gestora não conseguir abrir o app, uma sócia marca por ela: **Carteiras** → coluna Hoje → **Marcar ausência**. Ali também dá para marcar um dia que ainda vai chegar e para desfazer.

Quem cobre enxerga a carteira **só naquele dia**. Para uma ausência longa (férias, licença), passe os criadores para outra carteira.

## 4. Criar campanha

**O app não mostra ranking de campanha.** Ranking e progresso ficam no TikTok. No app, cada campanha é um card com o resumo do que fazer e os prêmios. **Tocar no card abre a campanha direto no TikTok.** Embaixo da lista fica o botão **Chamar minha gestora**.

**Campanha oficial (Backstage): só os destaques do mês.** Não é preciso cadastrar todas as campanhas do TikTok, só aquelas em que a Hera quer que o streamer foque.

1. Crie a campanha no **TikTok Backstage**, como hoje, e copie o link dela.
2. No app: **🏆 Campanhas** → **Nova campanha**, com origem **Oficial (Backstage)**, e marque **destaque do mês**. Sem essa marcação, a campanha não aparece para o streamer.
3. Preencha **o que o streamer deve fazer** em 2 a 4 linhas simples (ex.: "Faça 1h de LIVE em 15 dias do mês e some 40h"), os **prêmios**, início, fim e o **link da campanha no TikTok**.
4. Escolha o **público**: Tiers, grupos, parceiras ou "só novatos". Vazio = todos. Para lista fechada de nomes, adicione os participantes na mesma tela.

**Campanha da Hera (interna, relâmpago, maratona).** Mesmos passos, com origem **Interna** ou **Relâmpago**, e também com **o que fazer**, **prêmios** e **link no TikTok**. Ela aparece na aba "Da Hera". A equipe continua vendo uma tabela de acompanhamento no painel, atualizada a cada importação, mas o streamer não vê ranking.

Se faltar o link do TikTok, o card abre uma página simples com o resumo e as regras. A tela de campanhas da gestão avisa quais campanhas estão **sem link do TikTok** e quais Tiers estão sem campanha ativa.

## 5. Criar treinamento (Academy)

1. Menu **🎓 Academy** → **Adicionar treinamento**.
2. Dê um título, escolha o público e salve.
3. Adicione as aulas na mesma tela: título, **link do vídeo** (YouTube não listado, Drive etc.), minutos e se é **obrigatória**.
4. Aulas obrigatórias aparecem em destaque na Academy e no Início do streamer até ele marcar como assistida.
5. O progresso de cada creator aparece no perfil dele (Treinamentos concluídos).

## 6. Publicar aviso

1. Menu **📣 Conteúdos** → **Novo aviso**.
2. Escreva título e texto e, se quiser, um link.
3. Escolha o público (grupos, Tiers, parceiras). Vazio = todos.
4. Para fixar no topo da tela inicial, marque **fixar no topo**.
5. Com "publicar em" para agora, o aviso vai na hora e cada streamer recebe uma notificação no app. Com data futura, a rotina diária publica no dia.

## 7. Registrar 1:1

1. Abra o creator → aba **1:1 e plano de ação**.
2. O bloco 1 (Performance) já vem preenchido com os números do mês. Complete os blocos 2 a 5.
3. Escreva de 2 a 3 ações com **responsável e prazo** (bloco 6) e a data do **próximo 1:1** (bloco 7).
4. Marque o que foi feito do plano anterior e "Revisei o plano anterior".
5. Salve. Sem todos os blocos, o 1:1 fica marcado como **incompleto** ("sem registro, não conta").
6. Planos vencidos e 1:1 atrasados entram sozinhos na **Fila de ação** do Dashboard.

## 8. Manter a ficha do criador

Abra o creator (menu **👥 Creators**). Na aba **Visão geral**:

1. **Cadastro:** defina a trilha (o app mostra a que o criador sugeriu no primeiro acesso), o **nicho** (um dos 5 do Playbook), se o criador **faz batalha**, a **recrutadora**, quem **indicou** (o @ de um criador da Hera, se houver) e o aniversário. Clique em **Salvar cadastro**. A trilha e o "Faz batalha?" decidem qual versão de cada mensagem o app mostra para esse criador. Para uma pessoa aparecer na lista de recrutadoras, as sócias dão a ela o papel Recrutadora em Configurações → Papéis.
2. **Linha do tempo:** tudo o que foi enviado, respondido e anotado aparece aqui, com data e autor. Use **Salvar nota** para anotações e **O criador me escreveu** quando ele chamar por conta própria.
3. **Lembretes:** escreva o lembrete, escolha a data e clique em **Criar lembrete**. No dia, ele aparece na Fila de ação. Quando resolver, clique em **Feito**.
4. **Parou de fazer LIVE?** Depois da conversa, registre o motivo da lista e, se o criador disse, a data de volta. Saúde: só a categoria, sem detalhes.

Na aba **Batalhas**, depois de cada batalha agendada, registre a data, o oponente, os rounds, o resultado e os diamantes dos dois lados, com uma observação para as próximas. O histórico ajuda a escolher o próximo oponente.

Na aba **Mensagens**, o "Roteiro deste criador" traz todos os scripts já na versão da trilha dele, com os ajustes do nicho no topo. O que é de outra trilha aparece marcado.

Na aba **Saída**, o motivo da lista é obrigatório.

## 9. Biblioteca de mensagens

Menu **💬 Mensagens**. São os scripts do Playbook do Gestor, por etapa (boas-vindas, Desafio dos 5 dias, fechamento dos 14 dias, régua de sem LIVE, rodízio, batalha oficial, saída e os outros).

1. **Achar uma mensagem:** use a busca ou o filtro por trilha. Cada mensagem mostra as variações (por trilha e para quem não faz batalha) e as variáveis que o app preenche sozinho, como `{nome}`.
2. **Quem edita:** só as sócias e quem tem o papel **Conteúdo**. As gestoras leem e copiam.
3. **Editar:** abra a mensagem → mude o texto → **Salvar**. O texto anterior vai para o **Histórico de versões**, com a data e quem trocou. Para voltar atrás, clique em **Restaurar esta versão**.
4. **Verificador de tom:** o app não salva mensagem com as palavras "meta", "cobrança", "prazo" ou "horário" (pode "horário de Brasília"), nem escrita só no feminino ("bem-vinda", "pronta"). Use "bem-vindo(a)" ou reescreva a frase.
5. **Etiquetas:** "provisório" é texto que ainda não veio do Playbook e espera a redação final. "tom" é texto do Playbook que tem uma palavra da lista acima e espera decisão das sócias.
6. **Ajustes por nicho:** no fim da tela, o guia dos 5 nichos (o que muda no D2, no D4 e nos ganchos).

**Sem resposta?** A cadência entra sozinha na fila, para qualquer criador da carteira: +24h, +2 dias, +3 dias (no privado) e +5 dias. No onboarding, ela vem depois de qualquer mensagem do roteiro. Depois do D15, vem depois da pergunta do 4º dia sem LIVE. Se o criador respondeu no grupo, marque **Respondeu** na ficha, que a cadência para. Depois do +5 dias sem resposta, a fila pede para acionar quem recrutou.

## Rotina sugerida da gestora (15 minutos por dia)

1. **Dashboard → Fila do dia.** Trate de cima para baixo: suporte, o que tem data, o que vem do dado e, por último, o rodízio. Em cada item: **Copiar mensagem** → **Abrir grupo** → cole e envie → **Enviei**. Só o "Enviei" registra o contato e tira o item da fila. Não dá para falar hoje? **Adiar**, com o motivo. Cada criador recebe no máximo uma mensagem por dia, cada gestora tem um teto de 30 por dia e no domingo a fila não traz envios. Não vai trabalhar hoje? **Hoje não trabalho**, no alto da fila (item 3.1).
2. **❓ Dúvidas e ⚔️ Batalhas:** responda os pedidos do dia. Pedidos de batalha oficial: agende no TikTok e marque como "Aprovada" com o horário na resposta; o streamer recebe a notificação.
3. **🌱 Onboarding:** confira quem está entre o Dia 1 e o Dia 15.

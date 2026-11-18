# HERA CREATOR HUB — Especificação do produto

> Versão 3 · 30/09/2026. Fonte oficial das regras do produto, com todas as decisões de 28 a 30/09.
> As regras que nunca podem ser quebradas estão resumidas em `CLAUDE.md`. O estado atual está em `docs/STATUS_E_PROXIMOS_PASSOS.md`.
> Especificação detalhada da Parte 1 (decisões, arquitetura, fluxos): https://claude.ai/code/artifact/2eb11d49-3c82-4abb-ae36-7706cffa650b

---

## Como trabalhar

- Parta do código existente: leia `README.md` e `docs/STATUS_E_PROXIMOS_PASSOS.md` antes de mudar qualquer coisa. Não reescreva o que já funciona.
- Trabalhe **uma etapa por vez**. Ao fim de cada etapa: rode os testes, mostre o que funciona e siga.
- Decisões pequenas: escolha a opção mais simples, mobile-first e segura, registre em `docs/` e continue.
- Decisões grandes: pare e apresente **DECISÃO NECESSÁRIA** (problema, opções, prós e contras, recomendação).
- As regras abaixo **já foram aprovadas**. Não reabra nenhuma sem me perguntar.
- Use apenas **dados fictícios** em seeds, testes, commits e telas de demonstração.

## 0. Fontes oficiais

Quando este prompt e um documento divergirem, siga o prompt (ele já resolveu as divergências conhecidas) e me aponte a diferença.

| Documento | Para quê |
|---|---|
| `Playbook_do_Gestor_Hera_final.docx` | Tiers, onboarding, scripts de mensagem, cadência de não-resposta, árvore de decisão, 1:1 de 7 blocos, faixas dos indicadores |
| `Gestao_de_Criadores_Hera_v2.xlsx` | Modelo de dados anterior (cadastro, onboarding D1–D15, 1:1, saídas, relatório ao streamer) |
| `Dados do criador AAAA_MM_DD.xlsx` | Formato real da exportação do Backstage (PT) |
| `_Task_AAAAMM.xlsx` | Formato real da exportação Task (EN) |
| `Campanhas_Setembro_Hera.docx` | Como as campanhas são desenhadas por Tier |
| `Manual da Agência Hera.pdf` | Regras para o streamer. **Atenção:** o Manual fala em 4 meses para voltar após a saída; a regra oficial agora é 90 dias e o Manual será corrigido |
| `Incentivos Internos da Agência.pdf` | Política de premiação |

## 1. O produto

**Hera Creator Hub:** Web App responsivo, mobile-first e instalável como PWA para a **Agência Hera** (TikTok LIVE, Brasil). Tem duas áreas: a do **streamer** (celular) e a da **gestão** (desktop).

A pergunta que o app responde ao streamer: **"O que eu preciso fazer esta semana para melhorar meu resultado?"**

Contexto da operação:

- Cerca de 160 creators ativos, 93% no Tier 1. Cerca de 80% pertencem a **grupos parceiros** (coluna Grupo: Impulse, Lunow, Bia Baillo etc.). "Não está em um grupo" = creator direto da Hera.
- A operação hoje roda em WhatsApp (grupo individual com a gestora + Grupo de Avisos), TikTok Backstage e planilhas.
- Idioma: português do Brasil. Exibição no fuso America/Sao_Paulo.

## 2. Decisões de arquitetura (fechadas)

| # | Decisão |
|---|---|
| D1 | **Banco multi-agência, interface só Hera.** `agency_id` em todas as tabelas. Parceiras são `partner_groups` dentro da agência, não agências separadas. Motivo: a Hera pode vender o sistema a outras agências |
| D4 | **Stack:** Django 5 + HTMX + Alpine.js + CSS próprio (sem build). Postgres e app no **Railway** (plano Hobby, ~US$ 10–20/mês). Login com **django-allauth** (código por e-mail + Google; senha opcional; sessão persistente). Tarefas agendadas por cron do Railway chamando comandos Django. Arquivos em armazenamento compatível com S3 (ex.: Cloudflare R2). PWA com manifest e service worker próprios |
| — | **Segurança em duas camadas:** filtros por papel e carteira no Django **e** RLS no Postgres. O app conecta com um usuário de banco **sem superusuário** e informa o usuário logado a cada requisição (`app.user_id`). Os testes de isolamento atacam as duas camadas |
| D5 | **Tier oficial = mês fechado.** Não existe "Tier em andamento". Durante o mês, o streamer vê o Tier oficial e a barra "faltam X diamantes para o Tier N neste mês". Quem ainda não tem mês fechado fica no Primeiro Mês e no Tier 1 |
| D6 | **Importação semanal:** toda segunda de manhã, mais o dia 1 de cada mês para fechar o mês. Importação extra opcional no meio da semana quando houver novato entre o Dia 7 e o Dia 14. Alerta de dados velhos após **8 dias** sem importação |
| D8 | **Todos os creators** entram no banco pela importação. O acesso de streamer é **liberado por grupo parceiro** (liga/desliga), começando pela Hera direta. Painel para gestor de parceira fica para a V2 |
| D10 | **Sem IA.** A API oficial do WhatsApp fica **pronta na arquitetura** (tabela `outbox`) mas **desligada** até medir a necessidade (seção 9) |

## 3. Regras de negócio

### 3.1 Tiers (configuráveis no admin)

| Tier | Diamantes/mês | Fase |
|---|---|---|
| 1 | 0 – 39.999 | Aprender e criar hábito |
| 2 | 40.000 – 79.999 | Aprender e criar hábito |
| 3 | 80.000 – 149.999 | Criar consistência |
| 4 | 150.000 – 249.999 | Criar consistência |
| 5 | 250.000 – 349.999 | Desenvolver performance |
| 6 | 350.000 – 499.999 | Desenvolver performance |
| 7 | 500.000 – 799.999 | Desenvolver performance |
| 8 | 800.000 – 1.199.999 | Escalar com maturidade |
| 9 | 1.200.000 – 1.599.999 | Escalar com maturidade |
| 10 | 1.600.000+ | Escalar com maturidade |

Limite inferior inclusivo. Graduação do novato: 80.000 diamantes em até 90 dias.

### 3.2 Grupos (configuráveis no admin)

| Grupo | Regra |
|---|---|
| **Primeiro Mês** | Todo streamer novo. Definido pelo **tempo de casa**: termina no **dia 30** após a entrada |
| Bronze | Tier 1–2 |
| Prata | Tier 3–4 |
| Ouro | Tier 5–7 |
| Diamante | Tier 8–10 |

- Fora do Primeiro Mês, o grupo muda no **fechamento do mês**, junto com o Tier oficial.
- Cada troca de grupo notifica o streamer e a gestora, e fica no histórico com o motivo (ex.: "fim do Primeiro Mês").
- Cumprir a meta do onboarding vira **conquista**, não troca de grupo.

### 3.3 Dia válido, metas e onboarding

- **Dia válido:** 1h de LIVE no dia (LIVE < 30 min não conta; duas LIVEs de 35 min validam). O app usa a coluna "Dias válidos" do TikTok.
- **O dia TikTok é UTC:** vai das 21h às 20h59 de Brasília. Contagem em UTC, exibição em São Paulo. Lembrete fixo ao streamer: "seu dia fecha às 21h".
- **Meta do onboarding:** 5 dias válidos e 15h em 14 dias. **Meta em risco** = chegar ao Dia 10 sem esse ritmo.
- **Dois relógios no onboarding:** "dia de casa" (desde a entrada) e "dia do desafio" (desde a 1ª LIVE).
- **Meta mensal:** a meta do TikTok é **derivada** (valor ÷ % alcançada) para cada métrica. A gestão pode definir **meta individual** por cima, para **diamantes, horas e dias válidos**.

### 3.4 Carteira

- **Todo creator tem uma gestora única**, atribuída **manualmente** (uma a uma ou em lote).
- A coluna Agente (e-mail da gestora) é **só sugestão**.
- A carteira tem histórico (início e fim de cada atribuição).
- Isso também vale para agências que comprarem o sistema.

### 3.5 Saída e retorno

- Saída nos **primeiros 15 dias**: a agência remove; o creator pode voltar **a qualquer momento**.
- Saída **depois de 15 dias**: aviso prévio de até 30 dias; só pode voltar **após 90 dias** (configurável).
- O registro de saída mostra a **data em que o retorno fica liberado**.
- Quem sai perde premiações do mês e campanhas ativas.
- Na volta, o app **reativa o mesmo cadastro** (mesmo ID do TikTok) e guarda cada passagem pela agência.

### 3.6 Indicadores (faixas do Playbook, ajustadas)

- **Frequência de LIVE:** ruim ≤ 2 dias/semana, moderado 3–5, bom 6–7.
- **Diamantes:** ruim < 10k/mês, moderado 10k–59.999, bom ≥ 60k.
- **Batalhas:** bom = 2+ por LIVE e 6+ por semana; pico entre 20h e 21h.
- **Saída em 15 dias:** boa < 10%.
- **Árvore de decisão:** "primeiro cai a LIVE, depois cai o diamante". O alerta de queda sempre diz se a frequência caiu antes.
- **Audiência (UV) não existe na exportação:** fica fora.

### 3.7 Dinheiro

**O app não importa nem mostra valores de bônus ou de moeda para ninguém.** As colunas de bônus da Task são ignoradas. O streamer vê apenas conquistas derivadas do "Status do nível" do TikTok (ex.: "você manteve seu nível este mês").

### 3.8 Comunicação

- Meta interna de resposta da gestora: 2h. Promessa ao streamer: até 24h em dias úteis.
- Cadência de não-resposta: +24h, +2 dias, +3 dias (remetente muda para o papel "líder de gestão"), +5 dias.

## 4. Realidade dos dados

**Backstage "Dados do criador" (PT):**

- É **acumulada do período** (ex.: `2026-05-01 ~ 2026-05-19`), não diária.
- **Tudo vem como texto.** Durações como `90h 2m 52s`, `59m 31s`, `0s`; percentuais como `48.81%`, `-100.00%`; `-` = vazio.
- **ID de 19 dígitos:** guardar como texto.
- **Quem saiu perde o ID:** vem como "O criador deixou a agência", com Agente e ingresso vazios. Casar pelo **username** e abrir o registro de saída.
- As colunas variam entre 36 e 41 (algumas versões trazem Novos fãs e fã-clube).
- "Status do nível" e "Status da graduação" são do TikTok e ficam **ao lado** dos Tiers Hera, sem misturar.

**Task (EN):** números já tipados, mês como `202606`, flag de violação, flag Rookie. Colunas de bônus ignoradas.

**Importação:** upload → detectar template ("Backstage PT", "Task EN") pela assinatura dos cabeçalhos → mapear colunas novas uma vez e salvar → validar → prévia (atualizados, novos, saídas, erros) → gravar snapshot → recalcular → registrar quem importou e quando.

- Upsert por creator + período.
- Hash do arquivo impede reimportação idêntica.
- **Desfazer** apaga os snapshots do lote e recalcula.
- Creator novo vira cadastro **pendente** (sem convite automático).
- A gestão **nunca edita números**: tudo sai dos snapshots.

**Cálculos:**

- **Métricas semanais** = diferença entre snapshots consecutivos do mesmo mês ("sem LIVE desde a última importação" quando Δ horas = 0).
- **Ritmo:** média/dia = diamantes ÷ dias decorridos; necessário/dia = (meta − diamantes) ÷ dias restantes; 🟢 se média ≥ necessário, 🟠 se não.
- **Previsão:** diamantes + média/dia × dias restantes.
- **Fora do MVP** (dependem de dado diário): sequência de dias, melhor dia, melhor horário.

## 5. Papéis e permissões

Papéis: Admin, Gestora, Recrutadora, Conteúdo, Financeiro, Analista (leitura), Streamer e Gestor de parceira (V2).

- **Streamer:** só os próprios dados. Nunca lê tags, notas, 1:1 nem dados de outros, **nem por URL ou API** (bloqueado no banco, não só na tela).
- **Gestora:** a carteira vigente.
- **Recrutadora:** quem ela recrutou.
- **Conteúdo:** edita avisos, Academy, dicas, Q&A, templates, campanhas, benefícios e pesquisas.
- **Admin:** tudo, incluindo importação, configurações e usuários.
- WhatsApp e dados pessoais ficam em tabela separada, com acesso mínimo.

**LGPD:** termo aceito no 1º acesso (versão registrada), `audit_log` de ações administrativas, anonimização agendada após a saída.

## 6. Área do streamer (celular)

**Navegação inferior:** Início · Desempenho · Campanhas · Academy · Dúvidas. Perfil fica no avatar, ao lado do sino de notificações. Telas em cartões clicáveis e compactos.

**Início, nesta ordem:**

1. "Dados até DD/MM · importados em DD/MM às HH:MM".
2. **Meu mês:** diamantes, meta, %, quanto falta, necessário/dia × média, status 🟢/🟠, previsão.
3. **Missão da semana:** até 4 ações geradas por regras (ex.: "faltam 2 dias válidos", "faça 1h antes das 21h", campanha terminando, treino pendente), mais lembretes fixos que não dependem de dados.
4. **Meu Tier e grupo:** barras de diamantes, horas e dias válidos até o próximo Tier.
5. Campanhas em destaque, Dica da Hera, próximo treino e atalhos para **Benefícios** e **Pedir batalha**.

**Desempenho:** abas Mês e Histórico. Compara o creator **com ele mesmo** ("+18% vs. mês passado", "seu melhor mês foi agosto").

**Campanhas:**

- **Campanhas oficiais do TikTok:** o app **não espelha todas nem mostra ranking**, porque o streamer já vê isso no TikTok. Aparecem só as marcadas como **"destaque do mês"**, com o resumo "O que você deve fazer", os prêmios e o botão **"Abrir a campanha no TikTok"**.
- **Campanhas internas da Hera** (relâmpago etc.): têm ranking, sempre **entre pares do mesmo Tier**, mostrando só @, Tier e valor.

**Academy:** aulas por link (YouTube, Drive, Vimeo etc.), progresso por aula. O treino "Xô Restrições e Banimentos" é obrigatório no primeiro acesso.

**Dúvidas ("Pergunta pra Hera"):**

- Busca **sem IA** em perguntas e respostas cadastradas, feita com a busca de texto em português do Postgres.
- Ignora acentos e usa sinônimos ("PK" = batalha).
- Respostas podem ter **variáveis com os números do streamer**.
- Botão "Perguntar para minha gestora".
- Termos buscados sem resultado viram uma lista para o perfil Conteúdo.

**Botão "Chamar minha gestora"** (em Campanhas, Dúvidas e Perfil): abre o link do grupo individual no WhatsApp, colado pela gestora no perfil do creator. Sem link, cai no WhatsApp da gestora ou da agência.

**Também no MVP:**

- **Benefícios:** cupons e parcerias por Tier ou grupo, com "link de parceiro" sinalizado quando gerar comissão.
- **Pesquisas:** uma pergunta por tela, NPS, anônima opcional.
- **Pedido de batalha especial:** a gestora aprova; o app avisa se a LIVE cruzar as 21h.
- Notificações dentro do app.

**Primeiro acesso:** convite da gestora → código por e-mail ou Google → termo LGPD → confirmar o @ → 3 regras (dia fecha às 21h, 1h valida o dia, 5 dias e 15h em 14 dias) → treino obrigatório → instalar como app.

Linguagem próxima, humana e motivadora. Gamificação sem infantilizar.

## 7. Área da gestão (desktop)

- **Dashboard com fila de ação** limitada à carteira e ordenada por urgência: onboarding em risco (Dia 10), sem LIVE, queda > 30%, cadência vencida, perto de graduar, 1:1 atrasado, plano de ação vencido, chamados de dúvida, pedidos de batalha.
- **Perfil do creator:** abas Visão geral, 1:1, Onboarding, Mensagens, Campanhas e Saída. Inclui tags internas, notas, 1:1 de 7 blocos (bloco 1 já preenchido com os números), plano de ação com prazo, histórico de contatos e de passagens pela agência.
- **Onboarding D1–D15:** marcação automática pelos snapshots (1ª LIVE, 3 LIVEs, meta 5 dias e 15h).
- **Mensagens:** são **42 modelos** (`engage/defaults.py`): 39 vindos dos scripts do Playbook (alguns divididos em partes, como a saída após 15 dias) + 3 criados para o app (relatório mensal, convite para o app, lembrete semanal de meta). Cada um tem código próprio (ex.: ONB-D2-01) e variáveis, com botão de copiar e link para o WhatsApp.
  - O app registra cada contato e controla a cadência de não-resposta.
  - Relatório mensal individual e **em lote**.
  - **Disparo assistido** por público: a lista vem com o texto de cada pessoa preenchido e a gestora envia um por um, do WhatsApp dela.
- **Importar dados**, **Relatórios** (mensal da agência e por gestora, exportação CSV, métricas de sucesso) e **Configurações** (Tiers, grupos, faixas, alertas, carência, templates, gatilho da API do WhatsApp).
- Cadastros de conteúdo (campanhas, Academy, avisos, Q&A, benefícios, pesquisas) ficam no painel do Django por enquanto.

## 8. Escopo por versão

**MVP (construído):** tudo das seções 5 a 7, a importação com snapshots e as regras da seção 3.

**V2:**

- Conquistas, badges e sequências (marcos 25k, 50k, 80k, 150k).
- Campanhas de pontos de 3–6 meses com extrato (a tabela `points_ledger` já existe).
- Comunidade: perfis, feed de apresentação, depoimento, conquista e divulgação, com moderação.
- API oficial do WhatsApp, se aprovada.
- Criador de segmentos, biblioteca com busca, quiz pós-treino.
- Acesso para gestores de parceiras e **fechamento por parceira** em XLSX.
- Push notifications, Google Sheets, orçamento de prêmios (payout digitado à mão pela gestão), pareamento de batalhas, agenda "Batalhas da semana".

**V3:** IA (resumo semanal, coach, risco de saída), réguas automáticas por WhatsApp e e-mail, módulo de recrutadoras integrado ao Argus, abertura comercial multi-agência (cadastro de agências, planos, cobrança).

## 9. API oficial do WhatsApp: quando ligar

1. **Nos 2 primeiros meses do MVP**, o disparo assistido registra por semana: mensagens enviadas, quantas eram texto em lote, tempo estimado da gestora e taxa de resposta.
2. **Gatilho para testar:** número definido pela gestão, **editável nas configurações** (referência: ~150 mensagens em lote por semana).
3. **Teste de 30 dias:** 1 tipo de mensagem, metade dos streamers, comparando frequência de LIVE e tempo da gestão com a outra metade.
4. **Mantém** se a frequência subir ou se economizar pelo menos 2h por semana.

Custo de referência (conferir a tabela da Meta antes de ligar): utilidade ≈ R$ 0,035 por mensagem, marketing ≈ R$ 0,32; 150 streamers ≈ R$ 40–235/mês; respostas dentro de 24h são grátis. **Nunca** usar APIs não oficiais nem automação do WhatsApp Web.

## 10. Identidade visual

- Primária: roxo `#5c019b`.
- Ação/destaque: rosa `#fb4fa5`.
- Dados: ciano `#5de9f3`.
- Conquistas: dourados `#f4af55` / `#ecbb58`.
- Base neutra, com tema claro e escuro. Usar o logo da Hera no ícone do app.

## 11. Medição de sucesso (página só para Admin)

| Métrica | Meta |
|---|---|
| % de streamers que abrem o app na semana | O máximo possível, sem teto. O painel mostra a % semanal e a tendência |
| Frequência de LIVE da base (dias/semana) | Subir 1 faixa na mediana em 3 meses |
| Saída em 15 dias | < 10% |
| Novatos com 5 dias e 15h em 14 dias | Linha de base + 20 p.p. |
| Horas manuais economizadas por gestora | ≥ 5h/semana |

## 12. Testes obrigatórios

- **Isolamento:** streamer A não lê B; gestora X não lê a carteira de Y; streamer não lê tags, notas nem 1:1, nem por API direta. Nas duas camadas.
- **Importação:** upsert, reimportar sem duplicar, conversão de duração, % e fuso, ID de 19 dígitos, coluna renomeada, linha "deixou a agência", desfazer.
- **Cálculos:** Tier nas bordas (39.999 / 40.000), fim do Primeiro Mês no dia 30, meta derivada, ritmo, previsão, métricas semanais, regra de 15 e 90 dias na saída e no retorno.
- **Telas do streamer** testadas em 375px de largura.
- Verificação automática de que o app **não** conecta ao banco como superusuário (`hera.E001`).

## 13. Próximos passos (a partir de 30/09)

1. Publicar no Railway (`docs/COMO_RODAR_E_PUBLICAR.md`), criar o usuário de banco sem superusuário e agendar `rotina_diaria` às 06h.
2. Trocar o ícone pelo logo da Hera.
3. Revisar os textos: 42 mensagens e 23 perguntas e respostas.
4. Importar os dados reais de julho a setembro e conferir 5 creators contra o Backstage.
5. Piloto de 2 semanas: 1 gestora, ~20 streamers da Hera direta.
6. Liberar para toda a base direta, depois grupo a grupo.
7. Após 2 meses, decidir sobre a API do WhatsApp (seção 9).
8. Começar a V2.

Ao terminar qualquer etapa, atualize `docs/STATUS_E_PROXIMOS_PASSOS.md` com: o que foi feito, o que falta, como testar e decisões pequenas tomadas.

# Como rodar e como publicar

Guia para quem não é programador. Leva cerca de 30 minutos na primeira vez.

## A. Rodar no seu computador (para testar)

Você vai precisar instalar duas coisas: **Python 3.11 ou mais novo** (python.org) e **PostgreSQL 16** (postgresql.org/download). No Windows, marque "Add Python to PATH" na instalação.

1. **Abra o terminal** na pasta `hera-hub` (no Windows: clique com o botão direito na pasta → "Abrir no Terminal").
2. **Instale as dependências:**
   ```
   python -m pip install -r requirements.txt
   ```
3. **Crie o banco e o usuário do app.** Abra o "SQL Shell (psql)" que veio com o PostgreSQL, entre com o usuário `postgres` e cole:
   ```sql
   CREATE ROLE hera_app LOGIN PASSWORD 'hera' NOSUPERUSER CREATEDB NOBYPASSRLS;
   CREATE DATABASE hera OWNER hera_app;
   ```
   O usuário do app **não pode ser superusuário**: é isso que faz as regras de segurança (quem vê o quê) valerem dentro do banco.
4. **Crie as tabelas e os dados de demonstração:**
   ```
   python manage.py migrate
   python manage.py seed_demo
   ```
5. **Ligue o app:**
   ```
   python manage.py runserver
   ```
6. **Abra** http://localhost:8000 no navegador. Entre com um destes usuários (senha `hera-demo-2026`):

| Usuário | Vê |
| --- | --- |
| `admin@hera.demo` | Tudo, importação e configurações |
| `gestora1@hera.demo` | Só a carteira dela |
| `streamer01@hera.demo` | A tela do streamer |

Esses logins são só para o seu computador. **Eles não podem existir em produção** (veja "Depois de publicar").

Para ver a fila do dia cheia, com uma semana de verdade (o arquivo fica fora da pasta `hera-hub`):
```
python manage.py demo_semana --arquivo "..\exemplo-semana.json"
```
Entre com `admin@semana.demo` ou `gestora.a@semana.demo` até `gestora.e@semana.demo` (mesma senha).

Para ver a tela do streamer como no celular: no Chrome, aperte F12 e clique no ícone de celular.

Para rodar os testes automáticos: `python manage.py test tests`.

## B. Publicar no Railway

Custo inicial estimado: US$ 5–10/mês (veja STATUS_E_PROXIMOS_PASSOS.md).

**Antes de começar, instale no seu computador:**
- **Python 3.11 ou mais novo** (python.org). Na instalação, marque "Add Python to PATH". Depois, no terminal da pasta `hera-hub`, rode `python -m pip install -r requirements.txt`. O Python é necessário no passo 3.
- **GitHub Desktop** (desktop.github.com). Ele respeita o arquivo `.gitignore`, então não envia a pasta `seeds/`, o arquivo `.env` nem outros arquivos temporários. **Não use o upload por arrastar no site do GitHub:** ele envia tudo, inclusive o que deveria ficar de fora.

1. **Suba o código para o GitHub.** No GitHub Desktop: File → Add local repository → escolha a pasta `hera-hub` → "create a repository" → Publish repository, **com "Keep this code private" marcado**.
   **Antes de clicar em Publish, olhe a lista de arquivos à esquerda do GitHub Desktop:** não pode aparecer nada de `.venv`, `seeds`, `staticfiles`, `.env` nem arquivos começando com `~$`. Se aparecer, pare e avise: o `.gitignore` está deixando passar algo.
2. **Crie o projeto e o banco no Railway.** railway.com → assine o plano Hobby (US$ 5/mês) → New Project → Database → PostgreSQL. Ainda não crie o app.
3. **Crie o usuário do app no banco (passo obrigatório de segurança).** No seu computador, no terminal da pasta `hera-hub`, rode:
   ```
   python manage.py criar_usuario_banco --admin-url "COLE_AQUI_O_DATABASE_PUBLIC_URL"
   ```
   O `DATABASE_PUBLIC_URL` fica na aba Variables do serviço Postgres. O comando cria o usuário `hera_app` (sem superusuário) e mostra uma nova `DATABASE_URL`. Guarde essa URL: ela é uma senha. Rode o comando no seu próprio terminal (não cole a URL em conversas, nem na do Claude) e feche o terminal no fim.
   A URL usa o endereço público do banco e funciona tanto no app quanto no seu computador (passo 9). Se quiser economizar um pouco de tráfego, no app você pode trocar o endereço e a porta pelos internos, que aparecem na `DATABASE_URL` do Postgres (algo como `postgres.railway.internal:5432`). Mantenha o usuário `hera_app` e a senha nova.
4. **Crie o app.** No projeto: New → GitHub Repo → escolha o repositório. Na aba Variables do app, cole a `DATABASE_URL` do passo 3. **Nunca use a `DATABASE_URL` do usuário `postgres` no app.**
5. **Cadastre as outras variáveis** do arquivo `.env.example` na aba Variables do app:
   - `DEBUG=0`
   - `SECRET_KEY`: uma frase longa e aleatória. Sem ela, o app não liga em produção. Para gerar, rode no terminal da pasta `hera-hub`:
     ```
     python -c "import secrets; print(secrets.token_urlsafe(50))"
     ```
     Copie o resultado direto para a aba Variables. Ela é uma senha: não mande por WhatsApp nem cole em conversas.
   - `ALLOWED_HOSTS=.up.railway.app` (depois acrescente o seu domínio, separado por vírgula)
   - `CSRF_TRUSTED_ORIGINS=https://*.up.railway.app`
6. **E-mail: não é mais necessário** (desde 14/11/2026). O app não envia e-mails: o criador entra com o código que a gestora manda no grupo e cria a própria senha. Pule este passo e deixe as variáveis `EMAIL_*` de fora.
7. **Configure como o app liga.** No serviço do app, vá em Settings:
   - Em **Custom Start Command**, cole:
     ```
     python manage.py check --deploy --database default --fail-level ERROR && python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 120
     ```
     A primeira parte é a trava de segurança. O app **não liga** em dois casos: se estiver conectado ao banco como superusuário (o log mostra o erro `hera.E001`) ou se o banco tiver algum login de demonstração (erro `hera.E002`).
   - Em **Healthcheck Path**, coloque `/accounts/login/`.
8. **Publique.** O Railway faz o deploy sozinho a cada envio para o GitHub. Em Settings → Networking, clique em "Generate Domain" (ou ligue seu domínio, ex.: app.hera.com.br).
9. **Crie o primeiro Admin.** Depois que o primeiro deploy terminar (ele cria as tabelas), rode no terminal da pasta `hera-hub` do seu computador (PowerShell), usando a URL do passo 3:
   ```
   $env:DATABASE_URL="COLE_AQUI_A_URL_DO_PASSO_3"; python manage.py criar_admin --email seuemail@dominio.com --nome "Seu nome" --agencia "Agência Hera" --senha "UMA_SENHA_COM_8_OU_MAIS"
   ```
   Entre no app com esse e-mail e essa senha. Sem `--senha`, o comando cria uma senha provisória e mostra na tela. O mesmo comando serve para trocar a senha de uma sócia que esqueceu. Feche o terminal depois, para a URL e a senha não ficarem guardadas nele.
10. **Agende a rotina diária.** No projeto: New → GitHub Repo → o mesmo repositório. Nesse novo serviço:
    - Em Settings → **Custom Start Command**, coloque `python manage.py rotina_diaria`.
    - Em Settings → **Cron Schedule**, coloque `0 9 * * *`. O Railway conta em UTC: 9h UTC são 6h de Brasília.
    - Em Variables, use as mesmas variáveis do app.
11. **Login com Google: removido** (desde 14/11/2026). Todos entram com e-mail e senha.

### Depois de publicar

- **Logins de demonstração não podem existir em produção.** São os e-mails `@hera.demo` (como `admin@hera.demo`, `gestora1@hera.demo`, `streamer01@hera.demo`) e `@semana.demo` (`admin@semana.demo` e `gestora.a@semana.demo` até `gestora.e@semana.demo`). A senha deles (`hera-demo-2026`) está escrita neste guia, então qualquer pessoa que leia o guia entraria no app.
  - **Não rode `seed_demo` nem `demo_semana` em produção.** Os dois comandos se recusam a rodar com `DEBUG=0`.
  - **Não copie o banco do seu computador para produção.** Produção começa com banco novo, e a única conta criada à mão é a da sócia (passo 9).
  - Se um desses logins aparecer no banco de produção, o app não liga e o log mostra `hera.E002`.
- **Backups:** o Postgres do Railway tem backups; confira na aba Backups do banco.
- **Imagens de banner das campanhas:** por enquanto, não envie imagens pelo painel de cadastros. No Railway, os arquivos enviados se perdem a cada nova versão. Os cards de campanha funcionam sem imagem.
- **Atualizações:** cada envio ao GitHub publica uma nova versão e aplica as mudanças no banco automaticamente.

## C. Teste da gestão com dados reais

Decidido em 18/11/2026: publicar o que já existe para a gestão trabalhar com dados reais, enquanto a parte do criador (etapa 3) continua sendo construída. As próximas etapas ficam pausadas até a publicação estar de pé.

### O que já foi conferido no código (18/11)

- **Simulação num banco novo e vazio, como o de produção:** as tabelas são criadas do zero sem erro, a trava de segurança passa, a conta da sócia é criada pelo `criar_admin` e o `seed_demo` se recusa a rodar.
- **Corrigido um defeito que só aparecia em produção:** quem tinha papel de sócia ou Conteúdo ficava sem acesso a ⚙️ Configurações, Hera Academy e aos outros cadastros. Há um teste para não voltar (`tests/test_publicacao.py`).
- **`.gitignore` completo:** a pasta `.venv` (programas instalados) e os temporários do Word (`~$...`) não vão para o GitHub. A pasta `seeds/` (dados reais) e o `.env` já ficavam de fora.

Custo: plano Hobby do Railway, US$ 5 por mês para começar (estimativa de US$ 5 a 10 por mês; ver `STATUS_E_PROXIMOS_PASSOS.md`, seção 3). A assinatura e o cartão são feitos por você no site do Railway.

### O que a gestão já pode usar

Dashboard com a fila do dia, ficha do criador, carteiras e "Hoje não trabalho", onboarding, radar de graduação, biblioteca de mensagens (copiar, abrir grupo, "Enviei"), importação diária do Backstage, batalhas, campanhas, avisos, Hera Academy (cadastro de módulos e aulas) e relatórios. O passo a passo de cada um está em `docs/MANUAIS_GESTAO.md`.

### O que ainda não abrir para os criadores

**Não gere código de acesso para criadores durante o teste.** A parte do criador ainda está sendo terminada (faltam batalha oficial, campanhas, ajuda e Meu plano) e os vídeos da Hera Academy ainda são de exemplo. Sem código, nenhum criador entra: a gestão trabalha com os dados e os criadores não veem nada. A exceção são 1 ou 2 criadores de confiança, se a Hera quiser uma opinião antes do teste com 10.

### Ordem para começar (depois da parte B)

1. **Entre como sócia** (conta criada no passo 9 da parte B) e abra **⚙️ Configurações**.
2. **Cadastre as outras sócias e as gestoras.** Para cada pessoa:
   1. Configurações → **Usuários** → Adicionar. Em "Nome de usuário", escreva o **e-mail** da pessoa. Crie uma senha com 8 caracteres ou mais e salve.
   2. Na tela seguinte, preencha **Endereço de e-mail** (o mesmo e-mail) e o nome. Salve.
   3. Configurações → **Papéis** → Adicionar: escolha a pessoa e o papel ("Admin/CEO" para sócia, "Gestora de creators", "Recrutadora", "Conteúdo", "Financeiro" ou "Analista (somente leitura)"). Salve.
   4. Mande a senha para a pessoa por um canal privado.
3. **Suba os dados do Backstage.** Em ⬆️ Importar dados, envie os arquivos "Dados do criador" do mais antigo para o mais novo. Depois, os arquivos Task de fechamento de cada mês (só Admin ou Financeiro). Confira a pré-visualização antes de gravar cada um.
4. **Divida as carteiras.** Em 🗂️ Carteiras (só sócias), passe cada criador para a gestora certa. A coluna Agente do Backstage aparece só como sugestão.
5. **Confira 5 criadores que vocês conhecem bem:** números do mês, Tier, fase e fila do dia. Se algo não bater com o Backstage, anote o @ e o que estava diferente.
6. **Combine a rotina:** importação do Backstage todo dia de manhã (gestora ou sócia), e cada gestora trabalha pela fila do dia.
7. **Rotina diária automática:** no dia seguinte, confira em Deployments do Railway se o serviço da rotina (passo 10 da parte B) rodou.

### Durante o teste

- **Atualizações:** enquanto a parte do criador é construída, as mudanças ficam no seu computador. **Só envie ao GitHub (Push no GitHub Desktop) quando o Claude disser que a versão está pronta para publicar**, com os testes passando. Cada envio troca a versão que a gestão está usando.
- **Os dois bancos são separados.** O que a gestão faz no app publicado não aparece no `localhost` do seu computador, e o contrário também não.
- **Anote o que travar ou confundir:** a tela, o que tentou fazer e o que aconteceu. Isso vira a lista de ajustes.

### Decisões que são suas

- [ ] **Endereço:** começar com o endereço do Railway (algo como `hera-hub-production.up.railway.app`) ou já ligar um domínio da Hera (ex.: `app.hera.com.br`, que depende de quem cuida do domínio).
- [ ] **Quem entra no teste:** nomes e e-mails das sócias e gestoras.
- [ ] **Criadores no teste:** nenhum (recomendado) ou 1 ou 2 de confiança.

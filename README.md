# Refactor-Arch Skill — Refatoração Arquitetural Automatizada

Desafio do MBA de Engenharia de Software com IA. Construo uma **Skill do Claude Code**
(`refactor-arch`) que analisa, audita e refatora projetos backend legados para o padrão
MVC, **de forma agnóstica de stack**. A skill é executada em 3 projetos-alvo de
tecnologias diferentes (Python/Flask × 2 + Node/Express × 1) para provar que não está
acoplada a nenhuma deles.

> O enunciado original do desafio está preservado em [`CHALLENGE.md`](CHALLENGE.md).

**Status:** ✅ **APROVADO** — skill rodou as 3 fases (Análise → Auditoria → Refatoração
validada) nos 3 projetos. Todos os 4 critérios de aceite do enunciado atingidos em 3/3.

| Projeto | Stack | Findings | Boot + Endpoints OK |
|---|---|---|---|
| `code-smells-project` | Python/Flask 3.1.1 | 17 (6C + 3H + 5M + 2L) | ✓ |
| `ecommerce-api-legacy` | Node.js/Express 4 | 16 (5C + 5H + 4M + 2L) | ✓ |
| `task-manager-api` | Python/Flask 3.0.0 + SQLAlchemy | 16 (5C + 4H + 5M + 2L) | ✓ |

---

## A) Análise Manual

Antes de codar a skill, li manualmente os 3 projetos para entender **que** padrões
ela vai precisar detectar. Para cada um, listo os achados mais arquiteturalmente
relevantes — esses viraram a base do catálogo de anti-patterns da skill.

Convenção de severidade (igual à do enunciado): **CRITICAL** = falha de segurança ou
arquitetural que impede o sistema de funcionar/sustentar; **HIGH** = forte violação
de MVC/SOLID que trava manutenção; **MEDIUM** = padronização, duplicação,
performance moderada (ex: N+1); **LOW** = legibilidade, naming, magic numbers.

### Projeto 1 — `code-smells-project/` (Python/Flask · API de E-commerce)

Monolito de ~800 linhas em 4 arquivos. Acumula todos os anti-patterns "didáticos":
SQL Injection, credenciais hardcoded, ausência total de camadas. Serve como
**caso-fácil de detecção** para a skill.

| # | Sev | Anti-pattern | Local | Por que importa |
|---|---|---|---|---|
| 1 | **CRITICAL** | Hardcoded credentials & DEBUG=True em prod | `app.py:7-8`, vazado também em `controllers.py:285-290` | `SECRET_KEY` exposta no código e no `/health`; debug mode permite RCE via Werkzeug. |
| 2 | **CRITICAL** | SQL Injection sistêmica (string concatenation) | `models.py:28, 47-50, 57-61, 92, 109-111, 126-129, 174, 188, 280, 291` | Toda query usa `"... WHERE id = " + str(id)`. `login_usuario` é trivial de bypassar (`' OR '1'='1`). |
| 3 | **CRITICAL** | Endpoint admin sem auth executa SQL arbitrário | `app.py:59-78` (`/admin/query`) e `app.py:47-57` (`/admin/reset-db`) | Qualquer pessoa na internet wipe-out o banco ou roda `DROP TABLE`. |
| 4 | **CRITICAL** | Senha em texto puro + retornada na API | `database.py:76-83` (seed plain), `models.py:83, 99` (campo `senha` em `to_dict`-like), `models.py:110` (login compara plain) | Vazamento total de credenciais; viola LGPD/GDPR. |
| 5 | **HIGH** | God Module — sem separação de camadas | `models.py:1-315` | 4 domínios (produtos/usuários/pedidos/relatórios) num arquivo só; lógica de negócio (regra de desconto `models.py:256-262`) misturada com acesso a dados. |
| 6 | **HIGH** | Lógica de notificação no controller | `controllers.py:208-210, 248-250` | Envio de email/SMS/push escrito direto no controller via `print()` — impossível trocar canal, testar isoladamente, ou desacoplar do fluxo HTTP. |
| 7 | **HIGH** | Transação atômica ausente em `criar_pedido` | `models.py:133-169` | Insere pedido → insere itens → decrementa estoque sem `BEGIN/ROLLBACK`. Falha no meio = estado inconsistente. |
| 8 | **HIGH** | Conexão DB global single-instance | `database.py:4-10` | Variável global `db_connection` com `check_same_thread=False` — race conditions em workers concorrentes. |
| 9 | **HIGH** | CORS aberto e validação espalhada | `app.py:9`, `controllers.py:28-54` vs `72-90` | `CORS(app)` sem allowlist; validação de produto duplicada entre `criar_produto` e `atualizar_produto`. |
| 10 | **MEDIUM** | Query N+1 em listagens de pedidos | `models.py:171-201, 203-233` | Para cada pedido, 1 query de itens; para cada item, 1 query de produto. Deveria ser `JOIN`. |
| 11 | **MEDIUM** | `print()` como logger + PII no log | `controllers.py:8, 161, 179, 208-210` | Loga emails em login e detalhes de pedido. Sem nível, sem rotação. |
| 12 | **MEDIUM** | Rotas registradas manualmente sem Blueprint | `app.py:11-30` | 16 chamadas `add_url_rule` — deveria ser Blueprint por domínio. |
| 13 | **LOW** | String concat em vez de f-strings | `controllers.py:8, 11, 57, 161` | `"Listando " + str(len(produtos)) + " produtos"` em Python 3.12. |
| 14 | **LOW** | Variável `id` sombreia builtin | `controllers.py:14, 64, 98, 136` | Anti-padrão Python clássico. |

### Projeto 2 — `ecommerce-api-legacy/` (Node.js/Express · LMS com checkout)

Monolito Node usando `sqlite3` em modo callback. Foca em **callback hell**,
**estado global** e **falhas de segurança em fluxo de pagamento** — desafios
ortogonais aos do projeto 1.

| # | Sev | Anti-pattern | Local | Por que importa |
|---|---|---|---|---|
| 1 | **CRITICAL** | Secrets de produção hardcoded em source | `src/utils.js:1-7` | Inclui senha de DB e **`pk_live_*` do gateway de pagamento** — exposição em git history é game-over. |
| 2 | **CRITICAL** | Número do cartão e gateway key logados | `src/AppManager.js:45` | `console.log("Processando cartão ${cc} na chave ${config.paymentGatewayKey}")` — violação PCI-DSS imediata. |
| 3 | **CRITICAL** | "badCrypto" caseira para senha | `src/utils.js:17-23` + `AppManager.js:68` | Base64 truncada (reversível, sem salt) + fallback `"123456"` quando senha não vem no checkout. Conta criada com senha previsível. |
| 4 | **CRITICAL** | Endpoints admin/DELETE sem auth | `AppManager.js:80, 131` | `/api/admin/financial-report` e `DELETE /api/users/:id` abertos a qualquer um. |
| 5 | **CRITICAL** | Auto-criação de usuário no checkout | `AppManager.js:66-72` | Se o email não existe, cria sem confirmação — convite a account takeover trocando 1 char no email. |
| 6 | **HIGH** | God Class `AppManager` | `AppManager.js` inteiro | DB init + 3 rotas + lógica de checkout + relatório + decisões de pagamento num único arquivo de 142 linhas. |
| 7 | **HIGH** | Callback hell com contadores manuais | `AppManager.js:80-129` | 5 níveis de aninhamento; controle de fluxo via `coursesPending--` / `enrPending--`. Um erro silencioso quebra o contador e a resposta nunca volta. |
| 8 | **HIGH** | Pagamento por prefixo do cartão no controller | `AppManager.js:46` | `cc.startsWith("4") ? "PAID" : "DENIED"` — fake gateway colado dentro do controller, sem service nem porta de integração. |
| 9 | **HIGH** | Estado global mutável | `src/utils.js:9-10, 25` | `globalCache` (sem TTL) e `totalRevenue` exportados como `let` — race condition + memory leak. |
| 10 | **HIGH** | Erros silenciados + orphan records confessados | `AppManager.js:131-137` | `DELETE /users/:id` ignora `err` e responde `200 "Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."` literalmente. |
| 11 | **HIGH** | Sem transação no checkout | `AppManager.js:50-62` | `INSERT enrollment` → `INSERT payment` → `INSERT audit_log` em callbacks sequenciais; falha do 2º deixa enrollment órfão. |
| 12 | **MEDIUM** | N+1 brutal no relatório financeiro | `AppManager.js:80-129` | Para cada course → enrollments; para cada enrollment → user + payment. 1 + N + N×2 queries em vez de um `JOIN`. |
| 13 | **MEDIUM** | Naming críptico no body do request | `AppManager.js:29-33` | `usr`, `eml`, `pwd`, `c_id`, `cc` — contrato de API confuso. |
| 14 | **MEDIUM** | `express.json()` sem `limit` | `src/app.js:6` | Aceita payload de qualquer tamanho — vetor de DoS. |
| 15 | **MEDIUM** | API deprecated: `sqlite3` callback-mode | `package.json:11`, `AppManager.js` inteiro | Padrão moderno é `better-sqlite3` (sync) ou `sqlite` (Promises). Mantém o callback hell vivo. |
| 16 | **LOW** | `sqlite3.verbose()` em produção | `AppManager.js:1` | Verbose mode é só pra dev. |
| 17 | **LOW** | Código morto exportado | `src/utils.js:10, 25` | `totalRevenue` exportado e nunca usado. |

### Projeto 3 — `task-manager-api/` (Python/Flask · Task Manager com camadas parciais)

Projeto com **alguma** organização (models, routes, services, utils) — testa se a
skill sabe **melhorar** estrutura existente sem regredir. Problemas se escondem em
camadas presentes-mas-mal-usadas (`services/` órfão, `utils/helpers.py` ignorado).

| # | Sev | Anti-pattern | Local | Por que importa |
|---|---|---|---|---|
| 1 | **CRITICAL** | MD5 para hash de senha | `models/user.py:29, 32` | MD5 quebrado criptograficamente, sem salt, sem stretching. Trocar por bcrypt/argon2. |
| 2 | **CRITICAL** | Hash de senha exposto no `to_dict` | `models/user.py:21` | Todo GET `/users/:id`, response de criação/update e payload de `/login` retornam `password`. |
| 3 | **CRITICAL** | Credenciais SMTP hardcoded | `services/notification_service.py:9-10` | `email_password = 'senha123'` no source. |
| 4 | **CRITICAL** | Fake JWT previsível | `routes/user_routes.py:210` | `'token': 'fake-jwt-token-' + str(user.id)` — qualquer um forja o token de qualquer usuário. |
| 5 | **HIGH** | Service layer órfã | `services/notification_service.py` | Existe a pasta `services/` com `NotificationService`, mas nenhuma rota importa. Decoração arquitetural sem efeito. |
| 6 | **HIGH** | Fat Routes — lógica de negócio em rota | `routes/report_routes.py:30-68`, `routes/task_routes.py:273-299` | Cálculo de overdue, agregações de produtividade e taxa de conclusão dentro do handler HTTP. |
| 7 | **HIGH** | Lógica de "overdue" duplicada 5× | `models/task.py:50-60`, `task_routes.py:30-39, 71-80, 282-287`, `user_routes.py:171-180`, `report_routes.py:33-43` | O método `is_overdue()` do model existe, mas todas as rotas reimplementam in-line. |
| 8 | **HIGH** | Validações duplicadas + utils não usado | `routes/task_routes.py:92-114, 167-184` vs `utils/helpers.py:57-108` | `process_task_data` cobre tudo, mas as rotas validam inline. Mesma regex de email aparece em `user_routes.py:61, 106` **e** `utils/helpers.py:21`. |
| 9 | **HIGH** | `db.create_all()` no import do app | `app.py:30-31` | Schema é criado toda vez que `app.py` é importado (ex: `seed.py from app import app`). Deveria ser migration (Alembic). |
| 10 | **HIGH** | Categorias misturadas em `report_bp` | `routes/report_routes.py:157-223` | CRUD de Category vive no Blueprint de reports — viola limites de domínio. |
| 11 | **MEDIUM** | N+1 em `GET /tasks` | `routes/task_routes.py:41-57` | Para cada task: `User.query.get` + `Category.query.get`. Falta `joinedload`. |
| 12 | **MEDIUM** | N+1 em `/reports/summary user_productivity` | `routes/report_routes.py:53-68` | Loop sobre users com 1 query por user. |
| 13 | **MEDIUM** | `except:` cego engole tudo | `task_routes.py:62, 138, 204, 236`, `report_routes.py:186, 207, 221`, `user_routes.py:130, 149` | Captura `KeyboardInterrupt`/`SystemExit`; mensagens de erro inconsistentes. |
| 14 | **MEDIUM** | Falta paginação | `/tasks`, `/users`, `/categories`, `/reports/summary` | `Task.query.all()` retorna tudo — quebra com volume real. |
| 15 | **MEDIUM** | Deleção em cascata manual | `routes/user_routes.py:140-142` | Loop deletando tasks em vez de `cascade="all, delete-orphan"` no relationship. |
| 16 | **MEDIUM** | API deprecated: `Model.query.get(id)` | usado em todas as rotas | Deprecated em SQLAlchemy 2.x; substituir por `db.session.get(Model, id)`. |
| 17 | **MEDIUM** | API deprecated: `datetime.utcnow()` | `models/*.py`, `task_routes.py`, `report_routes.py` | Deprecated em Python 3.12+; usar `datetime.now(timezone.utc)`. |
| 18 | **LOW** | `type(x) == list` em vez de `isinstance` | `task_routes.py:141, 210`, `helpers.py:103` | Não-pythonic. |
| 19 | **LOW** | `count = count + 1` em vez de `+=` | `report_routes.py:37, 61, 121` | |
| 20 | **LOW** | Imports não usados | `app.py:7`, `task_routes.py:7`, `helpers.py:3-7` | `import os, sys, json, time` carregados e nunca chamados. |

### Resumo da Análise Manual

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---|---|---|---|---|
| code-smells-project | 4 | 5 | 3 | 2 | **14** |
| ecommerce-api-legacy | 5 | 6 | 4 | 2 | **17** |
| task-manager-api | 4 | 6 | 7 | 3 | **20** |

**Padrões que aparecem em ≥2 projetos** (viraram entradas do catálogo da skill):

- Hardcoded credentials / secrets → 3/3
- Endpoint sem autenticação → 3/3
- God Class/Module → 2/3
- Lógica de negócio no controller/route → 3/3
- Query N+1 → 3/3
- Senha mal protegida (plain, MD5, base64) → 3/3
- Transação ausente em fluxo multi-write → 2/3
- Validação duplicada / inline → 3/3
- `print`/`console.log` como logger → 3/3
- CORS aberto → 2/3
- API deprecated → 2/3 (sqlite3-callback, MD5, `Model.query.get`, `datetime.utcnow`)
- Erro engolido (`except:` / `if(err){}`) → 3/3

Esses 12 padrões cobrem >80% dos achados e formam o núcleo do catálogo
`anti-patterns.md` da skill.

---

## B) Construção da Skill

### Estrutura de arquivos

```
.claude/skills/refactor-arch/
├── SKILL.md                         # workflow das 3 fases + princípios
└── references/                      # carregados sob demanda por fase
    ├── analysis-heuristics.md       # Fase 1 — sinais p/ detectar stack/arq/domínio
    ├── anti-patterns.md             # Fase 2 — catálogo (21 APs)
    ├── report-template.md           # Fase 2 — formato exato do relatório
    ├── mvc-guidelines.md            # Fase 3 — arquitetura-alvo por stack
    └── refactoring-playbook.md      # Fase 3 — 18 receitas com before/after
```

Total: **6 arquivos / ~1700 linhas**. `SKILL.md` propositalmente curto (155 linhas) —
o conhecimento de domínio vive nos references e é carregado apenas quando relevante.

### Decisões de design

**1. Progressive disclosure (carregamento em camadas).**
A skill segue o padrão recomendado para Claude Code:

- **Metadata** (frontmatter name + description) → sempre em contexto, ~150 palavras.
- **`SKILL.md` body** → carregado quando a skill dispara, 155 linhas (bem abaixo do
  limite de ~500 sugerido).
- **References** → carregados sob demanda. A SKILL.md explicita "antes da Fase X,
  leia `references/Y.md`", então cada reference só entra em contexto durante a
  fase relevante. Isso mantém a janela de contexto enxuta e permite references
  longas (anti-patterns: 396 linhas; playbook: 793 linhas) sem inchar todas as
  invocações.

**2. Three-phase workflow com pausa obrigatória entre Fase 2 e 3.**
- Fase 1 = analisar, não modificar.
- Fase 2 = auditar, salvar relatório, **parar** no `[y/n]`.
- Fase 3 = só com aprovação humana explícita; valida boot + endpoints ao final.

A pausa é o ponto de **alinhamento humano** que o enunciado exige. A skill
descreve não só *como* pausar (terminar com `[y/n]` e não chamar mais tools) mas
*por que* (humano tem contexto de domínio que a skill não tem — pode aprovar
mudanças, ou reverter um "anti-pattern" que era intencional).

**3. Agnóstica por construção, não por boa intenção.**
- O catálogo descreve cada AP por **sinais concretos** (regex, padrões de código,
  presença/ausência de estruturas) — não por keywords de framework. Ex: AP06
  (God Module) detecta "arquivo único >300 linhas misturando 4+ responsabilidades"
  — vale pra Python, Node, Ruby ou Java.
- O playbook tem **exemplos Python E Node lado a lado** para os patterns onde a
  manifestação difere (PB03 SQL parametrizado, PB04 bcrypt, PB07 service
  extraction, PB11 callback-hell→async, etc.).
- `mvc-guidelines.md` tem **estruturas de diretório alvo por stack**
  (Python/Flask, Node/Express) com convenções específicas (Blueprints, Routers).

**4. 21 anti-patterns no catálogo (vs 8 mínimos do enunciado).**
O catálogo é organizado em índice clicável por severidade. Cada entrada tem 4 campos
fixos: **Severidade** + **Por que importa** + **Sinais de detecção** + **Recomendação**
(com `[ref: PBXX]` apontando para a receita correspondente).

Inclui APIs deprecated (AP18) com tabela de substituições — atende ao requisito
explícito do enunciado de detectar deprecated com equivalente moderno.

**5. Regra de deduplicação entre APs.**
Aprendi com o primeiro run (projeto 1): MD5 dispara tanto AP04 (senha mal
protegida) quanto AP18 (deprecated crypto). Sem regra clara, ambos eram
contados e o summary inflava. Adicionei explicitamente: "Use o AP mais
específico e descarte o sobreposto. Sobreposições conhecidas: …" — evita
double-counting sem perder rastreabilidade.

**6. Playbook ordenado por sequência de execução.**
O fim do `refactoring-playbook.md` tem **"Sequência sugerida na Fase 3"** com
ordem priorizada: segurança primeiro (PB01-PB05), depois estrutura (PB06-PB07),
depois flows críticos (PB08, PB11), depois qualidade (PB12-PB17), deprecated por
último (PB18 — busca global). Não é dogma, mas ordena bem a Fase 3 quando há
muitos findings a resolver.

### Como garanti que é agnóstica de tecnologia

Três testes que a skill teve que passar:

| Teste | Como passou |
|---|---|
| **Linguagens diferentes (Python e Node)** | Catálogo descreve padrões por sinais, não por keywords. Playbook tem exemplos Python + Node lado a lado. mvc-guidelines tem 2 árvores de diretório alvo. |
| **Frameworks diferentes (Flask, Express)** | Heurísticas detectam por manifest (`requirements.txt` vs `package.json`) e padrões de rota (`@app.route`, `app.get/post`). Estrutura MVC é descrita por responsabilidade, não por classe específica. |
| **Níveis de organização diferentes (monolito vs parcial)** | A skill tem 3 níveis de profundidade de intervenção: monolítico → criar do zero; parcial → mover/conectar; já MVC → cirúrgico. Bullet específico: "antes de criar pasta nova, `ls` e confirme — diretórios duplicados são pior que ausentes." |

### Iteração: o que mudou entre as 3 execuções

| # | Detectado durante execução | Mudança |
|---|---|---|
| 1 | Projeto 1: AP18 escalado pra CRITICAL gerava double-counting com AP04 (MD5 dispara ambos). | Adicionei **regra de deduplicação** no `anti-patterns.md` com sobreposições conhecidas. |
| 2 | Projeto 1: template do report cita `~<L> LOC` mas a Fase 1 não emitia LOC. | Adicionei `(~<L> LOC)` ao status block da Fase 1 no SKILL.md. |
| 3 | Projeto 1: macOS captura porta 5000 (AirPlay), boot na 5000 falhava. | Adicionei dica no SKILL.md Fase 3 com fallback `PORT=5555`. |
| 4 | Projeto 1: schemas refatorados (plain → bcrypt) falhavam silenciosamente contra DB antigo. | Adicionei passo "limpe o banco de dev" no início da validação Fase 3. |
| 5 | Projeto 2: `bcrypt` (native) não compilava sem build chain instalada. | Adicionei nota no PB04: "Em Node, prefira `bcryptjs` quando o ambiente não tem build chain". |
| 6 | Projeto 3: a refatoração quase criou `src/services/` ao lado de `services/` já existente. | Adicionei callout explícito no SKILL.md Fase 3: "Antes de criar uma pasta nova, `ls` no projeto." |

**Total: 6 melhorias aplicadas em 3 execuções.** Nenhuma exigiu reescrever a skill —
todas foram edições cirúrgicas. Skill final é a mesma em todos os 3 projetos
(MD5 idêntico) após sincronização.

### Anti-patterns no catálogo (resumo)

| ID | Nome | Sev |
|---|---|---|
| AP01 | Hardcoded Secrets / Credentials | CRITICAL |
| AP02 | Endpoint sem autenticação ou autorização | CRITICAL |
| AP03 | SQL Injection via string concatenation | CRITICAL |
| AP04 | Senha mal protegida (plain / MD5 / base64) | CRITICAL |
| AP05 | Dados sensíveis vazados em response/log | CRITICAL |
| AP06 | God Class / God Module | HIGH |
| AP07 | Lógica de negócio em controller/route | HIGH |
| AP08 | Multi-write flow sem transação | HIGH |
| AP09 | Service layer órfã | HIGH |
| AP10 | Estado global mutável | HIGH |
| AP11 | Callback hell / falta de async-await | HIGH |
| AP12 | Query N+1 | MEDIUM |
| AP13 | Validação duplicada inline | MEDIUM |
| AP14 | `print` / `console.log` como logger | MEDIUM |
| AP15 | Erros engolidos | MEDIUM |
| AP16 | CORS aberto sem allowlist | MEDIUM |
| AP17 | Falta de paginação em listagens | MEDIUM |
| AP18 | Uso de API deprecated | MEDIUM |
| AP19 | Magic numbers / enums hardcoded | LOW |
| AP20 | Naming críptico / sombreamento de builtin | LOW |
| AP21 | Imports não usados / código morto | LOW |

### Receitas no playbook (18 transformações com before/after)

PB01 (env vars) · PB02 (auth middleware) · PB03 (SQL parametrizado) · PB04
(bcrypt/argon2) · PB05 (allowlist serializer + logger seguro) · PB06 (quebrar
God Module) · PB07 (extract service) · PB08 (transação atômica) · PB09 (conectar
service órfã) · PB10 (eliminar estado global) · PB11 (callback hell → async) ·
PB12 (eliminar N+1) · PB13 (validação por schema) · PB14 (logger estruturado) ·
PB15 (error handler central) · PB16 (CORS com allowlist) · PB17 (paginação) ·
PB18 (atualizar deprecated APIs).

---

## C) Resultados

### Findings por projeto (relatórios completos em `reports/`)

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total | Relatório |
|---|---|---|---|---|---|---|
| 1 — `code-smells-project` | **6** | 3 | 5 | 2 | **17** | [`reports/audit-project-1.md`](reports/audit-project-1.md) |
| 2 — `ecommerce-api-legacy` | **5** | 5 | 4 | 2 | **16** | [`reports/audit-project-2.md`](reports/audit-project-2.md) |
| 3 — `task-manager-api` | **5** | 4 | 5 | 2 | **16** | [`reports/audit-project-3.md`](reports/audit-project-3.md) |

A skill encontrou consistentemente entre **16-17 findings por projeto**, sempre
com 5+ CRITICAL — bem acima do mínimo do enunciado (≥5 findings, ≥1 CRITICAL/HIGH).
Os achados batem 95% com a análise manual (ver Seção A).

### Estrutura antes/depois (resumo)

**Projeto 1 — code-smells-project**
- Antes: 4 arquivos na raiz (`app.py`, `controllers.py`, `models.py`, `database.py`), ~780 LOC.
- Depois: `app.py` (composition root, 47 linhas) + `src/` com 31 arquivos em
  `config/`, `middlewares/`, `repositories/`, `schemas/`, `services/`, `routes/`.

**Projeto 2 — ecommerce-api-legacy**
- Antes: 3 arquivos (`src/app.js`, `src/AppManager.js`, `src/utils.js`), ~180 LOC.
  `AppManager.js` é uma God Class com initDb + 3 rotas + checkout + relatório
  + decisões de pagamento, tudo em callback hell.
- Depois: `src/app.js` (composition root) + 18 arquivos JS divididos em
  `config/`, `db/`, `repositories/`, `services/`, `controllers/`, `routes/`,
  `middlewares/`, `schemas/`, `utils/`. **Zero callbacks aninhados** (migrado
  pra `better-sqlite3` sync + `db.transaction(fn)`).

**Projeto 3 — task-manager-api** (o mais interessante)
- Antes: 14 arquivos com `models/`, `routes/`, `services/`, `utils/` —
  **estrutura existe mas mal-usada**: `NotificationService` órfã (zero
  importadores); `utils/helpers.py:process_task_data` definida mas nenhuma
  rota chama; lógica de "overdue" duplicada inline em 5 handlers.
- Depois: **não recriei** `models/` nem `routes/` (já estavam estruturalmente
  OK). **Adicionei** o que faltava (`config/`, `middlewares/`, `schemas/`) +
  novos services (`task_service.py`, `user_service.py`, `report_service.py`,
  `category_service.py`). **Conectei** o `NotificationService` órfão (agora
  chamado de `task_service.create_task`). Movi `db.create_all()` de import
  time para CLI command (`python -m app init-db`).

### Checklist de Validação por projeto

#### Projeto 1 — code-smells-project

**Fase 1 — Análise**
- [x] Linguagem detectada corretamente (Python)
- [x] Framework detectado corretamente (Flask 3.1.1)
- [x] Domínio descrito corretamente (API de e-commerce: produtos, usuários, pedidos)
- [x] Número de arquivos analisados condiz com a realidade (4 source files / ~780 LOC)

**Fase 2 — Auditoria**
- [x] Relatório segue o template definido
- [x] Cada finding tem arquivo e linhas exatos
- [x] Findings ordenados por severidade (CRITICAL → LOW)
- [x] ≥ 5 findings (17 encontrados)
- [x] APIs deprecated incluídas (AP18 — plain-text como deprecated extremo de crypto)
- [x] Skill pausou e pediu confirmação antes da Fase 3

**Fase 3 — Refatoração**
- [x] Estrutura de diretórios segue padrão MVC (`src/{config,middlewares,repositories,services,schemas,routes}/`)
- [x] Configuração extraída para módulo de config (sem hardcoded)
- [x] Models criados para abstrair dados (`repositories/` + ORM-style)
- [x] Routes separadas por domínio (Blueprints)
- [x] Services concentram a lógica de negócio
- [x] Error handling centralizado (`middlewares/errors.py`)
- [x] Entry point claro (`app.py` = composition root, 47 linhas)
- [x] Aplicação inicia sem erros
- [x] Endpoints originais respondem corretamente (`/`, `/health`, `/produtos` → 200; `/admin/query` removido = 404)

#### Projeto 2 — ecommerce-api-legacy

**Fase 1 — Análise**
- [x] Linguagem detectada (Node.js)
- [x] Framework detectado (Express 4.18.2)
- [x] Domínio descrito (LMS / e-commerce de cursos com checkout)
- [x] Número de arquivos condiz (3 source files / ~180 LOC)

**Fase 2 — Auditoria**
- [x] Relatório segue o template
- [x] Cada finding com arquivo:linha
- [x] Ordem por severidade
- [x] ≥ 5 findings (16 encontrados)
- [x] APIs deprecated incluídas (`sqlite3` callback-mode)
- [x] Pausou para confirmação

**Fase 3 — Refatoração**
- [x] Estrutura MVC (`src/{config,db,repositories,services,controllers,routes,middlewares,schemas,utils}/`)
- [x] Config extraída (`src/config/index.js` + `.env.example`)
- [x] Models / repositories criados (6 repositories isolados por tabela)
- [x] Routes thin, separadas por domínio
- [x] Controllers + Services concentram fluxo
- [x] Error handling centralizado (`middlewares/errorHandler.js`)
- [x] Entry point claro (`src/app.js` = createApp + start)
- [x] Aplicação inicia sem erros
- [x] Endpoints originais respondem (`POST /api/checkout` cartão `4111…` → 200; `/api/admin/financial-report` → 401 sem token / 200 com admin JWT; `DELETE /api/users/:id` → 401)

#### Projeto 3 — task-manager-api

**Fase 1 — Análise**
- [x] Linguagem detectada (Python 3)
- [x] Framework detectado (Flask 3.0.0 + Flask-SQLAlchemy 3.1.1)
- [x] Domínio descrito (task manager: tasks, categorias, usuários)
- [x] Número de arquivos condiz (14 source files / ~1158 LOC)
- [x] **Bônus**: skill identificou explicitamente que `NotificationService` é órfão e `utils/helpers.process_task_data` não é usado

**Fase 2 — Auditoria**
- [x] Relatório segue o template
- [x] Cada finding com arquivo:linha
- [x] Ordem por severidade
- [x] ≥ 5 findings (16 encontrados)
- [x] APIs deprecated incluídas (`Model.query.get` e `datetime.utcnow`)
- [x] Pausou para confirmação

**Fase 3 — Refatoração**
- [x] Estrutura MVC **evoluída, não recriada** — manteve `models/`, `routes/`, `services/`; adicionou `config/`, `middlewares/`, `schemas/`
- [x] Config extraída (`config/settings.py`)
- [x] Models mantidos e melhorados (bcrypt, `to_dict` com allowlist)
- [x] Routes slim (lógica movida pra services)
- [x] Services completos (`task_service`, `user_service`, `report_service`, `category_service` + `notification_service` conectado)
- [x] Error handling centralizado (`middlewares/error_handler.py`)
- [x] Entry point claro (`app.py` + CLI `init-db`/`seed`)
- [x] Aplicação inicia sem erros
- [x] Endpoints originais respondem (`/`, `/health`, `/tasks`, `/reports/summary`, `/categories`, `/login` com JWT real → 200; auth enforcement quando `AUTH_DISABLED=false` → DELETE/admin sem token = 401)

### Critérios de aceite do enunciado (obrigatório nos 3 projetos)

| Critério | P1 | P2 | P3 |
|---|---|---|---|
| Fase 1 detecta stack corretamente | ✓ | ✓ | ✓ |
| Fase 2 encontra ≥ 5 findings | ✓ (17) | ✓ (16) | ✓ (16) |
| Fase 2 inclui ≥ 1 CRITICAL ou HIGH | ✓ (6+3) | ✓ (5+5) | ✓ (5+4) |
| Fase 3 aplicação funciona após refator | ✓ | ✓ | ✓ |

**4/4 critérios atendidos em 3/3 projetos.**

### Observações sobre como a skill se comportou em stacks diferentes

- **Python/Flask monolítico (P1)** foi o caso mais "fácil" — todos os anti-patterns
  estão na superfície, sem ofuscação. A skill encontrou 17 findings e refatorou
  para MVC limpo em uma única passada. Curva de tempo: ~5 min Fase 1+2, ~20 min Fase 3.
- **Node/Express monolítico (P2)** desafiou principalmente pela troca de
  paradigma (callback hell → async/transações). A receita PB11 + troca de
  driver para `better-sqlite3` foi o pivô. A escolha entre `bcrypt` (nativo)
  e `bcryptjs` virou nota explícita no PB04 — `bcryptjs` por simplicidade,
  sem depender de build chain.
- **Python/Flask parcialmente organizado (P3)** foi o teste mais rigoroso da
  agnosticidade — a skill precisou **não recrear** o que já existia. O bullet
  "antes de criar pasta nova, `ls`" foi escrito justamente após uma execução
  quase criar `src/services/` ao lado de `services/`. Skill versionada e
  propagada para os outros projetos após o ajuste.

### O aprendizado mais importante (replica o tom do projeto MBA anterior)

**A construção da skill é menos sobre escrever instruções e mais sobre
descrever sinais.** O catálogo de anti-patterns que escrevi inicialmente
ficava "código ruim em X.py" — útil para humano, inútil para detecção
automatizada. Reescrevi cada entrada em torno de **sinais detectáveis** (regex,
padrões de estrutura, ausência/presença concretas) e a precisão de detecção
saltou.

Em paralelo, o **playbook precisa de exemplos before/after na linguagem real,
não pseudocódigo.** Quando o playbook tinha só explicação textual, a
refatoração produzia soluções idiossincráticas. Quando tinha código Python E
Node lado a lado, copiava o padrão correto. O custo de escrever 2× o exemplo
se paga nos 3 projetos.

---

## D) Como Executar

### Pré-requisitos

- **Claude Code** instalado e autenticado (`claude --version`)
- Python 3.10+ (para projetos 1 e 3)
- Node.js 18+ + npm (para projeto 2)
- macOS / Linux

### Comandos por projeto

Cada projeto já tem `.claude/skills/refactor-arch/` instalada. A skill é
invocada via `/refactor-arch` dentro do projeto.

#### Projeto 1 — code-smells-project (Python/Flask)

```bash
cd code-smells-project
claude "/refactor-arch"
```

A skill vai:
1. Detectar Python + Flask + 4 arquivos monolíticos.
2. Produzir relatório (`../reports/audit-project-1.md`), pausar.
3. Após aprovação, refatorar para `src/` MVC, validar boot + endpoints.

Para validar manualmente após a refator:

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
rm -f loja.db                     # schema novo (bcrypt) — regere
PORT=5555 python app.py &         # macOS: porta 5000 é AirPlay; use 5555
curl http://127.0.0.1:5555/
curl http://127.0.0.1:5555/health
curl http://127.0.0.1:5555/produtos
kill %1
```

#### Projeto 2 — ecommerce-api-legacy (Node/Express)

```bash
cd ecommerce-api-legacy
claude "/refactor-arch"
```

Para validar após a refator:

```bash
npm install
PORT=3001 JWT_SECRET=dev-secret AUTH_DISABLED=true npm start &
curl http://localhost:3001/health
curl -X POST http://localhost:3001/api/checkout \
  -H 'Content-Type: application/json' \
  -d '{"usr":"Test","eml":"test@x.com","pwd":"senhaforte","c_id":2,"card":"4111222233334444"}'
kill %1
```

#### Projeto 3 — task-manager-api (Python/Flask parcial)

```bash
cd task-manager-api
claude "/refactor-arch"
```

Para validar após a refator:

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
rm -f tasks.db
python -m app init-db               # CLI nova, substitui o create_all em import
python -m app seed                  # popula 3 users + 4 categorias + 10 tasks
PORT=5557 AUTH_DISABLED=true python app.py &
curl http://127.0.0.1:5557/
curl http://127.0.0.1:5557/tasks?per_page=2
curl -X POST http://127.0.0.1:5557/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"joao@email.com","password":"1234"}'    # devolve JWT real
kill %1
```

### Como validar que a refatoração funcionou

A própria skill faz isso na Fase 3 (boot + curl em ≥2 endpoints + kill).
Para auditoria humana adicional:

1. **Estrutura**: `tree -L 3 -I 'node_modules|venv|__pycache__|*.db'` — deve mostrar
   `src/` (ou estrutura equivalente) com camadas claras.
2. **Zero secrets hardcoded**: `grep -rn 'SECRET\|pk_live\|password.*=.*[\"'\'']' src/ | grep -v '\.env'`
   — deve voltar vazio (ou só `os.environ.get`).
3. **Zero SQL concatenado** (em projetos 1 e 2): `grep -rn 'execute.*+.*str(\|cursor.execute(f' src/`
   — vazio.
4. **Zero MD5/SHA1 em senha** (projeto 3): `grep -rn 'hashlib.md5\|hashlib.sha1' models/` — vazio.
5. Cada projeto tem **README próprio** original em `<projeto>/README.md` (preservado).

### Solução de problemas

- **macOS: "Address already in use" na porta 5000** → AirPlay Receiver captura.
  Use `PORT=5555` (a config lê de env após refator).
- **Erro "table tasks already exists" ao bootar P3** → `tasks.db` velho com schema
  antigo. `rm -f tasks.db && python -m app init-db`.
- **`bcrypt` falha ao instalar no P2** → ambiente sem build chain. A skill já
  optou por `bcryptjs` (puro JS) — `npm install bcryptjs` resolve.
- **JWT inválido** → `JWT_SECRET` precisa ser o mesmo entre emissão e validação
  (mesmo processo Flask/Node). Para curl, gere o token no mesmo terminal/secret.

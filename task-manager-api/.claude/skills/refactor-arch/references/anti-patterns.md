# Anti-patterns Catalog

Catálogo de anti-patterns para a **Fase 2**. Cada entrada tem:
- **Severidade** (CRITICAL/HIGH/MEDIUM/LOW)
- **Sinais de detecção** (concretos — regex, padrões de código, estrutura — não "código ruim")
- **Por que importa** (impacto real)
- **Recomendação** (acionável; remetida ao playbook quando a transformação é não-trivial)

Os sinais são descritos de forma **agnóstica de stack**, com exemplos em Python e Node quando o padrão se manifesta de forma diferente.

## Índice

**CRITICAL** (segurança ou impossibilita funcionamento)
- [AP01 — Hardcoded Secrets / Credentials](#ap01)
- [AP02 — Endpoint sem autenticação ou autorização](#ap02)
- [AP03 — SQL Injection via string concatenation](#ap03)
- [AP04 — Senha mal protegida (plain / MD5 / base64 / "custom crypto")](#ap04)
- [AP05 — Dados sensíveis vazados em response/log](#ap05)

**HIGH** (forte violação de MVC/SOLID)
- [AP06 — God Class / God Module (sem separação de camadas)](#ap06)
- [AP07 — Lógica de negócio em controller/route (Fat Routes)](#ap07)
- [AP08 — Multi-write flow sem transação](#ap08)
- [AP09 — Service layer órfã (camada existente, não usada)](#ap09)
- [AP10 — Estado global mutável](#ap10)
- [AP11 — Callback hell / falta de async-await](#ap11)

**MEDIUM** (padronização, performance, duplicação)
- [AP12 — Query N+1](#ap12)
- [AP13 — Validação duplicada inline](#ap13)
- [AP14 — `print` / `console.log` como logger](#ap14)
- [AP15 — Erros engolidos (`except:` cego / err ignorado)](#ap15)
- [AP16 — CORS aberto sem allowlist](#ap16)
- [AP17 — Falta de paginação em listagens](#ap17)
- [AP18 — Uso de API deprecated](#ap18)

**LOW** (legibilidade, naming)
- [AP19 — Magic numbers / enums hardcoded espalhados](#ap19)
- [AP20 — Naming críptico ou sombreamento de builtin](#ap20)
- [AP21 — Imports não usados / código morto](#ap21)

---

## CRITICAL

### <a id="ap01"></a>AP01 — Hardcoded Secrets / Credentials
**Severidade:** CRITICAL

**Por que importa:** Credenciais em source viram parte do git history para sempre — mesmo após removidas, qualquer pessoa com acesso ao histórico (ou a um clone antigo) pode usá-las. Scanners automatizados encontram secrets públicos em minutos.

**Sinais de detecção:**
- Atribuições com valor literal: `SECRET_KEY = "..."`, `API_KEY = "..."`, `password = "..."`, `dbPass = "..."`, `email_password = "..."` (onde o valor é string e não `os.environ.get(...)` / `process.env.X`).
- Chaves com prefixos reconhecíveis: `pk_live_*`, `sk_live_*`, `ghp_*`, `xoxb-*`, `AKIA*`, `eyJ...` (JWT literal).
- Endpoints como `/health` ou `/debug` que **retornam** segredos no response body.
- `app.config['SECRET_KEY'] = '...'` direto no código.
- `DEBUG = True` literal em código de aplicação (não em arquivo de config dev separado).

**Recomendação:** Mover para variáveis de ambiente, carregadas via `os.environ.get(...)` / `process.env.X` (com defaults seguros) ou biblioteca como `python-dotenv`/`dotenv`. Documentar variáveis em `.env.example` (sem valores reais). Ver playbook PB01.

---

### <a id="ap02"></a>AP02 — Endpoint sem autenticação ou autorização
**Severidade:** CRITICAL

**Por que importa:** Operações administrativas e destrutivas (delete, reset, dump, executar SQL/comando) sem auth viram vetor de ataque trivial. Em produção, isso é o equivalente a deixar a porta aberta.

**Sinais de detecção:**
- Rotas com nome contendo `admin`, `delete`, `reset`, `dump`, `export`, `query`, `report` sem decorator/middleware visível de auth (`@requires_auth`, `authenticate`, etc.).
- Rota `DELETE` ou `POST` que altera estado sem verificação de sessão/token.
- Rota que executa SQL/comando arbitrário recebido no body (`/admin/query`, `/eval`).
- Rota que retorna dados de outros usuários sem checagem de ownership (`GET /users/:id` sem comparar `id` com usuário autenticado).
- Token "fake" gerado por concatenação previsível (`'fake-jwt-' + str(user.id)`) — convida bypass.

**Recomendação:** Adicionar decorator/middleware de auth. Endpoints destrutivos exigem role check (`@requires_role('admin')`). Tokens devem ser assinados (JWT real com secret + expiração). Ver playbook PB02.

---

### <a id="ap03"></a>AP03 — SQL Injection via string concatenation
**Severidade:** CRITICAL

**Por que importa:** Permite que atacante leia, modifique ou destrua qualquer coisa no banco. Em particular, `login`-like queries são triviais de bypassar (`' OR '1'='1`).

**Sinais de detecção:**
- Construção de query por `+`/`%`/f-string com input do usuário interpolado:
  - Python: `cursor.execute("SELECT * FROM users WHERE id = " + str(id))`, `cursor.execute(f"... WHERE email = '{email}'")`.
  - Node: `db.run(\`... WHERE id = ${id}\`)`.
- Query montada em pedaços (`query = "..."; query += " AND ..."`) com input do usuário concatenado.
- LIKE com `%` interpolado: `"... LIKE '%" + termo + "%'"`.

**Importante:** o uso correto é **placeholders parametrizados** (`cursor.execute("... WHERE id = ?", (id,))` / `db.run("... WHERE id = ?", [id])`) ou ORM (SQLAlchemy, Sequelize, Prisma).

**Recomendação:** Substituir todas as queries por chamadas parametrizadas ou ORM. Ver playbook PB03.

---

### <a id="ap04"></a>AP04 — Senha mal protegida
**Severidade:** CRITICAL

**Por que importa:** Vazamento do banco vira vazamento de credenciais — e usuários reusam senhas em outros serviços. Implementação errada vira "tudo igual a plain text" na prática.

**Sinais de detecção:**
- **Plain text**: campo `password`/`senha` no INSERT/UPDATE recebe direto a string do usuário, sem hash. `seed data` com senha em claro (`('admin', 'admin@x.com', 'admin123')`).
- **MD5 / SHA1**: `hashlib.md5(pwd.encode()).hexdigest()`, `crypto.createHash('md5').update(pwd).digest('hex')`. Quebrados criptograficamente.
- **Hash sem salt**: hash determinístico — mesma senha sempre dá mesmo hash; permite rainbow tables.
- **"Custom crypto" caseira**: loops manuais de base64, XORs, "encryption" inventada (ex: `for i in 1..10000 { hash += b64(pwd).substr(0,2) }`). Sempre **suspeite** quando vir crypto não-padrão.
- Login compara `senha == stored_password` em texto puro.

**Recomendação:** bcrypt (Python: `bcrypt`; Node: `bcrypt`/`bcryptjs`), argon2id (`argon2-cffi`/`argon2`), ou scrypt. Sempre com **salt aleatório por usuário** e parâmetros de custo razoáveis. Ver playbook PB04.

---

### <a id="ap05"></a>AP05 — Dados sensíveis vazados em response/log
**Severidade:** CRITICAL

**Por que importa:** PCI-DSS, LGPD/GDPR, e bom senso. Logar cartão de crédito ou retornar senha hashada no JSON expõe dados que jamais deveriam sair do server.

**Sinais de detecção:**
- `to_dict()` / `toJSON()` / serializer de User que inclui campo `password`/`senha`/`hash`.
- `console.log`/`print` com PAN (número de cartão), CVV, senha em claro, ou keys de API.
  - Padrão típico: `console.log("Processando cartão ${cc}...")`.
- Endpoint `/health` ou `/debug` que retorna config sensível (`SECRET_KEY`, `paymentGatewayKey`).
- Response de criação de usuário que ecoa a senha enviada.

**Recomendação:** Lista explícita de campos públicos no serializer (allowlist, não denylist). Logger com filtro de PII. Health check sem qualquer dado sensível. Ver playbook PB05.

---

## HIGH

### <a id="ap06"></a>AP06 — God Class / God Module
**Severidade:** HIGH

**Por que importa:** Impossível testar em isolamento. Qualquer mudança afeta tudo. Acoplamento total entre domínios.

**Sinais de detecção:**
- Arquivo único com >300 linhas misturando: routing + persistência + lógica de negócio + validação + formatação.
- Classe única com >10 métodos públicos cobrindo múltiplos domínios.
- Tipicamente: `models.py` que tem produtos + usuários + pedidos + relatórios; `AppManager.js` com initDb + setupRoutes + checkout + relatório.

**Recomendação:** Separar por domínio (1 arquivo por entidade ou agregado) e por camada (Model / Controller / Route / Service). Ver playbook PB06.

---

### <a id="ap07"></a>AP07 — Lógica de negócio em controller/route (Fat Routes)
**Severidade:** HIGH

**Por que importa:** Lógica presa no handler HTTP não é reutilizável (não dá pra chamar de um job, de um CLI), não é testável sem subir Flask/Express, e mistura "tradução de HTTP" com "regra de negócio".

**Sinais de detecção:**
- Handler com >30 linhas de lógica que não é parsing de request ou render de response.
- Cálculos de agregação, regras de desconto, decisões de "se status X então fazer Y", chamadas a serviços externos (email/SMS/push) **dentro** do handler.
- Loops que iteram sobre coleções de domínio dentro da rota (ex: calcular `overdue_count` no handler em vez de no service/model).
- `print/log` de "ENVIANDO EMAIL" / "ENVIANDO SMS" dentro do controller.

**Recomendação:** Extrair a lógica pra um **service** (objeto com métodos por caso de uso). Controller só faz: parsing → chamada do service → render. Ver playbook PB07.

---

### <a id="ap08"></a>AP08 — Multi-write flow sem transação
**Severidade:** HIGH

**Por que importa:** Se uma das operações falha no meio, fica estado inconsistente (pedido sem itens, enrollment sem pagamento, usuário deletado deixando órfãos).

**Sinais de detecção:**
- Sequência de 2+ `INSERT/UPDATE/DELETE` no mesmo handler sem `BEGIN`/`COMMIT`/`ROLLBACK`, ou sem `session.begin()` / `transaction()`.
- Em ORMs: múltiplos `db.session.add(...)` + `commit` sem try/except com rollback.
- Auto-confissão no código (ex: response que diz "usuário deletado mas matrículas ficaram sujas").

**Recomendação:** Envolver o fluxo em transação atômica com rollback explícito em erro. Ver playbook PB08.

---

### <a id="ap09"></a>AP09 — Service layer órfã
**Severidade:** HIGH

**Por que importa:** Pasta `services/` existente mas não usada cria a **ilusão** de boa arquitetura sem o benefício. Pior: outras pessoas vendo a estrutura assumem que a camada funciona e duplicam a lógica em outros lugares.

**Sinais de detecção:**
- Pasta `services/` (ou `usecases/`, `domain/`) com arquivos contendo classes/funções de domínio.
- **Nenhum** import de `services/X` em `routes/` ou `controllers/`.
- A lógica que **deveria** estar no service está duplicada inline em N rotas.

**Recomendação:** Conectar — mover de fato a lógica das rotas pro service existente, ou se ele estiver mal-feito, refazê-lo e usá-lo. Ver playbook PB09.

---

### <a id="ap10"></a>AP10 — Estado global mutável
**Severidade:** HIGH

**Por que importa:** Race conditions em workers/threads concorrentes. Memory leak (cache sem TTL). Impossível testar (estado contamina entre testes).

**Sinais de detecção:**
- `let globalCache = {}` / `globalCache: dict = {}` no escopo do módulo, mutado por handlers.
- Variável global `db_connection = None` com `check_same_thread=False` (SQLite).
- Singleton implícito (módulo Python importado mantém estado).
- Contador global (`totalRevenue`, `requestCount`) sem lock.

**Recomendação:** Estado por request (DI container, factory por request); cache externalizado (Redis) com TTL; conexão por pool gerenciado pelo framework (Flask `g`, Express middleware). Ver playbook PB10.

---

### <a id="ap11"></a>AP11 — Callback hell / falta de async-await
**Severidade:** HIGH

**Por que importa:** Aninhamento profundo de callbacks é difícil de ler, propaga erros mal, e força controle de fluxo manual (contadores decrementando) que tem bugs latentes silenciosos.

**Sinais de detecção:**
- 3+ níveis de callbacks aninhados em um único handler.
- Controle de fluxo via contadores manuais: `let pending = N; ...; pending--; if (pending === 0) res.json(...)`.
- Em Node: uso de `sqlite3` callback-mode quando o resto do projeto poderia ser Promise-based.

**Recomendação:** Reescrever com `async/await` + Promise-based driver (`better-sqlite3`, `sqlite` lib com promises, `pg` com Promise, etc.). Para sequências de operações DB, usar transação async. Ver playbook PB11.

---

## MEDIUM

### <a id="ap12"></a>AP12 — Query N+1
**Severidade:** MEDIUM

**Por que importa:** Performance que parece OK em dev (3 itens) e degrada drasticamente em prod (10k itens) — 1 query + N queries = quadrático efetivo.

**Sinais de detecção:**
- Loop sobre resultado de query A que faz, dentro do loop, query B para cada elemento.
- `for pedido in pedidos: cursor.execute("SELECT * FROM itens WHERE pedido_id = ?", ...)`.
- Em ORMs: acessar relationship dentro de loop sem `joinedload`/`selectinload` (SQLAlchemy) ou `include`/`populate` (Sequelize/Mongoose).

**Recomendação:** Substituir por JOIN único; em ORM, usar eager loading. Ver playbook PB12.

---

### <a id="ap13"></a>AP13 — Validação duplicada inline
**Severidade:** MEDIUM

**Por que importa:** Mesma regra escrita em N lugares — quando muda, esquece de atualizar em algum e gera inconsistência. Validação inline também mistura preocupação com lógica de negócio.

**Sinais de detecção:**
- Mesmo regex de email em ≥2 arquivos.
- Mesma lista de status válidos (`['pending', 'in_progress', 'done', 'cancelled']`) repetida em routes + model + utils.
- Mesmas regras de tamanho (`if len(title) < 3`) em create_X e update_X.
- Existência de função util de validação (`process_task_data`, `validate_X`) mas as rotas não a usam.

**Recomendação:** Esquemas de validação (marshmallow, pydantic, joi, zod) ou função única chamada pelas rotas. Ver playbook PB13.

---

### <a id="ap14"></a>AP14 — `print` / `console.log` como logger
**Severidade:** MEDIUM

**Por que importa:** Sem nível, sem destino configurável, sem timestamp consistente, sem rotação, sem filtro de PII. Em prod, vira lixo no stdout sem possibilidade de filtrar/agregar.

**Sinais de detecção:**
- `print(...)` / `console.log(...)` em handlers de rota, especialmente com formato `"AÇÃO: detalhe"`.
- Logs com dados sensíveis (email do usuário em login, número de cartão).

**Recomendação:** `logging` (Python stdlib) ou `pino`/`winston` (Node). Logger configurado uma vez no entry point com nível por env var. Ver playbook PB14.

---

### <a id="ap15"></a>AP15 — Erros engolidos
**Severidade:** MEDIUM

**Por que importa:** Erro engolido vira bug invisível em produção. `except:` cego ainda captura `KeyboardInterrupt`/`SystemExit` — o processo nem morre como deveria.

**Sinais de detecção:**
- Python: `try: ... except: pass` ou `except: return jsonify({'error': '...'})` (sem `Exception:` específico).
- Node: callback `(err, result) => { res.send(result); }` sem checar `err`.
- Em vários handlers, `try/except Exception as e` que devolve `str(e)` no response (info leak da exception).
- Auto-confissão (resposta diz "erro ignorado").

**Recomendação:** Error handler **centralizado** (Flask `@app.errorhandler`, Express middleware de erro) que distingue erros conhecidos (validação → 400, not found → 404, auth → 401) de inesperados (500 com mensagem genérica + log do stack). Ver playbook PB15.

---

### <a id="ap16"></a>AP16 — CORS aberto sem allowlist
**Severidade:** MEDIUM

**Por que importa:** `Access-Control-Allow-Origin: *` permite que qualquer site execute requests no nome do usuário (com cookies, em APIs com cookie-based auth).

**Sinais de detecção:**
- `CORS(app)` sem `origins=...`.
- `app.use(cors())` sem `{ origin: ... }`.
- Header literal `'Access-Control-Allow-Origin': '*'`.

**Recomendação:** Lista explícita de origins permitidas via env var (`CORS_ORIGINS=https://app.example.com,https://admin.example.com`). Ver playbook PB16.

---

### <a id="ap17"></a>AP17 — Falta de paginação em listagens
**Severidade:** MEDIUM

**Por que importa:** `SELECT * FROM tasks` retorna 1 registro em dev e 1 milhão em prod. Resposta gigante mata performance e cliente.

**Sinais de detecção:**
- `Model.query.all()` ou `db.all(SELECT *)` em handler de listagem público.
- Ausência de `?page=`/`?limit=`/`?cursor=` nos handlers de coleção.

**Recomendação:** Adicionar `limit`/`offset` (com defaults razoáveis: 20/0, max 100). Ou cursor-based para volumes grandes. Ver playbook PB17.

---

### <a id="ap18"></a>AP18 — Uso de API deprecated
**Severidade:** MEDIUM (escala pra HIGH se for crypto/security)

**Por que importa:** APIs deprecated continuam funcionando por um tempo, mas: param de comportamento (`datetime.utcnow` em Py 3.12+), receber warnings ruidosos, ou perder suporte de fato em uma versão futura. Pior, deprecated em security (MD5) é falha imediata.

**Sinais de detecção (catálogo crescente — sempre adicione quando encontrar):**

| Linguagem / Lib | Deprecated | Substituto moderno |
|---|---|---|
| Python 3.12+ | `datetime.utcnow()`, `datetime.utcfromtimestamp()` | `datetime.now(timezone.utc)`, `datetime.fromtimestamp(ts, tz=timezone.utc)` |
| SQLAlchemy 2.x | `Model.query.get(id)` | `db.session.get(Model, id)` |
| SQLAlchemy 2.x | `engine.execute(...)` | `with engine.connect() as conn: conn.execute(...)` |
| Flask 3.x | `app.before_first_request` | factory pattern (`create_app`) |
| Python crypto | `hashlib.md5`, `hashlib.sha1` (para senhas) | `bcrypt`, `argon2`, `scrypt` |
| Node | `new Buffer(x)` | `Buffer.from(x)` |
| Node | `sqlite3` callback-mode (legado para projetos novos) | `better-sqlite3` (sync) ou `sqlite` package (Promises) |
| Node | `request` (npm package — deprecated) | `axios`, `node-fetch`, `undici`, `fetch` global (Node 18+) |
| Node | `crypto.createCipher` | `crypto.createCipheriv` |
| Express 4 | `app.del(...)` | `app.delete(...)` |
| Python | `imp` module | `importlib` |

**Recomendação:** Substituir conforme tabela. Quando for crypto, **escalar** para CRITICAL (ver AP04).

---

## LOW

### <a id="ap19"></a>AP19 — Magic numbers / enums hardcoded
**Severidade:** LOW

**Por que importa:** Mudança de regra exige caçar números espalhados. Nome explicativo melhora legibilidade.

**Sinais de detecção:**
- Constantes numéricas no meio de lógica (`if faturamento > 10000`, `if priority < 1 or priority > 5`).
- Listas de strings repetidas (`['user', 'admin', 'manager']` em 3 lugares).

**Recomendação:** Constantes nomeadas (`MAX_FREE_TIER_REVENUE`, `VALID_ROLES`) em módulo `constants.py`/`constants.js`, ou enum (`enum.Enum` em Python, objeto literal/`enum` TS em Node).

---

### <a id="ap20"></a>AP20 — Naming críptico / sombreamento de builtin
**Severidade:** LOW

**Por que importa:** Código difícil de ler. `id`, `type`, `list` sombreando builtins viram bugs silenciosos.

**Sinais de detecção:**
- Vars de 1-3 letras com semântica não-óbvia (`u`, `e`, `p`, `cc`, `c_id`, `eml`).
- `def f(id):` / `id = ...` em Python (sombreia `id()` builtin).
- `type(x) == list` em vez de `isinstance(x, list)` (não-pythonic e quebra com subclasses).

**Recomendação:** Renomear pra forma explícita (`user_id`, `email`, `card_number`); usar `isinstance`.

---

### <a id="ap21"></a>AP21 — Imports não usados / código morto
**Severidade:** LOW

**Por que importa:** Ruído visual, sinal de manutenção descuidada. Em alguns casos vira bug latente (variável global "morta" mas exportada que alguém vai começar a usar).

**Sinais de detecção:**
- `import os, sys, json, time` no topo, nenhum usado no arquivo.
- Função/variável definida e nunca chamada.
- Exportação de símbolo (`module.exports = { ..., totalRevenue }`) que ninguém importa.

**Recomendação:** Remover. Linter (`ruff`, `eslint`) pega isso automaticamente — sugerir configuração em projeto sem.

---

## Como usar este catálogo durante a Fase 2

1. Não é necessário cobrir todos os 21 — cubra os que de fato aparecem.
2. Para cada arquivo do projeto, leia com o catálogo em mente e marque os achados.
3. Severidade é **descritiva, não inflacionada**. Se um `print` é só ruído (não tem PII), é MEDIUM. Se loga senha, vira CRITICAL (escala para AP05).
4. Quando um anti-pattern aparece em N lugares no mesmo arquivo, **agrupe** em um único finding com range de linhas — não infle o report com 17 entradas para o mesmo problema.

### Regra de deduplicação entre APs

Alguns padrões disparam mais de uma entrada do catálogo no mesmo ponto de código. Para evitar double-counting no relatório, use esta regra:

- **Use o AP mais específico e descarte o sobreposto.** Não reporte ambos.
- Sobreposições conhecidas:
  - `hashlib.md5(senha)` → reporte **só AP04** (Senha mal protegida). NÃO duplique como AP18 — a "deprecation" já está implícita no AP04.
  - `console.log("Processando cartão ${cc}...")` → reporte **só AP05** (Dados sensíveis em log). Não duplique como AP14 — o problema central é o vazamento, não o `console.log`.
  - Endpoint que dispara SQL arbitrário do body (`/admin/query`) → reporte como **AP02** (sem auth) com nota sobre AP03 (SQL injection) na descrição. Não duplique.
  - Hardcoded secret **e** ele também vazando no `/health` response → reporte como **AP01** com nota sobre AP05 na descrição. Pode optar por listar como 2 findings se quiser separar "secret no source" de "secret no response", mas seja explícito que são problemas conectados.

Quando dois APs cobrem o mesmo site de código sem que um seja mais específico que o outro, escolha o de **maior severidade** e mencione o outro na descrição.

### Não conte o mesmo padrão duas vezes no summary

O `Summary: CRITICAL: <n> | HIGH: <n> | ...` conta **entradas do relatório**, não APs únicos. Se você listar AP01 três vezes (3 arquivos diferentes), conte 3 no CRITICAL. Mas se você fundir em 1 entrada com múltiplos `arquivo:linha`, conte 1.

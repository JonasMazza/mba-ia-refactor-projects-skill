# Analysis Heuristics — Detectando stack, arquitetura e domínio

Use estes sinais durante a **Fase 1**. O objetivo é produzir um retrato honesto do projeto **antes** de auditá-lo. Análise ruim contamina tudo que vem depois.

## 1. Detecção de linguagem

Sinais primários (combine extensão dominante + arquivo de manifest):

| Manifest | Extensões | Linguagem |
|---|---|---|
| `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py` | `.py` | **Python** |
| `package.json` | `.js`, `.mjs`, `.cjs` | **Node.js** |
| `package.json` + `tsconfig.json` | `.ts`, `.tsx` | **TypeScript (Node)** |
| `Gemfile` | `.rb` | **Ruby** |
| `go.mod` | `.go` | **Go** |
| `pom.xml`, `build.gradle` | `.java`, `.kt` | **Java/Kotlin** |
| `composer.json` | `.php` | **PHP** |

Conte arquivos por extensão (excluindo `node_modules/`, `venv/`, etc.). A linguagem dominante é a que tem mais arquivos de código.

## 2. Detecção de framework + versão

Cheque o arquivo de dependências:

| Pista no manifest | Framework |
|---|---|
| `flask`, `Flask` | Flask |
| `fastapi` | FastAPI |
| `django`, `Django` | Django |
| `express` | Express |
| `fastify` | Fastify |
| `@nestjs/*` | NestJS |
| `koa` | Koa |
| `rails` | Rails |
| `sinatra` | Sinatra |
| `gin-gonic/gin` em `go.mod` | Gin |
| `spring-boot-*` em `pom.xml` | Spring Boot |

Extraia a **versão** quando possível (`flask==3.1.1` → 3.1.1; `"express": "^4.18.2"` → 4.18.x).

## 3. Detecção de banco / persistência

| Pista (import ou dep) | Persistência |
|---|---|
| `sqlite3`, `better-sqlite3`, `*.db` na raiz | SQLite |
| `psycopg2`, `pg`, `asyncpg`, `pg-promise` | PostgreSQL |
| `pymysql`, `mysql-connector`, `mysql2` | MySQL |
| `pymongo`, `mongoose`, `motor` | MongoDB |
| `redis`, `ioredis`, `redis-py` | Redis |
| `sqlalchemy`, `flask-sqlalchemy`, `sequelize`, `typeorm`, `prisma`, `peewee` | **anote o ORM em uso** |

**Bonus:** se houver um bootstrap de schema (`database.py`, `initDb`, `migrations/`), extraia os nomes das tabelas para o relatório da Fase 1 — eles ajudam a inferir o domínio.

## 4. Detecção de arquitetura atual

Examine a estrutura de diretórios e classifique em um destes 3 níveis:

### Nível A — Monolítico sem camadas
Sinais:
- Tudo num punhado de arquivos `.py`/`.js` na raiz, sem subdiretórios de código.
- Padrão típico: `app.py` + `models.py` + `controllers.py` + `database.py` lado a lado.
- Ou: tudo numa única classe gigante (`AppManager.js`, `Application.py`).

### Nível B — Parcialmente organizado
Sinais:
- Já existem pastas como `models/`, `routes/`, `controllers/`, `services/`, `utils/`, `middlewares/`.
- **CUIDADO**: existência de pasta ≠ uso real. Para cada pasta, faça uma checagem:
  - `services/` tem código — alguém **importa** esse código? Se ninguém importa, é **service layer órfã** (anti-pattern AP09).
  - `models/` tem código — está sendo usado via ORM, ou ainda há queries inline em outros lugares?
  - `utils/helpers.py` tem funções — as rotas as **chamam**, ou reimplementam tudo inline (anti-pattern AP13)?
- Reporte honestamente: "parcial — `services/` existe mas está órfã" é uma observação **muito** valiosa pro relatório.

### Nível C — MVC já implementado
Sinais:
- Separação clara `models/`, `views/` ou `routes/`, `controllers/`, com cada camada respeitando suas responsabilidades.
- Uso explícito de Dependency Injection ou pelo menos passagem de dependências via construtor.
- Se for este caso, a Fase 3 vira **intervenção cirúrgica** — só corrija os anti-patterns específicos do relatório, não reorganize estruturalmente.

## 5. Detecção do entry point

Procure pelo arquivo que sobe a aplicação:

| Stack | Pista |
|---|---|
| Flask | `app = Flask(__name__)` + `app.run(...)` — tipicamente `app.py` ou `wsgi.py` |
| FastAPI | `app = FastAPI(...)` + `uvicorn.run(...)` ou comando `uvicorn` |
| Django | `manage.py` + `wsgi.py`/`asgi.py` |
| Express | Arquivo apontado por `package.json:main` ou `scripts.start` — tipicamente `src/app.js`, `src/index.js`, `server.js` |
| Fastify | Mesma regra do Express |
| NestJS | `src/main.ts` |

Anote o caminho — vai ser usado na validação da Fase 3.

## 6. Detecção de endpoints

Stack-específico. Use grep com regex:

| Stack | Regex (aproximado) | Exemplo |
|---|---|---|
| Flask | `@\w+\.route\(['"](\/[^'"]*)` ou `add_url_rule\(['"](\/[^'"]*)` | `@app.route('/users')`, `@task_bp.route('/tasks')` |
| Express | `(app\|router)\.(get\|post\|put\|delete\|patch)\(['"](\/[^'"]*)` | `app.get('/users', ...)` |
| FastAPI | `@\w+\.(get\|post\|put\|delete\|patch)\(['"](\/[^'"]*)` | `@app.get('/items')` |
| Django | Em `urls.py`: `path\(['"]([^'"]*)['"]` | `path('users/', ...)` |
| NestJS | `@(Get\|Post\|Put\|Delete\|Patch)\(['"]([^'"]*)` em controllers | `@Get('users')` |

Anote pelo menos: **caminho + método**. Liste explicitamente 2-3 candidatos pra validação da Fase 3:
- 1 endpoint sem side-effect (`GET /`, `GET /health`).
- 1 endpoint de listagem (`GET /<recurso>`).

## 7. Detecção do domínio

Procure (nessa ordem):

1. **Nomes de tabelas/models** — eles são o sinal mais forte:
   - `users`, `produtos`, `pedidos`, `itens_pedido` → API de e-commerce
   - `courses`, `enrollments`, `payments`, `audit_logs` → LMS / checkout
   - `tasks`, `categories`, `users` → task manager
   - `posts`, `comments`, `likes` → social
2. **Rotas** — `/checkout`, `/financial-report`, `/users/:id/courses` reforçam o domínio.
3. **Seed data** — strings em `INSERT INTO ...` ou em scripts de seed costumam ser explícitas ("Notebook Gamer", "Clean Architecture", "Implementar autenticação JWT").
4. **README** do projeto se houver.

Resuma em 1 linha: "API de e-commerce (produtos, pedidos, usuários)".

## 8. O que NÃO fazer na Fase 1

- **Não comece a auditar** agora — só detecte e descreva. Auditoria é Fase 2.
- **Não chute uma stack** sem confirmar — se o `requirements.txt` está vazio, diga "indeterminado" em vez de adivinhar.
- **Não conte arquivos de `node_modules/`, `venv/`, `__pycache__/`, `.git/`, `dist/`, `build/`, `*.lock`** na contagem de "source files".
- **Não confunda "tem pasta X" com "usa pasta X bem".** Faça a checagem de uso real.

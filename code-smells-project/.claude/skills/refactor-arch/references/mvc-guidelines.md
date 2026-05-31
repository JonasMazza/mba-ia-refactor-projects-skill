# MVC Guidelines — Arquitetura-alvo da Fase 3

Esta é a **forma** que a Fase 3 deve dar ao projeto. O padrão MVC (Model-View-Controller) é interpretado para o contexto de APIs backend, onde "View" é frequentemente substituído por "Routes" (a fronteira HTTP).

## Princípios universais

1. **Cada camada tem uma responsabilidade.** Se você não consegue descrever a camada em uma frase, ela está fazendo coisa demais.
2. **Dependência flui em uma direção.** Routes/Views → Controllers → Services → Models. Nunca o contrário.
3. **A camada externa (Routes/Views) não sabe de banco.** Não há `cursor.execute` nem `Model.query.all()` num handler de rota.
4. **A camada interna (Models) não sabe de HTTP.** Não há `request`/`response` num model.
5. **Composition root no entry point.** O lugar que sobe a aplicação é onde dependências são instanciadas e injetadas.

## Responsabilidades por camada

### Models
- Representam **entidades de domínio** (`User`, `Product`, `Task`, `Order`).
- Sabem da estrutura dos dados (colunas, tipos, relações).
- Podem ter métodos de domínio puros (`is_overdue()`, `apply_discount(amount)`).
- **Não sabem** de HTTP, de rotas, de outros casos de uso.
- Em ORMs: classe que herda do base (`db.Model`, `Base`, etc.). Em projetos sem ORM, classe de dados (dataclass / TypedDict) + repositório que faz acesso ao banco.

### Repositories / DAOs (opcional, mas recomendado em projetos sem ORM)
- Encapsulam **queries** sobre um Model.
- Métodos como `find_by_id`, `find_all`, `save`, `delete`.
- Substituem o estilo "todo controller faz `cursor.execute` direto".
- Em projetos com ORM (SQLAlchemy, Sequelize, Mongoose), o ORM já faz esse papel; não precisa criar mais uma camada.

### Services / Use Cases
- Contêm a **lógica de negócio** que envolve mais de um Model ou regras não-triviais.
- Exemplo: `OrderService.create_order(user_id, items)` — valida estoque, calcula total, cria pedido, decrementa estoque, dispara notificações.
- São o lugar onde transações são gerenciadas.
- Não sabem de HTTP. Podem ser chamados de rotas, jobs, CLIs.

### Controllers
- (Quando explicitamente nomeados.) Coordenam um caso de uso completo respondendo a um request.
- Em projetos pequenos, pode-se omitir e ter a rota chamar o service direto. Em projetos médios, controllers concentram o fluxo (validar request → chamar service → traduzir exception em status code).
- **Não contêm regra de negócio** — só orquestração.

### Routes / Views
- A fronteira HTTP. Mapeiam URLs/métodos para handlers.
- Handlers fazem APENAS: parsing do request, chamada do controller/service, render do response.
- Não contêm validação de dados de domínio nem regra de negócio — só validação de **formato** (campos obrigatórios, tipos). Validação de domínio (existe usuário? estoque suficiente?) é responsabilidade do service.

### Middlewares / Decorators
- Cross-cutting concerns: autenticação, logging, CORS, rate limiting, error handling.
- Aplicados antes ou depois dos handlers sem que estes precisem saber.

### Config
- Toda configuração lida de **environment variables** (com defaults sensatos para dev).
- Centralizada em `config/settings.py` ou `src/config/index.js`.
- **Nada de literal sensível em código.**

## Estruturas de diretórios alvo (por stack)

### Python / Flask (monolito → MVC)

```
src/
├── app.py                      # entry point / composition root: cria app, registra blueprints, error handlers
├── config/
│   └── settings.py             # config carregada de env vars
├── models/
│   ├── __init__.py
│   ├── product.py
│   ├── user.py
│   └── order.py
├── repositories/               # (opcional, se sem ORM)
│   ├── product_repository.py
│   └── ...
├── services/
│   ├── auth_service.py
│   ├── product_service.py
│   ├── order_service.py
│   └── report_service.py
├── controllers/                # (opcional, em apps maiores)
│   ├── product_controller.py
│   └── ...
├── routes/                     # blueprints, um por domínio
│   ├── product_routes.py
│   ├── user_routes.py
│   └── order_routes.py
├── middlewares/
│   ├── auth.py                 # decorator @requires_auth
│   └── error_handler.py        # @app.errorhandler centralizado
├── schemas/                    # marshmallow / pydantic — validação de input/output
│   ├── product_schema.py
│   └── ...
└── database.py                 # init do SQLAlchemy / sessão
```

Para Flask: usar **Blueprints** por domínio. Cada `routes/X_routes.py` define um Blueprint e é registrado em `app.py` via `app.register_blueprint(...)`.

### Node.js / Express (monolito → MVC)

```
src/
├── app.js                      # entry point: cria express app, registra middlewares e routers
├── config/
│   └── index.js                # config de env vars
├── models/
│   ├── User.js
│   ├── Course.js
│   └── ...
├── repositories/               # se sem ORM (ex: usando sqlite3 direto)
│   ├── userRepository.js
│   └── ...
├── services/
│   ├── authService.js
│   ├── checkoutService.js
│   └── reportService.js
├── controllers/                # handlers — parsing + chamada do service + response
│   ├── checkoutController.js
│   ├── userController.js
│   └── reportController.js
├── routes/                     # Routers do Express, um por domínio
│   ├── checkoutRoutes.js
│   ├── userRoutes.js
│   └── reportRoutes.js
├── middlewares/
│   ├── auth.js                 # middleware authenticate
│   └── errorHandler.js
├── schemas/                    # joi / zod
│   └── checkoutSchema.js
└── db/
    └── index.js                # init do sqlite/pg/orm
```

Padrão: `app.js` faz `app.use('/api/checkout', checkoutRoutes)`. Os routes são "thin" — só montam paths e middlewares; a lógica fica nos controllers, que chamam services.

### Python/Flask já parcialmente organizado (mantenha o que está bom)

Se o projeto já tem `models/`, `routes/`, `services/`, `utils/`:

- **Não recrie** essas pastas. Trabalhe nelas.
- Se `services/` está órfã, **mova** a lógica das rotas pra lá e faça as rotas importarem.
- Se `utils/helpers.py` tem `process_task_data` e as rotas validam inline, **substitua** as validações inline por chamadas a `process_task_data` (ou migre pra `schemas/` se preferir Marshmallow).
- Adicione o que falta: `middlewares/auth.py`, `middlewares/error_handler.py`, `config/settings.py`.
- Mova `app.config['SECRET_KEY'] = '...'` pra `config/settings.py` lendo de env.
- Mova `db.create_all()` do import time pra um CLI command (`flask init-db` ou similar).

## Regras de implementação

### Composition root no entry point
O arquivo que sobe o app (`app.py`, `src/app.js`) é o único lugar onde:
- Config é carregada.
- DB é inicializado.
- Middlewares globais são registrados (CORS, auth opcional, error handler).
- Blueprints/Routers são registrados.

Ele **não** contém lógica de negócio. Não tem `@app.route` definindo handlers diretamente (exceto talvez `/health` muito simples).

### Imports
- `models/` pode ser importado por `services/`, `controllers/`, `routes/`.
- `services/` pode importar `models/`, `repositories/`. Pode importar outros services.
- `controllers/` importa `services/`, `schemas/`.
- `routes/` importa `controllers/` (ou `services/` em projetos sem controllers explícitos), `middlewares/`, `schemas/`.
- **Models não importam de cima** — não importam services, controllers, routes.

### Tratamento de erros
- Error handler centralizado (`@app.errorhandler` em Flask; middleware com `(err, req, res, next)` em Express).
- Exceptions de domínio (`NotFoundError`, `ValidationError`, `AuthError`) viram status codes (404, 400, 401) com mensagem amigável.
- Exception inesperada vira 500 com mensagem genérica + log do stack (não exponha `str(e)` ao cliente).

### Validação
- Schema (marshmallow / pydantic / joi / zod) na entrada de cada handler que recebe body.
- Validação de domínio (existe? autorizado?) no service, lançando exception apropriada.

## Anti-padrões a evitar na refatoração

- **Criar pastas que não vão ser usadas.** Se o projeto tem 3 rotas e nenhum case de uso complexo, não invente `services/` vazio "para deixar bonito". MVC é meio, não fim.
- **Reescrever do zero quando uma reorganização cirúrgica resolve.** Em projetos parciais, mover código existente pra lugar correto é melhor (e mais seguro) que reescrever.
- **Quebrar a API pública.** Mesmos paths, mesmos métodos, mesmos contratos de response — a menos que a refatoração tenha sido aprovada na pausa da Fase 2.
- **Esquecer o entry point.** Após criar a nova estrutura, o entry point precisa de fato registrar tudo. Senão a app boota mas as rotas retornam 404.

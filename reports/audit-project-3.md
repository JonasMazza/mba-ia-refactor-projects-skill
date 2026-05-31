================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python 3 + Flask 3.0.0 + Flask-SQLAlchemy 3.1.1
Files:   14 analyzed | ~1158 lines of code
Domain:  Task manager API — usuários gerenciam tasks classificadas por categoria, com prioridade, status e due date.

## Summary
CRITICAL: 5 | HIGH: 4 | MEDIUM: 5 | LOW: 2

## Findings

### [CRITICAL] AP01 — Hardcoded Secrets / Credentials
File: app.py:13; services/notification_service.py:7-10
Description: `SECRET_KEY = 'super-secret-key-123'` literal em app.py e credenciais SMTP (`email_user`, `email_password='senha123'`) hardcoded em NotificationService.__init__.
Impact: Tokens assinados com esta key são triviais de forjar; credenciais SMTP no source viram parte do git history para sempre.
Recommendation: Mover para env vars carregadas via `os.environ.get(...)` + `python-dotenv`. Centralizar em `config/settings.py`. Documentar em `.env.example` (sem valores reais). Rotacionar a chave SMTP no provedor (vazada no histórico).

### [CRITICAL] AP02 — Endpoint sem autenticação ou autorização
File: routes/user_routes.py:134-151 (DELETE /users/<id>); routes/user_routes.py:185-211 (POST /login emite token fake); routes/task_routes.py:225-238 (DELETE /tasks/<id>); routes/report_routes.py:211-223 (DELETE /categories/<id>)
Description: Endpoints destrutivos (DELETE users/tasks/categories) e administrativos sem qualquer verificação de token/role. `/login` emite `'fake-jwt-token-' + str(user.id)` — string previsível, não assinada — que nem é validada em lugar nenhum.
Impact: Qualquer cliente pode deletar usuários e dados arbitrariamente. O "token" é cosmético — não há controle de acesso real na aplicação.
Recommendation: Implementar JWT real com PyJWT (assinado com SECRET_KEY, com `exp`). Criar `middlewares/auth.py` com decorator `@requires_auth(role=None)`. Aplicar em todas as rotas destrutivas e em `/users` (admin-only para listar todos).

### [CRITICAL] AP04 — Senha mal protegida (MD5 sem salt)
File: models/user.py:27-32
Description: `set_password` usa `hashlib.md5(pwd.encode()).hexdigest()` e `check_password` compara hashes MD5 determinísticos. MD5 é criptograficamente quebrado e sem salt permite rainbow tables triviais.
Impact: Vazamento do banco vira vazamento de credenciais — usuários reusam senhas em outros serviços. Hashes MD5 sem salt são recuperáveis em segundos.
Recommendation: Migrar para `bcrypt` (`bcrypt.hashpw(pwd.encode(), bcrypt.gensalt())` / `bcrypt.checkpw(...)`). Como é dev data, regenerar seed com bcrypt — não é necessário migrar hashes antigos.

### [CRITICAL] AP05 — Dados sensíveis vazados em response
File: models/user.py:16-25 (campo `password` em `to_dict`); routes/user_routes.py:85-86 (POST /users retorna `to_dict`); routes/user_routes.py:207-211 (POST /login retorna `to_dict`)
Description: `User.to_dict()` inclui o campo `password` (hash MD5). Esse dict é serializado em todos os endpoints de usuário e em `/login`, expondo o hash da senha de qualquer usuário para qualquer requester.
Impact: Combinado com AP04, expõe credenciais hashadas via API pública — atacante coleta hashes navegando `/users/<id>` e quebra offline.
Recommendation: Allowlist explícita em `to_dict`/schema (incluir apenas `id`, `name`, `email`, `role`, `active`, `created_at`). Idealmente criar `schemas/user_schema.py` com marshmallow (já está em requirements.txt mas não é usado).

### [CRITICAL] AP09 — Service layer órfã (NotificationService)
File: services/notification_service.py:1-48
Description: Classe `NotificationService` com métodos `send_email`, `notify_task_assigned`, `notify_task_overdue` existe completa, mas `grep -rn NotificationService` retorna 0 importações fora do próprio arquivo. A camada inteira está morta no código.
Impact: Cria ilusão de boa arquitetura sem entregar o valor. Notificações de atribuição/atraso nunca são disparadas — feature silenciosamente quebrada. Outros desenvolvedores assumem que funciona e duplicam lógica.
Recommendation: Conectar via `TaskService`: ao criar task com `user_id` chamar `notification_service.notify_task_assigned(user, task)`; ao gerar overdue list chamar `notify_task_overdue`. Severidade CRITICAL pelo gap funcional + por estar combinada com AP01 (SMTP password hardcoded).

### [HIGH] AP07 — Lógica de negócio em route (Fat Routes)
File: routes/task_routes.py:11-63 (get_tasks: overdue + join inline); routes/task_routes.py:273-299 (task_stats: agregação inline); routes/report_routes.py:12-101 (summary_report: agregação massiva inline); routes/report_routes.py:103-155 (user_report: agregação inline); routes/user_routes.py:153-183 (get_user_tasks: overdue inline duplicado)
Description: Cinco handlers calculam overdue/agregações/joins de domínio inline com loops Python e múltiplas queries — mistura tradução HTTP com regras de negócio. A lógica `if due_date < utcnow and status not in done/cancelled` está duplicada 5×.
Impact: Lógica não-testável sem subir Flask; não reusável em jobs/CLI; quando regra de "overdue" mudar, precisa atualizar 5 lugares.
Recommendation: Extrair para `services/task_service.py` (`list_tasks`, `get_stats`, `is_overdue`) e `services/report_service.py` (`build_summary`, `build_user_report`). Handler vira parsing + chamada + jsonify.

### [HIGH] AP08 — Multi-write sem transação explícita
File: routes/user_routes.py:134-151 (delete_user)
Description: `delete_user` faz N+1 `db.session.delete(t)` em loop sobre tasks do usuário e só depois `db.session.delete(user)` + `commit`. Se commit falhar no meio, fica estado inconsistente (algumas tasks deletadas, user e demais tasks intactos).
Impact: Após erro silencioso (except cego adjacente), banco fica em estado parcialmente atualizado. Usuários "fantasma" ou tasks órfãs.
Recommendation: Usar `try/except` com `db.session.rollback()` em erro (parcialmente já existe, mas a deleção das tasks acontece fora do try). Idealmente extrair para `user_service.delete_user(id)` com transação atômica + cascade via `relationship(cascade='all, delete-orphan')`.

### [HIGH] AP13 — Validação duplicada inline (e `process_task_data` não usado)
File: routes/task_routes.py:96-114 (validações inline); routes/task_routes.py:166-184 (mesmas validações no update); utils/helpers.py:57-108 (`process_task_data` definido mas ninguém chama)
Description: Validação de `title` (3-200 chars), `status` (lista de 4), `priority` (1-5), `due_date` (formato YYYY-MM-DD) está duplicada em create_task e update_task. A função `process_task_data` no `utils/helpers.py` já implementa exatamente essa validação, mas nenhuma rota a importa.
Impact: Mudança de regra exige atualizar 2+ lugares; util existente é código morto que polui o utils/. Email regex idem (routes/user_routes.py:61 e :106).
Recommendation: Criar `schemas/task_schema.py` e `schemas/user_schema.py` com marshmallow (já em requirements.txt). Routes chamam `TaskSchema().load(data)` que centraliza validação + parsing. Remover `process_task_data` ou usá-lo.

### [HIGH] AP06 — God-route file + bootstrap em import time
File: app.py:30-31; routes/report_routes.py (categorias dentro de reports)
Description: (1) `with app.app_context(): db.create_all()` roda em import time — qualquer import do app dispara criação de schema (testes, CLI, REPL). (2) `report_routes.py` mistura responsabilidades de reports com CRUD completo de `/categories` (4 handlers). Categorias não pertencem ao domínio "reports".
Impact: `db.create_all()` em import time impede uso correto de migrations (Alembic) e duplica criação em qualquer ferramenta que importe `app`. Mistura de domínios em report_routes complica navegação.
Recommendation: Mover `db.create_all()` para CLI command (`@app.cli.command('init-db')`). Extrair categorias para `routes/category_routes.py` (novo blueprint) — preservando `/categories` na URL.

### [MEDIUM] AP12 — Query N+1
File: routes/task_routes.py:41-57 (loop em tasks acessando user e category via `Model.query.get`); routes/report_routes.py:53-68 (loop em users com `Task.query.filter_by(user_id=u.id).all()`); routes/user_routes.py:10-25 (loop em users acessa `u.tasks` lazy)
Description: Em listagens, para cada task/user faz query separada para o relacionamento. Em `summary_report`, cada user dispara 1 SELECT em tasks. Para N usuários e M tasks, são O(N+M) queries em vez de 1 com join.
Impact: Performance OK em dev (10 tasks), degrada drasticamente em prod (1k usuários × 100 tasks cada).
Recommendation: Usar `Task.query.options(joinedload(Task.user), joinedload(Task.category)).all()` em get_tasks. Em summary_report, fazer agregação em 1 query (`func.count` + `group_by(user_id)`).

### [MEDIUM] AP15 — Erros engolidos (`except:` cego)
File: routes/task_routes.py:62-63, 137-138, 204-205, 236-237; routes/user_routes.py:130-131, 149-150; routes/report_routes.py:186-188, 207-209, 221-223; utils/helpers.py:46-49
Description: `except:` cego (sem `Exception`) ou `except Exception` sem log do stack, devolvendo mensagem genérica. Cobre 10+ handlers + util.
Impact: Bugs invisíveis em prod (silenciosamente devolve 500 sem rastro). `except:` cego ainda captura KeyboardInterrupt/SystemExit — processo não morre como deveria.
Recommendation: Substituir por error handler centralizado com `@app.errorhandler(Exception)` em `middlewares/error_handler.py`. Domain exceptions (`NotFoundError`, `ValidationError`) viram códigos certos. Exceptions inesperadas viram 500 + log com traceback.

### [MEDIUM] AP16 — CORS aberto sem allowlist
File: app.py:15
Description: `CORS(app)` aplicado sem `origins=...` — equivalente a `Access-Control-Allow-Origin: *`.
Impact: Qualquer site na internet pode chamar a API em nome do usuário (relevante quando houver auth via cookie).
Recommendation: `CORS(app, origins=settings.CORS_ORIGINS)` lendo de env var (`CORS_ORIGINS=http://localhost:3000,https://app.example.com`).

### [MEDIUM] AP17 — Falta de paginação em listagens
File: routes/task_routes.py:14 (`Task.query.all()`); routes/user_routes.py:12 (`User.query.all()`); routes/report_routes.py:53 (`User.query.all()` no summary); routes/report_routes.py:159 (`Category.query.all()`)
Description: Endpoints de coleção retornam tudo sem `limit`/`offset`/`cursor`.
Impact: 10 registros em dev viram 100k em prod — payload gigante e timeouts.
Recommendation: Adicionar `?page=1&per_page=20` (default 20, max 100). Flask-SQLAlchemy fornece `.paginate(page=p, per_page=pp)` com metadados.

### [MEDIUM] AP18 — Uso de API deprecated
File: `Model.query.get(id)` em routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227 + routes/user_routes.py:29, 94, 117, 136, 155 + routes/report_routes.py:105, 192, 213; `datetime.utcnow()` em models/task.py:15-16, 52; models/user.py:14; models/category.py:11; routes/task_routes.py:31, 72, 215, 285; routes/user_routes.py:172; routes/report_routes.py:35, 45, 71, 133; utils/helpers.py:38; seed.py:66-74
Description: (a) `Model.query.get(id)` é legacy API em SQLAlchemy 2.x, deprecated em favor de `db.session.get(Model, id)`. (b) `datetime.utcnow()` é deprecated em Python 3.12+ por retornar naive datetime.
Impact: Warnings ruidosos; comportamento ambíguo ao comparar com datetimes timezone-aware; possível remoção em versões futuras.
Recommendation: Substituir `Model.query.get(id)` → `db.session.get(Model, id)`. Substituir `datetime.utcnow()` → `datetime.now(timezone.utc)` (importar `timezone`).

### [LOW] AP14 — `print` como logger
File: routes/task_routes.py:149, 153, 219, 234; routes/user_routes.py:83, 89, 147; utils/helpers.py:39, 41
Description: `print(...)` em handlers ("Task criada: ...", "ERRO: ..."). Sem nível, sem timestamp consistente, sem rotação.
Impact: Ruído em prod, impossível filtrar/agregar; mistura com stdout do framework.
Recommendation: Substituir por `logging.getLogger(__name__)` configurado uma vez no entry point com nível por env var.

### [LOW] AP19 — Magic numbers / enums hardcoded espalhados
File: routes/task_routes.py:110, 113, 177, 182 (lista `['pending','in_progress','done','cancelled']`); routes/user_routes.py:71, 120 (`['user','admin','manager']`); models/task.py:39, 46 (mesmas listas); routes/user_routes.py:65, 116 (length checks); routes/task_routes.py:96, 99 (length checks)
Description: Listas de status válidos repetidas 4×; lista de roles 2×; magic numbers (3, 200, 4) inline. `utils/helpers.py:110-116` já define `VALID_STATUSES`, `VALID_ROLES`, `MAX_TITLE_LENGTH`, mas ninguém usa.
Impact: Adicionar novo status exige caçar 4 lugares; magic numbers prejudicam legibilidade.
Recommendation: Importar `VALID_STATUSES` etc. de `utils/helpers.py` (ou mover para `models/constants.py` / `models/enums.py` com `enum.Enum`).

================================
Total: 16 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]

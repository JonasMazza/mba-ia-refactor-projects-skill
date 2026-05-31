================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1 (flask-cors 5.0.1, sqlite3 stdlib)
Files:   4 analyzed | ~780 lines of code
Domain:  API de e-commerce (produtos, usuários, pedidos, relatório de vendas)

## Summary
CRITICAL: 6 | HIGH: 3 | MEDIUM: 5 | LOW: 2

## Findings

### [CRITICAL] AP01 — Hardcoded Secrets / Credentials
File: app.py:7-8
Description: `SECRET_KEY = "minha-chave-super-secreta-123"` e `DEBUG = True` literais no código de aplicação. O mesmo secret também é ecoado no response do `/health` (controllers.py:289).
Impact: Secret entra no git history para sempre; assina/valida sessões Flask. `DEBUG=True` expõe Werkzeug debugger (RCE remoto) se a aplicação for publicada. Vazamento via `/health` torna o problema trivialmente explorável sem precisar acessar o repo.
Recommendation: Carregar via `os.environ.get("SECRET_KEY")` (sem default em prod); `DEBUG` controlado por env (`FLASK_DEBUG`). Adicionar `.env.example` e remover o campo `secret_key` do `/health`. (Ver playbook PB01.)

### [CRITICAL] AP02 — Endpoint sem autenticação ou autorização
File: app.py:47-78 (`/admin/reset-db`, `/admin/query`); app.py:11-30 (todas as rotas administrativas: criar/atualizar/deletar produto, listar usuários, listar todos pedidos, relatório de vendas, atualizar status de pedido)
Description: Nenhum decorator/middleware de auth em rota alguma. `/admin/reset-db` apaga 4 tabelas sem checagem. `/admin/query` executa SQL arbitrário recebido no body. `GET /usuarios` retorna todos os usuários (com senhas). `GET /pedidos/usuario/<id>` aceita id arbitrário sem checar ownership.
Impact: Atacante anônimo pode esvaziar o banco, executar `DROP TABLE`, ler senhas de todos os usuários e ler/modificar pedidos de qualquer um. Equivalente a porta aberta em produção.
Recommendation: Adicionar middleware/decorator de auth (`@requires_auth`), role check (`@requires_role('admin')`) nas rotas administrativas, e remover por completo `/admin/query` (não há caso de uso legítimo para SQL arbitrário via HTTP). (Ver playbook PB02.)

### [CRITICAL] AP03 — SQL Injection via string concatenation
File: models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 148-151, 155, 157-161, 163-166, 174, 188, 192, 206, 220, 224, 280, 289-297; app.py:67-69 (executa SQL bruto do body)
Description: Praticamente todas as queries em `models.py` são montadas via `+ str(...)`/concatenação de string com input do usuário. `login_usuario` (linha 109-111) interpola `email` e `senha` direto. `buscar_produtos` (linha 289-297) monta query incremental (`query += " AND ..."`) com input do usuário. Em `app.py:67-69`, `cursor.execute(query)` é chamado com SQL recebido literalmente no body.
Impact: Permite leitura/modificação/destruição arbitrária do banco. Login pode ser bypassado trivialmente (`' OR '1'='1' --`). LIKE com `%` interpolado em `buscar_produtos` permite tanto injection quanto break com aspas em buscas legítimas.
Recommendation: Substituir TODAS as queries por placeholders parametrizados (`cursor.execute("... WHERE id = ?", (id,))`). Em médio prazo, migrar para SQLAlchemy/ORM. Remover endpoint `/admin/query` (AP02). (Ver playbook PB03.)

### [CRITICAL] AP04 — Senha mal protegida (plain text)
File: database.py:75-83 (seed com senhas em claro); controllers.py:160 (`models.criar_usuario(nome, email, senha)` recebe e persiste plain); models.py:109-111 (login compara `senha == stored_password` via SQL); models.py:122-131 (INSERT da senha sem qualquer hash)
Description: Senhas são gravadas literalmente. Seed insere `("Admin", "admin@loja.com", "admin123", "admin")`. Login compara strings direto na cláusula WHERE.
Impact: Qualquer dump/leak do banco (ou da listagem `/usuarios`, AP05) entrega todas as credenciais. Como muitos usuários reutilizam senhas, o impacto vaza para outros serviços.
Recommendation: Usar `bcrypt` (`pip install bcrypt`): hash no `criar_usuario` com `bcrypt.hashpw(senha.encode(), bcrypt.gensalt())`; verificação no login com `bcrypt.checkpw`. Migrar usuários existentes via reset de senha. Remover senhas do seed (gerar hash no boot). (Ver playbook PB04.)

### [CRITICAL] AP05 — Dados sensíveis vazados em response/log
File: models.py:79-87 (`get_todos_usuarios` inclui campo `senha`); models.py:95-102 (`get_usuario_por_id` idem); controllers.py:132 (response de `GET /usuarios` ecoa o dict completo); controllers.py:161, 179, 182 (logs com email do usuário em login); controllers.py:289 (response de `/health` retorna `secret_key`)
Description: `GET /usuarios` devolve `senha` no JSON para qualquer cliente. `/health` devolve `SECRET_KEY` e `debug` no body. Logs imprimem email em login bem-sucedido e falhado, vazando enumeração de usuários.
Impact: Listagem pública de senhas + secret. PII (emails) em stdout sem filtro. Endpoint de health vira oráculo para reconhecimento.
Recommendation: Allowlist explícita de campos no serializer (`{"id","nome","email","tipo"}` — sem `senha`). Remover todos os campos sensíveis de `/health` (devolver só `{"status":"ok"}`). Trocar `print` por `logging` com filtro de PII (ver AP14). (Ver playbook PB05.)

### [CRITICAL] AP18 — Uso de API deprecated (escalado de MEDIUM por ser crypto/security)
File: models.py:122-131 (criação) + models.py:109-111 (login)
Description: Persistência de senhas em plain text é o "deprecated extremo": nenhuma forma de armazenamento de senha sem hash adequado é aceita pelas práticas atuais (OWASP ASVS, NIST 800-63B). Equivalente moderno: bcrypt / argon2id / scrypt.
Impact: Mesmo impacto de AP04; listado aqui porque o catálogo manda escalar deprecated-de-crypto para CRITICAL.
Recommendation: bcrypt (recomendado para Python) ou argon2-cffi. Ver AP04 acima. (Ver playbook PB04.)

### [HIGH] AP06 — God Module
File: models.py:1-314 (314 linhas); controllers.py:1-292 (292 linhas)
Description: `models.py` mistura persistência de 4 domínios (produtos, usuários, pedidos, itens) + lógica de relatório com regras de desconto (linhas 256-262) + N+1 (ver AP12). `controllers.py` faz parsing + validação inline + lógica de notificação fake (linhas 208-210, 248-250).
Impact: Qualquer mudança em um domínio mexe no arquivo dos outros. Impossível testar isolado. Acoplamento total.
Recommendation: Separar por domínio em packages: `models/produto.py`, `models/usuario.py`, `models/pedido.py`; `controllers/` análogo; extrair regras de negócio para `services/`. (Ver playbook PB06.)

### [HIGH] AP07 — Lógica de negócio em controller / model (Fat Routes + Fat Models)
File: controllers.py:188-220 (`criar_pedido` faz I/O fake de email/SMS/push); controllers.py:237-255 (`atualizar_status_pedido` decide notificações); controllers.py:24-58 (`criar_produto` tem 30+ linhas de validação inline); models.py:235-273 (`relatorio_vendas` calcula desconto progressivo dentro do "model")
Description: Notificações (email/SMS/push) disparadas pelo handler HTTP. Regras de desconto progressivo (10k/5k/1k) escritas no arquivo de persistência. Validação de payload misturada com orquestração.
Impact: Lógica não-testável sem subir Flask. Regras de desconto e notificação não-reaproveitáveis em job/CLI. Mudança de regra de desconto exige mexer em "model".
Recommendation: Criar `services/pedido_service.py` (criar_pedido, atualizar_status), `services/notification_service.py` (interface para email/SMS/push, com implementação real ou fake plugável), `services/relatorio_service.py` (regras de desconto). Controller fica só com parse + chamada + jsonify. (Ver playbook PB07.)

### [HIGH] AP08 — Multi-write flow sem transação
File: models.py:133-169 (`criar_pedido`)
Description: Fluxo faz 1 INSERT em `pedidos`, e em loop sobre os itens: 1 INSERT em `itens_pedido` + 1 UPDATE em `produtos.estoque`. O `db.commit()` está somente no fim, mas qualquer exceção entre os passos (ex: produto deletado entre validação e INSERT) deixa o pedido sem itens ou estoque inconsistente — não há `try/except` com rollback. Pior: a checagem de estoque na primeira passada (linhas 139-146) não trava as linhas, então duas requests concorrentes podem oversell.
Impact: Estado inconsistente em produção (pedidos órfãos, estoque negativo). Em SQLite com `check_same_thread=False` + global connection (AP10), risco aumentado por race.
Recommendation: Envolver em transação explícita (`BEGIN`/`COMMIT`/`ROLLBACK` em try/except) e travar linhas de estoque na leitura (ou usar `UPDATE ... WHERE estoque >= ?` e checar `rowcount`). Idealmente, mover para ORM com `db.session.begin()`. (Ver playbook PB08.)

### [HIGH] AP10 — Estado global mutável
File: database.py:4-12 (`db_connection = None` global, `check_same_thread=False`)
Description: Conexão SQLite singleton no escopo do módulo, compartilhada entre threads do Flask debug server (e workers se for promovido a gunicorn).
Impact: Race conditions em writes concorrentes; transações de uma request podem confundir outra. SQLite com conexão única + threads = bugs intermitentes em produção.
Recommendation: Conexão por request via `flask.g` (`get_db` checa `g.db`, fecha em `teardown_appcontext`). Para Flask + SQLite, esse é o padrão recomendado. (Ver playbook PB10.)

### [MEDIUM] AP12 — Query N+1
File: models.py:171-201 (`get_pedidos_usuario`); models.py:203-233 (`get_todos_pedidos`)
Description: Para cada pedido, faz 1 query para itens + 1 query por item para buscar o nome do produto. Com P pedidos médios I itens: 1 + P*(1+I) queries.
Impact: Em dev (3 pedidos) é imperceptível; em prod com 10k pedidos pode virar 100k+ queries por chamada de `/pedidos`. Endpoint não-paginado (AP17) amplifica.
Recommendation: Uma única query com JOIN: `SELECT p.*, i.*, pr.nome FROM pedidos p LEFT JOIN itens_pedido i ON i.pedido_id=p.id LEFT JOIN produtos pr ON pr.id=i.produto_id WHERE p.usuario_id=?` e agrupar em memória. (Ver playbook PB12.)

### [MEDIUM] AP13 — Validação duplicada inline
File: controllers.py:30-54 (`criar_produto`) vs controllers.py:74-90 (`atualizar_produto`)
Description: Mesma sequência de validações (nome/preco/estoque obrigatórios, preco>=0, estoque>=0, tamanho de nome) duplicada entre create e update. Lista de status válidos hardcoded em controllers.py:242. Lista de categorias hardcoded em controllers.py:52.
Impact: Mudança de regra exige editar N pontos; risco de divergência (de fato, `atualizar_produto` esqueceu da validação de tamanho de nome e de categoria).
Recommendation: Esquemas com `pydantic` ou função única `validate_produto_payload(dados)` chamada por create/update. Constantes `CATEGORIAS_VALIDAS`, `STATUS_VALIDOS` em `constants.py`. (Ver playbook PB13.)

### [MEDIUM] AP14 — `print` como logger
File: controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250; app.py:56, 83-86
Description: `print(...)` espalhado em handlers como mecanismo de log. Vários incluem PII (email do usuário, ver AP05) ou simulam side-effects ("ENVIANDO EMAIL: ...").
Impact: Sem nível, sem timestamp, sem destino configurável. Mistura "log de aplicação" com "side-effect fake". PII em stdout sem filtro fere LGPD/GDPR.
Recommendation: `logging` (stdlib): configurar uma vez no entry point com nível por env (`LOG_LEVEL`). Trocar `print` por `logger.info/warning/error`. Filtro de PII para campos sensíveis. (Ver playbook PB14.)

### [MEDIUM] AP15 — Erros engolidos / info-leak de exception
File: controllers.py:10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 218-220, 226-227, 234-235, 254-255, 261-262, 291-292
Description: Praticamente todos os handlers têm `try: ... except Exception as e: return jsonify({"erro": str(e)}), 500`. `str(e)` vaza detalhe interno (mensagens do SQLite, paths, schema) para o cliente. Não há logging do stack.
Impact: Information disclosure (atacante pode mapear o schema via mensagens de erro); bugs silenciam-se em prod (sem stack capturado). `KeyboardInterrupt`/`SystemExit` também não são capturados aqui porque pegou `Exception`, mas o catch indiscriminado ainda esconde tudo o mais.
Recommendation: Error handler centralizado (`@app.errorhandler(Exception)`) que retorna mensagem genérica + loga stack. Levantar exceções de domínio (`NotFoundError`, `ValidationError`) e mapeá-las para 404/400. Remover try/except dos controllers. (Ver playbook PB15.)

### [MEDIUM] AP16 — CORS aberto sem allowlist
File: app.py:9 (`CORS(app)`)
Description: `CORS(app)` sem `origins=...` libera `*` para todas as rotas, incluindo `/admin/*` e `/login`.
Impact: Qualquer site pode disparar requests autenticadas (se houver cookies) ou ler responses cross-origin. Combinado com AP02 (rotas admin sem auth), a superfície de ataque cresce.
Recommendation: `CORS(app, origins=os.environ.get("CORS_ORIGINS", "").split(","))` com allowlist explícita. (Ver playbook PB16.)

### [MEDIUM] AP17 — Falta de paginação em listagens
File: models.py:4-22 (`get_todos_produtos`); models.py:72-87 (`get_todos_usuarios`); models.py:171-233 (`get_pedidos_usuario`, `get_todos_pedidos`); models.py:285-314 (`buscar_produtos`)
Description: Todas as listagens fazem `SELECT *` sem `LIMIT`/`OFFSET`. Endpoints expõem isso publicamente (com listagem de pedidos sendo agravada pelo N+1, AP12).
Impact: Response gigante em prod; latência alta; risco de OOM. `/usuarios` sem paginação + sem auth = dump completo de usuários.
Recommendation: Adicionar `?page=` / `?limit=` (default 20, máximo 100) nas listagens. Aplicar `LIMIT ? OFFSET ?` nas queries. (Ver playbook PB17.)

### [LOW] AP19 — Magic numbers / enums hardcoded
File: models.py:257-262 (thresholds de desconto 10000/5000/1000 e taxas 0.1/0.05/0.02); controllers.py:48-50 (tamanho nome 2/200); controllers.py:52 (lista de categorias); controllers.py:242 (lista de status)
Description: Regras de negócio embutidas como constantes numéricas/strings no meio do código, repetidas em mais de um lugar (status também aparece em models e como string default no schema).
Impact: Mudança de regra exige caçar números; risco de divergência (a regra de desconto fica difícil de auditar/testar).
Recommendation: `constants.py` com `DISCOUNT_TIERS`, `CATEGORIAS_VALIDAS`, `STATUS_PEDIDO` (idealmente `enum.Enum`). Usado por services/controllers.

### [LOW] AP20 — Naming críptico / sombreamento de builtin
File: models.py:24, 43, 54, 65, 89, 92 etc. (parâmetro `id` em várias funções); controllers.py:14, 56, 64, 98, 101, 136, 160 (idem)
Description: Parâmetro `id` sombreia o builtin `id()` em quase toda função de produto/usuário/pedido.
Impact: Bug latente (uso futuro de `id()` retornará a variável); legibilidade ruim.
Recommendation: Renomear para `produto_id`, `usuario_id`, `pedido_id` conforme contexto. Configurar `ruff` com regra `A` (flake8-builtins).

================================
Total: 17 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]

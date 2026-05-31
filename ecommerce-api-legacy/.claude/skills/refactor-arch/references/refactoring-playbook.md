# Refactoring Playbook — Receitas de transformação (Fase 3)

Cada receita resolve um anti-pattern (ou família) do `anti-patterns.md`. Estrutura padrão de cada receita:
- **Resolve:** APXX (referência ao catálogo)
- **Quando aplicar**
- **Antes** (código com o problema)
- **Depois** (refatorado)
- **Notas** (gotchas comuns)

Os exemplos cobrem Python/Flask **e** Node/Express. Aplique a versão da sua stack; o padrão é o mesmo.

## Índice

- [PB01 — Extrair secrets para env vars](#pb01)
- [PB02 — Adicionar auth middleware/decorator](#pb02)
- [PB03 — Substituir string-concat SQL por queries parametrizadas / ORM](#pb03)
- [PB04 — Migrar hash de senha para bcrypt/argon2](#pb04)
- [PB05 — Allowlist de campos no serializer + logger seguro](#pb05)
- [PB06 — Quebrar God Module em camadas + Blueprints/Routers por domínio](#pb06)
- [PB07 — Extrair lógica de negócio do controller para service](#pb07)
- [PB08 — Envolver multi-write em transação atômica](#pb08)
- [PB09 — Conectar service layer órfã](#pb09)
- [PB10 — Eliminar estado global (request-scoped + cache externalizado)](#pb10)
- [PB11 — Promisify / async-await callback hell](#pb11)
- [PB12 — Eliminar N+1 com JOIN ou eager loading](#pb12)
- [PB13 — Substituir validação inline por schema](#pb13)
- [PB14 — Configurar logger estruturado](#pb14)
- [PB15 — Error handler centralizado](#pb15)
- [PB16 — CORS com allowlist por env](#pb16)
- [PB17 — Paginação por query params](#pb17)
- [PB18 — Atualizar APIs deprecated](#pb18)

---

## <a id="pb01"></a>PB01 — Extrair secrets para env vars
**Resolve:** AP01

**Quando aplicar:** sempre que houver literal de credencial/key/senha em source.

**Antes (Flask):**
```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.config["DEBUG"] = True
```

**Depois:**
```python
# config/settings.py
import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    SECRET_KEY = os.environ["SECRET_KEY"]            # explode se faltar — bom
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
    DB_URL = os.environ.get("DB_URL", "sqlite:///loja.db")

settings = Settings()

# app.py
from config.settings import settings
app.config["SECRET_KEY"] = settings.SECRET_KEY
app.config["DEBUG"] = settings.DEBUG
```

**Antes (Express):**
```js
const config = { dbPass: "senha_super_secreta", paymentGatewayKey: "pk_live_..." };
```

**Depois:**
```js
// src/config/index.js
require('dotenv').config();

if (!process.env.PAYMENT_GATEWAY_KEY) throw new Error('PAYMENT_GATEWAY_KEY missing');

module.exports = {
  port: parseInt(process.env.PORT || '3000', 10),
  dbPass: process.env.DB_PASS,
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY,
  smtpUser: process.env.SMTP_USER,
};
```

Crie `.env.example` (sem valores reais) e adicione `.env` ao `.gitignore`.

**Notas:** Para chaves que **já vazaram** no histórico do git, a refator não basta — é preciso rotacionar a chave no provedor. O relatório da Fase 2 deve mencionar isso na recomendação.

---

## <a id="pb02"></a>PB02 — Adicionar auth middleware/decorator
**Resolve:** AP02

**Antes (Flask):**
```python
@app.route('/admin/reset-db', methods=['POST'])
def reset_database():
    # ... apaga tudo, sem auth
```

**Depois:**
```python
# middlewares/auth.py
from functools import wraps
from flask import request, jsonify
import jwt
from config.settings import settings

def requires_auth(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            except jwt.PyJWTError:
                return jsonify({'error': 'unauthorized'}), 401
            if role and payload.get('role') != role:
                return jsonify({'error': 'forbidden'}), 403
            request.user = payload
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# routes/admin_routes.py
@admin_bp.route('/admin/reset-db', methods=['POST'])
@requires_auth(role='admin')
def reset_database():
    ...
```

**Depois (Express):**
```js
// middlewares/auth.js
const jwt = require('jsonwebtoken');
const { secretKey } = require('../config');

function requiresAuth(role) {
  return (req, res, next) => {
    const token = (req.headers.authorization || '').replace('Bearer ', '');
    try {
      const payload = jwt.verify(token, secretKey);
      if (role && payload.role !== role) return res.status(403).json({ error: 'forbidden' });
      req.user = payload;
      next();
    } catch {
      res.status(401).json({ error: 'unauthorized' });
    }
  };
}
module.exports = { requiresAuth };

// routes/adminRoutes.js
router.delete('/users/:id', requiresAuth('admin'), adminController.deleteUser);
```

**Notas:** Endpoints destrutivos (DELETE, reset) **exigem** role check. GET de dados de outros usuários exige ownership check (compare `req.user.id` com `:id` ou role admin).

---

## <a id="pb03"></a>PB03 — SQL parametrizado ou ORM
**Resolve:** AP03

**Antes:**
```python
cursor.execute("SELECT * FROM produtos WHERE id = " + str(id))
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
```

**Depois (parametrizado):**
```python
cursor.execute("SELECT * FROM produtos WHERE id = ?", (id,))
cursor.execute("SELECT * FROM usuarios WHERE email = ? AND senha = ?", (email, senha_hashed))
```

**Depois (com SQLAlchemy):**
```python
# models/product.py
class Product(db.Model):
    __tablename__ = 'produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200))
    # ...

# repositories ou direto no service
product = db.session.get(Product, id)
user = User.query.filter_by(email=email).first()
```

**Antes (Node, callback-style):**
```js
db.run(`SELECT * FROM users WHERE id = ${id}`);
```

**Depois:**
```js
db.run('SELECT * FROM users WHERE id = ?', [id]);
// ou com better-sqlite3:
const user = db.prepare('SELECT * FROM users WHERE id = ?').get(id);
```

**Notas:** Para LIKE com input variável, use `?` no padrão e monte o argumento: `cursor.execute("... LIKE ?", (f"%{termo}%",))`. Para queries dinâmicas (filtros opcionais), construa a lista de params em paralelo: `query_parts.append("AND categoria = ?"); params.append(categoria)`.

---

## <a id="pb04"></a>PB04 — bcrypt/argon2 para senha
**Resolve:** AP04

**Antes (MD5):**
```python
# models/user.py
def set_password(self, pwd):
    self.password = hashlib.md5(pwd.encode()).hexdigest()
def check_password(self, pwd):
    return self.password == hashlib.md5(pwd.encode()).hexdigest()
```

**Depois (bcrypt):**
```python
import bcrypt

def set_password(self, pwd: str):
    self.password = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt(rounds=12)).decode()
def check_password(self, pwd: str) -> bool:
    return bcrypt.checkpw(pwd.encode(), self.password.encode())
```

**Antes (Node "badCrypto"):**
```js
function badCrypto(pwd) { /* base64 truncado */ }
```

**Depois:**
```js
const bcrypt = require('bcrypt');                    // ou 'bcryptjs' (pure JS, sem build chain)
async function hashPassword(pwd) { return bcrypt.hash(pwd, 12); }
async function verifyPassword(pwd, hash) { return bcrypt.compare(pwd, hash); }
```

> **Em Node, prefira `bcryptjs`** quando o ambiente não tem build chain (macOS sem Xcode CLI tools, container alpine sem `python`/`make`/`g++`, CI minimal). API é compatível com `bcrypt`, dispensa `node-gyp`. Performance ~30% menor — aceitável pra maioria dos casos.

**Notas:** A migração de senhas existentes não pode ser feita "para o lado" (não dá pra converter MD5 em bcrypt sem ter a senha original). A estratégia padrão é: marcar usuários como "precisa rehash"; no próximo login bem-sucedido (validando o MD5), regravar como bcrypt. Documente isso na recommendation se houver usuários produtivos.

---

## <a id="pb05"></a>PB05 — Serializer com allowlist + logger seguro
**Resolve:** AP05

**Antes:**
```python
def to_dict(self):
    return {'id': self.id, 'name': self.name, 'email': self.email, 'password': self.password, ...}
```

**Depois:**
```python
PUBLIC_FIELDS = ('id', 'name', 'email', 'role', 'active', 'created_at')
def to_dict(self):
    return {f: getattr(self, f) for f in PUBLIC_FIELDS}
```

Ou usando marshmallow (preferível em projetos médios):
```python
# schemas/user_schema.py
from marshmallow import Schema, fields
class UserPublicSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    email = fields.Email()
    role = fields.Str()
    # 'password' NÃO declarado
```

**Logger seguro (vide PB14):** filtros que mascaram PII conhecidos antes de emitir. Para cartão de crédito, **nunca** logue — nem mascarado, melhor não passar pelo logger nenhum.

---

## <a id="pb06"></a>PB06 — Quebrar God Module
**Resolve:** AP06

**Antes (Flask):**
- `models.py` com produtos + usuários + pedidos + relatórios (315 linhas, queries inline).
- `controllers.py` com handlers de 4 domínios.
- `app.py` com 16 `add_url_rule(...)` listados a mão.

**Depois:**
```
src/
├── app.py                      # cria app, registra blueprints
├── models/
│   ├── product.py              # class Product
│   ├── user.py
│   └── order.py
├── services/
│   ├── product_service.py
│   ├── auth_service.py
│   ├── order_service.py
│   └── report_service.py
├── routes/
│   ├── product_routes.py       # product_bp = Blueprint('products', ...)
│   ├── user_routes.py
│   ├── order_routes.py
│   └── report_routes.py
└── database.py
```

`app.py`:
```python
from flask import Flask
from config.settings import settings
from database import db
from routes.product_routes import product_bp
from routes.user_routes import user_bp
from routes.order_routes import order_bp
from routes.report_routes import report_bp
from middlewares.error_handler import register_error_handlers

def create_app():
    app = Flask(__name__)
    app.config.from_object(settings)
    db.init_app(app)
    app.register_blueprint(product_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(report_bp)
    register_error_handlers(app)
    return app

if __name__ == '__main__':
    create_app().run(host='0.0.0.0', port=settings.PORT)
```

**Notas:** A `app.py` deveria ter no máximo 30-50 linhas após a refator. Se passar disso, ainda tem coisa demais ali.

---

## <a id="pb07"></a>PB07 — Lógica de negócio em service
**Resolve:** AP07

**Antes:**
```python
@app.route('/pedidos', methods=['POST'])
def criar_pedido():
    dados = request.get_json()
    # 30 linhas de validação, cálculo de total, inserts, decremento de estoque,
    # print de "ENVIANDO EMAIL", print de "ENVIANDO SMS", print de "ENVIANDO PUSH"...
    return jsonify(...)
```

**Depois:**
```python
# services/order_service.py
class OrderService:
    def __init__(self, notification_service):
        self.notifications = notification_service

    def create_order(self, user_id: int, items: list[dict]) -> Order:
        # validação de domínio
        # cálculo de total
        # criação do pedido (com transação — ver PB08)
        # disparo das notificações
        return order

# routes/order_routes.py
@order_bp.route('/pedidos', methods=['POST'])
@requires_auth()
def criar_pedido():
    data = OrderCreateSchema().load(request.get_json())   # validação de formato
    order = order_service.create_order(data['user_id'], data['items'])
    return jsonify(OrderSchema().dump(order)), 201
```

**Notas:** O service não usa `request` nem `jsonify`. Isso é o que permite chamá-lo de um job, CLI, ou teste sem subir o framework.

---

## <a id="pb08"></a>PB08 — Transação atômica
**Resolve:** AP08

**Antes:**
```python
cursor.execute("INSERT INTO pedidos ...")
for item in itens:
    cursor.execute("INSERT INTO itens_pedido ...")
    cursor.execute("UPDATE produtos SET estoque = ...")
db.commit()
```

**Depois (raw SQL):**
```python
try:
    cursor.execute("BEGIN")
    cursor.execute("INSERT INTO pedidos ...")
    for item in itens:
        cursor.execute("INSERT INTO itens_pedido ...", (...))
        cursor.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", (qty, pid))
    db.commit()
except Exception:
    db.rollback()
    raise
```

**Depois (SQLAlchemy):**
```python
try:
    with db.session.begin():
        order = Order(user_id=user_id, ...)
        db.session.add(order)
        for item in items:
            db.session.add(OrderItem(...))
            db.session.execute(update(Product).where(...).values(estoque=...))
    # commit automático ao sair do bloco com sucesso
except Exception:
    raise   # rollback automático
```

**Depois (Node — better-sqlite3, sync):**
```js
const checkout = db.transaction((userId, items) => {
  const orderId = db.prepare('INSERT INTO orders ...').run(userId, ...).lastInsertRowid;
  for (const item of items) {
    db.prepare('INSERT INTO order_items ...').run(orderId, item.id, item.qty);
    db.prepare('UPDATE products SET stock = stock - ? WHERE id = ?').run(item.qty, item.id);
  }
  return orderId;
});
const orderId = checkout(userId, items);
```

---

## <a id="pb09"></a>PB09 — Conectar service órfã
**Resolve:** AP09

**Quando aplicar:** projeto tem `services/X.py` com lógica útil, mas nenhuma rota importa.

**Receita:**
1. Identificar onde a lógica do service **deveria** estar sendo usada (as rotas que duplicam).
2. Verificar se o service está bem-feito; se não, refatorá-lo (PB07).
3. Trocar a duplicação inline por `from services.X import xservice; xservice.do_thing(...)`.
4. Garantir que o service é instanciado uma vez (no entry point ou factory) e injetado/importado consistentemente.

**Exemplo:** `NotificationService` órfã + 4 rotas com `print("ENVIANDO EMAIL ...")`. Após a refator: rotas chamam `notification_service.notify_X(...)`, o service centraliza o envio (e pode ser desligado em testes via mock/no-op service).

---

## <a id="pb10"></a>PB10 — Eliminar estado global
**Resolve:** AP10

**Antes:**
```js
let globalCache = {};
let totalRevenue = 0;
function logAndCache(k, v) { globalCache[k] = v; }
module.exports = { globalCache, totalRevenue, logAndCache };
```

**Depois (cache externalizado):**
```js
// services/cacheService.js
const Redis = require('ioredis');
const redis = new Redis(process.env.REDIS_URL);
async function set(k, v, ttl = 3600) { await redis.set(k, JSON.stringify(v), 'EX', ttl); }
async function get(k) { const v = await redis.get(k); return v ? JSON.parse(v) : null; }
module.exports = { set, get };
```

Para projetos pequenos sem Redis: cache **por request** (DI) ou simplesmente eliminado (na maioria dos casos o "cache" não estava sendo lido por ninguém).

**Para conexão DB global** (Python):
```python
# antes: db_connection global
# depois: usar flask-sqlalchemy (gerencia pool por request) ou Flask `g`:
from flask import g
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(...)
    return g.db
@app.teardown_appcontext
def close_db(_):
    db = g.pop('db', None)
    if db is not None: db.close()
```

---

## <a id="pb11"></a>PB11 — async/await em vez de callback hell
**Resolve:** AP11

**Antes (Express + sqlite3 callback):**
```js
app.post('/checkout', (req, res) => {
  db.get("SELECT * FROM courses WHERE id = ?", [cid], (err, course) => {
    db.get("SELECT id FROM users WHERE email = ?", [email], (err, user) => {
      db.run("INSERT INTO enrollments ...", [user.id, cid], function(err) {
        db.run("INSERT INTO payments ...", [this.lastID, ...], function(err) {
          // 5 níveis...
        });
      });
    });
  });
});
```

**Depois (better-sqlite3 sync + transaction):**
```js
// services/checkoutService.js
function checkout({ userId, courseId, cardNumber }) {
  const course = db.prepare('SELECT * FROM courses WHERE id = ? AND active = 1').get(courseId);
  if (!course) throw new NotFoundError('course');
  const status = paymentGateway.charge(cardNumber, course.price);   // sem console.log de PAN!
  if (status !== 'PAID') throw new PaymentDeclinedError();

  return db.transaction(() => {
    const enrId = db.prepare('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)')
                     .run(userId, courseId).lastInsertRowid;
    db.prepare('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)')
      .run(enrId, course.price, status);
    return enrId;
  })();
}

// controllers/checkoutController.js
async function checkoutHandler(req, res, next) {
  try {
    const data = await checkoutSchema.validateAsync(req.body);
    const enrollmentId = checkoutService.checkout(data);
    res.status(200).json({ enrollmentId });
  } catch (err) { next(err); }
}
```

**Notas:** Se a stack exige Promise-based (driver async), faça o mesmo padrão com `async/await` em vez do sync wrapper.

---

## <a id="pb12"></a>PB12 — Eliminar N+1
**Resolve:** AP12

**Antes (raw SQL):**
```python
for pedido in pedidos:
    cursor.execute("SELECT * FROM itens_pedido WHERE pedido_id = ?", (pedido['id'],))
    for item in itens:
        cursor.execute("SELECT nome FROM produtos WHERE id = ?", (item['produto_id'],))
```

**Depois (JOIN):**
```python
cursor.execute("""
    SELECT p.id, p.usuario_id, p.total, ip.produto_id, ip.quantidade, ip.preco_unitario, prod.nome
    FROM pedidos p
    LEFT JOIN itens_pedido ip ON ip.pedido_id = p.id
    LEFT JOIN produtos prod ON prod.id = ip.produto_id
    WHERE p.usuario_id = ?
""", (user_id,))
# montar a estrutura aninhada em uma passada Python
```

**Depois (SQLAlchemy eager loading):**
```python
from sqlalchemy.orm import joinedload
orders = (
    db.session.query(Order)
    .options(joinedload(Order.items).joinedload(OrderItem.product))
    .filter(Order.user_id == user_id)
    .all()
)
```

**Notas:** Para coleções grandes, `selectinload` (1 query extra para a relação inteira) costuma ser melhor que `joinedload` (cartesiano).

---

## <a id="pb13"></a>PB13 — Validação por schema
**Resolve:** AP13

**Antes:**
```python
if not data: return jsonify({'error': 'dados inválidos'}), 400
if 'title' not in data: return jsonify({'error': 'título obrigatório'}), 400
if len(data['title']) < 3: return jsonify({'error': 'curto'}), 400
# ...repetido em create_task e update_task
```

**Depois (marshmallow):**
```python
# schemas/task_schema.py
from marshmallow import Schema, fields, validate

class TaskCreateSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=3, max=200))
    description = fields.Str(load_default='')
    status = fields.Str(validate=validate.OneOf(['pending', 'in_progress', 'done', 'cancelled']))
    priority = fields.Int(validate=validate.Range(min=1, max=5), load_default=3)
    user_id = fields.Int()
    category_id = fields.Int()
    due_date = fields.Date()
    tags = fields.List(fields.Str())

# routes/task_routes.py
@task_bp.route('/tasks', methods=['POST'])
def create_task():
    try:
        data = TaskCreateSchema().load(request.get_json() or {})
    except ValidationError as e:
        return jsonify({'errors': e.messages}), 400
    task = task_service.create(data)
    return jsonify(TaskSchema().dump(task)), 201
```

**Notas:** Em Node, equivalentes são `joi` e `zod`. Schemas vivem em `schemas/` (Python) ou `schemas/`/`validators/` (Node) e são reutilizados entre create/update (use `partial=True` em update).

---

## <a id="pb14"></a>PB14 — Logger estruturado
**Resolve:** AP14

**Antes:** `print(f"Login bem-sucedido: {email}")`.

**Depois (Python):**
```python
# config/logging.py
import logging
import sys
def configure_logging(level: str = 'INFO'):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

# no entry point
configure_logging(level=settings.LOG_LEVEL)

# em qualquer módulo
import logging
log = logging.getLogger(__name__)
log.info("login.success", extra={'user_id': user.id})   # NÃO logar email/PII
```

**Depois (Node):**
```js
const pino = require('pino');
const log = pino({ level: process.env.LOG_LEVEL || 'info' });
log.info({ userId: user.id }, 'login.success');
```

**Notas:** Nunca logue número de cartão, CVV, ou senha — nem mascarado (PCI-DSS).

---

## <a id="pb15"></a>PB15 — Error handler centralizado
**Resolve:** AP15

**Antes:** cada handler com `try/except` que devolve `str(e)`.

**Depois (Flask):**
```python
# middlewares/error_handler.py
from flask import jsonify
from marshmallow import ValidationError

class AppError(Exception):
    status = 500
    def __init__(self, msg, status=None):
        super().__init__(msg)
        self.status = status or self.status

class NotFoundError(AppError): status = 404
class ValidationFailedError(AppError): status = 400
class AuthError(AppError): status = 401

def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app(e): return jsonify({'error': str(e)}), e.status

    @app.errorhandler(ValidationError)
    def handle_marshmallow(e): return jsonify({'errors': e.messages}), 400

    @app.errorhandler(Exception)
    def handle_unexpected(e):
        log.exception("unhandled")
        return jsonify({'error': 'internal server error'}), 500
```

**Depois (Express):**
```js
// middlewares/errorHandler.js
function errorHandler(err, req, res, _next) {
  req.log.error({ err }, 'request.failed');
  const status = err.status || 500;
  const message = status === 500 ? 'internal server error' : err.message;
  res.status(status).json({ error: message });
}
module.exports = errorHandler;

// no app.js — registrar POR ÚLTIMO (depois de todas as rotas)
app.use(errorHandler);
```

---

## <a id="pb16"></a>PB16 — CORS com allowlist
**Resolve:** AP16

**Antes:** `CORS(app)` / `app.use(cors())`.

**Depois (Flask):**
```python
allowed_origins = settings.CORS_ORIGINS.split(',')
CORS(app, origins=allowed_origins, supports_credentials=True)
```

**Depois (Express):**
```js
const cors = require('cors');
const allowedOrigins = process.env.CORS_ORIGINS.split(',');
app.use(cors({
  origin: (origin, cb) => allowedOrigins.includes(origin) ? cb(null, true) : cb(new Error('CORS')),
  credentials: true,
}));
```

---

## <a id="pb17"></a>PB17 — Paginação
**Resolve:** AP17

**Antes:** `return jsonify([t.to_dict() for t in Task.query.all()])`.

**Depois (offset/limit):**
```python
# helpers/pagination.py
def paginate(query, request):
    page = max(1, int(request.args.get('page', 1)))
    limit = min(100, max(1, int(request.args.get('limit', 20))))
    items = query.offset((page - 1) * limit).limit(limit).all()
    total = query.order_by(None).count()
    return {'items': items, 'page': page, 'limit': limit, 'total': total}

# routes/task_routes.py
@task_bp.route('/tasks')
def list_tasks():
    result = paginate(Task.query, request)
    return jsonify({
        'items': [TaskSchema().dump(t) for t in result['items']],
        'page': result['page'], 'limit': result['limit'], 'total': result['total'],
    })
```

---

## <a id="pb18"></a>PB18 — Atualizar deprecated APIs
**Resolve:** AP18

Tabela de substituições (referência rápida — para mais, ver catálogo AP18):

| Antes | Depois |
|---|---|
| `datetime.utcnow()` | `datetime.now(timezone.utc)` |
| `datetime.utcfromtimestamp(ts)` | `datetime.fromtimestamp(ts, tz=timezone.utc)` |
| `Model.query.get(id)` | `db.session.get(Model, id)` |
| `engine.execute(sql)` | `with engine.connect() as c: c.execute(text(sql))` |
| `hashlib.md5(pwd)` (para senha) | `bcrypt.hashpw(pwd, bcrypt.gensalt())` (PB04) |
| `new Buffer(x)` | `Buffer.from(x)` |
| `app.del(...)` (Express 3) | `app.delete(...)` |
| `sqlite3` callback (Node) | `better-sqlite3` (sync) ou `sqlite` (Promise) — ver PB11 |
| `request` npm package | `axios` / `node-fetch` / `undici` / global `fetch` |
| `crypto.createCipher` | `crypto.createCipheriv` |
| Flask `before_first_request` | factory `create_app()` + setup explícito |

Para cada substituição, faça também busca-global no projeto (`grep`) — esses padrões costumam estar em vários arquivos.

---

## Sequência sugerida na Fase 3

Aplique nesta ordem (segurança primeiro, depois estrutura, depois qualidade):

1. **PB01** (extrair secrets) — sem isso, o resto não vai pra prod.
2. **PB03, PB04, PB05** (SQL injection, senha, vazamento) — falhas de segurança.
3. **PB02** (auth em endpoints destrutivos).
4. **PB06** (quebrar God Module) — cria a estrutura onde o resto vai morar.
5. **PB07, PB09** (mover lógica pra service) — em projetos parciais, isso é a parte central.
6. **PB08, PB11** (transação, async) — corrigem flows críticos (checkout, pedido).
7. **PB12, PB13** (N+1, validação).
8. **PB14, PB15** (logger, error handler) — cross-cutting.
9. **PB10, PB16, PB17** (estado global, CORS, paginação).
10. **PB18** (deprecated APIs) — busca-global no fim, varrendo tudo de uma vez.

Após cada passo significativo, faça uma rodada de **validação leve** (importa sem erro? sobe app?). Não acumule muitas mudanças sem testar.

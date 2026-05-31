================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   Node.js + Express 4.18.2 (SQLite via sqlite3 ^5.1.6 callback-mode)
Files:   3 analyzed | ~180 lines of code
Domain:  LMS / e-commerce de cursos — checkout (cria user + matrícula + pagamento + audit log), relatório financeiro admin e delete de usuário

## Summary
CRITICAL: 5 | HIGH: 5 | MEDIUM: 4 | LOW: 2

## Findings

### [CRITICAL] AP01 — Hardcoded Secrets / Credentials
File: src/utils.js:1-7
Description: O objeto `config` tem `dbUser`, `dbPass: "senha_super_secreta_prod_123"`, `paymentGatewayKey: "pk_live_1234567890abcdef"` e `smtpUser` literais no source. A chave `pk_live_*` é prefixo público reconhecível de provider de pagamento (Stripe-like) — qualquer leak do repo expõe credencial de produção.
Impact: Vazamento permanente via git history; scanners automáticos detectam `pk_live_*` em minutos. `paymentGatewayKey` ainda é logado no checkout (ver AP05), amplificando exposição.
Recommendation: Mover tudo para `process.env.*` (carregado via `dotenv`). Criar `.env.example` sem valores reais; ler em `src/config/index.js`. Ver playbook PB01.

### [CRITICAL] AP02 — Endpoint sem autenticação ou autorização
File: src/AppManager.js:80 (GET /api/admin/financial-report); src/AppManager.js:131 (DELETE /api/users/:id)
Description: Rotas administrativas e destrutivas estão expostas sem nenhum middleware de auth. `GET /api/admin/financial-report` retorna receita total e e-mails dos alunos para qualquer cliente HTTP. `DELETE /api/users/:id` permite remover qualquer usuário sem token, sem role e sem ownership check.
Impact: Dump completo de dados sensíveis e destruição arbitrária de contas via curl. PII/financial leak + DoS por delete em massa.
Recommendation: Adicionar middleware `authRequired` em todas as rotas `/api/admin/*` exigindo role `admin` via JWT; `DELETE /api/users/:id` exige token e ownership (ou role admin). Ver playbook PB02.

### [CRITICAL] AP04 — Senha mal protegida ("custom crypto" base64)
File: src/utils.js:17-23; src/AppManager.js:68 (chamada)
Description: `badCrypto` faz loop de 10000 concatenações de `Buffer.from(pwd).toString('base64').substring(0,2)` e retorna os 10 primeiros chars. Resultado: hash determinístico, sem salt, derivado de base64 truncado — em prática equivale a guardar a senha em claro com encoding diferente.
Impact: Vazamento do banco = vazamento de senhas; rainbow tables triviais; usuários que reusam senha são comprometidos em outros serviços. PCI/LGPD violation.
Recommendation: Substituir por `bcrypt.hash(pwd, 10)` com salt automático; comparar com `bcrypt.compare`. Remover `badCrypto` por completo. Ver playbook PB04.

### [CRITICAL] AP05 — Dados sensíveis vazados em log (PAN do cartão)
File: src/AppManager.js:45
Description: `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)` loga o **número inteiro do cartão** (PAN) e a chave do gateway de pagamento em stdout.
Impact: Violação clara de PCI-DSS Req. 3.4 (PAN nunca pode ser armazenado/logado sem mascaramento). Stdout em prod normalmente vai para agregador → cartão fica armazenado em sistema fora de escopo PCI. Multa + perda de capacidade de processar pagamentos.
Recommendation: REMOVER o log. Se realmente precisa de rastreio, logar apenas BIN (6 primeiros) + last4 (`411122******4444`) via logger com filtro de PII (`pino`/`winston`). Nunca logar a `paymentGatewayKey`. Ver playbook PB05.

### [CRITICAL] AP08 — Multi-write flow sem transação
File: src/AppManager.js:50-62 (insert enrollment → insert payment → insert audit log); também src/AppManager.js:69-72 (insert user antes do flow)
Description: O fluxo de checkout executa até 4 INSERTs em cascata (user → enrollment → payment → audit_log) sem `BEGIN TRANSACTION`/`COMMIT`/`ROLLBACK`. Se o insert de payment falhar depois da matrícula, o usuário fica com curso ativo sem pagamento.
Impact: Estado financeiro inconsistente (matrícula sem pagamento, ou pagamento sem audit log). Reconciliação manual em prod é cara e propensa a erro. Combinado com AP11, o controle de fluxo é tão frágil que partial-writes em erro são quase certos.
Recommendation: Envolver o fluxo num bloco transacional (`db.exec('BEGIN')` … `COMMIT`/`ROLLBACK`) ou usar `better-sqlite3` que oferece `db.transaction(fn)` síncrono. Ver playbook PB08.

### [HIGH] AP06 — God Class
File: src/AppManager.js:1-142
Description: Uma única classe `AppManager` concentra: criação da conexão DB, criação de schema + seeds (initDb), definição de TODAS as 3 rotas, regras de negócio do checkout (decisão de pagamento, criação condicional de usuário, persistência em cascata), construção do relatório financeiro e delete de usuário. Não há separação de camada nem por domínio nem por responsabilidade.
Impact: Impossível testar em isolamento (sempre precisa subir Express + DB in-memory); qualquer mudança numa rota arrisca quebrar as outras; onboarding lento.
Recommendation: Quebrar em `src/{config,db,models,repositories,services,controllers,routes,middlewares,schemas}/`. Ver playbook PB06.

### [HIGH] AP07 — Lógica de negócio em route handler (Fat Routes)
File: src/AppManager.js:28-78 (handler POST /api/checkout); src/AppManager.js:80-129 (handler GET financial-report)
Description: O handler de `/api/checkout` decide criação condicional de usuário, processamento de pagamento, cascade de inserts e audit log — tudo dentro do `app.post(...)`. O handler de `financial-report` calcula agregação (revenue) e monta o relatório dentro do handler com callbacks aninhados.
Impact: Lógica não reusável fora do HTTP (não dá pra rodar checkout num job/CLI), não testável sem Express, e mistura HTTP-translation com regras de negócio.
Recommendation: Extrair para `services/CheckoutService.js` (`execute({user, course, card})`) e `services/ReportService.js` (`buildFinancialReport()`). Controllers viram parsing + chamada + render. Ver playbook PB07.

### [HIGH] AP10 — Estado global mutável
File: src/utils.js:9-10, 15; src/utils.js:25 (export)
Description: Módulo expõe `globalCache = {}` mutado por `logAndCache` (chamado em `AppManager.js:59`) e `totalRevenue = 0` (exportado mas nunca lido em lugar nenhum). Estado vive enquanto o processo viver, sem TTL e sem expiração.
Impact: Memory leak (cache cresce indefinidamente por usuário); race conditions sob carga; testes contaminam uns aos outros. `totalRevenue` é código morto que confunde leitor.
Recommendation: Remover `totalRevenue` (não usado em lugar nenhum). Trocar `globalCache` por `Map` com TTL (ex: `node-cache`) **ou** remover se for puro log — o `logAndCache` na linha 59 não tem leitor algum, então o cache também pode sumir. Ver playbook PB10.

### [HIGH] AP11 — Callback hell / falta de async-await
File: src/AppManager.js:37-77 (checkout: 5 níveis de callback aninhados); src/AppManager.js:83-128 (financial-report: contadores manuais `coursesPending` / `enrPending`)
Description: O checkout aninha `db.get` → `db.get` → `db.run` → `db.run` → `db.run` (5 níveis). O relatório financeiro implementa controle de fluxo manual decrementando contadores (`coursesPending--; if (coursesPending === 0) res.json(report)`) — padrão clássico de bugs latentes (race entre nested callbacks, contador nunca chega a 0 se um path errar).
Impact: Difícil de ler, propaga erros mal (vários `err` sequer são checados — ver AP15), e o controle de fluxo manual já tem bug: linha 95-99 (`enrollments.length === 0`) faz `report.push` mas não cobre o caso de `err` no SELECT enrollments.
Recommendation: Trocar driver para `better-sqlite3` (sync, simples) ou `sqlite` (Promise-based) e reescrever ambos os handlers com `async/await`. Ver playbook PB11.

### [HIGH] AP15 — Erros engolidos
File: src/AppManager.js:57 (callback do audit log ignora `err`); src/AppManager.js:104 e 106 (callbacks de user/payment não checam `err` — só seguem); src/AppManager.js:131-137 (delete user ignora `err` e ainda responde 200 com mensagem irônica auto-confessando o bug)
Description: Vários callbacks `(err, ...) => {...}` simplesmente ignoram `err`. O delete user responde "Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco." mesmo se o `DELETE` falhar — auto-confissão do problema.
Impact: Bugs invisíveis em prod; cliente recebe 200 mesmo em falha; debugging vira pesadelo.
Recommendation: Error handler centralizado (Express middleware `(err, req, res, next) => ...`); todos os callbacks DB checam `err` e propagam via `next(err)`. Ver playbook PB15.

### [MEDIUM] AP12 — Query N+1 no relatório financeiro
File: src/AppManager.js:83-128
Description: `financial-report` faz 1 query em `courses`, depois para cada curso 1 query em `enrollments`, depois para cada enrollment 2 queries (user + payment). Para N cursos e M alunos por curso = 1 + N + 2·N·M queries.
Impact: 3 cursos × 5 alunos = 31 queries; 100 cursos × 50 alunos = 10101 queries. Latência cresce quadraticamente; em prod com volume real, endpoint vira inacessível.
Recommendation: Substituir tudo por 1 JOIN: `SELECT c.id, c.title, u.name, u.email, p.amount, p.status FROM courses c LEFT JOIN enrollments e ON e.course_id=c.id LEFT JOIN users u ON u.id=e.user_id LEFT JOIN payments p ON p.enrollment_id=e.id` e agregar em memória. Ver playbook PB12.

### [MEDIUM] AP13 — Validação inline misturada com lógica
File: src/AppManager.js:29-35
Description: Validação dos campos de entrada do checkout (`u`, `e`, `cid`, `cc`) é feita inline com `if (!u || !e || !cid || !cc) return res.status(400).send("Bad Request")`. Não valida formato de e-mail nem que `card` tem 16 dígitos numéricos, nem que `pwd` tem tamanho mínimo. Nenhum schema reutilizável.
Impact: Garbage-in (e-mail malformado, card com letras) passa pela validação; regras espalhadas ficarão inconsistentes se outra rota também precisar validar.
Recommendation: Schema declarativo via `zod` ou `joi` em `src/schemas/checkout.schema.js`, aplicado por middleware antes do controller. Ver playbook PB13.

### [MEDIUM] AP14 — `console.log` como logger
File: src/AppManager.js:45; src/utils.js:13; src/app.js:13
Description: Uso de `console.log` para sinalizar "Processando cartão", "Salvando no cache" e "rodando na porta". Sem nível, sem timestamp consistente, sem destino configurável.
Impact: Em prod stdout vira lixo sem possibilidade de filtrar nível ou rotacionar. Nota: AP05 já cobre o caso CRITICAL específico do log com PAN; este finding cobre o uso geral. Ver regra de dedup.
Recommendation: Adotar `pino` (rápido, JSON-by-default) com nível por env (`LOG_LEVEL=info`). Ver playbook PB14.

### [MEDIUM] AP18 — Uso de API deprecated (`sqlite3` callback-mode)
File: package.json (dep `sqlite3`); src/AppManager.js (uso em todo o arquivo)
Description: Driver `sqlite3` callback-mode é o legado para projetos novos; ecosistema migrou para `better-sqlite3` (sync, transações nativas) ou `sqlite` (wrapper Promise-based em cima de `sqlite3`).
Impact: Força callback hell (AP11), não tem suporte nativo a transações via API ergonômica, manutenção do package é lenta.
Recommendation: Migrar para `better-sqlite3` — sync, suporta `db.transaction(fn)` e `db.prepare(...).all/get/run()`. Alternativa: `sqlite` package se quiser manter assinatura async.

### [LOW] AP20 — Naming críptico
File: src/AppManager.js:29-33
Description: Variáveis do body do request renomeadas para `u`, `e`, `p`, `cid`, `cc` — sem ganho de concisão real, perdendo legibilidade. Schema do request (`req.body.usr`, `eml`, `pwd`, `c_id`, `card`) também usa abreviações desnecessárias.
Impact: Leitor precisa decifrar; aumenta probabilidade de bug em manutenção.
Recommendation: Renomear para `name`, `email`, `password`, `courseId`, `cardNumber`. Aceitar opcionalmente os nomes antigos no schema por compatibilidade backward, mas mapear para nomes claros internamente.

### [LOW] AP21 — Imports não usados / código morto exportado
File: src/utils.js:10, 25
Description: `totalRevenue` é declarado, exportado, e nunca lido em lugar nenhum do projeto. `badCrypto` será removido em PB04. `globalCache` é exportado mas só `logAndCache` o mexe — leitura externa zero.
Impact: Ruído; sinal de manutenção descuidada; convida alguém a começar a usar `totalRevenue` achando que faz algo.
Recommendation: Remover `totalRevenue` por completo; remover `globalCache` da exportação (interno se mantido). Adicionar `eslint` com `no-unused-vars` em CI.

================================
Total: 16 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]

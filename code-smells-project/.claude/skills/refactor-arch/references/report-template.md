# Report Template — Audit Report (Fase 2)

Use este template **exato** ao renderizar o relatório no terminal e ao salvar em `reports/audit-project-<N>.md`. A consistência do formato é o que permite comparar projetos.

## Estrutura geral

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <nome do diretório>
Stack:   <Linguagem + Framework + versão>
Files:   <N> analyzed | ~<L> lines of code
Domain:  <descrição em 1 linha>

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

## Findings

<um bloco por finding, ordenado por severidade descendente>

================================
Total: <N> findings
================================
```

## Formato de cada finding

Cada finding é um bloco markdown:

```markdown
### [<SEV>] <APXX — Nome do anti-pattern>
File: <caminho/relativo.ext>:<linha>  (ou range :<de>-<até>)
Description: <1-2 linhas descrevendo o que está errado naquele ponto específico.>
Impact: <1-2 linhas — por que isso importa em produção / segurança / manutenção.>
Recommendation: <1-2 linhas acionáveis. Para AP18 (deprecated), inclua o equivalente moderno.>
```

### Exemplo 1 — finding CRITICAL

```markdown
### [CRITICAL] AP03 — SQL Injection via string concatenation
File: models.py:28
Description: Query `SELECT * FROM produtos WHERE id = " + str(id)` concatena input do usuário direto na SQL. O mesmo padrão se repete em models.py:47-50, 57-61, 92, 109-111, 280, 291.
Impact: Permite leitura/modificação/destruição arbitrária do banco. Em `login_usuario` (linha 109-111), permite bypass trivial (`' OR '1'='1`).
Recommendation: Substituir todas as queries por placeholders parametrizados (`cursor.execute("... WHERE id = ?", (id,))`). Em médio prazo, migrar para SQLAlchemy.
```

### Exemplo 2 — finding MEDIUM com deprecated API

```markdown
### [MEDIUM] AP18 — Uso de API deprecated (`datetime.utcnow()`)
File: models/task.py:52; models/user.py:14; models/category.py:11; routes/task_routes.py:31, 72, 285
Description: `datetime.utcnow()` é deprecated em Python 3.12+ por retornar objeto naive (sem timezone).
Impact: Warnings ruidosos no upgrade do Python; comportamento ambíguo ao comparar com objetos timezone-aware.
Recommendation: Substituir por `datetime.now(timezone.utc)`. Importar `timezone` de `datetime`.
```

### Exemplo 3 — finding HIGH agrupando múltiplas linhas

```markdown
### [HIGH] AP07 — Lógica de negócio em route (Fat Routes)
File: routes/report_routes.py:30-68
Description: Handler `summary_report` calcula overdue, agregações por usuário, e taxa de conclusão dentro do handler HTTP. Mistura tradução de request com regras de domínio.
Impact: Lógica não-testável sem subir Flask; não reusável (ex: gerar mesmo relatório em job ou CLI exige duplicar).
Recommendation: Extrair para `services/report_service.py` com método `build_summary()`. Handler vira: chamada do service + `jsonify`.
```

## Regras de conteúdo

- **Sempre inclua arquivo e linha.** Se o anti-pattern aparece em N lugares, agrupe num único finding com range (`:30-68`) ou lista de pontos (`models/task.py:52; models/user.py:14`).
- **Não invente.** Se você não tem certeza da linha, releia o arquivo antes de escrever. Pior do que um relatório curto é um relatório errado.
- **Recommendation acionável.** "Refatorar" sozinho não ajuda. "Extrair para `services/X.py` com método `build_summary`" ajuda.
- **Severidade descritiva.** Não infle severidade pra "parecer rigoroso". Use o catálogo: se está marcado como MEDIUM lá, é MEDIUM no relatório (a menos que combine com outro pattern que escale — ex: `print` com PII vira AP05 CRITICAL).
- **Ordem:** CRITICAL → HIGH → MEDIUM → LOW. Dentro da mesma severidade, ordene por arquivo (alfabético) ou por gravidade percebida.

## Após o relatório (pausa obrigatória)

Termine o output (e o arquivo) com esta linha exata:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

**Pare aí. Não chame mais tools. Aguarde o "y" do usuário.**

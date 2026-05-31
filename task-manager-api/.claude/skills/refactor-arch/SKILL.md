---
name: refactor-arch
description: Audita e refatora projetos backend legados para a arquitetura MVC (Model-View-Controller) de forma agnóstica de stack. Executa 3 fases sequenciais — análise do projeto, auditoria de anti-patterns com relatório formal, e refatoração validada por boot + endpoints. Use SEMPRE que o usuário invocar /refactor-arch, ou pedir para analisar arquitetura, refatorar para MVC, auditar anti-patterns ou code smells em uma codebase, modernizar projeto legado, reorganizar um monolito, ou produzir um audit report arquitetural. Funciona com Python/Flask, Node/Express, FastAPI, Django, NestJS e outras stacks de backend.
---

# Refactor-Arch — Auditoria e refatoração arquitetural para MVC

## O que esta skill faz

Pega o projeto no `cwd` e o leva para o padrão MVC em **3 fases obrigatórias e sequenciais**:

1. **Análise** — detecta stack (linguagem, framework, banco), mapeia arquitetura atual, identifica entry point, endpoints e domínio.
2. **Auditoria** — cruza o código contra o catálogo de anti-patterns, gera relatório classificado por severidade (CRITICAL/HIGH/MEDIUM/LOW), **pausa e pede confirmação** antes de mudar qualquer arquivo.
3. **Refatoração** — reestrutura para MVC, aplica as receitas do playbook, e **valida** que a aplicação continua funcionando (boot + endpoints).

A skill é agnóstica de tecnologia: o catálogo descreve padrões por **sinais** (não por palavras-chave de um framework), e o playbook tem exemplos em múltiplas stacks.

## Princípios gerais (válidos para as 3 fases)

- **Cite arquivo e linha exatos.** Achados sem `arquivo:linha` (ou range `arquivo:linha-linha`) são inúteis pra validação humana.
- **Não invente.** Se você não consegue confirmar uma detecção lendo o código, deixe fora do relatório. É melhor um relatório curto e correto do que longo e fabricado.
- **Preserve o que funciona.** A meta da Fase 3 é "mesmos endpoints, melhor estrutura". Não reescreva do zero quando não precisa. Em projeto parcialmente organizado, **evolua** o que existe.
- **Pause obrigatoriamente entre Fase 2 e Fase 3.** O humano precisa revisar o relatório antes de qualquer modificação. Essa pausa não é cosmética — é onde humano e skill se alinham.
- **Use os blocos de status visuais** (`================================ PHASE N: ...`) — eles são o principal feedback pro usuário.
- **Quando algo falhar, reporte honestamente.** Não declare sucesso falso. Se a app não bootou após a refator, diga, mostre o stderr, e ofereça-se pra debugar.

---

## Fase 1 — Análise

**Antes de começar, leia `references/analysis-heuristics.md`** — tem os sinais concretos para detectar linguagem/framework/banco/domínio em qualquer stack.

Passos:

1. Liste os arquivos do projeto excluindo `node_modules/`, `venv/`, `__pycache__/`, `.git/`, `dist/`, `build/`, `.next/`, `target/`.
2. Use as heurísticas para identificar:
   - **Linguagem** dominante
   - **Framework** principal + versão
   - **Dependências** que mudam a arquitetura (ORM, CORS, auth lib, etc.) — não a lista inteira
   - **Banco de dados** + nome das tabelas se possível
   - **Arquitetura atual** — descrição honesta (monolito de N arquivos? parcialmente organizado mas camada X está órfã? MVC já implementado?)
3. Identifique o **entry point** (`app.py`, `src/app.js`, `package.json:main`/`scripts.start`).
4. Identifique os **endpoints** declarados (varra por `@app.route`, `app.get/post/...`, `router.*`, `add_url_rule`, etc.). Liste pelo menos os de leitura (`GET /`, `GET /<recurso>`, `/health`) que vão servir pra validar a Fase 3.
5. Identifique o **domínio** (1 linha) a partir dos models/rotas/seed.

Imprima o bloco de status exatamente neste formato:

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <linguagem>
Framework:     <framework + versão se detectada>
Dependencies:  <libs arquiteturalmente relevantes>
Domain:        <1 linha do que a app faz>
Architecture:  <descrição honesta — monolito / parcial / MVC>
Source files:  <N> files analyzed (~<L> LOC)
DB tables:     <tabelas detectadas, ou "n/a">
Entry point:   <caminho do arquivo de boot>
Endpoints:     <N endpoints identificados — liste 2-3 dos mais óbvios>
================================
```

---

## Fase 2 — Auditoria

**Antes de começar, leia `references/anti-patterns.md`** (catálogo) **e `references/report-template.md`** (formato do relatório).

Passos:

1. Para cada arquivo de código fonte, varra contra o catálogo. Para cada anti-pattern detectado, registre:
   - **Severidade** (CRITICAL/HIGH/MEDIUM/LOW)
   - **ID + nome do anti-pattern** (ex: `AP03 — SQL Injection via string concatenation`)
   - **Arquivo:linha** (use range `arquivo:linha-linha` quando relevante)
   - **Descrição curta** do que está errado naquele ponto
   - **Impacto** (1-2 linhas)
   - **Recomendação curta** (1-2 linhas, acionável)
2. Quando detectar uso de **API deprecated** (AP18 do catálogo), inclua o equivalente moderno na recomendação.
3. Aspire a um mínimo de **5 achados** com pelo menos **1 CRITICAL ou HIGH**. Se de fato não houver mais que isso, não invente — projeto pequeno pode ter poucos problemas. Mas se houver mais, liste todos os relevantes.
4. Ordene por severidade descendente (CRITICAL → HIGH → MEDIUM → LOW).
5. Renderize o relatório seguindo `report-template.md`.
6. **Salve o relatório em arquivo:**
   - Detecte o caminho: se existir um diretório `reports/` em algum ancestral do `cwd` (geralmente o repositório-pai), use `<repo_root>/reports/audit-project-<N>.md`.
   - Se o usuário não tiver dito o N, pergunte ou deduza pelo nome do diretório (project-1 / project-2 / etc.). Se for impossível, use `<cwd>/reports/audit.md`.
7. Imprima o relatório também no terminal (mesmo conteúdo do arquivo).
8. **PAUSE.** Termine com a linha:

   ```
   Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
   ```

   E **pare**. Não chame mais tools. Aguarde a resposta do usuário.

Se o usuário responder `n` (ou variações de negação), pare e ofereça-se pra iterar o relatório. Só prossiga pra Fase 3 com `y` (ou variação de afirmação) explícita.

---

## Fase 3 — Refatoração

**Antes de começar, leia `references/mvc-guidelines.md`** (arquitetura-alvo por stack) **e `references/refactoring-playbook.md`** (receitas concretas com before/after).

Passos:

1. Decida a estrutura de diretórios alvo conforme `mvc-guidelines.md` para a stack detectada na Fase 1.
2. Adapte a profundidade da intervenção ao **nível atual** do projeto:
   - **Monolítico** (1-5 arquivos, tudo junto) → crie do zero a estrutura MVC e mova o código.
   - **Parcialmente organizado** (já tem `models/`, `routes/`, etc.) → mova lógica de negócio das rotas pra services/controllers, elimine duplicação, conecte camadas órfãs, mas **não recrie** o que já está OK.
   - **MVC implementado** → intervenção cirúrgica: só corrija os anti-patterns específicos do relatório.

   > **Antes de criar uma pasta nova**, `ls` no projeto. Se `services/` já existe, refatore o conteúdo em vez de criar `src/services/` ao lado. Diretórios duplicados são pior que ausentes — confundem qual é a fonte da verdade.
3. Para cada achado da Fase 2, aplique a receita correspondente do `refactoring-playbook.md`.
4. **Preserve a API pública**: mesmos endpoints, mesmos contratos (a menos que o humano tenha aprovado mudança no momento da pausa).
5. Mantenha o git status limpo de cada passo: vá fazendo commits parciais não é obrigatório, mas se precisar voltar atrás, use `git diff` pra ver o que mudou e `git checkout -- <file>` pra reverter pontos específicos.

### Validação (obrigatória — não pule)

Depois de mover o código:

1. **Limpe o banco de dev**, se houver (`rm -f loja.db tasks.db *.sqlite`). Schemas que mudaram (ex: senha plain → bcrypt hash, novas colunas) falham silenciosamente contra DB antigo.
2. **Boot.** Execute o entry point (`python app.py`, `npm start`, etc.) em background com timeout curto (5-10s). Capture exit code e stderr. Se quebrar → corrija antes de prosseguir.
   - **Dica macOS:** a porta `5000` é capturada pelo AirPlay Receiver desde macOS 12+. Se vir "Address already in use", suba com `PORT=5555 python app.py` (a config já lê de env var após a refator).
3. **Endpoints.** Faça `curl` (ou equivalente) em **pelo menos 2 endpoints**:
   - Um sem side-effect: `GET /` ou `GET /health` (espere 2xx).
   - Um de listagem: `GET /<recurso>` (espere 2xx ou 401 se exigir auth — 401 é OK se o endpoint passou a exigir auth como parte da correção).
4. **Mate o processo** da app depois de validar (`kill <pid>` ou similar).
5. Se alguma validação falhar, **não declare conclusão**. Reporte o erro, mostre o stderr, e itere.

Imprima o bloco final:

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<árvore do diretório com `tree -L 3 -I 'node_modules|venv|__pycache__'` ou equivalente>

## Anti-patterns addressed
<lista por severidade, ID + nome curto>

## Validation
  ✓ Application boots without errors
  ✓ GET / → 200
  ✓ GET /<recurso> → 200 (ou 401 esperado)
  ✓ Zero <padrão crítico> remaining   (ex: hardcoded secrets, SQL injection)
================================
```

---

## Resolução de problemas comuns

- **App não boota** após refator → reverta as últimas mudanças (`git checkout -- <file>` ou `git stash`) e itere mais devagar.
- **Endpoint 404** → verifique se o Blueprint/Router foi registrado no entry point.
- **Import error** → verifique imports circulares (Model → Controller → Model). Quebre com lazy imports ou inversão de dependência.
- **Achou anti-pattern fora do catálogo** → registre no relatório como `[UNCATEGORIZED]` com a mesma estrutura. Não esconda só porque não está catalogado.
- **Refator quebrou um teste existente** → mantenha os testes verdes. Ajuste imports nos testes se preciso, mas não mude o que eles validam sem perguntar.

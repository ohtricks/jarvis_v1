# Jarvis v1 — contexto para Claude Code

Assistente pessoal de IA para macOS. Respostas sempre em **português brasileiro (pt-BR)**.

## Como rodar

```bash
# Terminal 1 — proxy LiteLLM (obrigatório)
litellm --config config.yaml

# Terminal 2 — uso normal
jarvis "abra o chrome"
jarvis -x "liste os arquivos"      # -x executa de verdade (padrão: dry-run)
jarvis --dry "git push"            # força dry-run explícito
jarvis --yes "abra o vscode"       # alias de -x

# Com debug log detalhado
JARVIS_DEBUG=1 jarvis "abra o chrome"
```

### Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `ANTHROPIC_API_KEY` | — | API key real (usada via LiteLLM, obrigatória) |
| `OPENAI_API_BASE` | `http://localhost:4000` | URL do proxy LiteLLM |
| `OPENAI_API_KEY` | `sk-local` | Key do proxy (pode ser dummy) |
| `JARVIS_DEBUG` | `0` | `1` ativa debug logging em JSONL |
| `JARVIS_EXECUTE` | `0` | `1` inicia o server HTTP em modo execute (executa skills de verdade) |
| `JARVIS_PORT` | `8899` | porta do server HTTP |
| `JARVIS_TOKEN_REQUIRED` | `0` | `1` exige `X-Jarvis-Token` no server HTTP |

## Arquitetura (V3)

```
Input → [Built-in?] → [Router LLM: fast] → fast_reply | executor | planner
                                                           ↓           ↓
                                                        fast/brain  reasoning+thinking
                                                           ↓
                                                        [Queue] → [Risk Gate] → [Skill] → [Memory]
                                                                       ↓ (se bloqueado)
                                                                   [Aguarda confirmação do usuário]
                                                                       ↓ (yes / YES I KNOW)
                                                                   [Retoma execução]
```

- **Planner** (`reason:/think:/plan:`) — multi-step via reasoning, executa até bloqueio; suporta recovery automático
- **Executor** (`exec:/brain:`) — compila 1-3 ações via fast ou brain
- **Fast reply** (`fast:`) — resposta direta, sem actions (usa fast)
- **Built-in** — comandos do sistema processados sem nenhuma chamada LLM

## Arquivos críticos

### Core / Orquestração

| Arquivo | Responsabilidade |
|---------|-----------------|
| `jarvis/main.py` | Entry point CLI; processa flags `--execute/-x`, `--dry`, `--yes/-y` |
| `jarvis/agent.py` | Orquestrador — ponto de entrada do `run()`; aprende contexto de ações |
| `jarvis/llm.py` | Interface LLM; parâmetro `role=` identifica chamada no log; força `temperature=1` em reasoning |
| `jarvis/router.py` | Classifica input → fast_reply / executor / planner; suporta prefixos forçados |
| `jarvis/planner.py` | Gera plano multi-step via modelo `reasoning`; injeta context de memória |
| `jarvis/executor_llm.py` | Compila 1-3 ações via LLM para rota executor (`make_actions()`) |
| `jarvis/executor.py` | Executa itens da fila um a um; integra risk gate e recovery |
| `jarvis/commands.py` | Built-in commands sem LLM (yes, mode, auth, status, cancel, history...) |
| `jarvis/prompts.py` | Centraliza todos os prompts (ROUTER, PLANNER, ACTION_COMPILER, etc.) |
| `jarvis/ux.py` | Formata stages de execução e respostas UX para o usuário |

### Persistência / Estado

| Arquivo | Responsabilidade |
|---------|-----------------|
| `jarvis/queue.py` | Fila persistida em `~/.jarvis/queue.json`; máquina de estados por item |
| `jarvis/memory.py` | Estado persistido em `~/.jarvis/memory.json`; turns, session, state, pending |
| `jarvis/telemetry.py` | Log de debug + métricas de tokens; ativo com `JARVIS_DEBUG=1` |
| `jarvis/context_engine.py` | Captura CWD, git repo, branch — atualiza memory silenciosamente |

### Segurança / Risco

| Arquivo | Responsabilidade |
|---------|-----------------|
| `jarvis/risk.py` | Classifica risco: safe / risky / danger; gera mensagem de confirmação |
| `jarvis/risk_policy.py` | Carrega/salva `~/.jarvis/risk_policy.json` (patterns editáveis pelo usuário) |
| `jarvis/shell_policy.py` | Allowlist/blocklist de prefixos shell em `~/.jarvis/shell_policy.json` |
| `jarvis/security.py` | Redact de credenciais em logs; `secure_prompt()` para OAuth |
| `jarvis/observation.py` | Analisa output de falha; extrai sinais (cmd_not_found, permission_denied...) |
| `jarvis/autonomy_safe.py` | Propõe plano heurístico de recovery **sem LLM**, sempre read-only |

### Skills / Integrações

| Arquivo | Responsabilidade |
|---------|-----------------|
| `jarvis/skills/` | Diretório de skills; cada skill herda de `Skill` |
| `jarvis/skills/base.py` | Classe base `Skill` com contrato `run(args: dict) -> str` |
| `jarvis/skills/registry.py` | `build_skills()` retorna dict action→skill; `_CATALOG` com Capabilities |
| `jarvis/skills/capabilities.py` | Dataclass `Capability`; `get_capabilities_text()` para system prompts |
| `jarvis/integrations/google/gmail_api.py` | Wrapper Gmail API (list, get, send, reply, modify_labels) |
| `jarvis/server.py` | HTTP server FastAPI — 5 endpoints REST; ver seção **Server HTTP** abaixo |
| `config.yaml` | Modelos LiteLLM (fast/brain/reasoning), fallbacks, cache, timeout |

## Skills disponíveis

### Namespaces

```
system          → open_app, open_url, run_shell
dev             → git_status, git_add_all, git_commit, git_push
google.gmail
  read          → google_gmail_list_today, google_gmail_list_unread,
                  google_gmail_search, google_gmail_get_message, google_gmail_get_latest
  threads       → google_gmail_summarize_today, google_gmail_summarize_unread,
                  google_gmail_summarize_thread
  write         → google_gmail_send_email, google_gmail_reply
  labels        → google_gmail_mark_read, google_gmail_archive
```

### Risco por skill

| Skill | Risco | Observação |
|-------|-------|-----------|
| `open_app`, `open_url` | safe | Nunca bloqueia |
| `git_status`, `google_gmail_*` (read/threads) | safe | Somente leitura |
| `git_add_all`, `git_commit`, `git_push` | risky | Pede confirmação |
| `google_gmail_send_email`, `google_gmail_reply` | risky | Pede confirmação |
| `google_gmail_mark_read`, `google_gmail_archive` | risky | Pede confirmação |
| `run_shell` | dinâmico | Classificado via `risk_policy.json` |

## Risk Gate

Dois sistemas de classificação de risco:

1. **Fixed** (`_FIXED_SKILL_RISK` em `risk.py`) — hardcoded por skill (tabela acima)
2. **Dynamic** (`risk_policy.json`) — só para `run_shell`; editável pelo usuário

**Precedência para `run_shell`:**
```
danger_patterns → risky_patterns → safe_prefixes → fallback: risky (desconhecido)
```

**Fluxo de confirmação:**
- `safe` → executa direto (ou dry-run se modo dry)
- `risky` → bloqueia; requer `yes` / `sim` / `confirmar`
- `danger` → bloqueia; requer `YES I KNOW`
- Após confirmação: `unblock_to_pending()` + resume de onde parou

**Editando a policy em runtime:**
```bash
jarvis "adicionar safe ls -la"        # adiciona à safe_prefixes
jarvis "adicionar risky docker build" # adiciona à risky_patterns
jarvis "permitir python script.py"    # adiciona à shell allowlist
```

## Modos de operação

| Modo | Comportamento | Como ativar |
|------|---------------|-------------|
| `dry` (padrão) | Descreve ações sem executar; retorna `(dry-run) Eu...` | padrão; `mode dry` |
| `execute` | Executa automaticamente tudo | `jarvis -x "..."` ou `mode execute` |
| `safe` | Executa safe automaticamente; bloqueia risky/danger | `mode safe` |

## Built-in commands (sem LLM)

Processados por `commands.py` antes de qualquer chamada LLM:

| Comando | Ação |
|---------|------|
| `mode dry\|execute\|safe` | Muda modo de execução da sessão |
| `mode` | Mostra modo atual |
| `auth gmail [alias]` | Inicia wizard OAuth do Gmail |
| `gmail status [alias]` | Mostra contas Gmail autenticadas |
| `yes` / `sim` / `confirmar` | Aprova ação `risky` bloqueada |
| `YES I KNOW` | Aprova ação `danger` bloqueada |
| `não` / `cancelar` / `n` | Rejeita ação bloqueada e limpa fila |
| `ok` / `manda ver` | Aprova plano de recovery proposto |
| `continuar` | Retoma execução de onde parou |
| `executar tudo` | Executa todos os itens pendentes ignorando bloqueios |
| `status` / `plano status` | Mostra estado da fila atual |
| `queue` / `fila` | Lista itens da fila com status |
| `skills` / `habilidades` | Lista capabilities disponíveis |
| `últimos comandos` / `history` | Mostra últimas 10 execuções |
| `limpar memória` | Reset completo de `~/.jarvis/memory.json` |
| `adicionar safe\|risky\|danger <pattern>` | Edita `risk_policy.json` em runtime |
| `permitir <comando>` | Adiciona prefixo à shell allowlist |

## Dados persistidos (`~/.jarvis/`)

```
~/.jarvis/
├── memory.json         # turns (max 8), state (app/git/cwd), session (modo/browser), pending
├── queue.json          # goal + items; status: pending→running→done|failed|blocked|skipped
├── risk_policy.json    # safe_prefixes, risky_patterns, danger_patterns (run_shell)
├── shell_policy.json   # allowlist_prefixes, blocklist_patterns
├── metrics.json        # token usage acumulado por modelo
└── logs/
    ├── telemetry.jsonl              # eventos genéricos (token_usage, etc.)
    └── debug-YYYY-MM-DD.jsonl      # debug entries completos (JARVIS_DEBUG=1)
```

## Convenções de código

- **Idioma**: código em inglês; UX, prompts e comentários em pt-BR
- **Modo padrão**: dry-run — usar `-x` ou `mode execute` para executar de verdade
- **Funções privadas**: prefixo `_` (ex: `_learn_state_from_action`, `_DEFAULTS`)
- **Constantes**: `UPPER_CASE` (ex: `MAX_TURNS`, `QUEUE_PATH`)
- **Booleanos**: prefixo `is_` / `has_` / `should_` (ex: `is_allowed()`, `has_active_queue()`)
- **Datas**: ISO 8601 UTC com sufixo `Z` (ex: `2025-03-05T12:05:30.000000Z`)
- **JSON**: `ensure_ascii=False, indent=2` (preserva português)
- **Paths**: `Path.home() / ".jarvis"` (cross-platform)
- **Modelos**: `fast` = Haiku 4.5 | `brain` = Sonnet 4.6 | `reasoning` = Sonnet 4.6 + extended thinking
- **Type hints**: usar em funções públicas; retorno `-> str` obrigatório em skills

## Estrutura de prompts (`prompts.py`)

| Prompt | Modelo | Retorno JSON |
|--------|--------|--------------|
| `ROUTER_PROMPT` | `fast` | `{"route": "fast_reply\|executor\|planner", "response": "...", "executor_model": "fast\|brain"}` |
| `PLANNER_PROMPT` | `reasoning` | `{"goal": "...", "plan": [{"step": "...", "action": "...", ...args}]}` (max 8 steps) |
| `ACTION_COMPILER_PROMPT` | `fast\|brain` | action JSON ou `{"chat": "..."}` se sem ação (max 3 steps) |

Memory é injetada automaticamente nos prompts quando `should_inject_memory()` detecta follow-up curto (≤50 chars) ou palavras-chave ("agora", "também", "depois"...).

## Debug log

Quando `JARVIS_DEBUG=1`, cada request gera uma linha JSON em:

```
~/.jarvis/logs/debug-YYYY-MM-DD.jsonl
```

```bash
# Acompanhar em tempo real
tail -f ~/.jarvis/logs/debug-$(date +%Y-%m-%d).jsonl | python3 -m json.tool
```

Cada entrada contém: `ts`, `request_id`, `user_input`, `mode`, `route`, `route_forced`,
`memory_injected`, `llm_calls` (com tokens e ms por chamada), `plan`, `execution` (por step),
`response`, `total_ms`, `total_tokens`.

## Server HTTP (API)

O `server.py` expõe o Jarvis como uma API REST local via **FastAPI + uvicorn**.

### Como iniciar

```bash
# Terminal 1 — proxy LiteLLM (obrigatório)
litellm --config config.yaml

# Terminal 2 — server HTTP (dry-run por padrão)
python -m jarvis.server

# Em modo execute (skills executam de verdade)
JARVIS_EXECUTE=1 python -m jarvis.server

# Com porta e token personalizados
JARVIS_PORT=9000 JARVIS_TOKEN_REQUIRED=1 python -m jarvis.server
```

Ao iniciar, o server exibe a URL e o link do Swagger:
```
Jarvis API Server
    URL:   http://127.0.0.1:8899
    Docs:  http://127.0.0.1:8899/api/docs
    Mode:  dry-run
```

### Endpoints

| Método | Rota | Body / Query | Resposta resumida |
|--------|------|--------------|-------------------|
| `POST` | `/api/run` | `{"text": "comando"}` | `RunResponse` — resposta + info de bloqueio |
| `POST` | `/api/confirm` | `{"text": "yes"}` | `RunResponse` — confirma/rejeita ação bloqueada |
| `GET` | `/api/status` | — | modo, resumo da queue, bloqueio atual |
| `GET` | `/api/history` | `?limit=20` | últimas N execuções da queue |
| `GET` | `/api/skills` | — | lista de actions disponíveis |
| `GET` | `/` | — | UI estática de `../ui/dist/` (se existir) |

### Modelo de resposta (RunResponse)

```json
{
  "response": "texto da resposta",
  "request_id": "a1b2c3d4",
  "blocked": true,
  "blocked_kind": "risk",
  "blocked_step": "git push origin main",
  "blocked_note": "Vai enviar commits para o remoto.",
  "suggestions": ["yes", "não"]
}
```

`blocked_kind` pode ser: `risk` | `danger` | `allowlist` | `proposal` | `recovery` | `null`

### Autenticação (opcional)

Ativada com `JARVIS_TOKEN_REQUIRED=1`. O token é gerado automaticamente em `~/.jarvis/server_token`.

```bash
curl -H "X-Jarvis-Token: <token>" http://127.0.0.1:8899/api/run \
  -d '{"text": "abra o chrome"}' -H "Content-Type: application/json"
```

### Códigos HTTP

| Código | Situação |
|--------|---------|
| 200 | Sucesso (mesmo se `blocked: true`) |
| 400 | Campo `text` vazio |
| 401 | Token inválido ou ausente |
| 429 | Já processando outro comando (aguarde) |

### CORS

Origens permitidas por padrão: `localhost:5173` (Vite dev server) e `localhost:8899`.

Documentação interativa completa em [`docs/API.md`](docs/API.md).

## Criando novas skills

**5 passos:**

1. Criar `jarvis/skills/minha_skill.py` herdando de `Skill`:

```python
from jarvis.skills.base import Skill

class MinhaSkill(Skill):
    name = "minha_skill"

    def __init__(self, execute: bool = False):
        self.execute = execute

    def run(self, args: dict) -> str:
        campo = (args.get("campo") or "").strip()
        if not campo:
            return "Campo obrigatório não informado."
        if not self.execute:
            return f"(dry-run) Eu faria X com '{campo}'."
        try:
            # execução real aqui
            return f"Feito: {campo}."
        except Exception as e:
            return f"Erro: {e}"
```

2. Registrar em `jarvis/skills/registry.py` → `build_skills()`:

```python
from .minha_skill import MinhaSkill
# dentro de build_skills():
"minha_skill": MinhaSkill(execute=execute),
```

3. Adicionar `Capability` em `registry.py:_CATALOG` (para o LLM conhecer a skill):

```python
Capability(
    name="minha_skill",
    namespace="system",          # system | dev | google.gmail
    title="Descrição curta",
    description="Uma frase explicando o que faz.",
    args_schema={"campo": "string"},
    examples=["frase de exemplo", "outra frase"],
    risk="safe",                 # safe | risky | danger
),
```

4. Definir risco fixo em `jarvis/risk.py:_FIXED_SKILL_RISK` (se não for `run_shell`):

```python
"minha_skill": ("safe", "Descrição do risco"),
```

5. O `executor.py` despacha automaticamente quando o LLM retornar `{"action": "minha_skill", "campo": "valor"}`.

**Skills sem flag `execute`** (somente leitura, nunca modificam estado) **não precisam do `__init__`** com execute.

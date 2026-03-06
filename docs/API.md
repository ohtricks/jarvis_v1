# Jarvis API — Documentação HTTP

O Jarvis expõe uma API REST local via **FastAPI**, rodando em `http://127.0.0.1:8899`.

> Documentação interativa (Swagger): `http://127.0.0.1:8899/api/docs`

---

## Iniciando o server

```bash
# Pré-requisito: proxy LiteLLM rodando
litellm --config config.yaml

# Server em dry-run (padrão — descreve ações sem executar)
python -m jarvis.server

# Server em modo execute (skills executam de verdade)
JARVIS_EXECUTE=1 python -m jarvis.server

# Porta customizada
JARVIS_PORT=9000 python -m jarvis.server

# Com autenticação por token
JARVIS_TOKEN_REQUIRED=1 python -m jarvis.server

# Tudo junto
JARVIS_EXECUTE=1 JARVIS_PORT=9000 JARVIS_TOKEN_REQUIRED=1 python -m jarvis.server
```

**Saída ao iniciar:**
```
Jarvis API Server
    URL:   http://127.0.0.1:8899
    Docs:  http://127.0.0.1:8899/api/docs
    Mode:  dry-run
    Token: desabilitado
```

---

## Variáveis de ambiente do server

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `JARVIS_EXECUTE` | `0` | `1` coloca o server em modo execute |
| `JARVIS_PORT` | `8899` | Porta de escuta |
| `JARVIS_TOKEN_REQUIRED` | `0` | `1` exige header `X-Jarvis-Token` em todas as rotas autenticadas |

---

## Autenticação

Por padrão a autenticação está **desabilitada**. Para habilitar:

```bash
JARVIS_TOKEN_REQUIRED=1 python -m jarvis.server
```

O token é gerado automaticamente na primeira execução e salvo em `~/.jarvis/server_token`.

**Usando o token:**
```bash
TOKEN=$(cat ~/.jarvis/server_token)

curl http://127.0.0.1:8899/api/run \
  -H "Content-Type: application/json" \
  -H "X-Jarvis-Token: $TOKEN" \
  -d '{"text": "abra o chrome"}'
```

---

## Modelos de dados

### RunRequest
```json
{ "text": "string (obrigatório)" }
```

### ConfirmRequest
```json
{ "text": "string (obrigatório)" }
```

### RunResponse
```json
{
  "response":     "string — texto da resposta do Jarvis",
  "request_id":   "string — ID único da requisição (8 chars hex)",
  "blocked":      "boolean — true se aguarda confirmação do usuário",
  "blocked_kind": "string | null — tipo do bloqueio (ver abaixo)",
  "blocked_step": "string | null — descrição do step bloqueado",
  "blocked_note": "string | null — nota explicativa do bloqueio",
  "suggestions":  "array[string] — comandos sugeridos para o cliente exibir"
}
```

**Valores de `blocked_kind`:**

| Valor | Significado |
|-------|-------------|
| `risk` | Ação `risky` — aguarda `yes` / `não` |
| `danger` | Ação `danger` — aguarda `YES I KNOW` |
| `allowlist` | Comando shell não está na allowlist — propõe adicionar |
| `proposal` | Policy proposal para run_shell desconhecido |
| `recovery` | Falha detectada — propõe plano de recovery |
| `null` | Não bloqueado |

---

## Endpoints

### POST /api/run

Envia um comando ao Jarvis e retorna a resposta.

**Request:**
```bash
curl -X POST http://127.0.0.1:8899/api/run \
  -H "Content-Type: application/json" \
  -d '{"text": "abra o chrome"}'
```

**Response (200 — dry-run):**
```json
{
  "response": "(dry-run) Eu abriria: open -a 'Google Chrome'",
  "request_id": "a1b2c3d4",
  "blocked": false,
  "blocked_kind": null,
  "blocked_step": null,
  "blocked_note": null,
  "suggestions": []
}
```

**Response (200 — ação bloqueada, risky):**
```json
{
  "response": "⚠️  Confirmação necessária.\nVai enviar commits para o remoto.\nPara confirmar: yes\nPara cancelar: não",
  "request_id": "b5c6d7e8",
  "blocked": true,
  "blocked_kind": "risk",
  "blocked_step": "git push origin main",
  "blocked_note": "Vai enviar commits para o remoto.",
  "suggestions": ["yes", "não"]
}
```

**Erros:**
```
400 — { "detail": "Campo 'text' não pode ser vazio." }
401 — { "detail": "Token inválido." }
429 — { "detail": "Jarvis já está processando um comando. Aguarde." }
```

---

### POST /api/confirm

Confirma ou rejeita uma ação bloqueada. Internamente idêntico ao `/api/run` — o texto é processado pelo `handle_builtin()` como comando de confirmação.

**Comandos de confirmação:**

| Texto | Ação |
|-------|------|
| `yes` / `sim` / `confirmar` | Aprova ação `risky` |
| `YES I KNOW` | Aprova ação `danger` |
| `não` / `cancelar` / `n` | Rejeita e limpa a fila |
| `ok` / `manda ver` | Aprova plano de recovery |

**Request:**
```bash
curl -X POST http://127.0.0.1:8899/api/confirm \
  -H "Content-Type: application/json" \
  -d '{"text": "yes"}'
```

**Response (200 — confirmado):**
```json
{
  "response": "Commits enviados com sucesso.",
  "request_id": "c9d0e1f2",
  "blocked": false,
  "blocked_kind": null,
  "blocked_step": null,
  "blocked_note": null,
  "suggestions": []
}
```

---

### GET /api/status

Retorna o estado atual do Jarvis: modo, fila e bloqueio em andamento.

**Request:**
```bash
curl http://127.0.0.1:8899/api/status
```

**Response (200):**
```json
{
  "mode": "dry",
  "queue": {
    "total": 3,
    "pending": 1,
    "running": 0,
    "blocked": 1,
    "done": 1,
    "failed": 0,
    "skipped": 0
  },
  "blocked": true,
  "blocked_kind": "risk",
  "blocked_step": "git push origin main",
  "blocked_note": "Vai enviar commits para o remoto.",
  "suggestions": ["yes", "não"]
}
```

**Campos de `mode`:** `dry` | `execute` | `safe`

---

### GET /api/history

Retorna as últimas execuções registradas na queue.

**Request:**
```bash
# Últimas 20 (padrão)
curl http://127.0.0.1:8899/api/history

# Últimas 5
curl http://127.0.0.1:8899/api/history?limit=5
```

**Parâmetros query:**

| Parâmetro | Tipo | Padrão | Intervalo |
|-----------|------|--------|-----------|
| `limit` | int | 20 | 1–100 |

**Response (200):**
```json
{
  "items": [
    {
      "id": "a_20260306_120530_0",
      "ts": "2026-03-06T12:05:30.000000Z",
      "step": "Abrir Google Chrome",
      "action": "open_app",
      "status": "done",
      "risk": "safe",
      "result": "Google Chrome aberto.",
      "error": null
    },
    {
      "id": "a_20260306_120531_1",
      "step": "Enviar commits para origin",
      "action": "git_push",
      "status": "blocked",
      "risk": "risky",
      "result": null,
      "error": null
    }
  ]
}
```

**Valores de `status`:** `pending` | `running` | `blocked` | `done` | `failed` | `skipped`

---

### GET /api/skills

Lista todas as actions (skills) disponíveis, ordenadas alfabeticamente.

**Request:**
```bash
curl http://127.0.0.1:8899/api/skills
```

**Response (200):**
```json
{
  "skills": [
    "git_add_all",
    "git_commit",
    "git_push",
    "git_status",
    "google_gmail_archive",
    "google_gmail_get_latest",
    "google_gmail_get_message",
    "google_gmail_list_today",
    "google_gmail_list_unread",
    "google_gmail_mark_read",
    "google_gmail_reply",
    "google_gmail_search",
    "google_gmail_send_email",
    "google_gmail_summarize_thread",
    "google_gmail_summarize_today",
    "google_gmail_summarize_unread",
    "open_app",
    "open_url",
    "run_shell"
  ]
}
```

---

## Fluxo completo — exemplo com bloqueio

### 1. Enviar comando que bloqueia

```bash
curl -X POST http://127.0.0.1:8899/api/run \
  -H "Content-Type: application/json" \
  -d '{"text": "git push"}'
```

```json
{
  "response": "⚠️  Confirmação necessária.\n...",
  "blocked": true,
  "blocked_kind": "risk",
  "blocked_step": "git push origin main",
  "suggestions": ["yes", "não"]
}
```

### 2. Verificar status (opcional)

```bash
curl http://127.0.0.1:8899/api/status
```

```json
{ "blocked": true, "blocked_kind": "risk", ... }
```

### 3. Confirmar a ação

```bash
curl -X POST http://127.0.0.1:8899/api/confirm \
  -H "Content-Type: application/json" \
  -d '{"text": "yes"}'
```

```json
{
  "response": "Commits enviados com sucesso.",
  "blocked": false
}
```

---

## Fluxo completo — ação danger

```bash
# 1. Comando de risco alto
curl -X POST http://127.0.0.1:8899/api/run \
  -d '{"text": "rm -rf /tmp/pasta"}' \
  -H "Content-Type: application/json"

# Response: blocked_kind = "danger", suggestions = ["YES I KNOW", "não"]

# 2. Confirmação explícita
curl -X POST http://127.0.0.1:8899/api/confirm \
  -d '{"text": "YES I KNOW"}' \
  -H "Content-Type: application/json"
```

---

## CORS

O server aceita requests de:
- `http://localhost:5173` — Vite dev server
- `http://127.0.0.1:5173`
- `http://localhost:8899` — próprio server
- `http://127.0.0.1:8899`

Para alterar as origens permitidas, edite `jarvis/server.py` → `CORSMiddleware`.

---

## UI estática (Tauri / Vite)

Se o diretório `ui/dist/` existir, o server monta os arquivos estáticos em `/`.
Útil para integração com Tauri ou frontend Vite buildado.

```bash
# Build da UI (se existir)
cd ui && npm run build

# Acesso
open http://127.0.0.1:8899
```

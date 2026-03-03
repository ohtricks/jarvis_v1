# Jarvis v1 — contexto para Claude Code

Assistente pessoal de IA para macOS. Respostas sempre em **português brasileiro (pt-BR)**.

## Como rodar

```bash
# Terminal 1 — proxy LiteLLM (obrigatório)
litellm --config config.yaml

# Terminal 2 — uso normal
jarvis "abra o chrome"
jarvis -x "liste os arquivos"      # -x executa de verdade (padrão: dry-run)

# Com debug log detalhado
JARVIS_DEBUG=1 jarvis "abra o chrome"
```

## Arquitetura (V3)

```
Input → [Built-in?] → [Router LLM] → [Planner|Executor] → [Queue] → [Risk Gate] → [Skill] → [Memory]
```

- **Planner** (`reason:/think:/plan:`) — multi-step, executa até bloqueio
- **Executor** (`exec:/brain:`) — single-step
- **Fast reply** (`fast:`) — resposta direta, sem actions

## Arquivos críticos

| Arquivo | Responsabilidade |
|---------|-----------------|
| `jarvis/agent.py` | Orquestrador — ponto de entrada do `run()` |
| `jarvis/llm.py` | Interface LLM; parâmetro `role=` identifica chamada no log |
| `jarvis/router.py` | Classifica input → fast_reply / executor / planner |
| `jarvis/planner.py` | Gera plano multi-step via modelo `reasoning` |
| `jarvis/executor.py` | Executa itens da fila um a um |
| `jarvis/risk.py` | Classifica risco: safe / risky / danger |
| `jarvis/queue.py` | Fila persistida em `~/.jarvis/queue.json` |
| `jarvis/telemetry.py` | Log de debug + métricas de tokens |
| `jarvis/memory.py` | Estado persistido em `~/.jarvis/memory.json` |
| `jarvis/skills/` | Skills: `open_app`, `open_url`, `run_shell` |
| `config.yaml` | Modelos LiteLLM (fast/brain/reasoning) |

## Convenções

- **Idioma**: sempre pt-BR nas respostas ao usuário
- **Modo padrão**: dry-run (descreve sem executar); usar `-x` ou `mode execute` para executar
- **Modos**: `dry` | `execute` | `safe` (safe executa safe automaticamente, bloqueia risky/danger)
- **Risk gate**: safe → executa direto | risky → `jarvis yes` | danger → `YES I KNOW`
- **Modelos**: `fast` = Haiku 4.5 | `brain` = Sonnet 4.6 | `reasoning` = Sonnet 4.6 + extended thinking

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

## Criando novas skills

1. `jarvis/skills/minha_skill.py` — herdar de `Skill`, implementar `run(args)`
2. Registrar em `jarvis/skills/registry.py` → `build_skills()`
3. O `agent.py` despacha automaticamente quando o LLM retornar `{"action": "minha_skill"}`

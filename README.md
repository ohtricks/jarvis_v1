# Jarvis v1

Assistente pessoal de IA alimentado por múltiplos modelos LLM via LiteLLM proxy. Roda no macOS e responde em português brasileiro (pt-BR).

## Arquitetura

```
User Input
     │
     ▼
[Prefix Check] ──── força rota (plan:/think:/reason: | exec:/brain: | fast:)
     │
     ▼
[Built-in Commands] ── confirmações, memory, mode, queue, status (sem LLM)
     │
     ▼
[Router LLM] ──────── fast_reply | executor | planner
     │                    └── executor_model: "fast" | "brain"
     ▼
     ├── fast_reply ──────── responde direto (sem actions)
     │
     ├── executor ────────── Action Compiler (fast ou brain)
     │   (≤ 3 steps)        compila 1-3 ações diretas sem reasoning
     │
     └── planner ─────────── Planner (reasoning)
         (≤ 8 steps)         decomposição multi-step completa
     │
     ▼
[Queue] ──────────── persiste etapas em ~/.jarvis/queue.json
     │
     ▼
[Risk Gate] ──────── safe → executa automaticamente
                     risky → pede "jarvis yes"
                     danger → pede "YES I KNOW"
     │
     ▼
[Skill] ──────────── open_app | open_url | run_shell
     │
     ▼
[Memory] ─────────── salva estado + histórico (~/.jarvis/memory.json)
```

### Hierarquia de modelos por rota

| Rota | Modelo | Quando |
|------|--------|--------|
| `fast_reply` | — | Conversa, perguntas curtas (sem LLM extra) |
| `executor` + `fast` | Haiku 4.5 | Ações diretas: abrir apps/urls, rodar comandos simples, 2-3 ações encadeadas |
| `executor` + `brain` | Sonnet 4.6 | Pedidos com objetivo semântico: "me fale", "resuma", "liste", "extraia" |
| `planner` | Sonnet 4.6 (reasoning) | Análise de código, refatoração, implementação, planos longos |

## Como executar

### Pré-requisitos

- Python 3.10+
- macOS (skills `open_app` e `open_url` usam o comando `open`)
- Anthropic API key

### Instalação

```bash
# 1. Clone o repositório
git clone git@github.com:ohtricks/jarvis_v1.git
cd jarvis_v1

# 2. Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate

# 3. Instale as dependências e o comando jarvis
pip install litellm
pip install -e .

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env e adicione sua ANTHROPIC_API_KEY
```

`.env`:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key
# GEMINI_API_KEY=your_gemini_api_key  # se usar modelos Gemini
```

### Executando

Abra dois terminais:

```bash
# Terminal 1 — inicie o proxy LiteLLM
litellm --config config.yaml

# Terminal 2 — use o Jarvis
jarvis "abra o Safari"
jarvis -x "liste os arquivos do diretório atual"   # -x executa de verdade
```

### Flags da CLI

| Flag | Comportamento |
|------|--------------|
| (nenhuma) | Modo dry-run: descreve o que faria, sem executar |
| `--execute` / `-x` / `--yes` / `-y` | Modo execute: executa skills de verdade |
| `--dry` / `--dry-run` | Força dry-run explicitamente |

### Testando a conexão

```bash
python test.py
```

---

## Uso

```bash
# Abrir um app
jarvis "abra o Safari"

# Abrir múltiplos apps de uma vez
jarvis "abra o VSCode e o Slack"

# Abrir uma URL
jarvis "abra github.com"

# Executar comando shell (modo execute ativo)
jarvis -x "liste os arquivos do diretório atual"

# Plano multi-step
jarvis "plan: crie uma pasta projeto e inicialize um repositório git"

# Forçar rota específica
jarvis "reason: analise os trade-offs de usar Redis vs Memcached"
jarvis "fast: qual a capital da França?"
jarvis "exec: abra o Chrome"

# Conversa
jarvis "o que você pode fazer?"
```

### Prefixos de força de rota

| Prefixo | Rota | Comportamento |
|---------|------|---------------|
| `reason:` / `think:` / `plan:` | planner | Planejamento multi-step completo via reasoning |
| `exec:` / `brain:` | executor | Action Compiler com modelo fast (1-3 steps diretos) |
| `fast:` | fast_reply | Resposta rápida, sem executar actions |

### Modos de execução

| Modo | Comportamento |
|------|--------------|
| `dry` | Nunca executa skills — apenas descreve (padrão ao omitir flag) |
| `execute` | Executa tudo, incluindo ações risky/danger após confirmação |
| `safe` | Executa `safe` automaticamente; pede confirmação para `risky`/`danger` |

Mudar modo via comando (persiste na sessão):
```bash
jarvis "mode execute"
jarvis "mode dry"
jarvis "mode safe"
jarvis "mode"           # mostra o modo atual
```

### Comandos built-in (sem LLM)

| Comando | Ação |
|---------|------|
| `status` / `status plano` | Mostra o plano ativo e progresso da fila |
| `listar plano` / `etapas` / `queue` / `fila` | Lista todos os passos com status |
| `continua` / `continue` / `continuar` / `next` / `seguir` | Retoma execução do próximo passo |
| `executar tudo` / `executar todas` / `run all` / `execute all` | Executa todos os passos restantes |
| `executar proximo` / `run next` | Executa apenas o próximo passo |
| `cancelar` / `cancelar plano` / `parar` / `stop` | Cancela o plano ativo |
| `yes` / `y` / `confirmar` | Confirma ação risky pendente |
| `no` / `n` / `cancel` / `cancelar` | Cancela ação pendente |
| `YES I KNOW` | Confirma ação danger pendente |
| `mode dry\|execute\|safe` | Muda modo de execução |
| `limpar memória` / `clear memory` / `reset memory` | Limpa todo o estado e histórico |

---

## Skills disponíveis

| Skill | Descrição |
|-------|-----------|
| `open_app` | Abre aplicativos no macOS pelo nome |
| `open_url` | Abre URLs no navegador padrão ou escolhido |
| `run_shell` | Executa comandos shell (com allowlist de segurança) |

### open_app — aliases suportados

| Você fala | App aberto |
|-----------|------------|
| safari | Safari |
| chrome / google chrome | Google Chrome |
| firefox | Firefox |
| vscode / vs code / visual studio code | Visual Studio Code |
| workbench / mysql workbench | MySQLWorkbench |
| slack | Slack |
| discord | Discord |
| whatsapp | WhatsApp |

### run_shell — comandos permitidos

Prefixos na allowlist: `ls`, `pwd`, `whoami`, `git`, `python`, `pip`, `node`, `npm`, `pnpm`, `yarn`, `docker`, `docker-compose`, `php`, `composer`, `cat`, `echo`, `mkdir`, `touch`, `code`.

Comandos com `rm`, `sudo`, `shutdown`, `mkfs`, `dd`, `killall` são bloqueados ou exigem confirmação.

---

## Risk Gate

Antes de executar comandos shell, o Jarvis classifica o risco:

| Nível | Exemplos | Confirmação |
|-------|---------|-------------|
| **safe** | `ls`, `pwd`, `git status`, `git log` | Executa direto |
| **risky** | `git push`, `npm install`, `docker prune`, `kill` | `jarvis yes` para confirmar, `jarvis no` para cancelar |
| **danger** | `rm -rf`, `sudo`, `shutdown`, `dd`, `mkfs` | Digite exatamente: `YES I KNOW` |

```bash
# Exemplo: comando risky
jarvis -x "faça push das mudanças"
# → ⚠️ Confirmação necessária: git push origin main
# → Para confirmar: jarvis yes | Para cancelar: jarvis no

jarvis "yes"
# → Executando...
```

Após a confirmação, a execução retoma automaticamente até o próximo bloqueio ou o fim do plano.

---

## Memória

O Jarvis mantém estado persistente em `~/.jarvis/`:

| Arquivo | Conteúdo |
|---------|----------|
| `memory.json` | Histórico de conversa (8 turns) + estado de sessão |
| `queue.json` | Fila de tarefas do plano ativo (V3) |
| `logs/` | Eventos de telemetria e uso de tokens |

**Estado rastreado automaticamente:**
- Último app aberto, browser atual, última URL, último comando shell, diretório atual

**Injeção de contexto:** A memória é injetada automaticamente quando o input é curto (≤ 50 chars) ou contém palavras de continuação como "agora", "também", "isso", "então", "de novo", "continua", etc.

---

## Debug

```bash
JARVIS_DEBUG=1 jarvis "abra o Chrome"
```

Exibe: classificação do router, output do planner, decisões do executor, uso de tokens.

---

## Estrutura do projeto

```
jarvis_v1/
├── config.yaml          # Configuração dos modelos LiteLLM
├── pyproject.toml       # Metadados e dependências do projeto
├── .env.example         # Template de variáveis de ambiente
├── test.py              # Teste de conexão com o LLM
└── jarvis/
    ├── main.py          # Entry point da CLI (flags --execute / --yes / --dry)
    ├── agent.py         # Orquestrador principal (decisão + execução)
    ├── llm.py           # Interface com o LLM via LiteLLM proxy
    ├── router.py        # Classifica input: fast_reply | executor | planner + executor_model
    ├── planner.py       # Planejamento multi-step (reasoning, até 8 steps)
    ├── executor_llm.py  # Action Compiler: compila 1-3 ações diretas (fast ou brain)
    ├── executor.py      # Engine de execução da fila (V3)
    ├── queue.py         # Gerenciamento da fila de tarefas
    ├── risk.py          # Classificação de risco (safe / risky / danger)
    ├── commands.py      # Comandos built-in (sem LLM)
    ├── memory.py        # Persistência de estado e histórico
    ├── prompts.py       # System prompts: router, planner, action compiler
    ├── telemetry.py     # Logging de tokens e eventos
    ├── utils.py         # Utilitários (parse JSON, clean markdown)
    ├── brain.py         # (legado) interface antiga com LLM
    └── skills/
        ├── base.py      # Classe base para skills
        ├── registry.py  # Factory de skills
        ├── open_app.py  # Skill: abrir aplicativos no macOS
        ├── open_url.py  # Skill: abrir URLs no navegador
        └── run_shell.py # Skill: executar comandos shell (com allowlist)
```

---

## Models

| Role | Modelo padrão | Uso |
|------|--------------|-----|
| `fast` | Claude Haiku 4.5 | Router + Action Compiler para pedidos diretos |
| `brain` | Claude Sonnet 4.6 | Action Compiler para pedidos com objetivo semântico |
| `reasoning` | Claude Sonnet 4.6 (extended thinking, 8k tokens) | Planner: análise, refatoração, planos longos |

O router decide automaticamente qual modelo usar para cada pedido. `reasoning` só é acionado quando a tarefa realmente exige decomposição e análise profunda.

Os modelos são definidos em [config.yaml](config.yaml) e podem ser trocados a qualquer momento.

---

## Configuration

Os modelos são definidos em [config.yaml](config.yaml). Cada entrada mapeia um nome lógico (`fast`, `brain`, `reasoning`) a um modelo do provider, lendo a API key das variáveis de ambiente.

O router usa sempre o modelo `fast` (temperatura 0) para classificar o input antes de despachar ao modelo correto.

**Variáveis de ambiente opcionais:**

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `ANTHROPIC_API_KEY` | — | API key da Anthropic (obrigatória) |
| `OPENAI_API_BASE` | `http://localhost:4000` | Endpoint do proxy LiteLLM |
| `OPENAI_API_KEY` | `sk-local` | API key para o proxy |
| `JARVIS_DEBUG` | — | `1` para logs detalhados |

---

## Criando novas skills

1. Crie um arquivo em `jarvis/skills/minha_skill.py`:

```python
from .base import Skill

class MinhaSkill(Skill):
    name = "minha_skill"

    def __init__(self, execute: bool = True):
        self.execute = execute

    def run(self, args: dict) -> str:
        # _execute: True é injetado pelo risk gate após confirmação do usuário
        if not self.execute and not args.get("_execute"):
            return f"(dry-run) Eu executaria: {args}"
        # implemente a lógica aqui
        return "feito."
```

2. Registre em `jarvis/skills/registry.py`:

```python
from .minha_skill import MinhaSkill

def get_skills(execute: bool = True) -> dict:
    return {
        "open_app": OpenAppSkill(execute=execute),
        "open_url": OpenUrlSkill(execute=execute),
        "run_shell": RunShellSkill(execute=execute),
        "minha_skill": MinhaSkill(execute=execute),
    }
```

3. O `Agent` já sabe acionar a skill quando o LLM retornar `{"action": "minha_skill", ...}`.

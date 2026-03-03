# Jarvis v1

Assistente pessoal de IA alimentado por múltiplos modelos LLM via LiteLLM proxy. Roda no macOS e responde em português brasileiro (pt-BR).

## Arquitetura

```
User Input
     │
     ▼
[Prefix Check] ──── força modelo (reason:, plan:, fast:, brain:)
     │
     ▼
[Built-in Commands] ── memory, plans, confirmações (sem LLM)
     │
     ▼
[Router] ──────────── fast_reply | brain | reasoning
     │
     ▼
[LLM] ─────────────── chat | action | plan
     │
     ▼
[Risk Gate] ──────── safe → executa
                     risky → pede "jarvis yes"
                     danger → pede "YES I KNOW"
     │
     ▼
[Skill] ──────────── open_app | open_url | run_shell
     │
     ▼
[Memory] ─────────── salva estado + histórico (~/.jarvis/memory.json)
```

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

Prefixos na allowlist: `ls`, `pwd`, `whoami`, `git`, `python`, `pip`, `node`, `npm`, `docker`, `php`, `composer`, `cat`, `echo`, `mkdir`, `touch`, `code`.

Comandos com `rm`, `sudo`, `shutdown`, `mkfs`, `dd`, `killall` são bloqueados ou exigem confirmação.

## Uso

Com o proxy LiteLLM rodando, use o comando `jarvis`:

```bash
# Abrir um app
jarvis "abra o Safari"

# Abrir múltiplos apps de uma vez
jarvis "abra o VSCode e o Slack"

# Abrir uma URL
jarvis "abra github.com"

# Executar comando shell
jarvis "liste os arquivos do diretório atual"

# Plano multi-step
jarvis "plan: crie uma pasta projeto e inicialize um repositório git"

# Forçar modelo específico
jarvis "reason: analise os trade-offs de usar Redis vs Memcached"
jarvis "fast: qual a capital da França?"

# Conversa
jarvis "o que você pode fazer?"
```

### Prefixos de força de modelo

| Prefixo | Modelo usado |
|---------|--------------|
| `reason:` / `think:` | reasoning (pensamento estendido) |
| `plan:` | reasoning (planejamento multi-step) |
| `brain:` | brain (uso de ferramentas) |
| `fast:` | fast (resposta rápida) |

### Comandos built-in (sem LLM)

| Comando | Ação |
|---------|------|
| `status` / `status plano` | Mostra o plano ativo e progresso |
| `continua` / `continue` | Retoma execução do plano |
| `executar tudo` | Executa todos os passos restantes do plano |
| `cancelar` / `parar` | Cancela o plano ativo |
| `listar plano` | Lista todos os passos com progresso |
| `limpar memória` / `clear memory` | Limpa todo o estado e histórico |

## Risk Gate

Antes de executar comandos shell, o Jarvis classifica o risco:

| Nível | Exemplos | Confirmação |
|-------|---------|-------------|
| **safe** | `ls`, `pwd`, `git status`, `git log` | Executa direto |
| **risky** | `git push`, `npm install`, `docker prune`, `kill` | `jarvis yes` para confirmar, `jarvis no` para cancelar |
| **danger** | `rm -rf`, `sudo`, `shutdown`, `dd`, `mkfs` | Digite exatamente: `YES I KNOW` |

```bash
# Exemplo: comando risky
jarvis "faça push das mudanças"
# → ⚠️ Ação risky: git push origin main
# → Para confirmar: jarvis yes | Para cancelar: jarvis no

jarvis "yes"
# → Executando...
```

## Memória

O Jarvis mantém estado persistente em `~/.jarvis/memory.json`:

- **Histórico de conversa**: últimas 6 trocas (máx. 500 chars cada)
- **Estado de sessão**: último app aberto, browser atual, última URL, último comando shell, diretório atual
- **Plano ativo**: passo atual, progresso, ação pendente de confirmação

A memória é injetada automaticamente em inputs curtos ou que contêm palavras de continuação ("agora", "também", "de novo", "continua", etc.).

## Estrutura do projeto

```
jarvis_v1/
├── config.yaml          # Configuração dos modelos LiteLLM
├── pyproject.toml       # Metadados e dependências do projeto
├── .env.example         # Template de variáveis de ambiente
├── test.py              # Teste de conexão com o LLM
└── jarvis/
    ├── main.py          # Entry point da CLI (flags --execute / --yes)
    ├── agent.py         # Orquestrador principal (decisão + execução)
    ├── brain.py         # Interface com o LLM via LiteLLM proxy
    ├── router.py        # Classifica input: fast_reply | brain | reasoning
    ├── planner.py       # Planejamento multi-step e risk gate
    ├── commands.py      # Comandos built-in (sem LLM)
    ├── memory.py        # Persistência de estado e histórico
    ├── prompts.py       # System prompts do router e executor
    ├── utils.py         # Utilitários (parse JSON, clean markdown)
    └── skills/
        ├── base.py      # Classe base para skills
        ├── registry.py  # Factory de skills
        ├── open_app.py  # Skill: abrir aplicativos no macOS
        ├── open_url.py  # Skill: abrir URLs no navegador
        └── run_shell.py # Skill: executar comandos shell (com allowlist)
```

## Models

| Role | Modelo padrão | Alternativas (config.yaml) |
|------|--------------|---------------------------|
| `fast` | Claude Haiku 4.5 | Gemini 2.5 Flash |
| `brain` | Claude Haiku 4.5 | Claude Sonnet 4.6 |
| `reasoning` | Claude Haiku 4.5 (extended thinking) | Claude Opus 4.6 |

Os modelos são definidos em [config.yaml](config.yaml) e podem ser trocados a qualquer momento.

## Requirements

- Python 3.10+
- macOS (a skill `open_app` e `open_url` usam o comando `open`)
- LiteLLM (como proxy local)
- Anthropic API key (e/ou Gemini API key, dependendo dos modelos escolhidos)

## Setup

1. Clone o repositório:
   ```bash
   git clone git@github.com:ohtricks/jarvis_v1.git
   cd jarvis_v1
   ```

2. Crie e ative um ambiente virtual:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Instale as dependências e o comando `jarvis`:
   ```bash
   pip install litellm
   pip install -e .
   ```

4. Configure as variáveis de ambiente:
   ```bash
   cp .env.example .env
   ```

   `.env`:
   ```env
   ANTHROPIC_API_KEY=your_anthropic_api_key
   # GEMINI_API_KEY=your_gemini_api_key  # se usar modelos Gemini
   ```

5. Inicie o proxy LiteLLM:
   ```bash
   litellm --config config.yaml
   ```

6. Use o Jarvis:
   ```bash
   jarvis "abra o Safari"
   ```

## Configuration

Os modelos são definidos em [config.yaml](config.yaml). Cada entrada mapeia um nome lógico (`fast`, `brain`, `reasoning`) a um modelo do provider, lendo a API key das variáveis de ambiente.

O router usa sempre o modelo `fast` (temperatura 0) para classificar o input antes de despachar ao modelo correto.

## Criando novas skills

1. Crie um arquivo em `jarvis/skills/minha_skill.py`:

```python
from .base import Skill

class MinhaSkill(Skill):
    name = "minha_skill"

    def __init__(self, execute: bool = True):
        self.execute = execute

    def run(self, args: dict) -> str:
        if not self.execute:
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


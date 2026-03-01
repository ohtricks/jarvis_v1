# Jarvis v1

Assistente pessoal de IA alimentado por múltiplos modelos LLM via LiteLLM proxy. Roda no macOS e responde em português brasileiro (pt-BR).

## Arquitetura

```
jarvis "comando"
     │
     ▼
  Agent  ──── decide ────▶  Brain (LLM)
     │                         │
     │        JSON action ◀────┘
     ▼
  Skills (executa ação)
```

O `Agent` envia o comando do usuário ao `Brain` (LLM), que retorna um JSON com a ação a executar. O `Agent` então despacha para a skill correspondente.

## Skills disponíveis

| Skill | Descrição |
|-------|-----------|
| `open_app` | Abre aplicativos no macOS pelo nome |

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

## Uso

Com o proxy LiteLLM rodando, use o comando `jarvis`:

```bash
# Abrir um app
jarvis "abra o Safari"

# Abrir múltiplos apps de uma vez
jarvis "abra o VSCode e o Slack"

# Conversa
jarvis "o que você pode fazer?"
```

## Estrutura do projeto

```
jarvis_v1/
├── config.yaml          # Configuração dos modelos LiteLLM
├── pyproject.toml       # Metadados e dependências do projeto
├── test.py              # Teste de conexão com o LLM
└── jarvis/
    ├── main.py          # Entry point da CLI
    ├── agent.py         # Lógica do agente (decisão + execução)
    ├── brain.py         # Interface com o LLM via LiteLLM proxy
    └── skills/
        ├── base.py      # Classe base para skills
        ├── registry.py  # Registro de skills disponíveis
        └── open_app.py  # Skill: abrir aplicativos no macOS
```

## Models

| Role | Model |
|------|-------|
| `brain` | Gemini 2.5 Pro Preview / Gemini 2.5 Flash Preview |
| `reasoning` | Claude Sonnet 4.6 |
| `fast` | Gemini 2.5 Flash |

## Requirements

- Python 3.10+
- macOS (a skill `open_app` usa o comando `open -a`)
- LiteLLM
- Gemini API key
- Anthropic API key

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
   GEMINI_API_KEY=your_gemini_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
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

Os modelos são definidos em [config.yaml](config.yaml). Cada entrada mapeia um nome lógico (ex: `brain`, `reasoning`, `fast`) a um modelo do provider, lendo a API key das variáveis de ambiente.

## Criando novas skills

1. Crie um arquivo em `jarvis/skills/minha_skill.py`:

```python
from .base import Skill

class MinhaSkill(Skill):
    name = "minha_skill"

    def run(self, args: dict):
        # implemente a lógica aqui
        return "feito."
```

2. Registre em `jarvis/skills/registry.py`:

```python
from .minha_skill import MinhaSkill

SKILLS = {
    "open_app": OpenAppSkill(),
    "minha_skill": MinhaSkill(),
}
```

3. O `Agent` já sabe acionar a skill quando o LLM retornar `{"action": "minha_skill", ...}`.

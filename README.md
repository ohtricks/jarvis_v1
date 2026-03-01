# Jarvis v1

Personal AI assistant powered by multiple LLM models via LiteLLM proxy.

## Models

| Role | Model |
|------|-------|
| `brain` | Gemini 3.1 Pro Preview / Gemini 3 Flash Preview |
| `reasoning` | Claude Sonnet 4.6 |
| `fast` | Gemini 2.5 Flash |

## Requirements

- Python 3.11
- LiteLLM
- Gemini API key
- Anthropic API key

## Setup

1. Clone the repo:
   ```bash
   git clone git@github.com:ohtricks/jarvis_v1.git
   cd jarvis_v1
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install litellm
   ```

4. Configure environment variables — copy the example and fill in your keys:
   ```bash
   cp .env.example .env
   ```

   `.env`:
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   ```

5. Start the LiteLLM proxy:
   ```bash
   litellm --config config.yaml
   ```

## Configuration

Models are defined in [config.yaml](config.yaml). Each entry maps a logical model name (e.g. `brain`, `reasoning`, `fast`) to a provider model and reads the API key from environment variables.

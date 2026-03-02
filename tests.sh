#!/usr/bin/env bash
set -euo pipefail

JARVIS_BIN="${JARVIS_BIN:-jarvis}"
export JARVIS_DEBUG="${JARVIS_DEBUG:-1}"

SHOW_OUTPUT="${SHOW_OUTPUT:-1}"   # 1=mostra tudo; 0=só resumo

TOTAL_PROMPT=0
TOTAL_COMPLETION=0
TOTAL_TOKENS=0

extract_tokens() {
  local out="$1"
  local p_sum=0 c_sum=0 t_sum=0

  # Exemplo linha:
  # DEBUG USAGE(fast): prompt=181 completion=81 total=262
  while IFS= read -r line; do
    [[ "$line" == *"DEBUG USAGE("* ]] || continue

    # macOS-friendly: grep -oE
    local p c t
    p="$(echo "$line" | grep -oE 'prompt=[0-9]+' | head -n1 | cut -d= -f2 || true)"
    c="$(echo "$line" | grep -oE 'completion=[0-9]+' | head -n1 | cut -d= -f2 || true)"
    t="$(echo "$line" | grep -oE 'total=[0-9]+' | head -n1 | cut -d= -f2 || true)"

    p="${p:-0}"; c="${c:-0}"; t="${t:-0}"

    p_sum=$((p_sum + p))
    c_sum=$((c_sum + c))
    t_sum=$((t_sum + t))
  done <<< "$out"

  echo "$p_sum $c_sum $t_sum"
}

run_cmd() {
  local label="$1"; shift

  echo ""
  echo "============================================================"
  echo "TEST: $label"
  echo -n "CMD:  $JARVIS_BIN"
  for a in "$@"; do echo -n " [$a]"; done
  echo ""
  echo "------------------------------------------------------------"

  set +e
  local out
  out="$("$JARVIS_BIN" "$@" 2>&1)"
  local rc=$?
  set -e

  if [[ "$SHOW_OUTPUT" == "1" ]]; then
    echo "$out"
  fi

  read -r p c t < <(extract_tokens "$out")

  echo "------------------------------------------------------------"
  echo "TOKENS (este comando): prompt=$p completion=$c total=$t"

  TOTAL_PROMPT=$((TOTAL_PROMPT + p))
  TOTAL_COMPLETION=$((TOTAL_COMPLETION + c))
  TOTAL_TOKENS=$((TOTAL_TOKENS + t))

  if [[ $rc -ne 0 ]]; then
    echo "❌ FAIL (exit code=$rc)"
    return 1
  fi
  echo "✅ PASS"
}

echo "== Jarvis Mini Test Suite =="
echo "JARVIS_BIN=$JARVIS_BIN"
echo "JARVIS_DEBUG=$JARVIS_DEBUG"
echo ""

# 0) Setup
run_cmd "Setup: limpar memória" "limpar memória"

# 1) Plan step-by-step
run_cmd "Plan: chrome -> gmail -> youtube (executa só 1º passo)" "plan: abra o chrome, abra o gmail e depois abra o youtube"
run_cmd "Status do plano (sem LLM)" status
run_cmd "Listar plano (sem LLM)" "listar plano"

# 2) Continue até finalizar (sem LLM)
run_cmd "Continue (passo 2)" continue
run_cmd "Continua (passo 3)" continua

# 3) Cancelar plano
run_cmd "Criar plano para cancelar" "plan: abra o chrome, abra o gmail e abra o youtube"
run_cmd "Cancelar plano (sem LLM)" "cancelar plano"
run_cmd "Status após cancelar (sem LLM)" status

# 4) Risk Gate - RISKY
run_cmd "Risky: tentar git push (deve pedir confirmação)" "rode git push"
run_cmd "Negar pendência (no) (sem LLM)" no
run_cmd "Risky: git push novamente (deve pedir confirmação)" "rode git push"
run_cmd "Confirmar pendência (yes) (sem LLM)" yes

# 5) Risk Gate - DANGER (sudo)
run_cmd "Danger: sudo echo ok (deve exigir YES I KNOW)" "rode sudo echo ok"
run_cmd "Tentar confirmar com yes (deve recusar)" yes
run_cmd "Confirmar com YES I KNOW" "YES I KNOW"

# 6) Executar tudo com risco no meio
run_cmd "Plano com risky no meio (git push)" "plan: abra o chrome, rode git push e depois abra o gmail"
run_cmd "Executar tudo (deve PAUSAR no risky)" "executar tudo"
run_cmd "Confirmar pendência (yes)" yes
run_cmd "Executar tudo (deve concluir)" "executar tudo"

echo ""
echo "============================================================"
echo "TOTAL TOKENS (suite inteira):"
echo "prompt=$TOTAL_PROMPT completion=$TOTAL_COMPLETION total=$TOTAL_TOKENS"
echo "============================================================"
echo ""

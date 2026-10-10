#!/usr/bin/env bash
# Configura o shell para usar o gravador-vault sem instalar nada no sistema.
#
#   source launchers/gv-env.sh
#
# Define GV_RAIZ, carrega .env (se existir) e cria funções/aliases:
#   organizar, transcrever, transcrever-gradual, enriquecer,
#   indexar, conectar, aplicar-conexoes, rodada
#
# Usa o Python do venv do repositório (.venv/) se existir; senão, python3.
# Para tornar permanente, adicione ao ~/.bashrc:
#   [ -f /caminho/para/gravador-vault/launchers/gv-env.sh ] && . /caminho/para/gravador-vault/launchers/gv-env.sh

if [ -n "${BASH_SOURCE[0]:-}" ]; then
  _gv_script="${BASH_SOURCE[0]}"
else
  _gv_script="$0"
fi
_gv_dir="$(cd "$(dirname "$_gv_script")" && pwd)"
export GV_RAIZ="$(cd "$_gv_dir/.." && pwd)"

if [ -f "$GV_RAIZ/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$GV_RAIZ/.env"
  set +a
fi

_gv_python() {
  if [ -x "$GV_RAIZ/.venv/bin/python3" ]; then
    printf '%s\n' "$GV_RAIZ/.venv/bin/python3"
  else
    printf '%s\n' "python3"
  fi
}

organizar()            { "$(_gv_python)" "$GV_RAIZ/scripts/organizar.py" "$@"; }
transcrever()          { "$(_gv_python)" "$GV_RAIZ/scripts/transcrever.py" "$@"; }
transcrever_gradual()  { "$(_gv_python)" "$GV_RAIZ/scripts/transcrever-gradual.py" "$@"; }
enriquecer()           { "$(_gv_python)" "$GV_RAIZ/scripts/enriquecer.py" "$@"; }
indexar()              { "$(_gv_python)" "$GV_RAIZ/scripts/indexar.py" "$@"; }
conectar()             { "$(_gv_python)" "$GV_RAIZ/scripts/conectar.py" "$@"; }
aplicar_conexoes()     { "$(_gv_python)" "$GV_RAIZ/scripts/aplicar-conexoes.py" "$@"; }
rodada()               { "$(_gv_python)" "$GV_RAIZ/scripts/rodada.py" "$@"; }

alias transcrever-gradual='transcrever_gradual'
alias aplicar-conexoes='aplicar_conexoes'

unset _gv_script _gv_dir

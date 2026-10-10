"""Configuração central: caminhos, modelos e variáveis GV_*.

Ordem de resolução de cada valor:
  1. variável de ambiente GV_*
  2. arquivo .env na raiz do repositório (KEY=VALUE, sem export)
  3. padrão definido aqui

Só uma coisa é obrigatória: GV_VAULT, a pasta do vault Obsidian. Sem ela os
scripts param com uma mensagem dizendo como configurar. Preferimos erro claro a
adivinhar pastas.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ARQUIVO_ENV = RAIZ / ".env"

_ENV_CARREGADO = False


def carregar_env(path: Path = ARQUIVO_ENV) -> None:
    """Lê KEY=VALUE do .env sem sobrescrever variáveis já definidas no ambiente."""
    global _ENV_CARREGADO
    if _ENV_CARREGADO or not path.exists():
        _ENV_CARREGADO = True
        return
    for linha in path.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        if linha.startswith("export "):
            linha = linha[len("export "):]
        chave, valor = linha.split("=", 1)
        chave = chave.strip()
        valor = valor.strip().strip('"').strip("'")
        if chave and chave not in os.environ:
            os.environ[chave] = valor
    _ENV_CARREGADO = True


def env(nome: str, padrao: str | None = None) -> str | None:
    carregar_env()
    valor = os.environ.get(nome)
    if valor is None or valor == "":
        return padrao
    return valor


def _caminho(nome: str, padrao: Path | None) -> Path | None:
    valor = env(nome)
    if valor:
        return Path(valor).expanduser()
    return padrao


# --------------------------------------------------------------------------- #
# Caminhos                                                                     #
# --------------------------------------------------------------------------- #

def vault(obrigatorio: bool = True) -> Path:
    """Pasta do vault Obsidian (GV_VAULT). Erro acionável se ausente."""
    caminho = _caminho("GV_VAULT", None)
    if caminho is None:
        if not obrigatorio:
            return RAIZ / "vault-template"
        print(
            "Erro: GV_VAULT não definida.\n"
            "Aponte para a pasta do seu vault Obsidian, por exemplo:\n"
            f"  echo 'GV_VAULT=$HOME/meu-vault' >> {ARQUIVO_ENV}\n"
            "ou exporte a variável no shell antes de rodar o script.\n"
            "Para começar do zero, copie vault-template/ para onde quiser e aponte GV_VAULT para lá.",
            file=sys.stderr,
        )
        sys.exit(2)
    return caminho


def record() -> Path:
    """Pasta de staging dos áudios (GV_RECORD). Padrão: RECORD/ na raiz do repo."""
    return _caminho("GV_RECORD", RAIZ / "RECORD")


def cache() -> Path:
    """Cache local ignorado pelo git (GV_CACHE). Padrão: .cache/ na raiz do repo."""
    return _caminho("GV_CACHE", RAIZ / ".cache")


def categorias_yaml() -> Path:
    return _caminho("GV_CATEGORIAS", RAIZ / "config" / "categorias.yaml")


def inbox(vault_path: Path | None = None) -> Path:
    return (vault_path or vault()) / "00-INBOX"


def bases(vault_path: Path | None = None) -> Path:
    return (vault_path or vault()) / "01-BASES"


def conexoes(vault_path: Path | None = None) -> Path:
    return (vault_path or vault()) / "_conexoes"


# --------------------------------------------------------------------------- #
# Transcrição                                                                  #
# --------------------------------------------------------------------------- #

def idioma() -> str:
    """Código de idioma passado ao Whisper (GV_IDIOMA). Padrão: pt."""
    return env("GV_IDIOMA", "pt")


def stt_device() -> str:
    """cpu ou cuda (GV_STT_DEVICE)."""
    return env("GV_STT_DEVICE", "cpu")


def stt_compute() -> str:
    """int8 (CPU), float16 (GPU) etc. (GV_STT_COMPUTE)."""
    return env("GV_STT_COMPUTE", "int8")


def stt_modelo_padrao() -> str:
    return env("GV_STT_MODELO", "medium")


# --------------------------------------------------------------------------- #
# LLM                                                                          #
# --------------------------------------------------------------------------- #

def ollama_url() -> str:
    return env("GV_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")


def llm_modelo() -> str:
    return env("GV_LLM_MODEL", "qwen3.5:9b")


def embed_modelo() -> str:
    return env("GV_EMBED_MODEL", "bge-m3:latest")


def llm_fonte() -> str:
    """ollama (padrão), gemini ou auto."""
    return env("GV_LLM_FONTE", "ollama")


def resumo() -> dict[str, str]:
    """Para `--mostrar-config` e diagnósticos."""
    return {
        "RAIZ": str(RAIZ),
        "GV_VAULT": str(_caminho("GV_VAULT", None) or "(não definida)"),
        "GV_RECORD": str(record()),
        "GV_CACHE": str(cache()),
        "GV_CATEGORIAS": str(categorias_yaml()),
        "GV_IDIOMA": idioma(),
        "GV_STT_DEVICE": stt_device(),
        "GV_STT_COMPUTE": stt_compute(),
        "GV_STT_MODELO": stt_modelo_padrao(),
        "GV_OLLAMA_URL": ollama_url(),
        "GV_LLM_MODEL": llm_modelo(),
        "GV_EMBED_MODEL": embed_modelo(),
        "GV_LLM_FONTE": llm_fonte(),
    }

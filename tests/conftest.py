"""Fixtures compartilhadas. Nenhum teste precisa de Whisper nem de Ollama real."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


NOTA_EXEMPLO = """---
title: "20260602120000"
date: 2026-06-02
duracao: "4:12"
origem: "2026-06-02/transcrito/20260602120000.WAV"
modelo: {modelo}
categoria:
manter-audio:
tags:
  - gravador
  - inbox
---

## Transcrição

{transcricao}

---
*Observações:*
"""

TRANSCRICAO_OK = (
    "Dois de junho, caminhada, dissertação. Estava pensando na relação entre paisagem e memória "
    "e como a geografia cultural trata o lugar como acúmulo de camadas. Preciso reler o capítulo "
    "sobre topofilia e comparar com a noção de atmosfera. Pergunta aberta: a atmosfera é anterior "
    "à representação ou já é representação? Lembrar de anotar isso no caderno. Forte."
)


@pytest.fixture
def vault(tmp_path, monkeypatch):
    """Vault temporário com estrutura mínima; GV_VAULT/GV_RECORD/GV_CACHE apontando para tmp."""
    v = tmp_path / "vault"
    for pasta in ("00-INBOX", "01-BASES", "_conexoes", "NO-ROLE", "RESENHAS", "PRE-TEXTO",
                  "ENTREVISTA", "SONHEI-ESSA-NOITE", "INSIGHTS-MEDITACAO", "LENDO-COMENTANDO"):
        (v / pasta).mkdir(parents=True)
    record = tmp_path / "RECORD"
    record.mkdir()
    cache = tmp_path / "cache"
    monkeypatch.setenv("GV_VAULT", str(v))
    monkeypatch.setenv("GV_RECORD", str(record))
    monkeypatch.setenv("GV_CACHE", str(cache))
    monkeypatch.delenv("GV_OLLAMA_URL", raising=False)
    return v


@pytest.fixture
def record(vault):
    return Path(os.environ["GV_RECORD"])


def escrever_nota(pasta: Path, stem: str, transcricao: str = TRANSCRICAO_OK, modelo: str = "small",
                  extra_fm: str = "") -> Path:
    texto = NOTA_EXEMPLO.format(modelo=modelo, transcricao=transcricao)
    if extra_fm:
        texto = texto.replace("categoria:\n", f"categoria:\n{extra_fm}\n", 1)
    path = pasta / f"{stem}.md"
    path.write_text(texto, encoding="utf-8")
    return path


@pytest.fixture
def nota_inbox(vault):
    return escrever_nota(vault / "00-INBOX", "20260602120000")

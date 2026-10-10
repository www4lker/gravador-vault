"""Faster-Whisper: carregar modelo, transcrever, montar a nota.

Os parâmetros anti-alucinação (vad_filter, compression_ratio_threshold,
log_prob_threshold, no_speech_threshold, hallucination_silence_threshold) são
a primeira camada de defesa; a segunda é comum/alucinacao.py, aplicada depois.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from . import config

MODELOS = ("tiny", "base", "small", "medium", "large", "large-v3")

PARAMETROS_TRANSCRICAO = dict(
    beam_size=5,
    vad_filter=True,
    compression_ratio_threshold=2.1,
    log_prob_threshold=-0.6,
    no_speech_threshold=0.6,
    hallucination_silence_threshold=1.0,
)


def normalizar_modelo(modelo: str) -> str:
    return "large-v3" if modelo == "large" else modelo


def criar_modelo(modelo: str, device: str | None = None, compute_type: str | None = None):
    """Instancia WhisperModel. Se faster_whisper não estiver instalado, explica como instalar."""
    try:
        from faster_whisper import WhisperModel
    except ModuleNotFoundError as exc:
        if exc.name != "faster_whisper":
            raise
        raiz = config.RAIZ
        venv_py = raiz / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python3")
        print("\nErro: o pacote 'faster_whisper' não está disponível neste Python.", file=sys.stderr)
        print(f"Python atual: {sys.executable}", file=sys.stderr)
        if venv_py.exists():
            print(f"\nUse o Python do venv do repositório:\n  {venv_py} <script>", file=sys.stderr)
        else:
            print(
                "\nCrie o venv e instale as dependências:\n"
                f"  python3 -m venv {raiz / '.venv'}\n"
                f"  {raiz / '.venv' / 'bin' / 'pip'} install -r {raiz / 'requirements.txt'}",
                file=sys.stderr,
            )
        sys.exit(1)
    return WhisperModel(
        normalizar_modelo(modelo),
        device=device or config.stt_device(),
        compute_type=compute_type or config.stt_compute(),
    )


def transcrever(whisper, wav: Path, idioma: str | None = None) -> str:
    """Retorna a transcrição como parágrafos separados por linha em branco."""
    segments, _ = whisper.transcribe(
        str(wav),
        language=idioma or config.idioma(),
        **PARAMETROS_TRANSCRICAO,
    )
    paragrafos = [seg.text.strip() for seg in segments if seg.text.strip()]
    return "\n\n".join(paragrafos)


# --------------------------------------------------------------------------- #
# Metadados do áudio                                                           #
# --------------------------------------------------------------------------- #

def duracao_segundos(wav: Path) -> int:
    try:
        import av
        container = av.open(str(wav))
        s = int(container.duration / av.time_base)
        container.close()
        return s
    except Exception:
        return 0


def duracao_legivel(wav: Path) -> str:
    s = duracao_segundos(wav)
    return f"{s // 60}:{s % 60:02d}" if s else "?"


def formatar_total(segundos: int) -> str:
    h, m = segundos // 3600, (segundos % 3600) // 60
    return f"{h}h {m:02d}m" if h else f"{m}m"


def data_do_nome(stem: str) -> str | None:
    """YYYY-MM-DD a partir de um stem YYYYMMDDhhmmss; None se não for timestamp."""
    if len(stem) >= 8 and stem[:8].isdigit():
        try:
            return datetime.strptime(stem[:8], "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def extrair_data(wav: Path) -> str:
    return data_do_nome(wav.stem) or datetime.fromtimestamp(wav.stat().st_mtime).strftime("%Y-%m-%d")


def eh_wav(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in {".wav", ".mp3", ".m4a", ".ogg", ".flac"}


def glob_audio(pasta: Path) -> list[Path]:
    """Lista áudios de uma pasta sem duplicatas em sistemas case-insensitive."""
    return sorted(p for p in pasta.iterdir() if eh_wav(p))


def dentro_de_transcrito(path: Path) -> bool:
    return any(parte.lower() == "transcrito" for parte in path.parts)


# --------------------------------------------------------------------------- #
# Nota                                                                         #
# --------------------------------------------------------------------------- #

def origem_relativa(wav: Path, record: Path | None = None) -> str:
    """Caminho do áudio relativo a RECORD/, para não gravar caminhos de máquina na nota."""
    record = record or config.record()
    try:
        return wav.resolve().relative_to(record.resolve()).as_posix()
    except ValueError:
        return wav.name


def montar_nota(wav: Path, transcricao: str, modelo: str, record: Path | None = None) -> str:
    return f"""---
title: "{wav.stem}"
date: {extrair_data(wav)}
duracao: "{duracao_legivel(wav)}"
origem: "{origem_relativa(wav, record)}"
modelo: {normalizar_modelo(modelo)}
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


def perguntar_modelo(padrao: str | None = None) -> str:
    padrao = padrao or config.stt_modelo_padrao()
    resp = input(f"Modelo: [s]mall / [m]edium / [l]arge-v3 (Enter = {padrao}): ").strip().lower()
    if resp.startswith("s"):
        return "small"
    if resp.startswith("m"):
        return "medium"
    if resp.startswith("l"):
        return "large-v3"
    return normalizar_modelo(padrao)

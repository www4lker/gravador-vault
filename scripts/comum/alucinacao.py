"""Pré-filtro de transcrições alucinadas.

O Whisper, diante de silêncio ou ruído, tende a preencher com frases do seu
treinamento (créditos de vídeo, pedidos de inscrição, URLs). Este módulo
detecta os casos grosseiros antes de gastar uma chamada de LLM.

Heurísticas, nesta ordem:
  1. texto curto demais → "vazia"
  2. URLs em excesso → "alucinada"
  3. padrão típico repetido muitas vezes → "alucinada"
  4. razão de palavras únicas / total muito baixa → "alucinada" ou "suspeita"

É um filtro barato e conservador. Ele não pega alucinações semânticas
(frases plausíveis que nunca foram ditas). Ver LACUNAS.md.
"""

from __future__ import annotations

import re

PADROES_ALUCINACAO = [
    # PT-BR — padrões de vídeo
    "e aí", "obrigado por assistir", "você está assistindo",
    "inscreva-se", "se inscreva no canal",
    "não esqueça de curtir", "curta e compartilhe", "até a próxima",
    "legendas pela comunidade",
    # EN
    "subtitles by the amara", "thanks for watching", "like and subscribe",
]

URL_RE = re.compile(r"https?://|www\.|\.com\b|\.org\b|\.br\b")

MIN_PALAVRAS = 10
MAX_URLS = 2
MAX_REPETICOES_PADRAO = 10
RATIO_ALUCINADA = 0.05
RATIO_SUSPEITA = 0.15


def detectar(transcricao: str) -> dict:
    """Retorna {"qualidade": vazia|alucinada|suspeita|ok, "motivo": str|None, "ratio_unicidade": float?}."""
    palavras = transcricao.lower().split()
    if len(palavras) < MIN_PALAVRAS:
        return {"qualidade": "vazia", "motivo": "transcrição sem conteúdo útil"}

    ratio = len(set(palavras)) / len(palavras)
    base = {"ratio_unicidade": round(ratio, 3)}

    urls = len(URL_RE.findall(transcricao))
    if urls > MAX_URLS:
        return {
            "qualidade": "alucinada",
            "motivo": f"{urls} URLs detectadas — modelo preencheu com conteúdo de treinamento",
            **base,
        }

    texto_lower = transcricao.lower()
    for padrao in PADROES_ALUCINACAO:
        n = texto_lower.count(padrao)
        if n > MAX_REPETICOES_PADRAO:
            return {
                "qualidade": "alucinada",
                "motivo": f"'{padrao}' aparece {n}x — alucinação típica em silêncio/ruído",
                **base,
            }

    if ratio < RATIO_ALUCINADA:
        return {
            "qualidade": "alucinada",
            "motivo": f"unicidade {ratio:.1%} — provavelmente não capturou fala real",
            **base,
        }
    if ratio < RATIO_SUSPEITA:
        return {
            "qualidade": "suspeita",
            "motivo": f"unicidade baixa ({ratio:.1%}) — pode conter alucinações",
            **base,
        }

    return {"qualidade": "ok", "motivo": None, **base}


MARCADORES_FINAIS = ("forte", "raso", "desenvolver")


def detectar_marcador_final(transcricao: str, marcadores=MARCADORES_FINAIS) -> str | None:
    """Última palavra de triagem dita antes do stop (regra 4 do protocolo)."""
    ultimas = transcricao.lower().split()[-30:]
    for palavra in reversed(ultimas):
        limpa = palavra.strip(".,!?;:")
        if limpa in marcadores:
            return limpa
    return None

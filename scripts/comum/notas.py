"""Leitura e escrita de notas Markdown com frontmatter YAML.

Contrato da nota (ver docs/ARQUITETURA.md):

    ---
    title: "20260602120000"
    date: 2026-06-02
    duracao: "4:12"
    origem: "2026-06-02/transcrito/20260602120000.WAV"
    modelo: medium
    categoria:
    manter-audio:
    tags: [gravador, inbox]
    ---

    <callouts gerados pelos scripts, sempre acima da transcrição>

    ## Transcrição

    <texto do Whisper — nunca reescrito pelos scripts>

    ---
    *Observações:*
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

MARCADOR_TRANSCRICAO = "\n## Transcrição\n"
NOTE_RE = re.compile(r"^\d{14}$")
IGNORAR_PARTES = {".git", ".obsidian", ".trash", "_logs", "_conexoes", "01-BASES"}

ORDEM_FRONTMATTER_BASE = [
    "title", "date", "duracao", "origem", "modelo", "categoria",
    "manter-audio", "marcador-final", "llm-qualidade-transcricao",
]


def _sanitizar_frontmatter(fm_raw: str) -> str:
    r"""Troca backslashes por barras no campo origem antes de parsear.

    Notas antigas geradas no Windows podem ter `origem: "C:\..."`, que o YAML
    entre aspas duplas trata como escape inválido.
    """
    novas = []
    for linha in fm_raw.splitlines(keepends=True):
        if linha.startswith("origem:") and "\\" in linha:
            linha = linha.replace("\\", "/")
        novas.append(linha)
    return "".join(novas)


def separar(texto: str) -> tuple[str | None, str]:
    """Retorna (frontmatter_raw, corpo). frontmatter_raw é None se não houver."""
    if not texto.startswith("---"):
        return None, texto
    partes = texto.split("---", 2)
    if len(partes) < 3:
        return None, texto
    return partes[1], partes[2]


def ler(path: Path) -> tuple[dict, str]:
    """Retorna (frontmatter_dict, corpo). Frontmatter inválido vira {}."""
    return ler_texto(path.read_text(encoding="utf-8"))


def ler_texto(texto: str) -> tuple[dict, str]:
    fm_raw, corpo = separar(texto)
    if fm_raw is None:
        return {}, texto
    try:
        fm = yaml.safe_load(_sanitizar_frontmatter(fm_raw)) or {}
    except yaml.YAMLError:
        fm = {}
    if not isinstance(fm, dict):
        fm = {}
    return fm, corpo


def extrair_transcricao(corpo: str) -> str:
    """Texto entre `## Transcrição` e o próximo `---` ou `## `."""
    match = re.search(r"## Transcrição\n(.*?)(?=\n---|\n## |\Z)", corpo, re.DOTALL)
    return match.group(1).strip() if match else ""


def serializar_frontmatter(fm: dict, ordem_extra: list[str] | None = None) -> str:
    """Serializa preservando a ordem dos campos conhecidos; `tags` vai por último."""
    ordem = list(ORDEM_FRONTMATTER_BASE) + list(ordem_extra or [])
    linhas = ["---"]
    vistos: set[str] = set()

    def dump(campo: str) -> None:
        if fm[campo] is None:
            linhas.append(f"{campo}:")  # propriedade vazia, como o Obsidian escreve
        else:
            linhas.append(
                yaml.dump({campo: fm[campo]}, allow_unicode=True, default_flow_style=False,
                          sort_keys=False).rstrip()
            )
        vistos.add(campo)

    for campo in ordem:
        if campo in fm and campo != "tags":
            dump(campo)
    for campo in fm:
        if campo not in vistos and campo != "tags":
            dump(campo)
    if "tags" in fm:
        dump("tags")
    linhas.append("---")
    return "\n".join(linhas)


def inserir_antes_transcricao(corpo: str, bloco: str) -> str:
    """Insere um bloco acima de `## Transcrição`, sem tocar na transcrição."""
    if MARCADOR_TRANSCRICAO in corpo:
        return corpo.replace(MARCADOR_TRANSCRICAO, f"\n{bloco}\n{MARCADOR_TRANSCRICAO}", 1)
    return corpo.rstrip("\n") + f"\n\n{bloco}\n"


def montar(fm: dict, corpo: str, ordem_extra: list[str] | None = None) -> str:
    return serializar_frontmatter(fm, ordem_extra) + corpo


def nome_unico(pasta: Path, nome_base: str, sufixo: str = ".md") -> Path:
    candidato = pasta / f"{nome_base}{sufixo}"
    n = 2
    while candidato.exists():
        candidato = pasta / f"{nome_base}_{n}{sufixo}"
        n += 1
    return candidato


def ignorar(path: Path) -> bool:
    return any(parte in IGNORAR_PARTES for parte in path.parts)


def listar_notas(vault: Path, apenas_ids: bool = True) -> dict[str, Path]:
    """Mapa stem → caminho das notas do vault, fora das pastas de sistema.

    Com apenas_ids=True, só notas cujo nome é um ID (YYYYMMDDhhmmss).
    """
    notas: dict[str, Path] = {}
    if not vault.exists():
        return notas
    for path in sorted(vault.rglob("*.md")):
        if ignorar(path):
            continue
        if apenas_ids and not NOTE_RE.match(path.stem):
            continue
        notas.setdefault(path.stem, path)
    return notas


def stems_existentes(vault: Path) -> set[str]:
    """Todos os stems de .md do vault (qualquer nome), para evitar duplicatas."""
    return set(listar_notas(vault, apenas_ids=False))


def normalizar_lista(valor) -> list[str]:
    if not valor:
        return []
    if isinstance(valor, list):
        return [str(v).strip() for v in valor if str(v).strip()]
    return [str(valor).strip()]


WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")


def wikilinks_invalidos(texto: str, ids_validos: set[str]) -> list[str]:
    return [alvo for alvo in WIKILINK_RE.findall(texto) if alvo not in ids_validos]


def marcar_wikilinks_invalidos(texto: str, ids_validos: set[str]) -> str:
    def repl(match: re.Match) -> str:
        alvo = match.group(1)
        if alvo in ids_validos:
            return match.group(0)
        return f"`[[{alvo}]]` (ID não encontrado; revisar)"
    return WIKILINK_RE.sub(repl, texto)

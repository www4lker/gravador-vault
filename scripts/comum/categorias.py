"""Taxonomia e esquemas de análise carregados de config/categorias.yaml.

Tudo que depende de *quais* categorias existem passa por aqui: inferência de
categoria pela pasta ou pelo frontmatter, construção do prompt, renderização
do callout e mapeamento JSON → propriedades `llm-*`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import config

MAX_CHARS_TRANSCRICAO = 8_000

INSTRUCOES_COESAO = """
Para o campo "coesao":
- "boa"            : texto fluido, coerente, sem artefatos visíveis (confiança ≥ 8)
- "fragmentada"    : quebras de raciocínio, conteúdo principal recuperável (confiança 5–7)
- "re-transcrever" : substituições fonéticas, frases incompletas, lógica ininteligível (confiança < 5)
"""

CAMPO_COESAO = {"avaliacao": "boa|fragmentada|re-transcrever", "confianca": 0, "observacoes": None}


@dataclass
class Categoria:
    nome: str
    descricao: str = ""
    callout: str = "abstract"
    instrucao: str = ""
    campos: dict = field(default_factory=dict)
    frontmatter: dict = field(default_factory=dict)
    secoes: list = field(default_factory=list)
    avaliar_coesao: bool = True


@dataclass
class Taxonomia:
    categorias: dict[str, Categoria]
    fallback: str
    modelos_rapidos: list[str]
    marcadores_finais: list[str]
    frontmatter_padrao: dict[str, str]
    secoes_comuns: list[dict]
    origem: Path | None = None

    # ------------------------------------------------------------------ #
    @property
    def nomes(self) -> list[str]:
        return list(self.categorias)

    @property
    def pastas_vault(self) -> list[str]:
        """Pastas que o vault precisa ter: 00-INBOX, 01-BASES e uma por categoria."""
        pastas = ["00-INBOX", "01-BASES", "_conexoes"]
        pastas += [n for n in self.nomes if n != self.fallback]
        return pastas

    def get(self, nome: str) -> Categoria:
        return self.categorias.get(nome) or self.categorias[self.fallback]

    def inferir(self, note_path: Path, frontmatter: dict) -> str:
        """Pasta da nota manda; depois `categoria:` do frontmatter; depois fallback."""
        for parte in note_path.parts:
            if parte in self.categorias and parte != self.fallback:
                return parte
        cat_fm = str(frontmatter.get("categoria") or "").upper().strip()
        if cat_fm in self.categorias:
            return cat_fm
        return self.fallback

    def campos_frontmatter(self, nome: str) -> dict[str, str]:
        mapa = dict(self.frontmatter_padrao)
        mapa.update(self.get(nome).frontmatter)
        return mapa

    def propriedades_llm(self) -> list[str]:
        """Todas as propriedades llm-* que alguma categoria pode escrever, em ordem estável."""
        vistos: list[str] = ["llm-qualidade-transcricao"]
        for prop in self.frontmatter_padrao.values():
            if prop not in vistos:
                vistos.append(prop)
        for cat in self.categorias.values():
            for prop in cat.frontmatter.values():
                if prop not in vistos:
                    vistos.append(prop)
        return vistos

    # ------------------------------------------------------------------ #
    def pede_coesao(self, nome: str, modelo_stt: str) -> bool:
        return self.get(nome).avaliar_coesao and modelo_stt in self.modelos_rapidos

    def esquema_json(self, nome: str, modelo_stt: str) -> dict:
        cat = self.get(nome)
        esquema = json.loads(json.dumps(cat.campos))  # cópia profunda
        lista = "|".join(n for n in self.nomes if n != self.fallback)
        esquema = _substituir(esquema, "{categorias}", lista)
        if self.pede_coesao(nome, modelo_stt):
            esquema["coesao"] = dict(CAMPO_COESAO)
        return esquema

    def build_prompt(self, transcricao: str, modelo_stt: str, nome: str, idioma: str = "pt") -> str:
        cat = self.get(nome)
        transcricao = truncar(transcricao)
        esquema = self.esquema_json(nome, modelo_stt)
        if self.pede_coesao(nome, modelo_stt):
            coesao = (
                f"\n\nAnálise de coesão obrigatória (modelo de transcrição usado: {modelo_stt}, "
                f"rápido e mais sujeito a erro):\n{INSTRUCOES_COESAO}"
            )
        else:
            coesao = ""
        descricao_idioma = {"pt": "português brasileiro"}.get(idioma, idioma)
        return f"""Você é um assistente de análise de transcrições de áudio em {descricao_idioma}.
{cat.instrucao}{coesao}

Retorne APENAS um objeto JSON válido, sem texto antes ou depois, sem markdown, sem blocos de código.
Estrutura esperada para categoria {nome}:
{json.dumps(esquema, ensure_ascii=False, indent=2)}

Transcrição:
---
{transcricao}
---"""

    # ------------------------------------------------------------------ #
    def formatar_callout(self, dados: dict, nome: str, modelo_stt: str, fonte: str) -> str:
        cat = self.get(nome)
        titulo = f"> [!{cat.callout}]- Análise {fonte} · {nome}"

        if dados.get("_parse_error"):
            raw = str(dados.get("_raw", "")).strip()
            return "\n".join([
                titulo, ">",
                f"> ⚠️ Erro ao interpretar a resposta do provedor {fonte}.",
                ">", "> ```", *(f"> {l}" for l in raw.splitlines()), "> ```",
            ])

        linhas = [titulo, ">"]
        for secao in list(cat.secoes) + list(self.secoes_comuns):
            linhas.extend(_render_secao(secao, dados))
        while len(linhas) > 1 and linhas[-1] == ">":
            linhas.pop()
        texto = "\n".join(linhas)

        coesao = dados.get("coesao") or {}
        if self.pede_coesao(nome, modelo_stt) and coesao.get("avaliacao") in ("fragmentada", "re-transcrever"):
            obs = coesao.get("observacoes") or ""
            texto += (
                f"\n\n> [!warning] Coesão: {coesao['avaliacao']} ({coesao.get('confianca', '?')}/10)\n"
                + (f"> {obs}\n" if obs else "")
                + "> Considere re-transcrever com um modelo maior e marcar `manter-audio: re-transcrever`."
            )
        return texto

    def atualizar_frontmatter(self, fm: dict, dados: dict, nome: str) -> dict:
        if dados.get("_parse_error"):
            return fm
        mapa = self.campos_frontmatter(nome)
        for campo_json, propriedade in mapa.items():
            valor = dados.get(campo_json)
            if valor in (None, "", [], {}):
                continue
            if propriedade in fm and campo_json not in self.get(nome).frontmatter:
                # dois campos JSON apontando para a mesma propriedade: o primeiro vence
                continue
            fm[propriedade] = valor
        return fm


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def truncar(transcricao: str, limite: int = MAX_CHARS_TRANSCRICAO) -> str:
    if len(transcricao) <= limite:
        return transcricao
    return transcricao[:limite] + (
        f"\n\n[TRANSCRIÇÃO TRUNCADA — {len(transcricao)} chars totais, exibindo primeiros {limite}]"
    )


def _substituir(obj, token: str, valor: str):
    if isinstance(obj, str):
        return obj.replace(token, valor)
    if isinstance(obj, list):
        return [_substituir(x, token, valor) for x in obj]
    if isinstance(obj, dict):
        return {k: _substituir(v, token, valor) for k, v in obj.items()}
    return obj


def _c(linha: str) -> str:
    return f"> {linha}" if linha.strip() else ">"


def _render_secao(secao: dict, dados: dict) -> list[str]:
    campo = secao.get("campo")
    rotulo = secao.get("rotulo", campo)
    tipo = secao.get("tipo", "texto")
    valor = dados.get(campo)
    if valor in (None, "", [], {}):
        return []
    linhas: list[str] = []
    if tipo == "texto":
        linhas.append(_c(f"**{rotulo}:** {valor}"))
    elif tipo == "codigo":
        linhas.append(_c(f"**{rotulo}:** `{valor}`"))
    elif tipo == "inline":
        itens = valor if isinstance(valor, list) else [valor]
        linhas.append(_c(f"**{rotulo}:** " + " · ".join(str(i) for i in itens)))
    elif tipo == "lista":
        itens = valor if isinstance(valor, list) else [valor]
        linhas.append(_c(f"**{rotulo}:**"))
        for item in itens:
            if isinstance(item, dict):
                item = " — ".join(f"{k}: {v}" for k, v in item.items() if v)
            linhas.append(_c(f"- {item}"))
    elif tipo == "dict":
        if not isinstance(valor, dict) or not any(v for v in valor.values()):
            return []
        rotulos = secao.get("rotulos") or {}
        linhas.append(_c(f"**{rotulo}:**"))
        for k, v in valor.items():
            if v:
                linhas.append(_c(f"- {rotulos.get(k, k)}: {v}"))
    else:
        linhas.append(_c(f"**{rotulo}:** {valor}"))
    linhas.append(">")
    return linhas


# --------------------------------------------------------------------------- #
# Carregamento                                                                 #
# --------------------------------------------------------------------------- #

_CACHE: dict[str, Taxonomia] = {}


def carregar(path: Path | None = None) -> Taxonomia:
    path = Path(path or config.categorias_yaml())
    chave = str(path.resolve())
    if chave in _CACHE:
        return _CACHE[chave]
    if not path.exists():
        raise FileNotFoundError(f"categorias.yaml não encontrado: {path}")
    bruto = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cats_raw = bruto.get("categorias") or {}
    if not cats_raw:
        raise ValueError(f"{path}: nenhuma categoria definida")
    categorias = {}
    for nome, c in cats_raw.items():
        c = c or {}
        categorias[str(nome)] = Categoria(
            nome=str(nome),
            descricao=str(c.get("descricao", "")),
            callout=str(c.get("callout", "abstract")),
            instrucao=str(c.get("instrucao", "")).strip(),
            campos=dict(c.get("campos") or {}),
            frontmatter=dict(c.get("frontmatter") or {}),
            secoes=list(c.get("secoes") or []),
            avaliar_coesao=bool(c.get("avaliar_coesao", True)),
        )
    fallback = str(bruto.get("fallback") or next(iter(categorias)))
    if fallback not in categorias:
        raise ValueError(f"{path}: fallback '{fallback}' não está em categorias")
    tax = Taxonomia(
        categorias=categorias,
        fallback=fallback,
        modelos_rapidos=[str(m) for m in (bruto.get("modelos_rapidos") or ["tiny", "base", "small"])],
        marcadores_finais=[str(m) for m in (bruto.get("marcadores_finais") or ["forte", "raso", "desenvolver"])],
        frontmatter_padrao=dict(bruto.get("frontmatter_padrao") or {}),
        secoes_comuns=list(bruto.get("secoes_comuns") or []),
        origem=path,
    )
    _CACHE[chave] = tax
    return tax

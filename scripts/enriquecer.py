"""enriquecer.py — Análise semântica das notas transcritas via LLM, por categoria.

Para cada nota:
  1. pré-filtro de alucinação (comum/alucinacao.py) — se alucinada, só marca e sai
  2. prompt por categoria (config/categorias.yaml)
  3. chamada ao LLM (Ollama local por padrão; Gemini CLI opcional)
  4. callout Obsidian acima de `## Transcrição` + propriedades `llm-*` no frontmatter
  5. garante a Base de triagem em <vault>/01-BASES/_triagem.base

Uso:
  enriquecer.py                            # todas as notas em <vault>/00-INBOX/
  enriquecer.py <vault>/00-INBOX/nota.md   # uma nota
  enriquecer.py <vault>/RESENHAS/          # uma pasta
  enriquecer.py --fonte gemini             # sem LLM local
  enriquecer.py --force                    # reprocessa notas já enriquecidas
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from comum import alucinacao, categorias, config, llm, notas

ANALISE_RE = re.compile(r"Análise [^\n·]+ · ")
ANALISE_BLOCO_RE = re.compile(r"\n> \[![^\n]*Análise [^\n·]+ · [^\n]*(?:\n>[^\n]*)*")
AVISO_BLOCO_RE = re.compile(r"\n> \[!warning\] (?:Transcrição alucinada|Timeout|Coesão)[^\n]*(?:\n>[^\n]*)*")


def remover_analise_anterior(texto: str) -> str:
    texto = ANALISE_BLOCO_RE.sub("", texto)
    return AVISO_BLOCO_RE.sub("", texto)


def callout_alucinacao(qualidade: dict, modelo_stt: str, tax: categorias.Taxonomia) -> str:
    rec = ("Re-transcreva com um modelo maior após revisar o áudio original."
           if modelo_stt in tax.modelos_rapidos
           else "Revise o áudio — a qualidade do arquivo pode estar comprometida.")
    return (
        "> [!warning] Transcrição alucinada — análise não realizada\n"
        ">\n"
        f"> **Diagnóstico:** {qualidade['motivo']}\n"
        f"> **Unicidade:** {qualidade.get('ratio_unicidade', '—')}\n"
        f"> **Modelo usado:** {modelo_stt}\n"
        ">\n"
        f"> {rec}"
    )


def enriquecer_nota(path: Path, tax: categorias.Taxonomia, *, force: bool, fonte: str,
                    modelo_llm: str, timeout: int, dry_run: bool = False) -> str:
    """Retorna um rótulo de resultado: ok | ja-enriquecida | sem-transcricao | alucinada | timeout | erro | dry-run."""
    texto = path.read_text(encoding="utf-8")
    if ANALISE_RE.search(texto):
        if not force:
            print(f"  [já enriquecida] {path.name}")
            return "ja-enriquecida"
        texto = remover_analise_anterior(texto)
        if not dry_run:
            path.write_text(texto, encoding="utf-8")

    fm, corpo = notas.ler_texto(texto)
    transcricao = notas.extrair_transcricao(corpo)
    if not transcricao:
        print(f"  [sem transcrição] {path.name}")
        return "sem-transcricao"

    categoria = tax.inferir(path, fm)
    modelo_stt = str(fm.get("modelo") or "small")
    marcador = alucinacao.detectar_marcador_final(transcricao, tuple(tax.marcadores_finais))
    print(f"  categoria : {categoria}")
    print(f"  modelo    : {modelo_stt}")
    if marcador:
        print(f"  marcador  : {marcador}")
    if marcador and not fm.get("marcador-final"):
        fm["marcador-final"] = marcador

    ordem_extra = tax.propriedades_llm()
    qualidade = alucinacao.detectar(transcricao)
    if qualidade["qualidade"] in ("alucinada", "vazia"):
        fm["llm-qualidade-transcricao"] = qualidade["qualidade"]
        bloco = callout_alucinacao(qualidade, modelo_stt, tax)
        print(f"  [{qualidade['qualidade']}] {qualidade['motivo']}")
        if not dry_run:
            path.write_text(notas.montar(fm, notas.inserir_antes_transcricao(corpo, bloco), ordem_extra),
                            encoding="utf-8")
        return "alucinada"
    if qualidade["qualidade"] == "suspeita":
        print(f"  ⚠️  {qualidade['motivo']}")
        fm["llm-qualidade-transcricao"] = "suspeita"

    prompt = tax.build_prompt(transcricao, modelo_stt, categoria, config.idioma())
    if dry_run:
        print(f"  [dry-run] prompt de {len(prompt)} chars para {fonte}; nada gravado")
        return "dry-run"

    print(f"  analisando com {fonte}...", flush=True)
    try:
        resposta, fonte_label = llm.chamar(prompt, fonte, modelo_llm, timeout)
    except llm.LLMTimeout:
        fm.setdefault("llm-qualidade-transcricao", "timeout")
        bloco = (
            "> [!warning] Timeout — análise não realizada\n>\n"
            f"> Provedor `{fonte}` não respondeu em {timeout}s.\n"
            f"> Re-processe com: `enriquecer.py {path.name}`"
        )
        path.write_text(notas.montar(fm, notas.inserir_antes_transcricao(corpo, bloco), ordem_extra),
                        encoding="utf-8")
        print(f"  [timeout] {fonte} não respondeu em {timeout}s")
        return "timeout"
    except llm.LLMIndisponivel as exc:
        print(f"  [erro LLM] {exc}")
        return "erro"

    dados = llm.extrair_json(resposta)
    if dados is None:
        print("  ⚠️  JSON inválido — salvando resposta bruta no callout")
        dados = {"_raw": resposta, "_parse_error": True}

    fm = tax.atualizar_frontmatter(fm, dados, categoria)
    bloco = tax.formatar_callout(dados, categoria, modelo_stt, fonte_label)
    path.write_text(notas.montar(fm, notas.inserir_antes_transcricao(corpo, bloco), ordem_extra),
                    encoding="utf-8")
    print(f"  [ok] {path.name}")
    return "ok"


# --------------------------------------------------------------------------- #
# Base de triagem                                                              #
# --------------------------------------------------------------------------- #

BASE_TRIAGEM = """\
filters: "file.inFolder('00-INBOX')"
properties:
  llm-categoria-sugerida:
    displayName: Categoria sugerida
  manter-audio:
    displayName: Manter áudio
  marcador-final:
    displayName: Marcador
  duracao:
    displayName: Duração
  modelo:
    displayName: Modelo
  llm-qualidade-transcricao:
    displayName: Qualidade
views:
  - type: table
    name: Triagem
    order:
      - date
      - file.name
      - duracao
      - marcador-final
      - llm-categoria-sugerida
      - llm-qualidade-transcricao
      - categoria
      - manter-audio
      - modelo
"""


def garantir_base_triagem(vault: Path) -> None:
    bases = config.bases(vault)
    bases.mkdir(parents=True, exist_ok=True)
    base = bases / "_triagem.base"
    if not base.exists():
        base.write_text(BASE_TRIAGEM, encoding="utf-8")
        print(f"  [base] criada: {base}")


# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(description="Enriquece notas de transcrição com análise LLM por categoria.")
    parser.add_argument("alvo", nargs="?", default=None, help="Nota .md ou pasta (padrão: <vault>/00-INBOX/)")
    parser.add_argument("--force", action="store_true", help="Reprocessa notas já enriquecidas")
    parser.add_argument("--fonte", choices=["ollama", "gemini", "auto"], default=None,
                        help="Provedor LLM (padrão: GV_LLM_FONTE ou ollama)")
    parser.add_argument("--modelo", default=None, help="Modelo Ollama (padrão: GV_LLM_MODEL)")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout da chamada LLM em segundos")
    parser.add_argument("--dry-run", action="store_true", help="Mostra categoria/qualidade sem chamar LLM nem gravar")
    parser.add_argument("--categorias", default=None, help="Outro categorias.yaml (padrão: GV_CATEGORIAS)")
    args = parser.parse_args()

    vault = config.vault()
    tax = categorias.carregar(Path(args.categorias) if args.categorias else None)
    alvo = Path(args.alvo).expanduser() if args.alvo else config.inbox(vault)
    if not alvo.exists():
        print(f"Erro: '{alvo}' não encontrado.", file=sys.stderr)
        sys.exit(1)
    lista = [alvo] if alvo.is_file() else sorted(alvo.glob("*.md"))
    if not lista:
        print(f"Nenhuma nota .md em '{alvo}'.")
        return

    if not args.dry_run:
        garantir_base_triagem(vault)

    fonte = args.fonte or config.llm_fonte()
    modelo_llm = args.modelo or config.llm_modelo()
    print(f"\n{len(lista)} nota(s) · fonte={fonte} · modelo={modelo_llm} · categorias={tax.origem}\n")
    contagem: dict[str, int] = {}
    for i, nota in enumerate(lista, 1):
        print(f"[{i}/{len(lista)}] {nota.name}")
        try:
            r = enriquecer_nota(nota, tax, force=args.force, fonte=fonte, modelo_llm=modelo_llm,
                                timeout=args.timeout, dry_run=args.dry_run)
        except Exception as exc:  # noqa: BLE001 — uma nota ruim não derruba o lote
            print(f"  [erro] {exc}")
            r = "erro"
        contagem[r] = contagem.get(r, 0) + 1
        print()
    print("Concluído: " + ", ".join(f"{k}={v}" for k, v in sorted(contagem.items())))


if __name__ == "__main__":
    main()

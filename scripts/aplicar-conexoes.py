"""aplicar-conexoes.py — Escreve nas notas as conexões fortes/aprovadas de propostas.json.

Por padrão é dry-run: mostra o que faria. Só grava com --aplicar.

O que ele faz ao aplicar:
  - insere um bloco `Conexões locais` acima de `## Transcrição`
  - não mexe na transcrição, não move notas, não altera outras propriedades
  - não duplica o bloco se a nota já tiver um (substitui)
  - valida que todo [[wikilink]] aponta para um ID real antes de gravar

Uso:
  aplicar-conexoes.py --min-score 0.72 --max-links-por-nota 3
  aplicar-conexoes.py --aplicar --min-score 0.72
  aplicar-conexoes.py --propostas GV_CACHE/conexoes/propostas-rodada.json --aplicar
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from comum import config, notas

BLOCO_INICIO = "> [!info]- Conexões locais"


def carregar_propostas(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"propostas não encontradas: {path} — rode conectar.py primeiro")
    return json.loads(path.read_text(encoding="utf-8"))


def montar_blocos(propostas: dict, min_score: float, max_links: int) -> dict[str, dict]:
    """Agrupa por nota o que vai entrar no bloco. Aceita propostas.json (pares) e
    propostas de rodada (apply_plan por nota)."""
    if propostas.get("apply_plan"):
        blocos = {}
        for item in propostas["apply_plan"]:
            links = [l for l in item.get("candidate_links", []) if float(l.get("score") or 0) >= min_score][:max_links]
            if links or item.get("themes") or item.get("axes"):
                blocos[str(item["id"])] = {"themes": item.get("themes") or [], "axes": item.get("axes") or [],
                                           "links": links, "summary": item.get("summary") or ""}
        return blocos

    por_nota: dict[str, list] = defaultdict(list)
    for par in propostas.get("pairs", []):
        if float(par.get("score") or 0) < min_score or par.get("status") not in {"forte", "aprovado"}:
            continue
        motivo = "; ".join(par.get("motivos", []))
        por_nota[str(par["a"])].append({"target": str(par["b"]), "score": par["score"], "reason": motivo})
        por_nota[str(par["b"])].append({"target": str(par["a"]), "score": par["score"], "reason": motivo})
    return {
        nid: {"themes": [], "axes": [], "summary": "",
              "links": sorted(ls, key=lambda l: l["score"], reverse=True)[:max_links]}
        for nid, ls in por_nota.items()
    }


def texto_bloco(dados: dict, gerado_em: str) -> str:
    linhas = [BLOCO_INICIO, ">", f"> Gerado em `{gerado_em}` a partir de propostas locais revisadas.", ">"]
    if dados.get("themes"):
        linhas += ["> **Temas:** " + " · ".join(dados["themes"][:8]), ">"]
    if dados.get("axes"):
        linhas.append("> **Eixos:**")
        linhas += [f"> - {e}" for e in dados["axes"][:5]]
        linhas.append(">")
    if dados.get("links"):
        linhas.append("> **Conexões fortes:**")
        for l in dados["links"]:
            linhas.append(f"> - [[{l['target']}]] — score {float(l['score']):.3f}")
            if l.get("reason"):
                linhas.append(f">   - {l['reason']}")
    while linhas and linhas[-1] == ">":
        linhas.pop()
    return "\n".join(linhas)


PROPRIEDADE = "conexoes-locais"


def marcar_frontmatter(fm_raw: str, gerado_em: str) -> str:
    """Define `conexoes-locais: <data>` no frontmatter bruto, preservando o resto como está."""
    linhas = fm_raw.split("\n")
    nova = f'{PROPRIEDADE}: "{gerado_em}"'
    for i, linha in enumerate(linhas):
        if linha.startswith(f"{PROPRIEDADE}:"):
            linhas[i] = nova
            return "\n".join(linhas)
    # insere antes da última linha (que é vazia, antes do --- de fechamento)
    if linhas and linhas[-1].strip() == "":
        linhas.insert(len(linhas) - 1, nova)
    else:
        linhas.append(nova)
    return "\n".join(linhas)


def inserir_bloco(texto: str, dados: dict, gerado_em: str) -> str:
    bloco = texto_bloco(dados, gerado_em)
    if notas.MARCADOR_TRANSCRICAO not in texto:
        raise ValueError("nota sem seção ## Transcrição")
    fm_raw, corpo = notas.separar(texto)
    if fm_raw is None:
        raise ValueError("nota sem frontmatter")
    if BLOCO_INICIO in corpo:
        inicio = corpo.index(BLOCO_INICIO)
        fim = corpo.index(notas.MARCADOR_TRANSCRICAO, inicio)
        corpo_novo = corpo[:inicio] + bloco + "\n" + corpo[fim:]
    else:
        corpo_novo = notas.inserir_antes_transcricao(corpo, bloco)
    return f"---{marcar_frontmatter(fm_raw, gerado_em)}---" + corpo_novo


def planejar(vault: Path, propostas: dict, min_score: float, max_links: int, log=print) -> list[tuple[Path, str]]:
    mapa = notas.listar_notas(vault)
    blocos = montar_blocos(propostas, min_score, max_links)
    gerado_em = propostas.get("generated_at") or datetime.now().isoformat(timespec="seconds")
    alteradas = []
    for nid, dados in sorted(blocos.items()):
        path = mapa.get(nid)
        if not path:
            log(f"[aviso] nota ausente: {nid}")
            continue
        texto = path.read_text(encoding="utf-8")
        fm, _ = notas.ler_texto(texto)
        if not fm:
            log(f"[aviso] frontmatter ausente ou inválido: {nid}")
            continue
        # links para IDs que não existem no vault saem do bloco (e ficam no log)
        validos = [l for l in dados.get("links", []) if str(l.get("target")) in mapa]
        descartados = [str(l.get("target")) for l in dados.get("links", []) if str(l.get("target")) not in mapa]
        if descartados:
            log(f"[aviso] {nid}: links para IDs inexistentes descartados: {', '.join(sorted(set(descartados)))}")
        dados = {**dados, "links": validos}
        if not (validos or dados.get("themes") or dados.get("axes")):
            continue
        try:
            novo = inserir_bloco(texto, dados, gerado_em)
        except ValueError as exc:
            log(f"[aviso] {nid}: {exc}")
            continue
        invalidos = notas.wikilinks_invalidos(novo, set(mapa))
        if invalidos:
            log(f"[aviso] links inválidos em {nid}: {', '.join(sorted(set(invalidos)))}")
            continue
        if novo != texto:
            alteradas.append((path, novo))
    return alteradas


def main() -> None:
    parser = argparse.ArgumentParser(description="Aplica conexões aprovadas nas notas (dry-run por padrão).")
    parser.add_argument("--pasta", default=None, help="Vault (padrão: GV_VAULT)")
    parser.add_argument("--propostas", default=None, help="propostas.json (padrão: GV_CACHE/conexoes/propostas.json)")
    parser.add_argument("--min-score", type=float, default=0.72)
    parser.add_argument("--max-links-por-nota", type=int, default=3)
    parser.add_argument("--aplicar", action="store_true", help="Grava as alterações")
    args = parser.parse_args()

    vault = Path(args.pasta).expanduser().resolve() if args.pasta else config.vault()
    propostas_path = Path(args.propostas).expanduser().resolve() if args.propostas else config.cache() / "conexoes" / "propostas.json"
    if not vault.exists():
        print(f"Erro: vault não encontrado: {vault}", file=sys.stderr)
        sys.exit(1)
    try:
        propostas = carregar_propostas(propostas_path)
    except FileNotFoundError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)

    alteradas = planejar(vault, propostas, args.min_score, args.max_links_por_nota)
    print(f"Modo: {'APLICAR' if args.aplicar else 'DRY-RUN'}")
    print(f"Notas com bloco novo: {len(alteradas)}")
    for path, _ in alteradas[:30]:
        print(f"- {path}")
    if not args.aplicar:
        print("(nada gravado; use --aplicar para escrever)")
        return
    for path, novo in alteradas:
        path.write_text(novo, encoding="utf-8")
    print(f"[ok] notas alteradas: {len(alteradas)}")


if __name__ == "__main__":
    main()

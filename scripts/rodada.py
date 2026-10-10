"""rodada.py — Rodada completa sobre o vault inteiro, com checkpoint para retomar.

Encadeia indexar → conectar → (opcional) aplicar, gravando estado em
GV_CACHE/conexoes/rodada-checkpoint.json para sobreviver a quedas de energia,
limite de tempo e interrupções. Pensado para rodar à noite ou uma vez por mês.

Por padrão NÃO altera notas: gera propostas-rodada.json e um relatório em
<vault>/_conexoes/. Aplicar é um passo separado e explícito.

Uso:
  rodada.py --dry-run --full
  rodada.py --full --max-hours 8
  rodada.py --resume --full --max-hours 8
  rodada.py --limite 30                   # teste pequeno
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import conectar
import indexar
from comum import config, llm, notas


def _carregar_modulo(nome: str, arquivo: str):
    spec = importlib.util.spec_from_file_location(nome, Path(__file__).with_name(arquivo))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


aplicar = _carregar_modulo("aplicar_conexoes", "aplicar-conexoes.py")


def ler_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def escrever_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def estrutura_por_nota(lista: list[dict], pares: list[dict], temas: list[dict]) -> dict[str, dict]:
    links: dict[str, list] = defaultdict(list)
    for p in pares:
        if p.get("status") != "forte":
            continue
        motivo = "; ".join(p.get("motivos") or [])
        links[p["a"]].append({"target": p["b"], "score": p["score"], "reason": motivo})
        links[p["b"]].append({"target": p["a"], "score": p["score"], "reason": motivo})
    temas_nota: dict[str, list] = defaultdict(list)
    for t in temas:
        for nid in t.get("notas", []):
            temas_nota[nid].append(t["tema"])
    out = {}
    for n in lista:
        palavras = [str(p).strip() for p in n.get("palavras_chave", []) if str(p).strip()]
        tn = temas_nota.get(n["id"]) or palavras[:5]
        ls = sorted(links.get(n["id"], []), key=lambda l: l["score"], reverse=True)
        eixos = []
        if n.get("categoria"):
            eixos.append(f"categoria: {n['categoria']}")
        if palavras:
            eixos.append("palavras-chave: " + ", ".join(palavras[:6]))
        out[n["id"]] = {"path": n.get("path"), "themes": tn[:6], "candidate_links": ls[:5], "axes": eixos,
                        "summary": n.get("resumo") or "", "status": "proposto" if ls or tn else "sem-estrutura"}
    return out


def relatorio(propostas: dict) -> str:
    linhas = [
        "---", f"date: {datetime.now():%Y-%m-%d}", "tipo: rodada", f"run-id: {propostas['run_id']}",
        f"modelo-embedding: {propostas['embedding_model']}", f"modelo-llm: {propostas['llm_model']}",
        f"notas-analisadas: {propostas['notes_count']}", f"pares-candidatos: {len(propostas['pairs'])}",
        f"temas-candidatos: {len(propostas['themes'])}", "---", "",
        "# Rodada local", "", "## Resumo", "",
        f"- Notas analisadas: {propostas['notes_count']}",
        f"- Pares candidatos: {len(propostas['pairs'])}",
        f"- Temas candidatos: {len(propostas['themes'])}",
        f"- Blocos propostos: {len(propostas['apply_plan'])}", "",
        "## Conexões mais fortes", "",
    ]
    for p in propostas["pairs"][:30]:
        v = f" — {p['validacao_llm']}" if p.get("validacao_llm") else ""
        linhas.append(f"- [[{p['a']}]] <-> [[{p['b']}]] · {p['score']:.3f}{v}")
    linhas += ["", "## Temas recorrentes", ""]
    for t in propostas["themes"][:30]:
        links = ", ".join(f"[[{i}]]" for i in t.get("notas", [])[:8])
        linhas.append(f"- **{t['tema']}** ({t['score']}): {links}")
    linhas += ["", "## Prévia de aplicação", ""]
    for item in propostas["apply_plan"][:40]:
        partes = [f"{len(item.get('candidate_links', []))} links"]
        if item.get("themes"):
            partes.append("temas: " + ", ".join(item["themes"][:4]))
        linhas.append(f"- [[{item['id']}]]: {'; '.join(partes)}")
    linhas += ["", "## Próximos passos", "",
               "- Revisar este relatório e as Bases antes de aplicar.",
               "- Aplicar só com `aplicar-conexoes.py --propostas <propostas-rodada.json> --aplicar`.", ""]
    return notas.marcar_wikilinks_invalidos("\n".join(linhas), set(propostas["notes"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Rodada completa (indexar → conectar → relatório) com checkpoint.")
    parser.add_argument("--pasta", default=None, help="Vault (padrão: GV_VAULT)")
    parser.add_argument("--cache-dir", default=None, help="Cache (padrão: GV_CACHE/conexoes)")
    parser.add_argument("--limite", type=int, default=None, help="Limite de notas para teste")
    parser.add_argument("--full", action="store_true", help="Confirma intenção de analisar o vault inteiro")
    parser.add_argument("--resume", action="store_true", help="Retoma do checkpoint")
    parser.add_argument("--dry-run", action="store_true", help="Mostra escopo sem chamar Ollama nem gravar")
    parser.add_argument("--max-hours", type=float, default=None, help="Limite aproximado de horas")
    parser.add_argument("--modelo", default=None, help="Modelo LLM de validação (padrão: GV_LLM_MODEL)")
    parser.add_argument("--modelo-embedding", default=None, help="Modelo de embeddings (padrão: GV_EMBED_MODEL)")
    parser.add_argument("--min-score", type=float, default=0.55)
    parser.add_argument("--max-pares", type=int, default=200)
    parser.add_argument("--validar-llm", type=int, default=40)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--aplicar", action="store_true", help="Aplica as propostas ao final (cuidado)")
    parser.add_argument("--max-links-por-nota", type=int, default=3)
    args = parser.parse_args()

    vault = Path(args.pasta).expanduser().resolve() if args.pasta else config.vault()
    cache_dir = Path(args.cache_dir).expanduser().resolve() if args.cache_dir else config.cache() / "conexoes"
    modelo_llm = args.modelo or config.llm_modelo()
    modelo_emb = args.modelo_embedding or config.embed_modelo()
    if not vault.exists():
        print(f"Erro: vault não encontrado: {vault}", file=sys.stderr)
        sys.exit(1)
    if not args.full and args.limite is None:
        print("Erro: use --full para o vault inteiro ou --limite N para teste.", file=sys.stderr)
        sys.exit(1)

    checkpoint = cache_dir / "rodada-checkpoint.json"
    estado = ler_json(checkpoint, {}) if args.resume else {}
    if not estado:
        estado = {"run_id": datetime.now().strftime("%Y%m%d-%H%M%S"),
                  "started_at": datetime.now().isoformat(timespec="seconds"), "phase": "preflight", "completed": False}
    deadline = time.monotonic() + args.max_hours * 3600 if args.max_hours else None

    paths = indexar.listar(vault, args.limite)
    lidas = [n for p in paths if (n := indexar.ler_nota(p, vault))]
    emb_path = cache_dir / "embeddings.jsonl"
    anteriores = indexar.ler_jsonl(emb_path)
    pend = indexar.pendentes(lidas, anteriores, modelo_emb)
    print(f"Vault: {vault}\nRun ID: {estado['run_id']}\nNotas elegíveis: {len(lidas)}\nEmbeddings pendentes: {len(pend)}\nCache: {cache_dir}")
    if args.dry_run:
        return

    try:
        modelos = llm.listar_modelos(min(args.timeout, 30))
    except llm.LLMIndisponivel as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
    faltando = [m for m in (modelo_emb, modelo_llm) if m not in modelos]
    if faltando:
        print(f"Erro: modelos ausentes no Ollama: {', '.join(faltando)} (ollama pull <modelo>)", file=sys.stderr)
        sys.exit(1)

    # Fase 1: indexação incremental com checkpoint
    embeddings = dict(anteriores)
    estado["phase"] = "indexacao"
    escrever_json(checkpoint, estado)
    for i, n in enumerate(lidas, 1):
        ant = embeddings.get(n["id"])
        if ant and ant.get("hash") == n["hash"] and ant.get("modelo") == modelo_emb:
            continue
        if deadline and time.monotonic() >= deadline:
            estado.update({"indexed": i - 1, "completed": False})
            escrever_json(checkpoint, estado)
            indexar.escrever_jsonl(emb_path, list(embeddings.values()))
            print("[pausa] limite de tempo atingido; rode novamente com --resume.")
            return
        print(f"[{i}/{len(lidas)}] embedding {n['id']}", flush=True)
        embeddings[n["id"]] = {"id": n["id"], "path": n["path"], "hash": n["hash"], "mtime": n["mtime"],
                               "modelo": modelo_emb, "embedding": llm.embedding(n["texto_embedding"], modelo_emb, args.timeout)}
        estado.update({"indexed": i, "last_note": n["id"]})
        escrever_json(checkpoint, estado)

    publicas = [{k: v for k, v in n.items() if k != "texto_embedding"} for n in lidas]
    indexar.escrever_jsonl(cache_dir / "notas.jsonl", publicas)
    indexar.escrever_jsonl(emb_path, [embeddings[n["id"]] for n in lidas if n["id"] in embeddings])
    escrever_json(cache_dir / "manifest.json", {
        "generated_at": datetime.now().isoformat(timespec="seconds"), "vault": str(vault),
        "embedding_model": modelo_emb, "notes_count": len(lidas), "embeddings_count": len(embeddings),
    })

    # Fase 2: conexões
    estado["phase"] = "conexoes"
    escrever_json(checkpoint, estado)
    por_id = {n["id"]: n for n in publicas if n["id"] in embeddings}
    pares = conectar.pontuar_pares(list(por_id.values()), embeddings, args.min_score)[:args.max_pares]
    temas = conectar.temas_recorrentes(list(por_id.values()), pares)
    if pares and args.validar_llm > 0:
        try:
            validacoes = conectar.validar_com_llm(pares[:args.validar_llm], por_id, modelo_llm, args.timeout)
            for p in pares:
                p["validacao_llm"] = validacoes.get(f"{p['a']}|{p['b']}")
        except (llm.LLMIndisponivel, llm.LLMTimeout) as exc:
            print(f"[aviso] {exc}; mantendo proposta determinística.", file=sys.stderr)

    estruturas = estrutura_por_nota(list(por_id.values()), pares, temas)
    apply_plan = [{"id": nid, **e} for nid, e in sorted(estruturas.items()) if e["candidate_links"] or e["themes"]]
    propostas = {
        "run_id": estado["run_id"], "generated_at": datetime.now().isoformat(timespec="seconds"),
        "embedding_model": modelo_emb, "llm_model": modelo_llm, "notes_count": len(por_id),
        "notes": estruturas, "pairs": pares, "themes": temas, "apply_plan": apply_plan,
    }
    propostas_path = cache_dir / "propostas-rodada.json"
    escrever_json(propostas_path, propostas)

    out = config.conexoes(vault)
    out.mkdir(parents=True, exist_ok=True)
    rel_path = out / f"rodada-{datetime.now():%Y%m%d-%H%M%S}.md"
    rel_path.write_text(relatorio(propostas), encoding="utf-8")

    estado.update({"phase": "completed", "completed": True, "completed_at": datetime.now().isoformat(timespec="seconds"),
                   "propostas": str(propostas_path), "relatorio": str(rel_path)})

    # Fase 3 (opcional): aplicar
    if args.aplicar:
        estado["phase"] = "aplicacao"
        escrever_json(checkpoint, estado)
        alteradas = aplicar.planejar(vault, propostas, args.min_score, args.max_links_por_nota)
        for path, novo in alteradas:
            path.write_text(novo, encoding="utf-8")
        estado["notas_alteradas"] = len(alteradas)
        print(f"[ok] notas alteradas: {len(alteradas)}")
    escrever_json(checkpoint, estado)
    print(f"[ok] propostas: {propostas_path}\n[ok] relatório: {rel_path}")


if __name__ == "__main__":
    main()

"""conectar.py — Propostas revisáveis de conexões entre notas, a partir do índice.

Fórmula: similaridade de embeddings (peso maior) + palavras-chave em comum +
mesma categoria/pasta + termos fortes no resumo + proximidade temporal. O LLM
entra só no fim, para explicar os pares mais fortes. Ele não procura conexões
livremente no vault.

Saídas:
  GV_CACHE/conexoes/propostas.json          (para aplicar-conexoes.py)
  <vault>/_conexoes/conexoes-YYYYMMDD-HHMMSS.md
  <vault>/_conexoes/temas-YYYYMMDD-HHMMSS.md

Nenhuma nota é alterada.

Uso:
  conectar.py --dry-run --max-pares 20
  conectar.py --sem-llm
  conectar.py --max-pares 80
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from comum import config, llm, notas

STOPWORDS = {
    "a", "o", "as", "os", "um", "uma", "de", "do", "da", "das", "dos", "em", "no", "na",
    "nos", "nas", "para", "por", "com", "que", "e", "ou", "se", "ao", "aos", "como",
    "sobre", "mais", "menos", "não", "nao", "muito", "isso", "essa", "esse", "este",
    "esta", "pela", "pelo", "está", "esta", "são", "sao", "foi", "ser", "ter",
}
LIMIAR_FORTE = 0.72


def ler_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"cache ausente: {path} — rode indexar.py primeiro")
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def tokens_fortes(texto: str) -> set[str]:
    return {t for t in re.findall(r"[A-Za-zÀ-ÿ0-9_-]{4,}", texto.lower()) if t not in STOPWORDS}


def bonus_temporal(a: dict, b: dict) -> float:
    da, db = str(a.get("date") or ""), str(b.get("date") or "")
    if da and da == db:
        return 0.03
    if da[:7] and da[:7] == db[:7]:
        return 0.01
    return 0.0


def pontuar_pares(lista: list[dict], embeddings: dict[str, dict], min_score: float) -> list[dict]:
    pares = []
    for i, a in enumerate(lista):
        ea = embeddings.get(a["id"], {}).get("embedding") or []
        ka = {k.lower() for k in a.get("palavras_chave", [])}
        ta = tokens_fortes(a.get("resumo", ""))
        for b in lista[i + 1:]:
            eb = embeddings.get(b["id"], {}).get("embedding") or []
            sim = cosine(ea, eb)
            kb = {k.lower() for k in b.get("palavras_chave", [])}
            tb = tokens_fortes(b.get("resumo", ""))
            palavras_comuns = sorted(ka & kb)
            termos_comuns = sorted((ta & tb) - set(palavras_comuns))
            cat_bonus = 0.06 if a.get("categoria") == b.get("categoria") else 0.0
            pasta_bonus = 0.03 if a.get("pasta") == b.get("pasta") else 0.0
            kw_bonus = min(len(palavras_comuns) * 0.04, 0.16)
            termo_bonus = min(len(termos_comuns) * 0.015, 0.06)
            sim_norm = max(0.0, min((sim - 0.75) / 0.25, 1.0))
            score = min(sim_norm * 0.65 + cat_bonus + pasta_bonus + kw_bonus + termo_bonus + bonus_temporal(a, b), 1.0)
            if score < min_score:
                continue
            motivos = [f"similaridade {sim:.3f}"]
            if palavras_comuns:
                motivos.append("palavras-chave: " + ", ".join(palavras_comuns[:6]))
            if termos_comuns:
                motivos.append("termos no resumo: " + ", ".join(termos_comuns[:5]))
            if cat_bonus:
                motivos.append(f"categoria {a.get('categoria')}")
            pares.append({
                "a": a["id"], "b": b["id"],
                "score": round(score, 4), "similaridade": round(sim, 4),
                "motivos": motivos,
                "status": "forte" if score >= LIMIAR_FORTE else "revisar",
                "validacao_llm": None,
            })
    pares.sort(key=lambda p: p["score"], reverse=True)
    return pares


def temas_recorrentes(lista: list[dict], pares: list[dict]) -> list[dict]:
    contador: Counter = Counter()
    por_tema: dict[str, set] = defaultdict(set)
    for n in lista:
        for p in n.get("palavras_chave", []):
            tema = str(p).lower().strip()
            if tema:
                contador[tema] += 1
                por_tema[tema].add(n["id"])
    for par in pares:
        for motivo in par["motivos"]:
            if motivo.startswith("palavras-chave: "):
                for tema in motivo[len("palavras-chave: "):].split(", "):
                    por_tema[tema].update([par["a"], par["b"]])
    temas = []
    for tema, total in contador.most_common(30):
        ids = sorted(por_tema[tema])
        if len(ids) >= 2:
            temas.append({"tema": tema, "notas": ids[:20], "score": total,
                          "tags_sugeridas": [f"tema/{tema.replace(' ', '-')}"]})
    return temas


def validar_com_llm(pares: list[dict], por_id: dict[str, dict], modelo: str, timeout: int) -> dict[str, str]:
    itens = []
    for p in pares:
        a, b = por_id[p["a"]], por_id[p["b"]]
        itens.append({
            "a": p["a"], "b": p["b"], "score": p["score"], "motivos": p["motivos"],
            "nota_a": {"categoria": a.get("categoria"), "resumo": a.get("resumo"), "palavras": a.get("palavras_chave")},
            "nota_b": {"categoria": b.get("categoria"), "resumo": b.get("resumo"), "palavras": b.get("palavras_chave")},
        })
    prompt = (
        "Você valida conexões candidatas entre notas pessoais.\n"
        'Responda um objeto JSON onde cada chave é "A|B" (os dois IDs) e o valor é uma frase curta '
        "dizendo se a conexão faz sentido e por quê. Não invente fatos; use só os dados abaixo.\n\n"
        f"Pares:\n{json.dumps(itens, ensure_ascii=False)}\n"
    )
    resposta = llm.chamar_ollama(prompt, modelo, timeout, num_predict=1200)
    dados = llm.extrair_json(resposta)
    if not dados:
        raise llm.LLMIndisponivel("validação LLM devolveu JSON inválido")
    return {str(k): str(v) for k, v in dados.items()}


def relatorio_conexoes(pares: list[dict], por_id: dict[str, dict], modelo_emb: str, modelo_llm: str,
                       aviso: str | None) -> str:
    linhas = [
        "---", f"date: {datetime.now():%Y-%m-%d}", "tipo: conexoes",
        f"modelo-embedding: {modelo_emb}", f"modelo-llm: {modelo_llm}",
        f"notas-analisadas: {len(por_id)}", f"pares-candidatos: {len(pares)}", "---", "",
        "# Conexões sugeridas", "",
    ]
    if aviso:
        linhas += [f"> [!warning] {aviso}", ""]
    linhas += ["## Pares de notas", ""]
    for p in pares:
        a, b = por_id[p["a"]], por_id[p["b"]]
        linhas.append(f"- [[{p['a']}]] <-> [[{p['b']}]] | score {p['score']:.3f} | {p['status']}")
        linhas.append(f"  - Motivos: {'; '.join(p['motivos'])}")
        if p.get("validacao_llm"):
            linhas.append(f"  - Validação local: {p['validacao_llm']}")
        linhas.append(f"  - Contexto: {a.get('categoria')} / {b.get('categoria')}")
    linhas += ["", "## Próximas decisões", "",
               "- Marcar quais pares devem virar conexão permanente.",
               "- Transformar temas fortes em tags hierárquicas só depois de revisar.", ""]
    return notas.marcar_wikilinks_invalidos("\n".join(linhas), set(por_id))


def relatorio_temas(temas: list[dict], modelo_emb: str, modelo_llm: str, n_notas: int) -> str:
    linhas = [
        "---", f"date: {datetime.now():%Y-%m-%d}", "tipo: temas",
        f"modelo-embedding: {modelo_emb}", f"modelo-llm: {modelo_llm}",
        f"notas-analisadas: {n_notas}", f"temas-candidatos: {len(temas)}", "---", "",
        "# Temas recorrentes", "",
    ]
    for t in temas:
        links = ", ".join(f"[[{i}]]" for i in t["notas"][:10])
        linhas += [f"## {t['tema']}", f"- Score: {t['score']}",
                   f"- Tags sugeridas: `{', '.join(t['tags_sugeridas'])}`", f"- Notas: {links}", ""]
    return "\n".join(linhas).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera conexões revisáveis a partir do índice local.")
    parser.add_argument("--pasta", default=None, help="Vault (padrão: GV_VAULT)")
    parser.add_argument("--cache-dir", default=None, help="Cache (padrão: GV_CACHE/conexoes)")
    parser.add_argument("--modelo", default=None, help="Modelo Ollama de validação (padrão: GV_LLM_MODEL)")
    parser.add_argument("--min-score", type=float, default=0.55)
    parser.add_argument("--max-pares", type=int, default=80)
    parser.add_argument("--validar-llm", type=int, default=25, help="Quantos pares enviar ao LLM")
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--dry-run", action="store_true", help="Mostra contagens sem gravar")
    parser.add_argument("--sem-llm", action="store_true", help="Não chama o LLM")
    args = parser.parse_args()

    vault = Path(args.pasta).expanduser().resolve() if args.pasta else config.vault()
    cache_dir = Path(args.cache_dir).expanduser().resolve() if args.cache_dir else config.cache() / "conexoes"
    modelo = args.modelo or config.llm_modelo()
    if not vault.exists():
        print(f"Erro: vault não encontrado: {vault}", file=sys.stderr)
        sys.exit(1)

    try:
        lista = ler_jsonl(cache_dir / "notas.jsonl")
        embeddings = {e["id"]: e for e in ler_jsonl(cache_dir / "embeddings.jsonl")}
    except FileNotFoundError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
    manifest = json.loads((cache_dir / "manifest.json").read_text(encoding="utf-8")) if (cache_dir / "manifest.json").exists() else {}
    modelo_emb = manifest.get("embedding_model", config.embed_modelo())

    por_id = {n["id"]: n for n in lista if n["id"] in embeddings}
    pares = pontuar_pares(list(por_id.values()), embeddings, args.min_score)[:args.max_pares]
    temas = temas_recorrentes(list(por_id.values()), pares)

    print(f"Notas no cache: {len(por_id)}\nPares candidatos: {len(pares)}\nTemas candidatos: {len(temas)}")
    if args.dry_run:
        for p in pares[:10]:
            print(f"- {p['a']} <-> {p['b']} score={p['score']:.3f}")
        return

    aviso = None
    rotulo_llm = "sem-llm" if args.sem_llm else modelo
    if not args.sem_llm and pares and args.validar_llm > 0:
        try:
            validacoes = validar_com_llm(pares[:args.validar_llm], por_id, modelo, args.timeout)
            for p in pares:
                p["validacao_llm"] = validacoes.get(f"{p['a']}|{p['b']}")
        except (llm.LLMIndisponivel, llm.LLMTimeout) as exc:
            aviso = f"{exc}; mantendo proposta determinística."
            print(f"[aviso] {aviso}", file=sys.stderr)

    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "propostas.json").write_text(json.dumps({
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "embedding_model": modelo_emb, "llm_model": rotulo_llm,
        "notes_count": len(por_id), "pairs": pares, "themes": temas,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = config.conexoes(vault)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    (out / f"conexoes-{stamp}.md").write_text(relatorio_conexoes(pares, por_id, modelo_emb, rotulo_llm, aviso), encoding="utf-8")
    (out / f"temas-{stamp}.md").write_text(relatorio_temas(temas, modelo_emb, rotulo_llm, len(por_id)), encoding="utf-8")
    print(f"[ok] propostas: {cache_dir / 'propostas.json'}")
    print(f"[ok] relatórios em {out}")


if __name__ == "__main__":
    main()

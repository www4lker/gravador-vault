"""indexar.py — Índice local do vault com embeddings via Ollama.

Lê as notas (frontmatter, tags, categoria, resumo, palavras-chave e um trecho
da transcrição), gera um vetor por nota com o modelo de embeddings e grava em
GV_CACHE/conexoes/. Só recalcula notas cujo conteúdo mudou (hash).

Nada é escrito no vault.

Uso:
  indexar.py --dry-run --limite 20
  indexar.py --limite 20
  indexar.py --rebuild
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

from comum import config, llm, notas

MAX_TEXTO_EMBEDDING = 6000
TRECHO_TRANSCRICAO = 3500


def sha256(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def ler_jsonl(path: Path) -> dict[str, dict]:
    itens: dict[str, dict] = {}
    if not path.exists():
        return itens
    with path.open("r", encoding="utf-8") as fh:
        for linha in fh:
            linha = linha.strip()
            if linha:
                item = json.loads(linha)
                itens[str(item["id"])] = item
    return itens


def escrever_jsonl(path: Path, itens: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for item in itens:
            fh.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def ler_nota(path: Path, vault: Path) -> dict | None:
    texto = path.read_text(encoding="utf-8")
    fm, corpo = notas.ler_texto(texto)
    if not fm:
        return None
    transcricao = notas.extrair_transcricao(corpo) or corpo.strip()
    resumo = str(fm.get("llm-resumo") or "").strip()
    palavras = notas.normalizar_lista(fm.get("llm-palavras-chave"))
    tags = notas.normalizar_lista(fm.get("tags"))
    categoria = fm.get("categoria") or fm.get("llm-categoria-sugerida") or path.parent.name

    texto_embedding = "\n".join(p for p in [
        f"ID: {path.stem}",
        f"Categoria: {categoria}",
        f"Tags: {', '.join(tags)}" if tags else "",
        f"Palavras-chave: {', '.join(palavras)}" if palavras else "",
        f"Resumo: {resumo}" if resumo else "",
        f"Transcrição: {transcricao[:TRECHO_TRANSCRICAO]}" if transcricao else "",
    ] if p)

    return {
        "id": path.stem,
        "path": path.relative_to(vault).as_posix(),
        "pasta": path.parent.name,
        "date": str(fm.get("date") or ""),
        "categoria": str(categoria or ""),
        "tags": tags,
        "palavras_chave": palavras,
        "resumo": resumo,
        "amostra": transcricao[:500].replace("\n", " ").strip(),
        "texto_embedding": texto_embedding[:MAX_TEXTO_EMBEDDING],
        "mtime": path.stat().st_mtime,
        "hash": sha256(texto),
    }


def listar(vault: Path, limite: int | None) -> list[Path]:
    paths = list(notas.listar_notas(vault).values())
    return paths[:limite] if limite else paths


def pendentes(notas_lidas: list[dict], anteriores: dict[str, dict], modelo: str) -> list[dict]:
    return [
        n for n in notas_lidas
        if n["id"] not in anteriores
        or anteriores[n["id"]].get("hash") != n["hash"]
        or anteriores[n["id"]].get("modelo") != modelo
    ]


def indexar(vault: Path, cache_dir: Path, limite: int | None, modelo: str, timeout: int,
            rebuild: bool, dry_run: bool, log=print) -> dict:
    paths = listar(vault, limite)
    lidas = [n for p in paths if (n := ler_nota(p, vault))]
    emb_path = cache_dir / "embeddings.jsonl"
    anteriores = {} if rebuild else ler_jsonl(emb_path)
    pend = pendentes(lidas, anteriores, modelo)

    log(f"Vault: {vault}")
    log(f"Notas encontradas: {len(lidas)}")
    log(f"Embeddings pendentes: {len(pend)}")
    log(f"Cache: {cache_dir}")
    if dry_run:
        for n in pend[:20]:
            log(f"- {n['id']} {n['path']}")
        return {"notas": len(lidas), "pendentes": len(pend), "gravado": False}

    cache_dir.mkdir(parents=True, exist_ok=True)
    novos = []
    for i, n in enumerate(lidas, 1):
        ant = anteriores.get(n["id"])
        if ant and ant.get("hash") == n["hash"] and ant.get("modelo") == modelo:
            novos.append(ant)
            continue
        log(f"[{i}/{len(lidas)}] embedding {n['id']}")
        vetor = llm.embedding(n["texto_embedding"], modelo, timeout)
        novos.append({"id": n["id"], "path": n["path"], "hash": n["hash"], "mtime": n["mtime"],
                      "modelo": modelo, "embedding": vetor})

    publicas = [{k: v for k, v in n.items() if k != "texto_embedding"} for n in lidas]
    escrever_jsonl(cache_dir / "notas.jsonl", publicas)
    escrever_jsonl(emb_path, novos)
    (cache_dir / "manifest.json").write_text(json.dumps({
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "vault": str(vault),
        "embedding_model": modelo,
        "notes_count": len(lidas),
        "embeddings_count": len(novos),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(f"[ok] índice em {cache_dir}")
    return {"notas": len(lidas), "pendentes": len(pend), "gravado": True}


def main() -> None:
    parser = argparse.ArgumentParser(description="Indexa notas do vault com embeddings locais (Ollama).")
    parser.add_argument("--pasta", default=None, help="Vault (padrão: GV_VAULT)")
    parser.add_argument("--cache-dir", default=None, help="Cache (padrão: GV_CACHE/conexoes)")
    parser.add_argument("--limite", type=int, default=None, help="Máximo de notas (para testar)")
    parser.add_argument("--modelo-embedding", default=None, help="Modelo Ollama (padrão: GV_EMBED_MODEL)")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--rebuild", action="store_true", help="Recalcula todos os embeddings")
    parser.add_argument("--dry-run", action="store_true", help="Lista o que seria indexado, sem chamar Ollama")
    args = parser.parse_args()

    vault = Path(args.pasta).expanduser().resolve() if args.pasta else config.vault()
    cache_dir = Path(args.cache_dir).expanduser().resolve() if args.cache_dir else config.cache() / "conexoes"
    if not vault.exists():
        print(f"Erro: vault não encontrado: {vault}", file=sys.stderr)
        sys.exit(1)
    try:
        indexar(vault, cache_dir, args.limite, args.modelo_embedding or config.embed_modelo(),
                args.timeout, args.rebuild, args.dry_run)
    except llm.LLMIndisponivel as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

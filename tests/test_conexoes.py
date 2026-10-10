import importlib.util
import json
from pathlib import Path

import conectar
import indexar
from comum import notas
from conftest import escrever_nota

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location("aplicar_conexoes", SCRIPTS / "aplicar-conexoes.py")
aplicar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aplicar)


def test_cosine_e_tokens():
    assert abs(conectar.cosine([1, 0], [1, 0]) - 1.0) < 1e-9
    assert conectar.cosine([1, 0], [0, 1]) == 0.0
    assert conectar.cosine([], [1]) == 0.0
    assert conectar.tokens_fortes("A paisagem como memória, sobre a memória") == {"paisagem", "memória"}


def _nota(id_, cat, palavras, resumo, date="2026-06-02"):
    return {"id": id_, "pasta": cat, "categoria": cat, "palavras_chave": palavras, "resumo": resumo, "date": date}


def test_pontuar_pares_ordena_e_marca_forte():
    lista = [
        _nota("1", "NO-ROLE", ["paisagem", "memória"], "paisagem e memória cultural"),
        _nota("2", "NO-ROLE", ["paisagem", "memória"], "memória da paisagem"),
        _nota("3", "RESENHAS", ["cinema"], "um filme ruim", date="2025-01-01"),
    ]
    emb = {"1": {"embedding": [1.0, 0.0]}, "2": {"embedding": [0.99, 0.1]}, "3": {"embedding": [0.0, 1.0]}}
    pares = conectar.pontuar_pares(lista, emb, min_score=0.1)
    assert pares[0]["a"] == "1" and pares[0]["b"] == "2"
    assert pares[0]["status"] == "forte"
    assert any("palavras-chave: memória, paisagem" in m for m in pares[0]["motivos"])
    assert all(p["score"] <= 1.0 for p in pares)
    ids = {(p["a"], p["b"]) for p in pares}
    assert ("1", "3") not in ids and ("2", "3") not in ids


def test_temas_recorrentes():
    lista = [_nota("1", "X", ["café"], ""), _nota("2", "X", ["café", "sono"], ""), _nota("3", "X", ["sono"], "")]
    temas = conectar.temas_recorrentes(lista, [])
    nomes = {t["tema"]: t for t in temas}
    assert set(nomes) == {"café", "sono"}
    assert nomes["café"]["notas"] == ["1", "2"]
    assert nomes["café"]["tags_sugeridas"] == ["tema/café"]


def test_indexar_le_nota_e_dry_run(vault, tmp_path):
    escrever_nota(vault / "00-INBOX", "20260602120000",
                  extra_fm="llm-resumo: Resumo R\nllm-palavras-chave:\n  - paisagem")
    escrever_nota(vault / "NO-ROLE", "20260603070000")
    n = indexar.ler_nota(vault / "00-INBOX" / "20260602120000.md", vault)
    assert n["id"] == "20260602120000" and n["resumo"] == "Resumo R" and n["palavras_chave"] == ["paisagem"]
    assert n["categoria"] == "00-INBOX" and "Transcrição:" in n["texto_embedding"]
    logs = []
    r = indexar.indexar(vault, tmp_path / "cache", None, "fake", 5, False, True, log=logs.append)
    assert r == {"notas": 2, "pendentes": 2, "gravado": False}
    assert not (tmp_path / "cache").exists()


def test_aplicar_insere_bloco_marca_frontmatter_e_nao_duplica(vault):
    a = escrever_nota(vault / "00-INBOX", "20260602120000")
    b = escrever_nota(vault / "NO-ROLE", "20260603070000")
    propostas = {
        "generated_at": "2026-07-01T10:00:00",
        "pairs": [
            {"a": "20260602120000", "b": "20260603070000", "score": 0.8, "status": "forte", "motivos": ["similaridade 0.9"]},
            {"a": "20260602120000", "b": "99999999999999", "score": 0.9, "status": "forte", "motivos": []},
            {"a": "20260602120000", "b": "20260603070000", "score": 0.95, "status": "revisar", "motivos": []},
        ],
    }
    blocos = aplicar.montar_blocos(propostas, 0.72, 3)
    # o par com ID inexistente entra no plano mas é barrado na validação de wikilinks
    assert set(blocos) == {"20260602120000", "20260603070000", "99999999999999"}
    avisos = []
    alteradas = aplicar.planejar(vault, propostas, 0.72, 3, log=avisos.append)
    assert {p.name for p, _ in alteradas} == {"20260602120000.md", "20260603070000.md"}
    assert any("nota ausente: 99999999999999" in m for m in avisos)
    assert any("links para IDs inexistentes descartados: 99999999999999" in m for m in avisos)
    for path, novo in alteradas:
        path.write_text(novo, encoding="utf-8")

    texto = a.read_text(encoding="utf-8")
    assert texto.index("> [!info]- Conexões locais") < texto.index("## Transcrição")
    assert "[[20260603070000]] — score 0.800" in texto
    assert "[[99999999999999]]" not in texto
    fm, corpo = notas.ler_texto(texto)
    assert fm["conexoes-locais"] == "2026-07-01T10:00:00"
    assert fm["title"] == "20260602120000"
    assert notas.extrair_transcricao(corpo).startswith("Dois de junho")

    # segunda aplicação: substitui o bloco, não duplica
    propostas["generated_at"] = "2026-08-01T10:00:00"
    for path, novo in aplicar.planejar(vault, propostas, 0.72, 3, log=avisos.append):
        path.write_text(novo, encoding="utf-8")
    texto2 = a.read_text(encoding="utf-8")
    assert texto2.count("> [!info]- Conexões locais") == 1
    assert texto2.count("conexoes-locais:") == 1
    assert "2026-08-01T10:00:00" in texto2 and "2026-07-01T10:00:00" not in texto2


def test_aplicar_apply_plan_de_rodada(vault):
    escrever_nota(vault / "00-INBOX", "20260602120000")
    escrever_nota(vault / "NO-ROLE", "20260603070000")
    propostas = {"generated_at": "x", "apply_plan": [{
        "id": "20260602120000", "themes": ["café"], "axes": ["categoria: X"],
        "candidate_links": [{"target": "20260603070000", "score": 0.9, "reason": "r"}],
    }]}
    alteradas = aplicar.planejar(vault, propostas, 0.72, 3, log=lambda m: None)
    assert len(alteradas) == 1
    assert "> **Temas:** café" in alteradas[0][1] and "> - categoria: X" in alteradas[0][1]


def test_relatorio_marca_wikilinks_invalidos():
    por_id = {"1": _nota("1", "X", [], ""), "2": _nota("2", "X", [], "")}
    pares = [{"a": "1", "b": "2", "score": 0.8, "status": "forte", "motivos": ["m"], "validacao_llm": "faz sentido"}]
    rel = conectar.relatorio_conexoes(pares, por_id, "emb", "llm", None)
    assert "[[1]] <-> [[2]]" in rel and "Validação local: faz sentido" in rel
    assert "ID não encontrado" not in rel

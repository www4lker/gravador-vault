from pathlib import Path

from comum import notas
from conftest import NOTA_EXEMPLO, TRANSCRICAO_OK


def test_ler_e_extrair_transcricao(tmp_path):
    p = tmp_path / "20260602120000.md"
    p.write_text(NOTA_EXEMPLO.format(modelo="small", transcricao=TRANSCRICAO_OK), encoding="utf-8")
    fm, corpo = notas.ler(p)
    assert fm["title"] == "20260602120000"
    assert fm["modelo"] == "small"
    assert fm["categoria"] is None
    assert notas.extrair_transcricao(corpo) == TRANSCRICAO_OK


def test_ler_sem_frontmatter(tmp_path):
    p = tmp_path / "x.md"
    p.write_text("## Transcrição\n\noi oi oi\n", encoding="utf-8")
    fm, corpo = notas.ler(p)
    assert fm == {}
    assert notas.extrair_transcricao(corpo) == "oi oi oi"


def test_sanitiza_origem_windows():
    texto = '---\ntitle: "x"\norigem: "C:\\Users\\alguem\\RECORD\\x.WAV"\n---\n\n## Transcrição\n\nabc\n'
    fm, _ = notas.ler_texto(texto)
    assert fm["origem"] == "C:/Users/alguem/RECORD/x.WAV"


def test_frontmatter_invalido_vira_vazio():
    fm, corpo = notas.ler_texto("---\n: : :\n  - [\n---\n\n## Transcrição\n\nabc\n")
    assert fm == {}
    assert "abc" in corpo


def test_serializar_ordem_e_tags_por_ultimo():
    fm = {"tags": ["a"], "llm-resumo": "r", "title": "t", "date": "2026-06-02", "campo-novo": 1}
    s = notas.serializar_frontmatter(fm, ordem_extra=["llm-resumo"])
    linhas = s.splitlines()
    assert linhas[0] == "---" and linhas[-1] == "---"
    assert linhas.index("title: t") < linhas.index("date: '2026-06-02'") < linhas.index("llm-resumo: r")
    assert linhas.index("campo-novo: 1") < linhas.index("tags:")


def test_inserir_antes_transcricao_nao_toca_na_transcricao():
    corpo = "\n\n## Transcrição\n\ntexto original\n\n---\n*Observações:*\n"
    novo = notas.inserir_antes_transcricao(corpo, "> [!tip]- bloco")
    assert novo.index("> [!tip]- bloco") < novo.index("## Transcrição")
    assert "texto original" in novo
    assert novo.count("## Transcrição") == 1


def test_inserir_sem_marcador_vai_para_o_fim():
    assert notas.inserir_antes_transcricao("corpo sem secao\n", "> b").endswith("> b\n")


def test_nome_unico(tmp_path):
    (tmp_path / "a.md").write_text("x")
    (tmp_path / "a_2.md").write_text("x")
    assert notas.nome_unico(tmp_path, "a").name == "a_3.md"
    assert notas.nome_unico(tmp_path, "b").name == "b.md"


def test_listar_notas_ignora_pastas_de_sistema_e_nao_ids(tmp_path):
    for rel in ("00-INBOX/20260602120000.md", "NO-ROLE/20260603070000.md", "01-BASES/x.md",
                ".obsidian/y.md", "_conexoes/20260604000000.md", "00-INBOX/rascunho.md"):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("---\ntitle: a\n---\n")
    ids = notas.listar_notas(tmp_path)
    assert set(ids) == {"20260602120000", "20260603070000"}
    todos = notas.stems_existentes(tmp_path)
    assert "rascunho" in todos and "x" not in todos and "y" not in todos


def test_wikilinks():
    texto = "ver [[20260602120000]] e [[inexistente]] e [[20260602120000|alias]]"
    assert notas.wikilinks_invalidos(texto, {"20260602120000"}) == ["inexistente"]
    marcado = notas.marcar_wikilinks_invalidos(texto, {"20260602120000"})
    assert "`[[inexistente]]` (ID não encontrado; revisar)" in marcado
    assert "[[20260602120000|alias]]" in marcado

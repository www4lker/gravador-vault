import json
from pathlib import Path

import pytest
import yaml

from comum import categorias

RAIZ = Path(__file__).resolve().parents[1]
YAML = RAIZ / "config" / "categorias.yaml"


@pytest.fixture
def tax():
    return categorias.carregar(YAML)


def test_carrega_todas(tax):
    assert tax.fallback == "INBOX"
    assert set(tax.nomes) >= {"INBOX", "NO-ROLE", "RESENHAS", "PRE-TEXTO", "ENTREVISTA", "SONHEI-ESSA-NOITE"}
    assert "00-INBOX" in tax.pastas_vault and "INBOX" not in tax.pastas_vault
    assert "NO-ROLE" in tax.pastas_vault


def test_inferir_pela_pasta_depois_frontmatter_depois_fallback(tax):
    assert tax.inferir(Path("/v/RESENHAS/x.md"), {}) == "RESENHAS"
    assert tax.inferir(Path("/v/00-INBOX/x.md"), {"categoria": "no-role"}) == "NO-ROLE"
    assert tax.inferir(Path("/v/00-INBOX/x.md"), {"categoria": "inexistente"}) == "INBOX"
    assert tax.inferir(Path("/v/00-INBOX/x.md"), {}) == "INBOX"


def test_esquema_substitui_token_e_coesao(tax):
    esquema = tax.esquema_json("INBOX", "small")
    assert "NO-ROLE|" in esquema["categoria_sugerida"]
    assert "INBOX" not in esquema["categoria_sugerida"]
    assert "coesao" in esquema
    assert "coesao" not in tax.esquema_json("INBOX", "medium")
    # sonhos nunca pedem coesão, mesmo com modelo rápido
    assert "coesao" not in tax.esquema_json("SONHEI-ESSA-NOITE", "small")


def test_build_prompt_contem_instrucao_e_json_valido(tax):
    prompt = tax.build_prompt("texto da transcrição", "small", "PRE-TEXTO")
    assert "robustez argumentativa" in prompt
    assert "texto da transcrição" in prompt
    inicio, fim = prompt.index("{"), prompt.rindex("}") + 1
    esquema = json.loads(prompt[inicio:fim])
    assert "estrutura_argumentativa" in esquema and "coesao" in esquema


def test_truncar():
    t = categorias.truncar("a" * 10_000, limite=100)
    assert t.startswith("a" * 100) and "TRUNCADA" in t


def test_callout_pre_texto_renderiza_dict_e_codigo(tax):
    dados = {
        "palavras_chave": ["atmosfera", "paisagem"],
        "resumo": "Resumo aqui.",
        "estrutura_argumentativa": {"premissa": "P", "tese": "T", "objecao_interna": "", "veredito_provisorio": "V"},
        "status_argumento": "hipotese",
        "perguntas_abertas": ["Q1"],
        "instrucoes_para_si": [],
        "coesao": {"avaliacao": "fragmentada", "confianca": 6, "observacoes": "cortes"},
    }
    c = tax.formatar_callout(dados, "PRE-TEXTO", "small", "Ollama")
    assert c.startswith("> [!abstract]- Análise Ollama · PRE-TEXTO")
    assert "> **Resumo:** Resumo aqui." in c
    assert "> - Premissa: P" in c and "Objeção interna" not in c
    assert "> **Status:** `hipotese`" in c
    assert "> **Palavras-chave:** atmosfera · paisagem" in c
    assert "> - Q1" in c
    assert "Instruções para si" not in c
    assert "[!warning] Coesão: fragmentada (6/10)" in c
    assert all(l.startswith(">") or l == "" for l in c.splitlines())


def test_callout_sem_aviso_de_coesao_para_modelo_medium(tax):
    dados = {"resumo": "r", "coesao": {"avaliacao": "re-transcrever", "confianca": 2}}
    assert "Coesão" not in tax.formatar_callout(dados, "NO-ROLE", "medium", "Ollama")


def test_callout_parse_error(tax):
    c = tax.formatar_callout({"_parse_error": True, "_raw": "blá\nblé"}, "NO-ROLE", "small", "Gemini")
    assert "Erro ao interpretar" in c and "> blá" in c and "> blé" in c


def test_atualizar_frontmatter_mapeia_llm(tax):
    fm = {"title": "x"}
    dados = {"palavras_chave": ["a"], "resumo": "R", "status_argumento": "aberto", "perguntas_abertas": []}
    fm = tax.atualizar_frontmatter(fm, dados, "PRE-TEXTO")
    assert fm["llm-palavras-chave"] == ["a"]
    assert fm["llm-resumo"] == "R"
    assert fm["llm-status-argumento"] == "aberto"
    assert "llm-perguntas-abertas" not in fm
    # resumo fenomenológico também vira llm-resumo
    fm2 = tax.atualizar_frontmatter({}, {"resumo_fenomenologico": "F"}, "INSIGHTS-MEDITACAO")
    assert fm2["llm-resumo"] == "F"
    # resenhas: argumento central vira resumo
    fm3 = tax.atualizar_frontmatter({}, {"argumento_central": "AC"}, "RESENHAS")
    assert fm3["llm-resumo"] == "AC"


def test_propriedades_llm_estaveis(tax):
    props = tax.propriedades_llm()
    assert props[0] == "llm-qualidade-transcricao"
    assert "llm-status-argumento" in props and "llm-modo-inferido" in props
    assert len(props) == len(set(props))


def test_yaml_customizado(tmp_path):
    custom = {
        "fallback": "CAIXA",
        "categorias": {
            "CAIXA": {"callout": "question", "instrucao": "Resuma.", "campos": {"resumo": "..."},
                      "secoes": [{"campo": "resumo", "rotulo": "Resumo", "tipo": "texto"}]},
            "AULA": {"callout": "info", "instrucao": "Aula.", "campos": {"topicos": ["..."]},
                     "frontmatter": {"topicos": "llm-topicos"},
                     "secoes": [{"campo": "topicos", "rotulo": "Tópicos", "tipo": "lista"}]},
        },
    }
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump(custom, allow_unicode=True, sort_keys=False), encoding="utf-8")
    tax = categorias.carregar(p)
    assert tax.nomes == ["CAIXA", "AULA"]
    assert tax.pastas_vault == ["00-INBOX", "01-BASES", "_conexoes", "AULA"]
    c = tax.formatar_callout({"topicos": ["x", "y"]}, "AULA", "medium", "Ollama")
    assert "> - x" in c and "> - y" in c
    assert tax.atualizar_frontmatter({}, {"topicos": ["x"]}, "AULA") == {"llm-topicos": ["x"]}


def test_fallback_invalido(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("fallback: NAO\ncategorias:\n  A: {}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        categorias.carregar(p)

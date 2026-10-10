from comum import alucinacao
from conftest import TRANSCRICAO_OK


def test_ok():
    r = alucinacao.detectar(TRANSCRICAO_OK)
    assert r["qualidade"] == "ok"
    assert r["ratio_unicidade"] > 0.5


def test_vazia():
    assert alucinacao.detectar("oi tudo bem")["qualidade"] == "vazia"


def test_padrao_repetido():
    texto = " ".join(["obrigado por assistir"] * 15) + " e algumas palavras diferentes aqui"
    r = alucinacao.detectar(texto)
    assert r["qualidade"] == "alucinada"
    assert "obrigado por assistir" in r["motivo"]


def test_urls():
    texto = "visite www.exemplo.com e www.outro.org e https://x.br agora " * 2
    assert alucinacao.detectar(texto)["qualidade"] == "alucinada"


def test_unicidade_baixa_suspeita():
    # 10% de palavras únicas: suspeita, não alucinada
    texto = " ".join(["palavra"] * 90 + [f"outra{i}" for i in range(10)])
    assert alucinacao.detectar(texto)["qualidade"] == "suspeita"


def test_unicidade_quase_zero_alucinada():
    texto = " ".join(["tchau"] * 200 + ["fim"])
    assert alucinacao.detectar(texto)["qualidade"] == "alucinada"


def test_marcador_final():
    assert alucinacao.detectar_marcador_final(TRANSCRICAO_OK) == "forte"
    assert alucinacao.detectar_marcador_final("nada a ver aqui.") is None
    assert alucinacao.detectar_marcador_final("isso precisa... desenvolver!") == "desenvolver"
    assert alucinacao.detectar_marcador_final("é raso.", marcadores=("ok",)) is None

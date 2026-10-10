"""Ponta a ponta sem modelos: um servidor HTTP falso faz o papel do Ollama.

Cobre: transcrever --dry-run, enriquecer (ok, alucinada, já-enriquecida, --force),
indexar → conectar → aplicar-conexoes com embeddings falsos, e a Base de triagem.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from comum import notas
from conftest import TRANSCRICAO_OK, escrever_nota

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "scripts"


class FakeOllama(BaseHTTPRequestHandler):
    """Responde /api/generate com JSON fixo e /api/embed com vetores determinísticos."""

    pedidos: list[dict] = []

    def log_message(self, *a):  # silencia
        pass

    def do_GET(self):
        if self.path == "/api/tags":
            self._json({"models": [{"name": "fake-llm"}, {"name": "fake-emb"}]})
        else:
            self.send_error(404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(n) or b"{}")
        FakeOllama.pedidos.append({"path": self.path, **payload})
        if self.path == "/api/generate":
            prompt = payload.get("prompt", "")
            assert payload.get("think") is False
            if "valida conexões" in prompt.lower():
                self._json({"response": json.dumps({"20260602120000|20260603070000": "ambas tratam de paisagem"})})
                return
            resposta = {
                "palavras_chave": ["paisagem", "memória", "atmosfera"],
                "resumo": "Reflexão sobre paisagem e memória na geografia cultural.",
                "categoria_sugerida": "NO-ROLE",
                "perguntas_abertas": ["A atmosfera é anterior à representação?"],
                "instrucoes_para_si": ["Reler o capítulo sobre topofilia"],
                "coesao": {"avaliacao": "boa", "confianca": 9, "observacoes": None},
            }
            self._json({"response": json.dumps(resposta, ensure_ascii=False)})
        elif self.path == "/api/embed":
            texto = payload.get("input", "")
            # notas que falam de paisagem ficam próximas; a de cinema longe
            v = [1.0, 0.05] if "paisagem" in texto.lower() else [0.0, 1.0]
            self._json({"embeddings": [v]})
        else:
            self.send_error(404)

    def _json(self, obj):
        corpo = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)


@pytest.fixture
def ollama(monkeypatch):
    FakeOllama.pedidos = []
    srv = HTTPServer(("127.0.0.1", 0), FakeOllama)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    monkeypatch.setenv("GV_OLLAMA_URL", url)
    monkeypatch.setenv("GV_LLM_MODEL", "fake-llm")
    monkeypatch.setenv("GV_EMBED_MODEL", "fake-emb")
    yield url
    srv.shutdown()


def run(script: str, *args: str, esperado: int = 0) -> subprocess.CompletedProcess:
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True,
                       encoding="utf-8", timeout=120)
    assert r.returncode == esperado, f"{script} {args}\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}"
    return r


def test_help_de_todos_os_scripts():
    for s in ("organizar.py", "transcrever.py", "transcrever-gradual.py", "enriquecer.py",
              "indexar.py", "conectar.py", "aplicar-conexoes.py", "rodada.py"):
        r = run(s, "--help")
        assert "usage" in r.stdout.lower() or "uso" in r.stdout.lower()


def test_sem_gv_vault_erro_acionavel(monkeypatch, tmp_path):
    monkeypatch.delenv("GV_VAULT", raising=False)
    monkeypatch.setenv("GV_RECORD", str(tmp_path))
    r = run("transcrever.py", "--dry-run", esperado=2)
    assert "GV_VAULT" in r.stderr and "vault-template" in r.stderr


def test_transcrever_dry_run_cria_pastas_e_lista(vault, record):
    dia = record / "2026-06-02"
    dia.mkdir()
    (dia / "20260602120000.WAV").write_bytes(b"RIFF")
    (dia / "20260602121500.WAV").write_bytes(b"RIFF")
    (dia / "transcrito").mkdir()
    (dia / "transcrito" / "20260601000000.WAV").write_bytes(b"RIFF")
    escrever_nota(vault / "00-INBOX", "20260602121500")  # já tem nota → ignorado

    r = run("transcrever.py", "--dry-run")
    assert "1 áudio(s) pendente(s)" in r.stdout
    assert "2026-06-02/20260602120000.WAV" in r.stdout
    assert "1 ignorado(s)" in r.stdout
    assert "20260601000000" not in r.stdout  # transcrito/ é ignorado
    assert (vault / "NO-ROLE").is_dir() and (vault / "01-BASES").is_dir()
    assert (dia / "20260602120000.WAV").exists()  # nada movido

    r = run("transcrever.py", "--mostrar-config")
    assert "GV_VAULT" in r.stdout and str(vault) in r.stdout


def test_enriquecer_ok_e_idempotente(vault, ollama):
    nota = escrever_nota(vault / "00-INBOX", "20260602120000")
    r = run("enriquecer.py")
    assert "ok=1" in r.stdout
    texto = nota.read_text(encoding="utf-8")
    fm, corpo = notas.ler_texto(texto)
    assert fm["llm-palavras-chave"] == ["paisagem", "memória", "atmosfera"]
    assert fm["llm-resumo"].startswith("Reflexão")
    assert fm["llm-categoria-sugerida"] == "NO-ROLE"
    assert fm["marcador-final"] == "forte"
    assert fm["tags"] == ["gravador", "inbox"]
    assert "> [!question]- Análise Ollama · INBOX" in corpo
    assert "> **Categoria sugerida:** `NO-ROLE`" in corpo
    assert corpo.index("Análise Ollama") < corpo.index("## Transcrição")
    assert notas.extrair_transcricao(corpo) == TRANSCRICAO_OK
    assert "*Observações:*" in corpo
    assert (vault / "01-BASES" / "_triagem.base").exists()
    # o prompt enviado é o da categoria INBOX com coesão (modelo small)
    gen = [p for p in FakeOllama.pedidos if p["path"] == "/api/generate"]
    assert len(gen) == 1 and "coesao" in gen[0]["prompt"] and gen[0]["format"] == "json"

    # segunda rodada: nada muda
    FakeOllama.pedidos = []
    r = run("enriquecer.py")
    assert "ja-enriquecida=1" in r.stdout and not FakeOllama.pedidos
    assert nota.read_text(encoding="utf-8") == texto

    # --force: remove e refaz, sem duplicar callout
    r = run("enriquecer.py", "--force")
    assert "ok=1" in r.stdout
    t2 = nota.read_text(encoding="utf-8")
    assert t2.count("Análise Ollama") == 1
    assert t2.count("## Transcrição") == 1


def test_enriquecer_categoria_pela_pasta(vault, ollama):
    escrever_nota(vault / "PRE-TEXTO", "20260603070000", modelo="medium")
    run("enriquecer.py", str(vault / "PRE-TEXTO"))
    texto = (vault / "PRE-TEXTO" / "20260603070000.md").read_text(encoding="utf-8")
    assert "> [!abstract]- Análise Ollama · PRE-TEXTO" in texto
    gen = [p for p in FakeOllama.pedidos if p["path"] == "/api/generate"][0]
    assert "robustez argumentativa" in gen["prompt"] and "coesao" not in gen["prompt"]


def test_enriquecer_alucinada_nao_chama_llm(vault, ollama):
    nota = escrever_nota(vault / "00-INBOX", "20260602120000",
                         transcricao=" ".join(["obrigado por assistir"] * 20) + " tchau tchau tchau")
    r = run("enriquecer.py")
    assert "alucinada=1" in r.stdout
    assert not FakeOllama.pedidos
    fm, corpo = notas.ler_texto(nota.read_text(encoding="utf-8"))
    assert fm["llm-qualidade-transcricao"] == "alucinada"
    assert "[!warning] Transcrição alucinada" in corpo


def test_enriquecer_dry_run_nao_grava(vault, ollama):
    nota = escrever_nota(vault / "00-INBOX", "20260602120000")
    antes = nota.read_text(encoding="utf-8")
    r = run("enriquecer.py", "--dry-run")
    assert "dry-run=1" in r.stdout and not FakeOllama.pedidos
    assert nota.read_text(encoding="utf-8") == antes
    assert not (vault / "01-BASES" / "_triagem.base").exists()


def test_enriquecer_ollama_fora_do_ar(vault, monkeypatch):
    monkeypatch.setenv("GV_OLLAMA_URL", "http://127.0.0.1:9")  # porta fechada
    nota = escrever_nota(vault / "00-INBOX", "20260602120000")
    antes = nota.read_text(encoding="utf-8")
    r = run("enriquecer.py", "--timeout", "5")
    assert "erro=1" in r.stdout and "indisponível" in r.stdout
    assert nota.read_text(encoding="utf-8") == antes


def test_fluxo_conexoes_completo(vault, ollama):
    escrever_nota(vault / "00-INBOX", "20260602120000",
                  extra_fm="llm-resumo: paisagem e memória\nllm-palavras-chave: [paisagem, memória]")
    escrever_nota(vault / "NO-ROLE", "20260603070000",
                  extra_fm="llm-resumo: a paisagem como memória\nllm-palavras-chave: [paisagem, memória]")
    escrever_nota(vault / "RESENHAS", "20260604080000",
                  transcricao="Um filme sobre cinema e montagem, nada de geografia. " * 3,
                  extra_fm="llm-resumo: cinema\nllm-palavras-chave: [cinema]")

    r = run("indexar.py", "--dry-run")
    assert "Notas encontradas: 3" in r.stdout and "Embeddings pendentes: 3" in r.stdout
    r = run("indexar.py")
    assert "Embeddings pendentes: 3" in r.stdout
    cache = Path(vault).parent / "cache" / "conexoes"
    assert (cache / "notas.jsonl").exists() and (cache / "embeddings.jsonl").exists()
    manifest = json.loads((cache / "manifest.json").read_text())
    assert manifest["embedding_model"] == "fake-emb" and manifest["notes_count"] == 3

    # segunda indexação: nada pendente (hash igual)
    r = run("indexar.py")
    assert "Embeddings pendentes: 0" in r.stdout

    r = run("conectar.py", "--dry-run", "--min-score", "0.3")
    assert "Pares candidatos: 1" in r.stdout
    r = run("conectar.py", "--min-score", "0.3")
    propostas = json.loads((cache / "propostas.json").read_text(encoding="utf-8"))
    assert len(propostas["pairs"]) == 1
    par = propostas["pairs"][0]
    assert {par["a"], par["b"]} == {"20260602120000", "20260603070000"}
    assert par["status"] == "forte" and par["validacao_llm"] == "ambas tratam de paisagem"
    relatorios = sorted((vault / "_conexoes").glob("*.md"))
    assert len(relatorios) == 2
    rel = (vault / "_conexoes" / relatorios[0].name).read_text(encoding="utf-8")
    assert "tipo: conexoes" in rel and "ID não encontrado" not in rel

    r = run("aplicar-conexoes.py")
    assert "DRY-RUN" in r.stdout and "Notas com bloco novo: 2" in r.stdout
    assert "Conexões locais" not in (vault / "NO-ROLE" / "20260603070000.md").read_text(encoding="utf-8")
    r = run("aplicar-conexoes.py", "--aplicar")
    assert "notas alteradas: 2" in r.stdout
    texto = (vault / "NO-ROLE" / "20260603070000.md").read_text(encoding="utf-8")
    assert "[[20260602120000]]" in texto and "conexoes-locais:" in texto
    assert "Conexões locais" not in (vault / "RESENHAS" / "20260604080000.md").read_text(encoding="utf-8")

    # rodada completa, sem aplicar, usando o mesmo stub
    r = run("rodada.py", "--full", "--min-score", "0.3")
    # as duas notas que receberam bloco mudaram de hash e são re-indexadas; a terceira não
    assert "Embeddings pendentes: 2" in r.stdout
    assert (cache / "propostas-rodada.json").exists()
    assert any(p.name.startswith("rodada-") for p in (vault / "_conexoes").glob("*.md"))
    r = run("rodada.py", "--dry-run", esperado=1)
    assert "--full" in r.stderr

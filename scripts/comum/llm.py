"""Chamadas a modelos de linguagem.

Padrão: Ollama local via HTTP (privacidade, sem custo, sem rede).
Opcional: Gemini CLI, para máquinas sem LLM local. Explícito, nunca automático,
a menos que a fonte seja "auto".

Só a biblioteca padrão. Sem SDKs.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

from . import config


class LLMIndisponivel(RuntimeError):
    """Daemon fora do ar, modelo ausente ou CLI não instalado."""


class LLMTimeout(RuntimeError):
    """A chamada excedeu o timeout."""


# --------------------------------------------------------------------------- #
# Ollama                                                                       #
# --------------------------------------------------------------------------- #

def _post(url: str, payload: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except TimeoutError as exc:
        raise LLMTimeout(f"{url} não respondeu em {timeout}s") from exc
    except urllib.error.HTTPError as exc:
        corpo = exc.read().decode("utf-8", errors="replace")[:300]
        raise LLMIndisponivel(f"HTTP {exc.code} em {url}: {corpo}") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError) or "timed out" in str(exc.reason):
            raise LLMTimeout(f"{url} não respondeu em {timeout}s") from exc
        raise LLMIndisponivel(f"Ollama indisponível em {url}: {exc.reason}") from exc


def chamar_ollama(
    prompt: str,
    modelo: str | None = None,
    timeout: int = 180,
    url: str | None = None,
    json_mode: bool = True,
    num_predict: int | None = None,
    num_ctx: int = 8192,
    temperatura: float = 0.1,
) -> str:
    """Geração não-streaming. `think: false` é obrigatório para modelos com modo
    de raciocínio (Qwen 3.x): sem ele o JSON pode ir para `thinking` e
    `response` voltar vazio."""
    base = (url or config.ollama_url()).rstrip("/")
    payload = {
        "model": modelo or config.llm_modelo(),
        "prompt": f"/no_think\n{prompt}",
        "stream": False,
        "think": False,
        "options": {"temperature": temperatura, "num_ctx": num_ctx},
    }
    if json_mode:
        payload["format"] = "json"
    if num_predict:
        payload["options"]["num_predict"] = num_predict
    body = _post(f"{base}/api/generate", payload, timeout)
    return str(body.get("response") or body.get("thinking") or "").strip()


def embedding(texto: str, modelo: str | None = None, timeout: int = 120, url: str | None = None) -> list[float]:
    """Vetor de embedding. Tenta /api/embed (Ollama ≥ 0.2) e cai para /api/embeddings."""
    base = (url or config.ollama_url()).rstrip("/")
    modelo = modelo or config.embed_modelo()
    try:
        body = _post(f"{base}/api/embed", {"model": modelo, "input": texto}, timeout)
        vetores = body.get("embeddings") or []
        if vetores and isinstance(vetores[0], list):
            return [float(v) for v in vetores[0]]
    except LLMIndisponivel as exc:
        if "HTTP 404" not in str(exc):
            raise
    body = _post(f"{base}/api/embeddings", {"model": modelo, "prompt": texto}, timeout)
    vetor = body.get("embedding") or []
    if not vetor:
        raise LLMIndisponivel("Ollama não retornou embedding")
    return [float(v) for v in vetor]


def listar_modelos(timeout: int = 10, url: str | None = None) -> set[str]:
    base = (url or config.ollama_url()).rstrip("/")
    req = urllib.request.Request(f"{base}/api/tags", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise LLMIndisponivel(f"Ollama indisponível em {base}: {exc.reason}") from exc
    return {str(m.get("name")) for m in body.get("models", [])}


# --------------------------------------------------------------------------- #
# Gemini CLI (opcional)                                                        #
# --------------------------------------------------------------------------- #

def chamar_gemini(prompt: str, timeout: int = 180) -> str:
    """Usa o binário `gemini` autenticado na máquina. Prompt via stdin para
    evitar problemas de quebra de linha no cmd.exe."""
    cmd = ["cmd", "/c", "gemini", "-p", "", "-o", "text"] if sys.platform == "win32" \
        else ["gemini", "-p", "", "-o", "text"]
    try:
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8",
        )
    except FileNotFoundError as exc:
        raise LLMIndisponivel("Gemini CLI não encontrado no PATH") from exc
    try:
        stdout, _ = proc.communicate(input=prompt, timeout=timeout)
        return stdout.strip()
    except subprocess.TimeoutExpired as exc:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        proc.kill()
        proc.wait()
        raise LLMTimeout(f"gemini não respondeu em {timeout}s") from exc


# --------------------------------------------------------------------------- #
# Despacho                                                                     #
# --------------------------------------------------------------------------- #

def chamar(prompt: str, fonte: str | None = None, modelo: str | None = None, timeout: int = 180) -> tuple[str, str]:
    """Retorna (resposta, rótulo_da_fonte). Rótulo entra no título do callout."""
    fonte = fonte or config.llm_fonte()
    if fonte == "gemini":
        return chamar_gemini(prompt, timeout), "Gemini"
    if fonte == "ollama":
        return chamar_ollama(prompt, modelo, timeout), "Ollama"
    if fonte == "auto":
        try:
            return chamar_ollama(prompt, modelo, timeout), "Ollama"
        except LLMIndisponivel as exc:
            print(f"  [auto] Ollama indisponível ({exc}); tentando Gemini...", flush=True)
            return chamar_gemini(prompt, timeout), "Gemini"
    raise ValueError(f"fonte desconhecida: {fonte}")


# --------------------------------------------------------------------------- #
# Parse                                                                        #
# --------------------------------------------------------------------------- #

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def extrair_json(texto: str) -> dict | None:
    """Pega o primeiro objeto JSON da resposta, tolerando markdown em volta."""
    if not texto:
        return None
    candidato = texto.strip()
    if candidato.startswith("```"):
        candidato = re.sub(r"^```[a-zA-Z]*\n?", "", candidato).rstrip("`").strip()
    for tentativa in (candidato, _JSON_RE.search(candidato).group(0) if _JSON_RE.search(candidato) else None):
        if not tentativa:
            continue
        try:
            dados = json.loads(tentativa)
        except json.JSONDecodeError:
            continue
        if isinstance(dados, dict):
            return dados
    return None

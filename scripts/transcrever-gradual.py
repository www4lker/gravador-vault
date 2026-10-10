"""transcrever-gradual.py — Re-transcreve áudios já processados, dia a dia, interativamente.

Para quando a primeira passada usou um modelo rápido e uma nota merece melhor.

Estrutura esperada: RECORD/YYYY-MM-DD/transcrito/*.WAV

Uso:
  transcrever-gradual.py                         # tabela de todos os dias
  transcrever-gradual.py RECORD/2026-06-02       # só um dia
  transcrever-gradual.py --modo sobrescrever     # padrão: sobrescreve a nota
  transcrever-gradual.py --modo novo             # cria _v2, preserva original
  transcrever-gradual.py --modo pular            # pula quem já tem nota
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from comum import config, notas, stt

ANALISE_RE = re.compile(r"Análise [^\n·]+ · ")


# --------------------------------------------------------------------------- #
# Tecla única, cross-platform                                                  #
# --------------------------------------------------------------------------- #

def pedir_tecla(opcoes: str, prompt: str = "") -> str:
    if prompt:
        print(prompt, end="", flush=True)
    if sys.platform == "win32":
        import msvcrt
        while True:
            ch = msvcrt.getwch()
            if ch == "\x03":
                print()
                raise KeyboardInterrupt
            if ch in opcoes:
                print(ch)
                return ch
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch == "\x03":
                print()
                raise KeyboardInterrupt
            if ch in opcoes:
                print(ch)
                return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def modelo_por_tecla(tecla: str) -> str:
    return {"s": "small", "m": "medium", "l": "large-v3"}.get(tecla, "medium")


# --------------------------------------------------------------------------- #
# Coleta                                                                       #
# --------------------------------------------------------------------------- #

def coletar_transcritos(pasta: Path) -> list[Path]:
    """RECORD/ → todos os */transcrito/; RECORD/dia → dia/transcrito/; transcrito/ → ele mesmo."""
    wavs: list[Path] = []
    for sub in sorted(p for p in pasta.iterdir() if p.is_dir() and not p.name.startswith("_")):
        t = sub / "transcrito"
        if t.is_dir():
            wavs += stt.glob_audio(t)
    if wavs:
        return wavs
    t = pasta / "transcrito"
    if t.is_dir():
        return stt.glob_audio(t)
    return stt.glob_audio(pasta)


def agrupar_por_dia(wavs: list[Path]) -> dict[str, list[Path]]:
    grupos: dict[str, list[Path]] = defaultdict(list)
    for w in wavs:
        chave = w.stem[:8] if stt.data_do_nome(w.stem) else "outros"
        grupos[chave].append(w)
    return dict(sorted(grupos.items()))


def data_legivel(chave: str) -> str:
    try:
        return datetime.strptime(chave, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return chave


def nota_tem_analise(nota: Path) -> bool:
    try:
        return bool(ANALISE_RE.search(nota.read_text(encoding="utf-8")))
    except OSError:
        return False


# --------------------------------------------------------------------------- #
# Exibição                                                                     #
# --------------------------------------------------------------------------- #

def mostrar_tabela(dias: dict, processados: set, mapa_notas: dict[str, Path]) -> None:
    print()
    print(f"  {'':2}  {'#':>2}  {'Data':<12}  {'Áudios':>7}  {'Notas':>8}  {'Enriq.':>7}")
    print("  " + "-" * 52)
    for i, (chave, wavs) in enumerate(dias.items(), 1):
        ns = [mapa_notas.get(w.stem) for w in wavs]
        n_notas = sum(1 for n in ns if n)
        n_enriq = sum(1 for n in ns if n and nota_tem_analise(n))
        feito = "v" if chave in processados else " "
        print(f"  {feito}  {i:>2}  {data_legivel(chave):<12}  {len(wavs):>7}  {n_notas}/{len(wavs):<5}  {n_enriq:>5}{' !' if n_enriq else '  '}")
    print()


def mostrar_dia(chave: str, wavs: list[Path], modo: str, mapa_notas: dict[str, Path]) -> None:
    total = sum(stt.duracao_segundos(w) for w in wavs)
    print(f"\n=== {data_legivel(chave)} — {len(wavs)} arquivo(s) (~{stt.formatar_total(total)}) ===")
    enriquecidas = 0
    for w in wavs:
        nota = mapa_notas.get(w.stem)
        hora = f"{w.stem[8:10]}:{w.stem[10:12]}:{w.stem[12:14]}" if len(w.stem) >= 14 else "?"
        if nota is None:
            flag = "[nova]"
        elif nota_tem_analise(nota):
            enriquecidas += 1
            flag = "[nota existe, ENRIQUECIDA !]"
        else:
            flag = "[nota existe]"
        print(f"  {hora}  {stt.duracao_legivel(w):>6}  {w.name}  {flag}")
    if enriquecidas and modo == "sobrescrever":
        print(f"\n  ! {enriquecidas} nota(s) com análise LLM serão perdidas (modo sobrescrever).")


# --------------------------------------------------------------------------- #
# Transcrição                                                                  #
# --------------------------------------------------------------------------- #

def destino_nota(wav: Path, modo: str, inbox: Path, existente: Path | None) -> Path:
    if modo == "novo":
        n = 2
        while (inbox / f"{wav.stem}_v{n}.md").exists():
            n += 1
        return inbox / f"{wav.stem}_v{n}.md"
    return existente or inbox / f"{wav.stem}.md"


def processar(wav: Path, modelo: str, modo: str, whisper, inbox: Path, record: Path,
              existente: Path | None) -> str:
    if modo == "pular" and existente is not None:
        return "[pulada — nota já existe]"
    transcricao = stt.transcrever(whisper, wav)
    destino = destino_nota(wav, modo, inbox, existente)
    destino.write_text(stt.montar_nota(wav, transcricao, modelo, record), encoding="utf-8")
    if existente and destino == existente:
        return f"ok {destino.name} (sobrescrita)"
    if existente:
        return f"ok {destino.name} (nova, original preservada)"
    return f"ok {destino.name} (criada)"


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-transcreve áudios dia a dia com controle interativo.")
    parser.add_argument("pasta", nargs="?", default=None, help="RECORD/ ou RECORD/YYYY-MM-DD/ (padrão: GV_RECORD)")
    parser.add_argument("--modo", choices=["sobrescrever", "novo", "pular"], default="sobrescrever")
    args = parser.parse_args()

    vault = config.vault()
    record = config.record()
    inbox = config.inbox(vault)
    inbox.mkdir(parents=True, exist_ok=True)
    pasta = Path(args.pasta).expanduser() if args.pasta else record
    if not pasta.exists():
        print(f"Erro: '{pasta}' não encontrada.", file=sys.stderr)
        sys.exit(1)

    wavs = coletar_transcritos(pasta)
    if not wavs:
        print(f"Nenhum áudio transcrito em '{pasta}'. Rode organizar.py e transcrever.py primeiro.")
        return

    dias = agrupar_por_dia(wavs)
    mapa_notas = notas.listar_notas(vault, apenas_ids=False)
    processados: set[str] = set()
    whisper = None
    modelo_atual = ""

    print(f"\nPasta : {pasta}\nModo  : {args.modo}\n{len(wavs)} arquivo(s) em {len(dias)} dia(s)")
    n_opcoes = min(len(dias), 9)
    opcoes_dia = "".join(str(i) for i in range(1, n_opcoes + 1))
    if len(dias) > 9:
        print("(mais de 9 dias: só os 9 primeiros são selecionáveis; passe a pasta de um dia para os demais)")

    while True:
        mostrar_tabela(dias, processados, mapa_notas)
        ch = pedir_tecla(opcoes_dia + "q", f"Selecione um dia [1-{n_opcoes}] ou q: ")
        if ch == "q":
            break
        chave = list(dias)[int(ch) - 1]
        wavs_dia = dias[chave]
        mostrar_dia(chave, wavs_dia, args.modo, mapa_notas)

        ch2 = pedir_tecla("smlnq", "\nProcessar:  [s]mall  [m]edium  [l]arge-v3  [n]ão  [q]uit: ")
        if ch2 == "q":
            break
        if ch2 == "n":
            continue
        modelo = modelo_por_tecla(ch2)
        if whisper is None or modelo_atual != modelo:
            print(f"\nCarregando modelo {modelo}...", end="", flush=True)
            whisper = stt.criar_modelo(modelo)
            modelo_atual = modelo
            print(" pronto.")

        total = len(wavs_dia)
        parcial = False
        for i, wav in enumerate(wavs_dia, 1):
            print(f"\n[{i}/{total}] {wav.name}  ({stt.duracao_legivel(wav)}, {modelo})")
            try:
                status = processar(wav, modelo, args.modo, whisper, inbox, record, mapa_notas.get(wav.stem))
                print(f"  {status}")
                mapa_notas = notas.listar_notas(vault, apenas_ids=False)
            except Exception as exc:  # noqa: BLE001 — um áudio ruim não derruba o lote
                print(f"  [ERRO] {exc}")
            if i < total:
                ch3 = pedir_tecla("cdq", "  [c]ontinuar  [d]ia seguinte  [q]uit: ")
                if ch3 == "q":
                    print(f"\nDias processados: {len(processados)}/{len(dias)}")
                    return
                if ch3 == "d":
                    parcial = True
                    break
        processados.add(chave)
        print(f"\nok {data_legivel(chave)} {'parcial' if parcial else 'concluído'}.")

    print(f"\nDias processados: {len(processados)}/{len(dias)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompido.")

"""organizar.py — Organiza áudios de RECORD/ em subpastas por data (YYYY-MM-DD).

Estrutura resultante:
  RECORD/
    2026-06-02/
      20260602120000.WAV        ← ainda não transcrito
      transcrito/
        20260602123000.WAV      ← já transcrito (movido por transcrever.py)
    _sem-data/                  ← nomes sem timestamp (ver --renomear-por-mtime)

O ID de uma nota é o nome do áudio (YYYYMMDDhhmmss). Gravadores baratos já nomeiam
assim. Para fontes com outro padrão de nome (celular, Zoom, etc.), use
--renomear-por-mtime: o arquivo é renomeado pela data de modificação antes de ser
organizado. Sem essa flag, vai para _sem-data/ e você decide à mão.

Uso:
  organizar.py                      # opera em GV_RECORD
  organizar.py /outro/RECORD
  organizar.py --dry-run
  organizar.py --renomear-por-mtime
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

from comum import config, stt


def mover(src: Path, dst: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"  [dry] {src.name}  →  {dst.parent.name}/{dst.name}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)


def nome_por_mtime(wav: Path) -> Path:
    """YYYYMMDDhhmmss a partir do mtime. Colisão no mesmo segundo desloca +1 s."""
    base = datetime.fromtimestamp(wav.stat().st_mtime).replace(microsecond=0)
    for delta in range(3600):
        stamp = (base + timedelta(seconds=delta)).strftime("%Y%m%d%H%M%S")
        candidato = wav.with_name(stamp + wav.suffix.upper())
        if candidato == wav or not candidato.exists():
            return candidato
    raise RuntimeError(f"não consegui gerar nome único para {wav.name}")


def organizar(record: Path, dry_run: bool, renomear: bool) -> dict:
    movidos = ignorados = sem_data = renomeados = 0

    # 1. Áudios soltos em RECORD/
    soltos = stt.glob_audio(record)
    if soltos:
        print(f"\n[1/3] {len(soltos)} áudio(s) novo(s) em {record.name}/")
    for wav in soltos:
        data = stt.data_do_nome(wav.stem)
        if data is None and renomear:
            novo = nome_por_mtime(wav)
            print(f"  [mtime] {wav.name}  →  {novo.name}")
            if not dry_run:
                wav = wav.rename(novo)
            else:
                wav = novo
            renomeados += 1
            data = stt.data_do_nome(wav.stem)
        if data is None:
            print(f"  [?] {wav.name}  →  _sem-data/  (nome sem timestamp)")
            mover(wav, record / "_sem-data" / wav.name, dry_run)
            sem_data += 1
            continue
        dst = record / data / wav.name
        if dst.exists():
            print(f"  [=] {wav.name}  já existe em {data}/, ignorado")
            ignorados += 1
            continue
        print(f"  {wav.name}  →  {data}/")
        mover(wav, dst, dry_run)
        movidos += 1

    # 2. Legado: RECORD/transcrito/ flat → RECORD/YYYY-MM-DD/transcrito/
    legado = record / "transcrito"
    wavs_legado = stt.glob_audio(legado) if legado.is_dir() else []
    if wavs_legado:
        print(f"\n[2/3] {len(wavs_legado)} áudio(s) em transcrito/ legado")
    for wav in wavs_legado:
        data = stt.data_do_nome(wav.stem)
        if data is None:
            mover(wav, record / "_sem-data" / "transcrito" / wav.name, dry_run)
            sem_data += 1
            continue
        dst = record / data / "transcrito" / wav.name
        if dst.exists():
            ignorados += 1
            continue
        print(f"  transcrito/{wav.name}  →  {data}/transcrito/")
        mover(wav, dst, dry_run)
        movidos += 1
    if not dry_run and legado.exists() and not any(legado.iterdir()):
        legado.rmdir()

    # 3. Relatório
    print("\n[3/3] Resumo")
    dias = sorted(d.name for d in record.iterdir()
                  if d.is_dir() and d.name not in ("transcrito", "_sem-data"))
    for dia in dias:
        pendentes = len(stt.glob_audio(record / dia))
        tdir = record / dia / "transcrito"
        transcritos = len(stt.glob_audio(tdir)) if tdir.exists() else 0
        flags = []
        if pendentes:
            flags.append(f"{pendentes} pendente(s)")
        if transcritos:
            flags.append(f"{transcritos} transcrito(s)")
        print(f"  {dia}  —  {', '.join(flags) if flags else 'vazio'}")

    print(f"\n  {movidos} movido(s), {ignorados} ignorado(s), {sem_data} sem-data, {renomeados} renomeado(s)")
    if dry_run:
        print("  [dry-run: nada foi movido]")
    return {"movidos": movidos, "ignorados": ignorados, "sem_data": sem_data, "renomeados": renomeados}


def main() -> None:
    parser = argparse.ArgumentParser(description="Organiza áudios de RECORD/ em subpastas YYYY-MM-DD/.")
    parser.add_argument("record", nargs="?", default=None, help="Pasta RECORD/ (padrão: GV_RECORD)")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o que faria sem mover nada")
    parser.add_argument("--renomear-por-mtime", action="store_true",
                        help="Renomeia arquivos sem timestamp no nome usando a data de modificação")
    args = parser.parse_args()

    record = Path(args.record).expanduser() if args.record else config.record()
    if not record.exists():
        print(f"Erro: '{record}' não encontrada.", file=sys.stderr)
        sys.exit(1)

    print(f"RECORD: {record}")
    if args.dry_run:
        print("Modo: dry-run (sem alterações)")
    organizar(record, args.dry_run, args.renomear_por_mtime)


if __name__ == "__main__":
    main()

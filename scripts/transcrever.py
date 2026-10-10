"""transcrever.py — Áudio → nota Markdown em <vault>/00-INBOX/ via Faster-Whisper.

Uso:
  transcrever.py                         # todos os áudios pendentes em GV_RECORD
  transcrever.py RECORD/2026-06-02       # só um dia
  transcrever.py arquivo.WAV --modelo medium
  transcrever.py --dry-run               # lista pendentes sem transcrever
  transcrever.py --mostrar-config

Depois de transcrever, o áudio é movido para <dia>/transcrito/. Áudios cujo ID
já tem nota no vault são pulados (use transcrever-gradual.py para refazer).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from comum import categorias, config, notas, stt


def inicializar_vault(vault: Path, tax: categorias.Taxonomia) -> None:
    for pasta in tax.pastas_vault:
        (vault / pasta).mkdir(parents=True, exist_ok=True)


def coletar_pendentes(alvo: Path, stems_existentes: set[str]) -> tuple[list[Path], list[Path]]:
    if alvo.is_file():
        wavs = [alvo] if stt.eh_wav(alvo) else []
    else:
        wavs = sorted(p for p in alvo.rglob("*") if stt.eh_wav(p) and not stt.dentro_de_transcrito(p))
    pendentes = [w for w in wavs if w.stem not in stems_existentes]
    ja_tem = [w for w in wavs if w.stem in stems_existentes]
    return pendentes, ja_tem


def transcrever_arquivo(wav: Path, modelo: str, whisper, inbox: Path, record: Path) -> Path:
    print(f"  arquivo : {wav.name}")
    print(f"  modelo  : {modelo}")
    print(f"  duração : {stt.duracao_legivel(wav)}")
    print("  transcrevendo...", flush=True)

    transcricao = stt.transcrever(whisper, wav)
    nota = notas.nome_unico(inbox, wav.stem)
    nota.write_text(stt.montar_nota(wav, transcricao, modelo, record), encoding="utf-8")
    print(f"  nota    : {nota}")

    destino = wav.parent / "transcrito"
    destino.mkdir(exist_ok=True)
    wav.rename(destino / wav.name)
    print("  áudio   : movido para transcrito/")
    return nota


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcreve áudios → Markdown em <vault>/00-INBOX/")
    parser.add_argument("alvo", nargs="?", default=None, help="Áudio ou pasta (padrão: GV_RECORD)")
    parser.add_argument("--modelo", choices=stt.MODELOS, default=None,
                        help="Modelo Faster-Whisper (pergunta se omitido)")
    parser.add_argument("--dry-run", action="store_true", help="Lista pendentes sem transcrever nem mover")
    parser.add_argument("--mostrar-config", action="store_true", help="Imprime a configuração resolvida e sai")
    args = parser.parse_args()

    if args.mostrar_config:
        for k, v in config.resumo().items():
            print(f"{k:16} {v}")
        return

    vault = config.vault()
    record = config.record()
    tax = categorias.carregar()
    inicializar_vault(vault, tax)
    inbox = config.inbox(vault)

    alvo = Path(args.alvo).expanduser() if args.alvo else record
    if not alvo.exists():
        print(f"Erro: '{alvo}' não encontrado.", file=sys.stderr)
        sys.exit(1)
    if alvo.is_file() and not stt.eh_wav(alvo):
        print("Erro: o arquivo não é um áudio suportado.", file=sys.stderr)
        sys.exit(1)

    pendentes, ja_tem = coletar_pendentes(alvo, notas.stems_existentes(vault))

    if args.dry_run:
        print(f"\nAlvo: {alvo}")
        print(f"{len(pendentes)} áudio(s) pendente(s)")
        for w in pendentes:
            print(f"  {stt.origem_relativa(w, record)}")
        if ja_tem:
            print(f"\n{len(ja_tem)} ignorado(s) porque já existe nota no vault")
            for w in ja_tem:
                print(f"  {stt.origem_relativa(w, record)}")
        print("\n[dry-run: nada foi transcrito ou movido]")
        return

    if not pendentes:
        print(f"Nenhum áudio pendente em '{alvo}'.")
        if ja_tem:
            print(f"{len(ja_tem)} ignorado(s): nota já existe. Use transcrever-gradual.py para refazer.")
        return

    print(f"\n{len(pendentes)} arquivo(s) a transcrever → {inbox}")
    if ja_tem:
        print(f"{len(ja_tem)} ignorado(s): nota já existe no vault")

    modelo = stt.normalizar_modelo(args.modelo) if args.modelo else stt.perguntar_modelo()
    print(f"Modelo: {modelo}  (device={config.stt_device()}, compute={config.stt_compute()}, idioma={config.idioma()})\n")
    whisper = stt.criar_modelo(modelo)

    for i, wav in enumerate(pendentes, 1):
        print(f"[{i}/{len(pendentes)}]")
        transcrever_arquivo(wav, modelo, whisper, inbox, record)
        print()

    print(f"Concluído. Abra o vault em {vault} e revise 00-INBOX/.")


if __name__ == "__main__":
    main()

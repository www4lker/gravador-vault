import os
import time
from pathlib import Path

import organizar
from comum import stt


def _wav(pasta: Path, nome: str) -> Path:
    p = pasta / nome
    p.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")
    return p


def test_data_do_nome():
    assert stt.data_do_nome("20260602120000") == "2026-06-02"
    assert stt.data_do_nome("gravacao_final") is None
    assert stt.data_do_nome("20261399000000") is None  # mês 13


def test_organiza_por_dia_e_sem_data(record):
    _wav(record, "20260602120000.WAV")
    _wav(record, "20260602121500.wav")
    _wav(record, "20260604120000.WAV")
    _wav(record, "memo.WAV")
    r = organizar.organizar(record, dry_run=False, renomear=False)
    assert r == {"movidos": 3, "ignorados": 0, "sem_data": 1, "renomeados": 0}
    assert (record / "2026-06-02" / "20260602120000.WAV").exists()
    assert (record / "2026-06-02" / "20260602121500.wav").exists()
    assert (record / "2026-06-04" / "20260604120000.WAV").exists()
    assert (record / "_sem-data" / "memo.WAV").exists()


def test_dry_run_nao_move(record):
    _wav(record, "20260602120000.WAV")
    r = organizar.organizar(record, dry_run=True, renomear=False)
    assert r["movidos"] == 1
    assert (record / "20260602120000.WAV").exists()
    assert not (record / "2026-06-02").exists()


def test_renomear_por_mtime(record):
    p = _wav(record, "memo.WAV")
    t = time.mktime((2026, 6, 5, 7, 30, 15, 0, 0, -1))
    os.utime(p, (t, t))
    r = organizar.organizar(record, dry_run=False, renomear=True)
    assert r["renomeados"] == 1 and r["sem_data"] == 0
    assert (record / "2026-06-05" / "20260605073015.WAV").exists()


def test_legado_transcrito_flat(record):
    (record / "transcrito").mkdir()
    _wav(record / "transcrito", "20260602123000.WAV")
    organizar.organizar(record, dry_run=False, renomear=False)
    assert (record / "2026-06-02" / "transcrito" / "20260602123000.WAV").exists()
    assert not (record / "transcrito").exists()


def test_nao_sobrescreve_existente(record):
    (record / "2026-06-02").mkdir()
    _wav(record / "2026-06-02", "20260602120000.WAV")
    _wav(record, "20260602120000.WAV")
    r = organizar.organizar(record, dry_run=False, renomear=False)
    assert r["ignorados"] == 1 and (record / "20260602120000.WAV").exists()

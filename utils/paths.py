"""Caminhos canônicos do repositório (raiz / data / results / figures).

Todos os scripts devem importar daqui em vez de strings relativas na raiz.
Uso típico (no topo de um script em scripts/):

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from utils.paths import raw, processed, result, figure, ensure_dirs
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results"
FIGURES = RESULTS / "figures"
NOTEBOOKS = ROOT / "notebooks"
SCRIPTS = ROOT / "scripts"
DOCS = ROOT / "docs"

# Atalhos usados por quase toda a bateria
RESULTADOS_COMPARACAO_CSV = RESULTS / "resultados_comparacao.csv"
RESULTADOS_COMPARACAO_JSON = RESULTS / "resultados_comparacao.json"
DATASET_BOD_MDL2 = DATA_PROCESSED / "dataset_canonico_bod_mdl2.csv"
DATASET_BOD_ZERO = DATA_PROCESSED / "dataset_canonico_bod_zero.csv"
DATASET_BOD_ROS = DATA_PROCESSED / "dataset_canonico_bod_ros.csv"


def ensure_dirs() -> None:
    """Cria data/raw, data/processed, results e results/figures se faltarem."""
    for d in (DATA_RAW, DATA_PROCESSED, RESULTS, FIGURES, NOTEBOOKS, DOCS):
        d.mkdir(parents=True, exist_ok=True)


def raw(nome: str) -> Path:
    return DATA_RAW / nome


def processed(nome: str) -> Path:
    return DATA_PROCESSED / nome


def result(nome: str) -> Path:
    return RESULTS / nome


def figure(nome: str) -> Path:
    """Destino de PNG do pipeline (results/figures/). Cria a pasta se preciso."""
    FIGURES.mkdir(parents=True, exist_ok=True)
    return FIGURES / nome


def as_str(p: Path | str) -> str:
    """Converte Path para str — pandas/matplotlib aceitam os dois, mas
    open()/alguns callers esperam str."""
    return str(p)


def bootstrap_sys_path() -> Path:
    """Insere ROOT e scripts/ em sys.path para `import utils` e
    `from script_00_preprocessamento import ...` funcionarem ao rodar
    `python scripts/script_XX.py` a partir de qualquer CWD."""
    import sys

    for p in (str(ROOT), str(SCRIPTS)):
        if p not in sys.path:
            sys.path.insert(0, p)
    ensure_dirs()
    return ROOT

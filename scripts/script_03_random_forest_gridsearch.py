"""
Utilitarios de engenharia de features baseados em arvore para o TDS (secao
3.c da metodologia): carregamento da serie e construcao de features (tempo,
mes do ano, lags, media movel). Usados por script_10_detrend_arvore.py
(Detrend+RF, publico) e pelos capstones script_14/script_31.

D-73: o Random Forest "puro" (sem destendenciamento) que rodava neste script
deixou de ser reportado como metodo publico na reducao da bateria para os 7
metodos citados na revisao externa de 14/10/2026 -- extraido para
scripts/bateria_estendida/script_34_random_forest_puro.py, que importa as
funcoes abaixo. Este arquivo continua publico por ser dependencia direta de
script_10/14/31 (nao pode sumir do repositorio junto com o metodo).
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.paths import bootstrap_sys_path
bootstrap_sys_path()


import numpy as np
import pandas as pd

from script_00_preprocessamento import construir_datasets


def carregar_serie_tds() -> pd.DataFrame:
    _, _, _, base = construir_datasets()
    d = base[["Data", "TDS_mgL"]].dropna().sort_values("Data").reset_index(drop=True)
    d["t_anos"] = (d["Data"] - d["Data"].iloc[0]).dt.days / 365.25
    return d


def construir_features(d: pd.DataFrame) -> pd.DataFrame:
    f = d.copy()
    f["mes_sin"] = np.sin(2 * np.pi * f["Data"].dt.month / 12)
    f["mes_cos"] = np.cos(2 * np.pi * f["Data"].dt.month / 12)
    f["lag_1"] = f["TDS_mgL"].shift(1)
    f["lag_12"] = f["TDS_mgL"].shift(12)
    f["media_movel_3"] = f["TDS_mgL"].shift(1).rolling(3).mean()
    return f.dropna().reset_index(drop=True)


FEATURES = ["t_anos", "mes_sin", "mes_cos", "lag_1", "lag_12", "media_movel_3"]

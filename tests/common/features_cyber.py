"""Engenharia de features do ramo ciber (Dataset T-ITS), espelhando
notebooks/Analise Dataset T-ITS/Info_Dataset_T-ITS.ipynb para que os
cenários sintéticos gerados em tests/ sejam compatíveis com
best_model_cyber.keras (mesmas colunas, mesma ordem, mesma janela).

Diferença estrutural em relação a tests/common/features.py (ramo físico):
o Dataset T-ITS é tráfego de rede capturado em sessões — a coluna
`timestamp_c` tem saltos grandes entre blocos de captura (não é um único
voo contínuo). Por isso os ataques sintéticos aqui (tests/attacks/*_cyber.py)
usam janelas por ÍNDICE DE LINHA sobre a subsequência de tráfego `benign`
ordenada por tempo, não por segundos decorridos.
"""

from pathlib import Path

import numpy as np
import pandas as pd

FEATS_V2 = [
    "frame.len",
    "ip.len",
    "time_since_last_packet",
    "wlan.fc.type",
    "wlan.duration",
    "udp.length",
    "data.len",
]
WINDOW = 10
CLASS_NAMES = ["Benign", "DoS attack", "Replay"]
CLASS_MAP = {"benign": 0, "DoS attack": 1, "Replay": 2}


def find_tits_csv() -> Path:
    here = Path.cwd().resolve()
    for anchor in [here, *here.parents]:
        p = anchor / "data" / "Dataset_T-ITS.csv"
        if p.is_file():
            return p
    raise FileNotFoundError("data/Dataset_T-ITS.csv")


def _to_numeric(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["timestamp_c"] = pd.to_numeric(df["timestamp_c"], errors="coerce")
    for col in FEATS_V2:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_full_dataset() -> pd.DataFrame:
    """Carrega o CSV completo, mantém só as 3 classes reais (benign/DoS
    attack/Replay — descarta o rótulo espúrio '2' presente no CSV bruto),
    converte tipos e ordena por timestamp_c. Espelha as células 6/8/9/10 do
    notebook de treino."""
    df = pd.read_csv(find_tits_csv(), sep=",", low_memory=False)
    df = df[df["class"].isin(CLASS_MAP.keys())].copy()
    df = _to_numeric(df)

    base_cols = ["frame.len", "ip.len", "time_since_last_packet"]
    df = df.dropna(subset=base_cols + ["timestamp_c", "class"])
    for col in FEATS_V2:
        if col in base_cols:
            continue
        med = df[col].median()
        if pd.isna(med):
            med = 0.0
        df[col] = df[col].fillna(med)

    df = df.sort_values("timestamp_c").reset_index(drop=True)
    return df


def load_benign_ordered() -> pd.DataFrame:
    """Subsequência só de tráfego `benign`, ordenada por timestamp_c —
    usada como "sessão base" para injetar ataques sintéticos, análogo ao
    voo Normal do ramo físico."""
    df = load_full_dataset()
    df = df[df["class"] == "benign"].reset_index(drop=True)
    return df


def build_windows(df: pd.DataFrame, window: int = WINDOW):
    """Janelas deslizantes (stride 1) sobre FEATS_V2, na ordem das linhas
    (já ordenadas por timestamp_c). Retorna X (n_janelas, window, n_features)
    e o índice de linha final de cada janela."""
    df = df.reset_index(drop=True)
    n = len(df)
    X, end_idx = [], []
    for i in range(0, n - window + 1):
        X.append(df.iloc[i : i + window][FEATS_V2].to_numpy(dtype=np.float32))
        end_idx.append(i + window - 1)
    return np.stack(X), np.array(end_idx)

"""Engenharia de features do ramo físico (PX4), espelhando
notebooks/Analise UAVAttackData PX4-QUAD/Infos_lstm_fusao_px4.ipynb
para que os dados sintéticos gerados em tests/ sejam compatíveis
com os modelos já treinados (mesmas colunas, mesma ordem, mesma janela).
"""

from pathlib import Path

import numpy as np
import pandas as pd

FEATS = [
    "x",
    "y",
    "z",
    "vx",
    "vy",
    "vz",
    "eph_loc",
    "eph_gps",
    "innov_norm",
    "dv_xy",
    "r_xy",
]
WINDOW = 40


def find_px4_quad_sitl() -> Path:
    here = Path.cwd().resolve()
    for anchor in [here, *here.parents]:
        p = anchor / "data" / "UAVAttackData" / "Simulated - OTU Survey" / "PX4-QUAD-SITL"
        if p.is_dir():
            return p
    raise FileNotFoundError("data/UAVAttackData/.../PX4-QUAD-SITL")


def pick_vehicle_local_position_csv(folder: Path) -> Path:
    matches = sorted(folder.glob("*vehicle_local_position*.csv"))
    matches = [m for m in matches if "setpoint" not in m.name and "groundtruth" not in m.name]
    if not matches:
        raise FileNotFoundError(folder)
    return matches[0]


def log_prefix(folder: Path) -> str:
    name = pick_vehicle_local_position_csv(folder).name
    suf = "_vehicle_local_position_0.csv"
    if not name.endswith(suf):
        raise ValueError(name)
    return name[: -len(suf)]


def load_merged(folder: Path, condition: str) -> pd.DataFrame:
    """Carrega e funde local_position + gps_position + ekf2_innovations de um log."""
    pref = log_prefix(folder)
    loc = pd.read_csv(folder / f"{pref}_vehicle_local_position_0.csv", sep=",").sort_values("timestamp")
    gps = pd.read_csv(folder / f"{pref}_vehicle_gps_position_0.csv", sep=",").sort_values("timestamp")
    ekf = pd.read_csv(folder / f"{pref}_ekf2_innovations_0.csv", sep=",").sort_values("timestamp")
    m = pd.merge_asof(loc, gps, on="timestamp", suffixes=("_loc", "_gps"), direction="backward")
    m = pd.merge_asof(m.sort_values("timestamp"), ekf.sort_values("timestamp"), on="timestamp", direction="backward")
    return m.assign(condition=condition)


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona innov_norm, v_xy_gps, v_xy_loc, dv_xy e r_xy (relativo ao 1º ponto do df)."""
    df = df.copy()
    cols_innov = ["vel_pos_innov[0]", "vel_pos_innov[1]", "vel_pos_innov[2]"]
    M = df[cols_innov].astype(float).to_numpy()
    df["innov_norm"] = np.sqrt(np.sum(M * M, axis=1))
    df["v_xy_gps"] = np.sqrt(df["vel_n_m_s"].astype(float) ** 2 + df["vel_e_m_s"].astype(float) ** 2)
    df["v_xy_loc"] = np.sqrt(df["vx"].astype(float) ** 2 + df["vy"].astype(float) ** 2)
    df["dv_xy"] = np.abs(df["v_xy_loc"] - df["v_xy_gps"])

    x0, y0 = float(df["x"].iloc[0]), float(df["y"].iloc[0])
    df["r_xy"] = np.sqrt((df["x"] - x0) ** 2 + (df["y"] - y0) ** 2)
    return df


def build_windows(df: pd.DataFrame, window: int = WINDOW):
    """Janelas deslizantes (stride 1) sobre FEATS, na ordem do timestamp.

    Retorna X (n_janelas, window, n_features) e o timestamp final de cada janela
    (útil para saber se ela cobre trecho atacado).
    """
    df = df.sort_values("timestamp").reset_index(drop=True)
    n = len(df)
    X, end_ts = [], []
    for i in range(0, n - window + 1):
        X.append(df.iloc[i : i + window][FEATS].to_numpy(dtype=np.float32))
        end_ts.append(df["timestamp"].iloc[i + window - 1])
    return np.stack(X), np.array(end_ts)

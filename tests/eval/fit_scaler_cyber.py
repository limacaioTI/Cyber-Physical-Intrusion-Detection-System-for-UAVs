"""Reconstrói e persiste (joblib) o MinMaxScaler do treino do ramo ciber
(Dataset T-ITS), espelhando a célula 11 (M2) do notebook de treino:
split temporal 80/20 **por classe** (não um corte único global), ordenado
por `timestamp_c`, e o scaler é ajustado só nas janelas de treino.

Uso:
    python -m tests.eval.fit_scaler_cyber --out tests/eval/cyber_scaler.joblib
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.common.features_cyber import CLASS_MAP, FEATS_V2, WINDOW, load_full_dataset


def _prepare_sequences(data: np.ndarray, target: np.ndarray, window: int):
    if len(data) <= window:
        raise ValueError(f"Só há {len(data)} linhas; é preciso mais de {window} para montar janelas.")
    X, y = [], []
    for i in range(len(data) - window):
        X.append(np.asarray(data[i : i + window], dtype=np.float32))
        y.append(int(target[i + window]))
    return np.stack(X, axis=0), np.asarray(y, dtype=np.int64)


def fit_reference_scaler(window: int = WINDOW, frac_train: float = 0.8):
    from sklearn.preprocessing import MinMaxScaler

    df_model = load_full_dataset()
    target = df_model["class"].map(CLASS_MAP).values
    data = df_model[FEATS_V2].values.astype(np.float32)

    X, y = _prepare_sequences(data, target, window)

    n_total = len(X)
    t_row = df_model["timestamp_c"].to_numpy(dtype=np.float64)
    t_label = t_row[window : window + n_total]
    idx_all = np.arange(n_total, dtype=np.int64)
    train_mask = np.zeros(n_total, dtype=bool)

    for c in np.unique(y):
        ic = idx_all[y == c]
        if len(ic) == 0:
            continue
        order = np.argsort(t_label[ic])
        idx_sorted = ic[order]
        if len(idx_sorted) < 2:
            train_mask[idx_sorted] = True
            continue
        sp_c = int(frac_train * len(idx_sorted))
        sp_c = max(1, min(sp_c, len(idx_sorted) - 1))
        train_mask[idx_sorted[:sp_c]] = True

    X_train = X[train_mask]
    n, w, f = X_train.shape
    scaler = MinMaxScaler()
    scaler.fit(X_train.reshape(-1, f))
    return scaler


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--window", type=int, default=WINDOW)
    parser.add_argument("--frac-train", type=float, default=0.8, help="Fração de treino por classe (split M2)")
    parser.add_argument("--out", default="tests/eval/cyber_scaler.joblib")
    args = parser.parse_args()

    print("Reconstruindo o MinMaxScaler de referência (mesmo split M2 do notebook)...")
    scaler = fit_reference_scaler(window=args.window, frac_train=args.frac_train)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(scaler, out_path)
    print(f"Scaler salvo em: {out_path}")
    print(f"n_features_in_={scaler.n_features_in_}")


if __name__ == "__main__":
    main()

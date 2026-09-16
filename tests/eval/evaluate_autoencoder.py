"""Avalia o LSTM-Autoencoder (tests/eval/train_autoencoder.py) contra um CSV
de ataque gerado em tests/attacks/, usando erro de reconstrução + threshold
em vez de argmax sobre classes (como em tests/eval/evaluate_model.py, que
avalia o classificador fechado best_model_px4.keras).

Diferente do classificador de 3 classes, o autoencoder não tem noção de
"Normal / GPS Spoofing / Ping DoS": ele só reconstrói janelas e sinaliza como
anômala qualquer janela cujo erro de reconstrução ultrapasse o threshold
calibrado em treino (percentil do erro sobre validação Normal). Isso permite
comparar, para o MESMO CSV de ataque, a taxa de deteção do classificador
fechado (evaluate_model.py) com a do autoencoder (este script) — ver a
tabela comparativa em docs/proximos-passos-tests-autoencoder.md.

Uso:
    python -m tests.eval.evaluate_autoencoder \
        --attack-csv tests/outputs/replay/normal_replay.csv \
        --model tests/eval/autoencoder_px4.keras \
        --threshold-file tests/eval/autoencoder_px4_threshold.json \
        --scaler tests/eval/px4_scaler.joblib
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.common.features import FEATS, WINDOW


def build_eval_windows(attack_csv: Path, window: int = WINDOW):
    """Espelha tests.eval.evaluate_model.build_eval_windows: janelas deslizantes
    sobre o CSV de ataque, rotuladas por is_attack (1 se qualquer amostra da
    janela veio do trecho atacado)."""
    df = pd.read_csv(attack_csv).sort_values("timestamp").reset_index(drop=True)
    if "is_attack" not in df.columns:
        raise ValueError(f"{attack_csv} não tem coluna 'is_attack' — gere com tests/attacks/*.py")

    missing = [c for c in FEATS if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas em falta no CSV de ataque: {missing}")

    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATS)
    n = len(df)
    X, y_window = [], []
    for i in range(0, n - window + 1):
        chunk = df.iloc[i : i + window]
        X.append(chunk[FEATS].to_numpy(dtype=np.float32))
        y_window.append(int(chunk["is_attack"].max()))
    return np.stack(X), np.array(y_window)


def reconstruction_error(model, X: np.ndarray) -> np.ndarray:
    X_hat = model.predict(X, verbose=0)
    return np.mean(np.square(X - X_hat), axis=(1, 2))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--attack-csv", required=True, help="CSV gerado por tests/attacks/*.py (precisa de 'is_attack')")
    parser.add_argument("--model", default="tests/eval/autoencoder_px4.keras", help="Caminho do autoencoder .keras")
    parser.add_argument(
        "--threshold-file",
        default="tests/eval/autoencoder_px4_threshold.json",
        help="JSON salvo por tests.eval.train_autoencoder com o threshold calibrado",
    )
    parser.add_argument(
        "--scaler",
        default="tests/eval/px4_scaler.joblib",
        help="Scaler .joblib persistido (tests.eval.fit_scaler) — precisa ser o MESMO usado no treino do autoencoder",
    )
    args = parser.parse_args()

    import tensorflow as tf  # import tardio: só quando o script roda de fato

    scaler_path = Path(args.scaler)
    if not scaler_path.is_file():
        raise FileNotFoundError(f"Scaler não encontrado em {scaler_path}. Rode tests.eval.fit_scaler primeiro.")
    scaler = joblib.load(scaler_path)

    threshold_path = Path(args.threshold_file)
    if not threshold_path.is_file():
        raise FileNotFoundError(f"Threshold não encontrado em {threshold_path}. Rode tests.eval.train_autoencoder primeiro.")
    with open(threshold_path) as f:
        threshold_info = json.load(f)
    threshold = threshold_info["threshold"]
    window = int(threshold_info.get("window", WINDOW))

    print(f"Carregando autoencoder: {args.model}")
    model = tf.keras.models.load_model(args.model)

    print(f"Threshold de deteção (p{threshold_info.get('percentile', '?')} do erro em validação Normal): {threshold:.6f}")

    print(f"Montando janelas de avaliação a partir de: {args.attack_csv}")
    X, y_attack = build_eval_windows(Path(args.attack_csv), window=window)
    ns, win, nf = X.shape
    X_scaled = scaler.transform(X.reshape(-1, nf)).reshape(ns, win, nf)

    errors = reconstruction_error(model, X_scaled)
    is_anomaly = errors > threshold

    print(f"\nTotal de janelas: {ns} | janelas tocando o ataque: {int(y_attack.sum())}")

    err_attack = errors[y_attack == 1]
    err_normal = errors[y_attack == 0]
    print(f"\nErro de reconstrução — janelas SEM ataque: média={err_normal.mean():.6f} | máx={err_normal.max():.6f}")
    if err_attack.size:
        print(f"Erro de reconstrução — janelas COM ataque: média={err_attack.mean():.6f} | máx={err_attack.max():.6f}")

    if y_attack.sum() > 0:
        detection_rate = is_anomaly[y_attack == 1].mean()
        print(f"\nTaxa de deteção (erro > threshold durante o ataque): {detection_rate:.3f}")
    false_alarm = is_anomaly[y_attack == 0].mean() if (y_attack == 0).sum() > 0 else float("nan")
    print(f"Taxa de falso alarme (erro > threshold fora do ataque): {false_alarm:.3f}")

    print("\n=== Matriz: is_attack (linha) x sinalizado como anômalo (coluna) ===")
    print("            " + "  ".join(f"{n:>12}" for n in ["Não-anômalo", "Anômalo"]))
    for attack_flag, row_label in [(0, "sem ataque"), (1, "com ataque")]:
        row = [
            int(np.sum((y_attack == attack_flag) & (is_anomaly == flag)))
            for flag in [False, True]
        ]
        print(f"{row_label:>12}" + "".join(f"{v:>14}" for v in row))


if __name__ == "__main__":
    main()

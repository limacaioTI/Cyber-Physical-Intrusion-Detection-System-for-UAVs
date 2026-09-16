"""Avalia o classificador do ramo ciber (best_model_cyber.keras) contra um
CSV de ataque sintético gerado em tests/attacks/*_cyber.py — equivalente, no
ramo ciber, ao tests/eval/evaluate_model.py do ramo físico.

O modelo foi treinado com 3 classes REAIS do Dataset T-ITS (Benign / DoS
attack / Replay). Diferente do ramo físico, DoS e Replay aqui SÃO classes de
treino — então esta avaliação testa generalização de MAGNITUDE (um DoS
sintético mais suave ou mais agressivo que o log real, um replay "canônico"
de tráfego benigno) e não um vetor de ataque totalmente desconhecido. Ainda
assim, o teste é útil pelo mesmo motivo do ramo físico: mede se a
assinatura aprendida generaliza além da instância exata vista em treino.

Uso:
    python -m tests.eval.evaluate_model_cyber \
        --attack-csv tests/outputs/dos_cyber/benign_dos_suave.csv \
        --scaler tests/eval/cyber_scaler.joblib
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.common.features_cyber import CLASS_MAP, CLASS_NAMES, FEATS_V2, WINDOW
from tests.eval.fit_scaler_cyber import fit_reference_scaler

LABEL_MAP = {"Benign": 0, "DoS attack": 1, "Replay": 2}


def build_eval_windows(attack_csv: Path, window: int = WINDOW):
    df = pd.read_csv(attack_csv).reset_index(drop=True)
    if "is_attack" not in df.columns:
        raise ValueError(f"{attack_csv} não tem coluna 'is_attack' — gere com tests/attacks/*_cyber.py")

    missing = [c for c in FEATS_V2 if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas em falta no CSV de ataque: {missing}")

    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATS_V2)
    n = len(df)
    X, y_window = [], []
    for i in range(0, n - window + 1):
        chunk = df.iloc[i : i + window]
        X.append(chunk[FEATS_V2].to_numpy(dtype=np.float32))
        y_window.append(int(chunk["is_attack"].max()))
    return np.stack(X), np.array(y_window)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--attack-csv", required=True, help="CSV gerado por tests/attacks/*_cyber.py (precisa de 'is_attack')")
    parser.add_argument(
        "--model",
        default="notebooks/Analise Dataset T-ITS/best_model_cyber.keras",
        help="Caminho do modelo .keras",
    )
    parser.add_argument(
        "--scaler",
        default="tests/eval/cyber_scaler.joblib",
        help="Scaler .joblib persistido (tests.eval.fit_scaler_cyber). Se ausente, reconstrói do zero.",
    )
    args = parser.parse_args()

    import tensorflow as tf  # import tardio: só quando o script roda de fato

    if args.scaler and Path(args.scaler).is_file():
        print(f"Carregando scaler persistido: {args.scaler}")
        scaler = joblib.load(args.scaler)
    else:
        print("Reconstruindo o MinMaxScaler de referência (mesmo split M2 do notebook)...")
        scaler = fit_reference_scaler()

    print(f"Carregando modelo: {args.model}")
    model = tf.keras.models.load_model(args.model)

    print(f"Montando janelas de avaliação a partir de: {args.attack_csv}")
    X, y_attack = build_eval_windows(Path(args.attack_csv))
    ns, win, nf = X.shape
    X_scaled = scaler.transform(X.reshape(-1, nf)).reshape(ns, win, nf)

    probs = model.predict(X_scaled, verbose=0)
    y_pred = np.argmax(probs, axis=1)
    pred_names = np.array(CLASS_NAMES)[y_pred]

    print(f"\nTotal de janelas: {ns} | janelas tocando o ataque: {int(y_attack.sum())}")

    print("\n=== Distribuição de predições — janelas SEM ataque (is_attack=0) ===")
    for name, count in zip(*np.unique(pred_names[y_attack == 0], return_counts=True)):
        print(f"  {name}: {count}")

    print("\n=== Distribuição de predições — janelas COM ataque (is_attack=1) ===")
    for name, count in zip(*np.unique(pred_names[y_attack == 1], return_counts=True)):
        print(f"  {name}: {count}")

    if y_attack.sum() > 0:
        flagged = (y_pred[y_attack == 1] != LABEL_MAP["Benign"]).mean()
        print(f"\nTaxa de deteção (previsão != Benign durante o ataque): {flagged:.3f}")
    false_alarm = (y_pred[y_attack == 0] != LABEL_MAP["Benign"]).mean() if (y_attack == 0).sum() > 0 else float("nan")
    print(f"Taxa de falso alarme (previsão != Benign fora do ataque): {false_alarm:.3f}")

    print("\n=== Matriz: is_attack (linha) x classe prevista (coluna) ===")
    print("            " + "  ".join(f"{n:>13}" for n in CLASS_NAMES))
    for attack_flag, row_label in [(0, "sem ataque"), (1, "com ataque")]:
        row = [int(np.sum((y_attack == attack_flag) & (y_pred == c))) for c in range(len(CLASS_NAMES))]
        print(f"{row_label:>12}" + "".join(f"{v:>15}" for v in row))


if __name__ == "__main__":
    main()

"""Avalia um modelo treinado (ex.: best_model_px4.keras) contra um CSV de
ataque gerado em tests/attacks/ (ex.: tests/outputs/replay/normal_replay.csv).

O notebook de treino (Infos_lstm_fusao_px4.ipynb) não salva o StandardScaler
usado para normalizar as janelas — só o `.keras`. Por padrão, este script
reconstrói o MESMO scaler: refaz o split treino/teste por voo (80/20
temporal, por condição) exatamente como no notebook, ajusta o scaler nas
janelas de treino, e só então transforma as janelas do cenário de ataque.
Isso é reproduzível porque os logs brutos (Normal / GPS Spoofing / Ping DoS)
não mudam — mas é redundante recalcular isso a cada avaliação. Use
`--scaler tests/eval/px4_scaler.joblib` (gerado uma vez por
`python -m tests.eval.fit_scaler`) para carregar o scaler já persistido em
vez de reconstruí-lo.

O modelo foi treinado só com 3 classes (Normal, GPS Spoofing, Ping DoS) — ele
nunca viu "replay" como rótulo. Por isso a avaliação aqui não é um
classification_report contra uma 4ª classe; é um teste de deteção de anomalia:
comparamos a distribuição de predições nas janelas que tocam o trecho
atacado (`is_attack`) contra as janelas fora dele. Um IDS que generaliza bem
deve deixar de prever "Normal" com confiança durante o ataque.

Uso:
    python -m tests.eval.evaluate_model \
        --attack-csv tests/outputs/replay/normal_replay.csv \
        --model "notebooks/Analise UAVAttackData PX4-QUAD/best_model_px4.keras"
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
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.common.features import FEATS, WINDOW, add_derived_features, find_px4_quad_sitl, load_merged

CLASS_NAMES = ["Normal", "GPS Spoofing", "Ping DoS"]
LABEL_MAP = {"Normal": 0, "GPS Spoofing": 1, "Ping DoS": 2}


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    return df[FEATS + ["condition", "timestamp"]].replace([np.inf, -np.inf], np.nan).dropna()


def _train_windows_for_condition(df: pd.DataFrame, window: int, frac_train: float) -> np.ndarray:
    """Só a parte de TREINO (80% inicial), como em build_windows_for_condition do notebook."""
    df = df.sort_values("timestamp").reset_index(drop=True)
    n = len(df)
    split = max(int(frac_train * n), window + 1)
    X = [df.iloc[i : i + window][FEATS].to_numpy(dtype=np.float32) for i in range(0, split - window)]
    return np.stack(X)


def fit_reference_scaler(window: int = WINDOW, frac_train: float = 0.8) -> StandardScaler:
    """Reconstrói o StandardScaler original: ajustado nas janelas de treino
    dos três voos brutos, exatamente como no notebook (mesma ordem, mesmo split).
    """
    base = find_px4_quad_sitl()
    parts = []
    for cond, sub in [("Normal", "Normal"), ("GPS Spoofing", "GPS Spoofing"), ("Ping DoS", "Ping DoS")]:
        merged = add_derived_features(load_merged(base / sub, condition=cond))
        data = _clean(merged)
        parts.append(_train_windows_for_condition(data, window, frac_train))
    X_train = np.concatenate(parts, axis=0)
    ns, win, nf = X_train.shape
    scaler = StandardScaler()
    scaler.fit(X_train.reshape(-1, nf))
    return scaler


def build_eval_windows(attack_csv: Path, window: int = WINDOW):
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
        # janela é "atacada" se qualquer amostra dentro dela veio do replay
        y_window.append(int(chunk["is_attack"].max()))
    return np.stack(X), np.array(y_window)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--attack-csv", required=True, help="CSV gerado por tests/attacks/*.py (precisa de 'is_attack')")
    parser.add_argument(
        "--model",
        default="notebooks/Analise UAVAttackData PX4-QUAD/best_model_px4.keras",
        help="Caminho do modelo .keras",
    )
    parser.add_argument(
        "--scaler",
        default=None,
        help="Caminho de um scaler .joblib já persistido (tests.eval.fit_scaler). "
        "Se omitido ou inexistente, reconstrói o scaler do zero (mais lento).",
    )
    args = parser.parse_args()

    import tensorflow as tf  # import tardio: só quando o script roda de fato

    if args.scaler and Path(args.scaler).is_file():
        print(f"Carregando scaler persistido: {args.scaler}")
        scaler = joblib.load(args.scaler)
    else:
        print("Reconstruindo o StandardScaler de referência (mesmo split do notebook)...")
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

    # Taxa de deteção: fração das janelas atacadas em que o modelo NÃO previu "Normal"
    if y_attack.sum() > 0:
        flagged = (y_pred[y_attack == 1] != LABEL_MAP["Normal"]).mean()
        print(f"\nTaxa de deteção (previsão != Normal durante o ataque): {flagged:.3f}")
    false_alarm = (y_pred[y_attack == 0] != LABEL_MAP["Normal"]).mean() if (y_attack == 0).sum() > 0 else float("nan")
    print(f"Taxa de falso alarme (previsão != Normal fora do ataque): {false_alarm:.3f}")

    print("\n=== Matriz: is_attack (linha) x classe prevista (coluna) ===")
    print("            " + "  ".join(f"{n:>13}" for n in CLASS_NAMES))
    for attack_flag, row_label in [(0, "sem ataque"), (1, "com ataque")]:
        row = [int(np.sum((y_attack == attack_flag) & (y_pred == c))) for c in range(len(CLASS_NAMES))]
        print(f"{row_label:>12}" + "".join(f"{v:>15}" for v in row))


if __name__ == "__main__":
    main()

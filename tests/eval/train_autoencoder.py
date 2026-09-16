"""Treina um LSTM-Autoencoder de deteção de anomalia sobre o ramo físico
(PX4-QUAD-SITL), como alternativa à classificação fechada (Dense(3, softmax))
usada em best_model_px4.keras.

Motivação (ver tests/README.md e docs/proximos-passos-tests-autoencoder.md):
os testes de ataque sintético em tests/attacks/ mostraram que o classificador
fechado não generaliza para vetores de ataque fora do repertório de treino
(Replay: 23% de deteção; FDI: 0%) nem para variações de magnitude de classes
conhecidas (GPS Spoofing suave: 0%). Um autoencoder treinado só com voos
Normal não depende de rótulo de ataque: aprende a reconstruir o padrão de
telemetria legítima, e qualquer sequência que se desvie — conhecida ou não —
tende a produzir erro de reconstrução alto.

Pipeline:
  1. Carrega o voo Normal (mesma fonte usada pelos ataques sintéticos) via
     tests/common/features.py — mesmas FEATS/WINDOW do notebook de treino.
  2. Split sequencial 80/20 (treino/validação), sem embaralhar (série
     temporal), mesmo espírito do split usado em tests/eval/evaluate_model.py.
  3. Normaliza com o MESMO scaler de referência já persistido por
     tests/eval/fit_scaler.py (garante compatibilidade com os CSVs de ataque
     avaliados em evaluate_autoencoder.py).
  4. Treina um LSTM-Autoencoder (encoder -> vetor latente -> decoder) a
     minimizar o erro de reconstrução (MSE) sobre as janelas de treino.
  5. Define o threshold de deteção como um percentil (padrão: 95) do erro de
     reconstrução nas janelas de VALIDAÇÃO (Normal, não vistas em treino) —
     evita usar o próprio erro de treino, que tende a ser otimista.
  6. Salva o modelo (.keras) e o threshold (.json) em tests/eval/.

Uso:
    python -m tests.eval.train_autoencoder \
        --out-model tests/eval/autoencoder_px4.keras \
        --out-threshold tests/eval/autoencoder_px4_threshold.json
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

from tests.common.features import FEATS, WINDOW, add_derived_features, find_px4_quad_sitl, load_merged

DEFAULT_SCALER = Path("tests/eval/px4_scaler.joblib")


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    return df[FEATS + ["timestamp"]].replace([np.inf, -np.inf], np.nan).dropna()


def _windows(df: pd.DataFrame, window: int) -> np.ndarray:
    df = df.sort_values("timestamp").reset_index(drop=True)
    n = len(df)
    X = [df.iloc[i : i + window][FEATS].to_numpy(dtype=np.float32) for i in range(0, n - window + 1)]
    return np.stack(X)


def load_normal_windows(flight: str, window: int, frac_train: float):
    """Carrega o voo `flight` e retorna (janelas de treino, janelas de validação),
    com split sequencial (sem embaralhar) para respeitar a ordem temporal."""
    base = find_px4_quad_sitl()
    merged = add_derived_features(load_merged(base / flight, condition=flight))
    data = _clean(merged)
    data = data.sort_values("timestamp").reset_index(drop=True)

    split = int(frac_train * len(data))
    train_df = data.iloc[:split].reset_index(drop=True)
    val_df = data.iloc[split:].reset_index(drop=True)

    X_train = _windows(train_df, window)
    X_val = _windows(val_df, window)
    return X_train, X_val


def build_autoencoder(window: int, n_features: int, latent_dim: int = 16):
    import tensorflow as tf
    from tensorflow.keras import layers, models

    inputs = layers.Input(shape=(window, n_features))
    encoded = layers.LSTM(32, activation="tanh", return_sequences=True)(inputs)
    encoded = layers.LSTM(latent_dim, activation="tanh", return_sequences=False)(encoded)

    decoded = layers.RepeatVector(window)(encoded)
    decoded = layers.LSTM(latent_dim, activation="tanh", return_sequences=True)(decoded)
    decoded = layers.LSTM(32, activation="tanh", return_sequences=True)(decoded)
    outputs = layers.TimeDistributed(layers.Dense(n_features))(decoded)

    model = models.Model(inputs, outputs, name="lstm_autoencoder_px4")
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3), loss="mse")
    return model


def reconstruction_error(model, X: np.ndarray) -> np.ndarray:
    """Erro de reconstrução por janela: MSE médio sobre passos de tempo e features."""
    X_hat = model.predict(X, verbose=0)
    return np.mean(np.square(X - X_hat), axis=(1, 2))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--flight", default="Normal", help="Subpasta do voo usado para treino (padrão: Normal)")
    parser.add_argument("--window", type=int, default=WINDOW)
    parser.add_argument("--frac-train", type=float, default=0.8, help="Fração inicial do voo usada em treino")
    parser.add_argument("--latent-dim", type=int, default=16)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--percentile", type=float, default=95.0, help="Percentil do erro de validação usado como threshold")
    parser.add_argument("--scaler", default=str(DEFAULT_SCALER), help="Scaler .joblib persistido (tests.eval.fit_scaler)")
    parser.add_argument("--out-model", default="tests/eval/autoencoder_px4.keras")
    parser.add_argument("--out-threshold", default="tests/eval/autoencoder_px4_threshold.json")
    args = parser.parse_args()

    import tensorflow as tf  # import tardio: só quando o script roda de fato

    scaler_path = Path(args.scaler)
    if not scaler_path.is_file():
        raise FileNotFoundError(
            f"Scaler não encontrado em {scaler_path}. Rode primeiro:\n"
            "  python -m tests.eval.fit_scaler --out tests/eval/px4_scaler.joblib"
        )
    scaler = joblib.load(scaler_path)

    print(f"Carregando voo '{args.flight}' e montando janelas (window={args.window})...")
    X_train, X_val = load_normal_windows(args.flight, args.window, args.frac_train)
    print(f"Janelas de treino: {X_train.shape} | Janelas de validação: {X_val.shape}")

    ns_tr, win, nf = X_train.shape
    ns_val = X_val.shape[0]
    X_train_scaled = scaler.transform(X_train.reshape(-1, nf)).reshape(ns_tr, win, nf)
    X_val_scaled = scaler.transform(X_val.reshape(-1, nf)).reshape(ns_val, win, nf)

    print(f"Construindo LSTM-Autoencoder (latent_dim={args.latent_dim})...")
    model = build_autoencoder(window=win, n_features=nf, latent_dim=args.latent_dim)
    model.summary()

    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor="val_loss", patience=5, restore_best_weights=True
    )
    history = model.fit(
        X_train_scaled,
        X_train_scaled,
        validation_data=(X_val_scaled, X_val_scaled),
        epochs=args.epochs,
        batch_size=args.batch_size,
        callbacks=[early_stop],
        verbose=2,
    )

    print("\nCalculando threshold de deteção sobre o erro de reconstrução da validação (Normal)...")
    val_errors = reconstruction_error(model, X_val_scaled)
    threshold = float(np.percentile(val_errors, args.percentile))
    print(f"Erro de reconstrução (validação) — média: {val_errors.mean():.6f} | p{args.percentile:.0f}: {threshold:.6f}")

    out_model_path = Path(args.out_model)
    out_model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(out_model_path)
    print(f"Modelo salvo em: {out_model_path}")

    out_threshold_path = Path(args.out_threshold)
    out_threshold_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_threshold_path, "w") as f:
        json.dump(
            {
                "threshold": threshold,
                "percentile": args.percentile,
                "window": args.window,
                "flight": args.flight,
                "val_error_mean": float(val_errors.mean()),
                "val_error_std": float(val_errors.std()),
                "final_val_loss": float(history.history["val_loss"][-1]),
            },
            f,
            indent=2,
        )
    print(f"Threshold salvo em: {out_threshold_path}")


if __name__ == "__main__":
    main()

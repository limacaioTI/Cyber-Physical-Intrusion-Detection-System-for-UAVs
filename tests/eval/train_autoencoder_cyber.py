"""Treina um LSTM-Autoencoder de deteção de anomalia sobre o ramo ciber
(Dataset T-ITS), equivalente a tests/eval/train_autoencoder.py (ramo
físico) — alternativa à classificação fechada (Dense(3, softmax)) usada em
best_model_cyber.keras.

Motivação: os testes de ataque sintético em tests/attacks/*_cyber.py
mostraram que o classificador fechado do ramo ciber também sofre de
overfitting à instância — mesmo DoS numa magnitude próxima da real (log de
treino) só é detectado em 26,1% dos casos, e nenhuma janela é reconhecida
como "DoS attack" (as sinalizadas são confundidas com Replay); Replay
canônico (retransmissão literal de tráfego benigno) tem 0% de deteção (ver
tests/README.md, seção "Ramo ciber"). Um autoencoder treinado só com
tráfego `benign` não depende de rótulo de ataque: aprende a reconstruir o
padrão de tráfego legítimo, e qualquer desvio — de magnitude/forma
diferente ou não — tende a produzir erro de reconstrução alto.

Pipeline (espelha train_autoencoder.py, adaptado ao ramo ciber):
  1. Carrega a subsequência `benign` do Dataset T-ITS via
     tests/common/features_cyber.py (mesmas FEATS_V2/WINDOW do notebook de
     treino do ramo ciber).
  2. Split sequencial 80/20 (treino/validação) por ÍNDICE DE LINHA, sem
     embaralhar — mesmo espírito do ramo físico, adaptado à estrutura de
     captura em sessões do T-ITS (ver features_cyber.py).
  3. Normaliza com o MESMO scaler de referência já persistido por
     tests/eval/fit_scaler_cyber.py.
  4. Treina um LSTM-Autoencoder a minimizar o erro de reconstrução (MSE)
     sobre as janelas de treino.
  5. Define o threshold de deteção como um percentil (padrão: 95) do erro
     de reconstrução nas janelas de VALIDAÇÃO (benign, não vistas em
     treino).
  6. Salva o modelo (.keras) e o threshold (.json) em tests/eval/.

Uso:
    python -m tests.eval.train_autoencoder_cyber \
        --out-model tests/eval/autoencoder_cyber.keras \
        --out-threshold tests/eval/autoencoder_cyber_threshold.json
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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.common.features_cyber import WINDOW, build_windows, load_benign_ordered

DEFAULT_SCALER = Path("tests/eval/cyber_scaler.joblib")


def load_benign_windows(window: int, frac_train: float):
    """Carrega o tráfego benign e retorna (janelas de treino, janelas de
    validação), com split sequencial por índice de linha (sem embaralhar)."""
    benign = load_benign_ordered()
    split = int(frac_train * len(benign))
    train_df = benign.iloc[:split].reset_index(drop=True)
    val_df = benign.iloc[split:].reset_index(drop=True)

    X_train, _ = build_windows(train_df, window)
    X_val, _ = build_windows(val_df, window)
    return X_train, X_val


def build_autoencoder(window: int, n_features: int, latent_dim: int = 8):
    import tensorflow as tf
    from tensorflow.keras import layers, models

    inputs = layers.Input(shape=(window, n_features))
    encoded = layers.LSTM(16, activation="tanh", return_sequences=True)(inputs)
    encoded = layers.LSTM(latent_dim, activation="tanh", return_sequences=False)(encoded)

    decoded = layers.RepeatVector(window)(encoded)
    decoded = layers.LSTM(latent_dim, activation="tanh", return_sequences=True)(decoded)
    decoded = layers.LSTM(16, activation="tanh", return_sequences=True)(decoded)
    outputs = layers.TimeDistributed(layers.Dense(n_features))(decoded)

    model = models.Model(inputs, outputs, name="lstm_autoencoder_cyber")
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3), loss="mse")
    return model


def reconstruction_error(model, X: np.ndarray) -> np.ndarray:
    X_hat = model.predict(X, verbose=0)
    return np.mean(np.square(X - X_hat), axis=(1, 2))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--window", type=int, default=WINDOW)
    parser.add_argument("--frac-train", type=float, default=0.8, help="Fração inicial da subsequência benign usada em treino")
    parser.add_argument("--latent-dim", type=int, default=8)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--percentile", type=float, default=95.0, help="Percentil do erro de validação usado como threshold")
    parser.add_argument("--scaler", default=str(DEFAULT_SCALER), help="Scaler .joblib persistido (tests.eval.fit_scaler_cyber)")
    parser.add_argument("--out-model", default="tests/eval/autoencoder_cyber.keras")
    parser.add_argument("--out-threshold", default="tests/eval/autoencoder_cyber_threshold.json")
    args = parser.parse_args()

    import tensorflow as tf  # import tardio: só quando o script roda de fato

    scaler_path = Path(args.scaler)
    if not scaler_path.is_file():
        raise FileNotFoundError(
            f"Scaler não encontrado em {scaler_path}. Rode primeiro:\n"
            "  python -m tests.eval.fit_scaler_cyber --out tests/eval/cyber_scaler.joblib"
        )
    scaler = joblib.load(scaler_path)

    print(f"Carregando tráfego benign e montando janelas (window={args.window})...")
    X_train, X_val = load_benign_windows(args.window, args.frac_train)
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

    print("\nCalculando threshold de deteção sobre o erro de reconstrução da validação (benign)...")
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

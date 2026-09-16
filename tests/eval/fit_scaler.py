"""Reconstrói e persiste (joblib) o StandardScaler do treino do ramo físico
(PX4-QUAD-SITL), para deixar de precisar reconstruí-lo a cada avaliação.

O notebook de treino (Infos_lstm_fusao_px4.ipynb) não salva o scaler — só o
`.keras`. Este script roda a mesma reconstrução já usada em
tests/eval/evaluate_model.py (fit_reference_scaler) e salva o resultado uma
única vez; evaluate_model.py passa a carregar esse arquivo via --scaler em
vez de reajustar o scaler a cada execução.

Uso:
    python -m tests.eval.fit_scaler --out tests/eval/px4_scaler.joblib
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.eval.evaluate_model import WINDOW, fit_reference_scaler


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--window", type=int, default=WINDOW, help="Tamanho da janela (padrão: mesmo do treino)")
    parser.add_argument("--frac-train", type=float, default=0.8, help="Fração de treino usada no split por voo")
    parser.add_argument("--out", default="tests/eval/px4_scaler.joblib", help="Caminho de saída do scaler")
    args = parser.parse_args()

    print("Reconstruindo o StandardScaler de referência (mesmo split do notebook)...")
    scaler = fit_reference_scaler(window=args.window, frac_train=args.frac_train)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(scaler, out_path)
    print(f"Scaler salvo em: {out_path}")
    print(f"n_features_in_={scaler.n_features_in_}")


if __name__ == "__main__":
    main()

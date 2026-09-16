"""Simula um ataque de GPS spoofing progressivo sobre um voo do PX4-QUAD-SITL.

Ideia do ataque: o atacante transmite sinais GPS falsos com posição/velocidade
que se desviam gradualmente da realidade (spoofing "lento", para não disparar
checagens grosseiras de salto instantâneo). A cada passo dentro da janela de
ataque, soma-se um deslocamento crescente (drift linear, `--drift-rate` m/s)
na direção `--heading-deg` a:

  - x, y            -> posição fundida (o que o EKF "acredita" ser sua posição,
                        já que confia parcialmente no GPS)
  - vel_n_m_s/vel_e_m_s -> velocidade reportada pelo GPS

vx/vy (velocidade estimada pelo EKF/outros sensores) são deixados intactos:
isso faz `dv_xy = |v_xy_loc - v_xy_gps|` crescer, e `r_xy` (deriva acumulada
desde o início do log) disparar — a mesma assinatura observada no log real de
"GPS Spoofing" do dataset (r_xy da ordem de 10^4-10^5 m vs ~10^2 m em voo
normal, ver notebooks/Analise UAVAttackData PX4-QUAD/DOCUMENTO.md).

Saída: CSV com as mesmas colunas do pipeline de treino, mais `is_attack`
(0/1), pronto para tests/eval/evaluate_model.py.

Uso:
    python -m tests.attacks.gps_spoofing_attack \
        --attack-start 60 --duration 20 --drift-rate 5 --heading-deg 45 \
        --out tests/outputs/gps_spoofing/normal_spoofed.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.common.features import add_derived_features, find_px4_quad_sitl, load_merged


def inject_gps_spoofing(
    df: pd.DataFrame,
    attack_start_s: float,
    duration_s: float,
    drift_rate_m_s: float,
    heading_deg: float,
) -> pd.DataFrame:
    """Soma um drift linear crescente a x/y e vel_n_m_s/vel_e_m_s durante o ataque.

    O drift começa em 0 no início da janela e cresce `drift_rate_m_s` por
    segundo decorrido de ataque — simula um spoofing gradual, não um salto
    instantâneo (mais difícil de detectar por regras simples de threshold).
    """
    df = df.sort_values("timestamp").reset_index(drop=True)
    t0 = df["timestamp"].iloc[0]
    t = (df["timestamp"] - t0) / 1e6  # PX4 timestamp em us -> segundos relativos

    attack_mask = (t >= attack_start_s) & (t < attack_start_s + duration_s)
    if attack_mask.sum() == 0:
        raise ValueError("Janela de ataque vazia — ajuste --attack-start/--duration.")

    heading_rad = np.deg2rad(heading_deg)
    dx_dir, dy_dir = np.cos(heading_rad), np.sin(heading_rad)

    elapsed = (t - attack_start_s).clip(lower=0.0)
    drift_mag = np.where(attack_mask, elapsed * drift_rate_m_s, 0.0)

    df["x"] = df["x"] + drift_mag * dx_dir
    df["y"] = df["y"] + drift_mag * dy_dir
    # GPS reporta a velocidade "necessária" para sustentar o drift crescente:
    # soma o próprio drift_rate à componente reportada de velocidade N/E.
    df.loc[attack_mask, "vel_n_m_s"] = df.loc[attack_mask, "vel_n_m_s"] + drift_rate_m_s * dx_dir
    df.loc[attack_mask, "vel_e_m_s"] = df.loc[attack_mask, "vel_e_m_s"] + drift_rate_m_s * dy_dir

    df["is_attack"] = attack_mask.astype(int)
    return df


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--flight", default="Normal", help="Subpasta do voo fonte (padrão: Normal)")
    parser.add_argument("--attack-start", type=float, default=60.0, help="Início (s) do spoofing")
    parser.add_argument("--duration", type=float, default=20.0, help="Duração (s) do spoofing")
    parser.add_argument("--drift-rate", type=float, default=5.0, help="Taxa de deriva (m/s) dentro do ataque")
    parser.add_argument("--heading-deg", type=float, default=45.0, help="Direção do drift (graus, 0=N, 90=E)")
    parser.add_argument("--out", default=None, help="Caminho do CSV de saída")
    args = parser.parse_args()

    base = find_px4_quad_sitl()
    folder = base / args.flight
    merged = load_merged(folder, condition=args.flight)

    attacked = inject_gps_spoofing(merged, args.attack_start, args.duration, args.drift_rate, args.heading_deg)
    attacked = add_derived_features(attacked)

    out_path = Path(args.out) if args.out else Path("tests/outputs/gps_spoofing") / f"{args.flight.lower()}_spoofed.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    attacked.to_csv(out_path, index=False)

    n_attack = int(attacked["is_attack"].sum())
    max_r_xy_attack = attacked.loc[attacked["is_attack"] == 1, "r_xy"].max() if n_attack else float("nan")
    print(f"Voo fonte: {folder}")
    print(f"Linhas totais: {len(attacked)} | linhas marcadas como ataque: {n_attack}")
    print(f"r_xy máximo durante o ataque: {max_r_xy_attack:.2f} m")
    print(f"CSV salvo em: {out_path}")


if __name__ == "__main__":
    main()

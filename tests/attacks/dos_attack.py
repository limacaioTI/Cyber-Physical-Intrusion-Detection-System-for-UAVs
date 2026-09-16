"""Simula um ataque de negação de serviço (DoS) sobre o enlace de um voo do
PX4-QUAD-SITL — inspirado no cenário "Ping DoS" do dataset (flood no enlace
que atrasa/derruba telemetria).

Ressalva importante (ver notebooks/Analise UAVAttackData PX4-QUAD/DOCUMENTO.md,
§3): no log real de "Ping DoS" do dataset, o `dt` entre amostras ficou
estável (~0,10s) igual às outras pastas — ou seja, o flood de rede não
necessariamente aparece como gap na cadência do log de bordo (o log é local,
não reflete o enlace ar-terra diretamente). Isso é uma das razões prováveis
do recall baixo (~0,23) do modelo nessa classe.

Por isso este ataque simula DUAS formas de degradação, para comparar:

  --mode gaps   : derruba uma fração das amostras dentro da janela de ataque
                  (perda de pacotes "clássica" — gera dt maior, mas pode não
                  bater com o padrão que o modelo aprendeu, ver ressalva acima).
  --mode freeze : mantém a cadência de amostras, mas congela eph_gps/eph_loc e
                  as inovações do EKF (`vel_pos_innov`) no último valor válido
                  antes do ataque — simula o autopiloto "perdendo" atualização
                  do enlace mas continuando a logar localmente, o que é mais
                  coerente com o achado do §3 do DOCUMENTO.md.

Saída: CSV com is_attack (0/1), pronto para tests/eval/evaluate_model.py.

Uso:
    python -m tests.attacks.dos_attack \
        --attack-start 60 --duration 20 --mode gaps --drop-prob 0.7 \
        --out tests/outputs/dos/normal_dos_gaps.csv

    python -m tests.attacks.dos_attack \
        --attack-start 60 --duration 20 --mode freeze \
        --out tests/outputs/dos/normal_dos_freeze.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.common.features import add_derived_features, find_px4_quad_sitl, load_merged

FREEZE_COLS = [
    "eph_loc",
    "eph_gps",
    "vel_pos_innov[0]",
    "vel_pos_innov[1]",
    "vel_pos_innov[2]",
]


def _attack_mask(df: pd.DataFrame, attack_start_s: float, duration_s: float) -> pd.Series:
    t0 = df["timestamp"].iloc[0]
    t = (df["timestamp"] - t0) / 1e6
    mask = (t >= attack_start_s) & (t < attack_start_s + duration_s)
    if mask.sum() == 0:
        raise ValueError("Janela de ataque vazia — ajuste --attack-start/--duration.")
    return mask


def inject_dos_gaps(df: pd.DataFrame, attack_start_s: float, duration_s: float, drop_prob: float, seed: int) -> pd.DataFrame:
    """Derruba `drop_prob` das amostras dentro da janela de ataque (perda de pacotes)."""
    df = df.sort_values("timestamp").reset_index(drop=True)
    mask = _attack_mask(df, attack_start_s, duration_s)

    rng = np.random.default_rng(seed)
    drop = mask & (rng.random(len(df)) < drop_prob)

    df["is_attack"] = (mask & ~drop).astype(int)
    kept = df.loc[~drop].reset_index(drop=True)
    return kept


def inject_dos_freeze(df: pd.DataFrame, attack_start_s: float, duration_s: float) -> pd.DataFrame:
    """Congela eph_loc/eph_gps/inovações no último valor válido antes do ataque,
    mantendo a cadência de amostras (dt inalterado)."""
    df = df.sort_values("timestamp").reset_index(drop=True)
    mask = _attack_mask(df, attack_start_s, duration_s)

    first_attack_idx = df.index[mask][0]
    frozen_values = df.loc[first_attack_idx - 1, FREEZE_COLS]
    for col in FREEZE_COLS:
        df.loc[mask, col] = frozen_values[col]

    df["is_attack"] = mask.astype(int)
    return df


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--flight", default="Normal", help="Subpasta do voo fonte (padrão: Normal)")
    parser.add_argument("--attack-start", type=float, default=60.0, help="Início (s) do DoS")
    parser.add_argument("--duration", type=float, default=20.0, help="Duração (s) do DoS")
    parser.add_argument("--mode", choices=["gaps", "freeze"], default="gaps")
    parser.add_argument("--drop-prob", type=float, default=0.7, help="[gaps] fração de amostras derrubadas")
    parser.add_argument("--seed", type=int, default=42, help="[gaps] semente do sorteio de drops")
    parser.add_argument("--out", default=None, help="Caminho do CSV de saída")
    args = parser.parse_args()

    base = find_px4_quad_sitl()
    folder = base / args.flight
    merged = load_merged(folder, condition=args.flight)

    if args.mode == "gaps":
        attacked = inject_dos_gaps(merged, args.attack_start, args.duration, args.drop_prob, args.seed)
    else:
        attacked = inject_dos_freeze(merged, args.attack_start, args.duration)
    attacked = add_derived_features(attacked)

    out_path = Path(args.out) if args.out else Path("tests/outputs/dos") / f"{args.flight.lower()}_dos_{args.mode}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    attacked.to_csv(out_path, index=False)

    n_attack = int(attacked["is_attack"].sum())
    print(f"Voo fonte: {folder} | modo: {args.mode}")
    print(f"Linhas totais: {len(attacked)} | linhas marcadas como ataque: {n_attack}")
    print(f"CSV salvo em: {out_path}")


if __name__ == "__main__":
    main()

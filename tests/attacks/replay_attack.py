"""Simula um ataque de replay sobre um voo "Normal" do PX4-QUAD-SITL.

Ideia do ataque: o atacante grava uma janela de telemetria legítima capturada
mais cedo no voo (`--source-start`) e a retransmite mais tarde (`--attack-start`),
sobrescrevendo os valores "ao vivo" durante `--duration` segundos. O timestamp
continua a avançar normalmente (o atacante não consegue voltar o relógio do
autopiloto), mas x/y/z/vx/vy/vz/eph/inovações ficam "congelados" repetindo o
trecho antigo — a assinatura clássica de replay: estado físico não muda de
forma consistente com o tempo que passa.

Saída: um CSV com as mesmas colunas usadas pelo pipeline de treino
(tests/common/features.py) mais uma coluna `is_attack` (0/1), pronto para
avaliação por um IDS (ver tests/eval/, a implementar).

Uso:
    python -m tests.attacks.replay_attack \
        --source-start 5 --attack-start 60 --duration 15 \
        --out tests/outputs/replay/normal_replay.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.common.features import add_derived_features, find_px4_quad_sitl, load_merged


def inject_replay(df: pd.DataFrame, source_start_s: float, attack_start_s: float, duration_s: float) -> pd.DataFrame:
    """Substitui os campos físicos no intervalo [attack_start, attack_start+duration)
    pelos valores gravados em [source_start, source_start+duration), mantendo o
    timestamp original (o atacante não controla o relógio do veículo).
    """
    df = df.sort_values("timestamp").reset_index(drop=True)
    t0 = df["timestamp"].iloc[0]
    t = (df["timestamp"] - t0) / 1e6  # timestamp PX4 é us -> segundos relativos

    replay_cols = [
        "x", "y", "z", "vx", "vy", "vz",
        "eph_loc", "eph_gps",
        "vel_n_m_s", "vel_e_m_s", "vel_d_m_s",
        "vel_pos_innov[0]", "vel_pos_innov[1]", "vel_pos_innov[2]",
    ]
    replay_cols = [c for c in replay_cols if c in df.columns]

    source_mask = (t >= source_start_s) & (t < source_start_s + duration_s)
    attack_mask = (t >= attack_start_s) & (t < attack_start_s + duration_s)

    n_source = int(source_mask.sum())
    n_attack = int(attack_mask.sum())
    if n_source == 0 or n_attack == 0:
        raise ValueError("Janela de origem ou de ataque vazia — ajuste os offsets.")

    source_block = df.loc[source_mask, replay_cols].to_numpy()
    # Repete/trunca o bloco gravado para cobrir exatamente as amostras do trecho atacado.
    reps = int(np.ceil(n_attack / n_source))
    replayed = np.tile(source_block, (reps, 1))[:n_attack]

    df.loc[attack_mask, replay_cols] = replayed
    df["is_attack"] = attack_mask.astype(int)
    return df


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--flight", default="Normal", help="Subpasta do voo fonte (padrão: Normal)")
    parser.add_argument("--source-start", type=float, default=5.0, help="Início (s) do trecho legítimo gravado")
    parser.add_argument("--attack-start", type=float, default=60.0, help="Início (s) da reinjeção")
    parser.add_argument("--duration", type=float, default=15.0, help="Duração (s) do ataque")
    parser.add_argument("--out", default=None, help="Caminho do CSV de saída")
    args = parser.parse_args()

    base = find_px4_quad_sitl()
    folder = base / args.flight
    merged = load_merged(folder, condition=args.flight)

    # Injeta o replay nas colunas cruas ANTES de derivar innov_norm/dv_xy/r_xy,
    # para que as features derivadas reflitam os valores replayados (não os originais).
    attacked = inject_replay(merged, args.source_start, args.attack_start, args.duration)
    attacked = add_derived_features(attacked)

    out_path = Path(args.out) if args.out else Path("tests/outputs/replay") / f"{args.flight.lower()}_replay.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    attacked.to_csv(out_path, index=False)

    n_attack = int(attacked["is_attack"].sum())
    print(f"Voo fonte: {folder}")
    print(f"Linhas totais: {len(attacked)} | linhas marcadas como ataque: {n_attack}")
    print(f"CSV salvo em: {out_path}")


if __name__ == "__main__":
    main()

"""Simula um ataque de DoS (inundação de pacotes) sobre tráfego `benign`
real do Dataset T-ITS — equivalente, no ramo ciber, ao tests/attacks/dos_attack.py
do ramo físico.

Diferença em relação ao ramo físico: o Dataset T-ITS é tráfego de rede
capturado em sessões, com saltos grandes de tempo entre blocos — não é um
único voo contínuo. Por isso a janela de ataque aqui é definida por
ÍNDICE DE LINHA (`--attack-start-row`/`--duration-rows`) sobre a
subsequência `benign` ordenada por `timestamp_c`, não por segundos
decorridos.

Ideia do ataque: DoS real (classe `DoS attack` no dataset) tem pacotes bem
menores e mais frequentes que o tráfego benigno (ver
notebooks/Analise Dataset T-ITS/DOCUMENTO.md, §3.2 e §4.2: frame.len médio
~44 em DoS attack vs ~127 em benign; ritmo de captura mais denso). Este
script simula isso sinteticamente: durante a janela de ataque, encolhe os
tamanhos de pacote (`frame.len`/`ip.len`/`udp.length`/`data.len`, divididos
por `--size-divisor`) e acelera o ritmo (`time_since_last_packet` dividido
por `--rate-multiplier`) — parametrizável para testar deteção em diferentes
intensidades (suave vs. agressivo), como já feito para GPS Spoofing no ramo
físico.

Saída: CSV com as mesmas colunas usadas pelo pipeline de treino do ramo
ciber, mais `is_attack` (0/1), pronto para
tests/eval/evaluate_model_cyber.py.

Uso:
    python -m tests.attacks.dos_attack_cyber \
        --attack-start-row 500 --duration-rows 60 \
        --rate-multiplier 2 --size-divisor 1.5 \
        --out tests/outputs/dos_cyber/benign_dos_suave.csv

    python -m tests.attacks.dos_attack_cyber \
        --attack-start-row 500 --duration-rows 60 \
        --rate-multiplier 20 --size-divisor 4 \
        --out tests/outputs/dos_cyber/benign_dos_agressivo.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.common.features_cyber import load_benign_ordered

SIZE_COLS = ["frame.len", "ip.len", "udp.length", "data.len"]


def inject_dos_flood(
    df: pd.DataFrame,
    attack_start_row: int,
    duration_rows: int,
    rate_multiplier: float,
    size_divisor: float,
) -> pd.DataFrame:
    """Encolhe pacotes e acelera o ritmo de captura na janela [start, start+duration)."""
    df = df.reset_index(drop=True).copy()
    n = len(df)
    end_row = min(attack_start_row + duration_rows, n)
    if attack_start_row >= n or end_row <= attack_start_row:
        raise ValueError(f"Janela de ataque fora do intervalo válido (0..{n}).")

    mask = pd.Series(False, index=df.index)
    mask.iloc[attack_start_row:end_row] = True

    df["time_since_last_packet"] = df["time_since_last_packet"].astype(np.float64)
    for col in SIZE_COLS:
        df[col] = df[col].astype(np.float64)

    df.loc[mask, "time_since_last_packet"] = df.loc[mask, "time_since_last_packet"] / rate_multiplier
    for col in SIZE_COLS:
        df.loc[mask, col] = df.loc[mask, col] / size_divisor

    df["is_attack"] = mask.astype(int)
    return df


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--attack-start-row", type=int, default=500, help="Índice de linha (na subsequência benign) onde o DoS começa")
    parser.add_argument("--duration-rows", type=int, default=60, help="Duração do DoS em número de linhas/pacotes")
    parser.add_argument("--rate-multiplier", type=float, default=5.0, help="Divide time_since_last_packet por este fator (ritmo mais denso)")
    parser.add_argument("--size-divisor", type=float, default=3.0, help="Divide frame.len/ip.len/udp.length/data.len por este fator")
    parser.add_argument("--out", default=None, help="Caminho do CSV de saída")
    args = parser.parse_args()

    benign = load_benign_ordered()
    print(f"Linhas benign disponíveis: {len(benign)}")

    attacked = inject_dos_flood(
        benign, args.attack_start_row, args.duration_rows, args.rate_multiplier, args.size_divisor
    )

    out_path = Path(args.out) if args.out else Path("tests/outputs/dos_cyber") / "benign_dos.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    attacked.to_csv(out_path, index=False)

    n_attack = int(attacked["is_attack"].sum())
    print(f"Linhas totais: {len(attacked)} | linhas marcadas como ataque: {n_attack}")
    print(
        f"  frame.len durante o ataque: média={attacked.loc[attacked['is_attack'] == 1, 'frame.len'].mean():.2f} "
        f"(benign médio geral: {benign['frame.len'].mean():.2f})"
    )
    print(
        f"  time_since_last_packet durante o ataque: média={attacked.loc[attacked['is_attack'] == 1, 'time_since_last_packet'].mean():.6f} "
        f"(benign médio geral: {benign['time_since_last_packet'].mean():.6f})"
    )
    print(f"CSV salvo em: {out_path}")


if __name__ == "__main__":
    main()

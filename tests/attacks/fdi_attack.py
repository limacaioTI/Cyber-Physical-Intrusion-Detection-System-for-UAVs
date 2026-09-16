"""Simula um ataque de False Data Injection (FDI) sobre um voo do PX4-QUAD-SITL.

Ideia do ataque: diferente de replay (repete um trecho passado) e de GPS
spoofing (deriva gradual e crescente, para escapar de checagens de salto
instantâneo), FDI é a manipulação direta e abrupta de uma leitura de sensor
ou estado interno na camada de aplicação — o atacante escreve um valor
fabricado, fora da faixa plausível, sem qualquer relação com a evolução real
do voo. Aqui isso é simulado como um salto instantâneo (degrau, não rampa)
em uma ou mais colunas-alvo durante a janela de ataque, sustentado no mesmo
valor até o fim do ataque.

Modos de injeção (`--mode`):
  absolute : fixa a(s) coluna(s)-alvo em `--value` durante o ataque (valor
             fabricado, dissociado do valor real).
  offset   : soma `--value` ao valor real (deslocamento constante, sem rampa
             — ao contrário do drift crescente do gps_spoofing_attack.py).
  scale    : multiplica o valor real por `--value` (ex.: inflar eph_gps para
             simular um sensor de incerteza corrompido).

Por padrão, ataca `eph_gps`/`eph_loc` (leituras de incerteza de posição) com
`--mode scale`, um vetor plausível de FDI: o atacante força o filtro a
reportar alta incerteza/confiança falsa sem mexer em x/y/z diretamente. Use
`--targets` para atacar outras colunas (ex.: x,y,z para injeção de posição
falsa).

Saída: CSV com as mesmas colunas do pipeline de treino, mais `is_attack`
(0/1), pronto para tests/eval/evaluate_model.py.

Uso:
    python -m tests.attacks.fdi_attack \
        --attack-start 60 --duration 20 --mode scale --value 50 \
        --targets eph_loc,eph_gps \
        --out tests/outputs/fdi/normal_fdi_eph.csv

    python -m tests.attacks.fdi_attack \
        --attack-start 60 --duration 15 --mode absolute --value 1000 \
        --targets x,y \
        --out tests/outputs/fdi/normal_fdi_position.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.common.features import add_derived_features, find_px4_quad_sitl, load_merged

DEFAULT_TARGETS = ["eph_loc", "eph_gps"]


def _attack_mask(df: pd.DataFrame, attack_start_s: float, duration_s: float) -> pd.Series:
    t0 = df["timestamp"].iloc[0]
    t = (df["timestamp"] - t0) / 1e6
    mask = (t >= attack_start_s) & (t < attack_start_s + duration_s)
    if mask.sum() == 0:
        raise ValueError("Janela de ataque vazia — ajuste --attack-start/--duration.")
    return mask


def inject_fdi(
    df: pd.DataFrame,
    attack_start_s: float,
    duration_s: float,
    mode: str,
    value: float,
    targets: list[str],
) -> pd.DataFrame:
    """Aplica o degrau/offset/escala fabricado nas colunas-alvo durante a janela de ataque."""
    df = df.sort_values("timestamp").reset_index(drop=True)
    mask = _attack_mask(df, attack_start_s, duration_s)

    missing = [c for c in targets if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas-alvo ausentes no log: {missing}")

    for col in targets:
        if mode == "absolute":
            df.loc[mask, col] = value
        elif mode == "offset":
            df.loc[mask, col] = df.loc[mask, col] + value
        elif mode == "scale":
            df.loc[mask, col] = df.loc[mask, col] * value
        else:
            raise ValueError(f"Modo desconhecido: {mode}")

    df["is_attack"] = mask.astype(int)
    return df


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--flight", default="Normal", help="Subpasta do voo fonte (padrão: Normal)")
    parser.add_argument("--attack-start", type=float, default=60.0, help="Início (s) do FDI")
    parser.add_argument("--duration", type=float, default=20.0, help="Duração (s) do FDI")
    parser.add_argument("--mode", choices=["absolute", "offset", "scale"], default="scale")
    parser.add_argument("--value", type=float, default=50.0, help="Valor fabricado/deslocamento/fator, conforme --mode")
    parser.add_argument(
        "--targets",
        default=",".join(DEFAULT_TARGETS),
        help=f"Colunas-alvo separadas por vírgula (padrão: {','.join(DEFAULT_TARGETS)})",
    )
    parser.add_argument("--out", default=None, help="Caminho do CSV de saída")
    args = parser.parse_args()

    targets = [c.strip() for c in args.targets.split(",") if c.strip()]

    base = find_px4_quad_sitl()
    folder = base / args.flight
    merged = load_merged(folder, condition=args.flight)

    # Injeta o FDI nas colunas cruas ANTES de derivar innov_norm/dv_xy/r_xy,
    # para que as features derivadas reflitam os valores fabricados.
    attacked = inject_fdi(merged, args.attack_start, args.duration, args.mode, args.value, targets)
    attacked = add_derived_features(attacked)

    out_path = Path(args.out) if args.out else Path("tests/outputs/fdi") / f"{args.flight.lower()}_fdi_{args.mode}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    attacked.to_csv(out_path, index=False)

    n_attack = int(attacked["is_attack"].sum())
    print(f"Voo fonte: {folder} | modo: {args.mode} | alvos: {targets}")
    print(f"Linhas totais: {len(attacked)} | linhas marcadas como ataque: {n_attack}")
    for col in targets:
        vals = attacked.loc[attacked["is_attack"] == 1, col]
        print(f"  {col} durante o ataque: min={vals.min():.3f} max={vals.max():.3f}")
    print(f"CSV salvo em: {out_path}")


if __name__ == "__main__":
    main()

"""Simula um ataque de replay sobre tráfego `benign` real do Dataset T-ITS —
equivalente, no ramo ciber, ao tests/attacks/replay_attack.py do ramo físico.

Ideia do ataque: o atacante grava um bloco de pacotes legítimos capturados
mais cedo (`--source-start-row`, em número de linhas) e o retransmite mais
tarde (`--attack-start-row`), sobrescrevendo as features de rede
(FEATS_V2) durante `--duration-rows` linhas. Diferente do ramo físico
(timestamp contínuo de voo), aqui a ordem de linha É a ordem temporal da
subsequência `benign` — o replay preserva os valores exatos de um trecho já
visto, só reordenado no tempo.

Nota: `Replay` já é uma classe REAL do Dataset T-ITS (ver aviso em
tests/README.md) — mas o log real de Replay não é uma repetição literal de
tráfego benigno, é uma sessão de captura própria com estatísticas
diferentes (frame.len médio ~49, perto de DoS). Este script testa um replay
"canônico": retransmissão exata de pacotes benignos, o cenário mais difícil
de distinguir de tráfego legítimo por estatística pura (mesma distribuição
de tamanho/protocolo, só fora de ordem no tempo) — útil para avaliar se o
modelo usa `time_since_last_packet` (o único sinal que muda) para perceber
a repetição.

Saída: CSV com as mesmas colunas do pipeline de treino do ramo ciber, mais
`is_attack` (0/1), pronto para tests/eval/evaluate_model_cyber.py.

Uso:
    python -m tests.attacks.replay_attack_cyber \
        --source-start-row 50 --attack-start-row 500 --duration-rows 60 \
        --out tests/outputs/replay_cyber/benign_replay.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.common.features_cyber import FEATS_V2, load_benign_ordered


def inject_replay(
    df: pd.DataFrame,
    source_start_row: int,
    attack_start_row: int,
    duration_rows: int,
) -> pd.DataFrame:
    """Substitui FEATS_V2 no intervalo [attack_start_row, attack_start_row+duration_rows)
    pelos valores gravados em [source_start_row, source_start_row+duration_rows).
    `timestamp_c` original é preservado (o atacante não controla o relógio)."""
    df = df.reset_index(drop=True).copy()
    n = len(df)

    source_end = min(source_start_row + duration_rows, n)
    attack_end = min(attack_start_row + duration_rows, n)
    if source_start_row >= n or source_end <= source_start_row:
        raise ValueError(f"Janela de origem fora do intervalo válido (0..{n}).")
    if attack_start_row >= n or attack_end <= attack_start_row:
        raise ValueError(f"Janela de ataque fora do intervalo válido (0..{n}).")

    n_source = source_end - source_start_row
    n_attack = attack_end - attack_start_row

    source_block = df.loc[source_start_row : source_end - 1, FEATS_V2].to_numpy()
    reps = int(np.ceil(n_attack / n_source))
    replayed = np.tile(source_block, (reps, 1))[:n_attack]

    attack_mask = pd.Series(False, index=df.index)
    attack_mask.iloc[attack_start_row:attack_end] = True

    df.loc[attack_mask, FEATS_V2] = replayed
    df["is_attack"] = attack_mask.astype(int)
    return df


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-start-row", type=int, default=50, help="Início (linha) do trecho legítimo gravado")
    parser.add_argument("--attack-start-row", type=int, default=500, help="Início (linha) da reinjeção")
    parser.add_argument("--duration-rows", type=int, default=60, help="Duração do ataque em número de linhas")
    parser.add_argument("--out", default=None, help="Caminho do CSV de saída")
    args = parser.parse_args()

    benign = load_benign_ordered()
    print(f"Linhas benign disponíveis: {len(benign)}")

    attacked = inject_replay(benign, args.source_start_row, args.attack_start_row, args.duration_rows)

    out_path = Path(args.out) if args.out else Path("tests/outputs/replay_cyber") / "benign_replay.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    attacked.to_csv(out_path, index=False)

    n_attack = int(attacked["is_attack"].sum())
    print(f"Linhas totais: {len(attacked)} | linhas marcadas como ataque: {n_attack}")
    print(f"CSV salvo em: {out_path}")


if __name__ == "__main__":
    main()

# tests/ — simulação de ataques e avaliação dos IDS

Pasta de testes do TCC: gera cenários de ataque sobre os voos do PX4-QUAD-SITL
já existentes em `data/UAVAttackData/`, e (próximo passo) avalia os modelos
treinados (`notebooks/.../best_model_px4.keras`) contra esses cenários.

> **Importante — classes reais vs. ataques sintéticos.** O dataset
> PX4-QUAD-SITL só tem 3 pastas de log, logo 3 classes reais de treino:
> `Normal`, `GPS Spoofing` e `Ping DoS`. **Replay e FDI não existem como
> classe no dataset** — não há pasta de log rotulada como tal, e o modelo
> nunca viu esses rótulos em treino (o FDI, inclusive, é citado no
> referencial teórico do TCC como vetor sem rótulo dedicado nos datasets
> usados). `tests/attacks/replay_attack.py` e `tests/attacks/fdi_attack.py`
> geram esses dois cenários **sinteticamente**, injetando o padrão de
> ataque em cima de um voo `Normal` real — não são uma 4ª/5ª classe do
> PX4-QUAD-SITL, são testes de generalização: avaliam como o IDS reage a um
> ataque que ele nunca viu em treino, o que é o cenário mais realista para
> um atacante real (que não está limitado ao repertório do seu dataset).
> `gps_spoofing_attack.py` e `dos_attack.py`, por outro lado, geram
> variações sintéticas de classes que **existem** no treino (GPS Spoofing e
> Ping DoS), só variando a magnitude/forma do ataque.

## Estrutura

```
tests/
├── common/
│   ├── features.py       # engenharia de features do ramo FÍSICO (PX4), espelha o notebook
│   │                      # (load_merged, add_derived_features, FEATS, WINDOW, build_windows)
│   └── features_cyber.py # engenharia de features do ramo CIBER (T-ITS), espelha o notebook
│                          # (load_benign_ordered, FEATS_V2, WINDOW, build_windows)
├── attacks/
│   ├── replay_attack.py         # [físico] replay sobre um voo Normal
│   ├── gps_spoofing_attack.py   # [físico] drift progressivo de GPS
│   ├── dos_attack.py            # [físico] gaps/freeze simulando degradação do enlace
│   ├── fdi_attack.py            # [físico] injeção de dados falsos (degrau abrupto)
│   ├── dos_attack_cyber.py      # [ciber] flood sintético sobre tráfego benign
│   └── replay_attack_cyber.py   # [ciber] replay canônico sobre tráfego benign
├── eval/
│   ├── evaluate_model.py        # [físico] avalia o classificador (.keras) contra um CSV de ataque
│   ├── fit_scaler.py            # [físico] reconstrói e persiste (joblib) o scaler de referência
│   ├── train_autoencoder.py     # [físico] treina o LSTM-Autoencoder (só voos Normal)
│   ├── evaluate_autoencoder.py  # [físico] avalia o autoencoder por erro de reconstrução + threshold
│   ├── evaluate_model_cyber.py  # [ciber] avalia o classificador (.keras) contra um CSV de ataque
│   └── fit_scaler_cyber.py      # [ciber] reconstrói e persiste (joblib) o scaler de referência
└── outputs/             # CSVs gerados pelos ataques (não versionados nos dados brutos)
```

`tests/common/features.py` existe para que qualquer ataque novo (spoofing,
DoS, FDI) reaproveite exatamente a mesma pipeline de merge/features do
notebook de treino — garantindo que os CSVs gerados aqui sejam compatíveis
com os modelos já treinados.

## Replay attack

`tests/attacks/replay_attack.py` simula um atacante que grava um trecho de
telemetria legítima (`--source-start`, em segundos desde o início do voo) e o
retransmite mais tarde (`--attack-start`), sobrescrevendo x/y/z/vx/vy/vz,
`eph_loc`/`eph_gps` e as inovações de velocidade do EKF durante
`--duration` segundos. O timestamp continua avançando normalmente — só o
estado físico fica "congelado", repetindo o passado.

```bash
python -m tests.attacks.replay_attack \
    --flight Normal \
    --source-start 5 --attack-start 60 --duration 15 \
    --out tests/outputs/replay/normal_replay.csv
```

Saída: CSV com as mesmas colunas do pipeline de treino, mais uma coluna
`is_attack` (1 nas linhas reinjetadas, 0 no resto) para servir de rótulo na
avaliação.

## Avaliação do modelo

`tests/eval/evaluate_model.py` carrega um `.keras` treinado e avalia contra
um CSV de ataque (qualquer um gerado em `tests/attacks/`, desde que tenha a
coluna `is_attack`). Como o notebook de treino não salva o `StandardScaler`
usado para normalizar as janelas, o script pode **reconstruir o mesmo
scaler** do zero (refazendo o split treino/teste 80/20 por voo, exatamente
como no notebook, e ajustando o scaler só nas janelas de treino) — mas isso
é lento e redundante em cada execução. Rode uma vez:

```bash
python -m tests.eval.fit_scaler --out tests/eval/px4_scaler.joblib
```

e reaproveite o scaler persistido em todas as avaliações seguintes com
`--scaler tests/eval/px4_scaler.joblib` (se omitido, o script volta a
reconstruir do zero, mantendo compatibilidade com o comportamento anterior).

Como o modelo só foi treinado com 3 classes (Normal / GPS Spoofing / Ping
DoS) e nunca viu "replay" como rótulo, a avaliação não é um
`classification_report` contra uma 4ª classe — é um teste de deteção de
anomalia: compara a distribuição de predições nas janelas que tocam o
trecho atacado (`is_attack=1`) contra as janelas fora dele, reportando taxa
de deteção (previsão ≠ Normal durante o ataque) e taxa de falso alarme
(previsão ≠ Normal fora do ataque).

```bash
python -m tests.eval.evaluate_model \
    --attack-csv tests/outputs/replay/normal_replay.csv \
    --model "notebooks/Analise UAVAttackData PX4-QUAD/best_model_px4.keras"
```

## Achados — replay (classe não vista no treino)

O modelo foi treinado com `Dense(3, softmax)` — só existem 3 saídas possíveis
(Normal / GPS Spoofing / Ping DoS), não existe um "não sei". Como replay não é
nenhuma dessas classes, o resultado abaixo não é "o modelo detectou replay":
é "com qual das 3 classes conhecidas o modelo confundiu o replay".

Rodando `evaluate_model.py` sobre `tests/outputs/replay/normal_replay.csv`
(replay de 15s injetado aos 60s de um voo Normal):

- **146/189 (77%)** das janelas que tocam o trecho replayado foram
  classificadas como **Normal** — o modelo não percebeu nada de errado.
- **43/189 (23%)** foram classificadas como **GPS Spoofing** — o "salto" de
  estado causado pelo replay (posição/velocidade mudando de forma
  inconsistente com o tempo) se parece parcialmente com a assinatura de
  spoofing que o modelo aprendeu.
- Taxa de falso alarme fora do ataque: 4,4% (aceitável como baseline).

**Implicação para o TCC:** um IDS multi-classe fechado (softmax sobre rótulos
conhecidos) generaliza mal para tipos de ataque não vistos no treino — ele
tende a "encaixar" o desconhecido na classe mais parecida ou, na maioria dos
casos aqui, simplesmente não perceber (rotula como Normal). É uma limitação
real e citável; motiva discutir, como trabalho futuro, deteção de anomalia
(autoencoder, one-class SVM) em vez de classificação fechada. Como o **GPS
Spoofing é uma das 3 classes de treino**, a expectativa é uma taxa de deteção
bem mais alta que os 23% do replay — a comparar depois de rodar
`gps_spoofing_attack.py` (abaixo).

## GPS spoofing attack

`tests/attacks/gps_spoofing_attack.py` simula um spoofing de GPS progressivo:
um desvio (drift) que cresce linearmente ao longo de `--duration` segundos, na
direção `--heading-deg`, aplicado a `x`, `y` (posição fundida, o que o EKF
"acredita" ser sua posição) e a `vel_n_m_s`/`vel_e_m_s` (velocidade reportada
pelo GPS). `vx`/`vy` (velocidade do EKF/local) são deixados intactos, o que
faz `dv_xy` (uma das 11 features) crescer — a mesma assinatura observada no
log real de "GPS Spoofing" do dataset (`r_xy` explode para 10⁴–10⁵ m).

```bash
python -m tests.attacks.gps_spoofing_attack \
    --flight Normal \
    --attack-start 60 --duration 20 --drift-rate 5 --heading-deg 45 \
    --out tests/outputs/gps_spoofing/normal_spoofed.csv
```

### Achados — magnitude do drift importa (sensível à escala vista no treino)

Duas rodadas com `evaluate_model.py`, mesmo voo/janela de ataque, só variando
a intensidade do drift:

| Cenário | `drift-rate` / `duration` | `r_xy` máx. durante ataque | Taxa de deteção |
|---|---|---|---|
| Spoofing suave | 5 m/s / 20s | ~255 m | **0%** — 100% classificado como Normal |
| Spoofing agressivo | 200 m/s / 60s | ~11.900 m | **46,6%**, maioria corretamente como "GPS Spoofing" |

O log real de "GPS Spoofing" do dataset tem `r_xy` na ordem de 10⁴–10⁵ m (ver
`notebooks/Analise UAVAttackData PX4-QUAD/DOCUMENTO.md`, §3). O modelo parece
ter aprendido a reconhecer spoofing **apenas nessa escala** — um drift suave e
gradual (o que um atacante mais cauteloso faria, para evitar deteção) passa
completamente despercebido. Isso é outra limitação relevante para a
discussão do TCC: o F1 de 0,519 reportado no notebook para GPS Spoofing é
otimista para spoofings sutis, porque o único exemplo de treino é um ataque
de magnitude extrema.

## DoS attack

`tests/attacks/dos_attack.py` simula degradação do enlace de duas formas
(`--mode gaps` derruba amostras; `--mode freeze` mantém a cadência mas
congela `eph_loc`/`eph_gps`/inovações do EKF no último valor válido — ver
docstring do script para a justificativa de cada modo frente ao achado do
`DOCUMENTO.md` de que o `dt` do log real de "Ping DoS" não mostra gaps).

```bash
python -m tests.attacks.dos_attack --attack-start 60 --duration 20 --mode gaps --drop-prob 0.7
python -m tests.attacks.dos_attack --attack-start 60 --duration 20 --mode freeze
```

**Achado:** taxa de deteção **0%** nos dois modos (falso-alarme basal de
4,4% inalterado). Consistente com o recall baixo (0,23) de Ping DoS já
reportado no teste temporal do notebook — reforça que essa é a classe mais
fraca do modelo, e que a assinatura que ele aprendeu para "DoS" não se
generaliza nem para variações sintéticas simples do mesmo tipo de ataque.

## FDI attack (False Data Injection)

> FDI **não é uma classe do dataset PX4-QUAD-SITL** — não existe pasta de
> log real rotulada como FDI (ver aviso no topo deste README). O que
> `fdi_attack.py` gera é inteiramente sintético: um degrau fabricado sobre
> um voo `Normal` real, usado como teste de generalização contra um ataque
> fora do repertório de treino — igual ao Replay.

`tests/attacks/fdi_attack.py` simula manipulação direta de leituras/estados
na camada de aplicação: diferente de replay (repete um trecho passado) e de
spoofing (drift gradual crescente), o FDI aqui é um **degrau abrupto** —
valor fabricado, fixo, sem rampa — em uma ou mais colunas-alvo durante a
janela de ataque (`--mode absolute/offset/scale`).

```bash
python -m tests.attacks.fdi_attack \
    --attack-start 60 --duration 20 --mode scale --value 50 \
    --targets eph_loc,eph_gps \
    --out tests/outputs/fdi/normal_fdi_eph.csv

python -m tests.attacks.fdi_attack \
    --attack-start 60 --duration 15 --mode absolute --value 1000 \
    --targets x,y \
    --out tests/outputs/fdi/normal_fdi_position.csv
```

### Achados — FDI

Rodando `evaluate_model.py` sobre os dois cenários (injeção de incerteza
`eph_loc`/`eph_gps` e injeção de posição falsa `x`/`y`):

- **0% de deteção** nos dois casos — 100% das janelas que tocam o trecho
  atacado foram classificadas como **Normal**.
- Taxa de falso alarme fora do ataque: 4,4% (mesmo baseline dos outros
  ataques).

Mesmo um salto abrupto e artificial de 1000m em x/y — fisicamente absurdo
para um quadricóptero — não é percebido: o modelo compara apenas a janela
inteira contra os padrões vistos em treino, e como FDI não é nenhuma das 3
classes conhecidas (Normal/GPS Spoofing/Ping DoS), ele é "absorvido" como
Normal, exatamente como o Replay. Reforça a mesma conclusão do achado do
Replay: sem um mecanismo de "não sei" (classificação aberta ou deteção de
anomalia), qualquer vetor de ataque fora do repertório de treino tende a
passar despercebido.

## Síntese — os 4 vetores de ataque testados (classificador fechado)

| Ataque | Classe real do dataset PX4? | Visto no treino? | Taxa de deteção observada |
|---|---|---|---|
| Replay | Não — gerado sinteticamente sobre um voo Normal | Não (rótulo inexistente) | 23% (confundido majoritariamente com Normal) |
| GPS Spoofing suave (r_xy ~255m) | Sim (`GPS Spoofing`) | Sim, mas em outra escala | 0% |
| GPS Spoofing agressivo (r_xy ~11.900m, escala do treino) | Sim (`GPS Spoofing`) | Sim | 46,6% |
| DoS (gaps ou freeze) | Sim (`Ping DoS`) | Sim | 0% |
| FDI (degrau em eph_loc/eph_gps ou x/y) | Não — gerado sinteticamente sobre um voo Normal | Não (rótulo inexistente) | 0% |

Achado central: mesmo nas duas classes em que o modelo foi treinado
diretamente (Spoofing, DoS), a deteção só funciona quando o ataque sintético
reproduz de perto a magnitude/forma do único exemplo visto em treino. E para
os dois vetores fora do repertório de treino (Replay, FDI), a deteção é nula
ou quase nula. Isso é evidência de **overfitting à instância** (um log por
classe, não ao fenômeno) e de que um classificador fechado não generaliza
para ataques não vistos — o achado mais forte para a seção de
limitações/trabalhos futuros do TCC, e a motivação direta para a proposta do
autoencoder (abaixo).

## Autoencoder (LSTM) — deteção de anomalia sem rótulo de ataque

`tests/eval/train_autoencoder.py` treina um LSTM-Autoencoder **só com
janelas do voo Normal** (80% inicial em treino, 20% final em validação,
split sequencial — sem embaralhar, respeita a ordem temporal). A decisão de
anomalia não usa softmax/argmax: compara o erro de reconstrução (MSE) de
cada janela contra um threshold calibrado como o percentil 95 do erro nas
janelas de validação (Normal, não vistas em treino).

```bash
python -m tests.eval.train_autoencoder \
    --out-model tests/eval/autoencoder_px4.keras \
    --out-threshold tests/eval/autoencoder_px4_threshold.json

python -m tests.eval.evaluate_autoencoder \
    --attack-csv tests/outputs/replay/normal_replay.csv \
    --model tests/eval/autoencoder_px4.keras \
    --threshold-file tests/eval/autoencoder_px4_threshold.json
```

### Achados — autoencoder vs. classificador fechado, mesmos 4 ataques

| Ataque | Classificador fechado (softmax) | Autoencoder (erro de reconstrução) |
|---|---|---|
| Replay | 23% | 9% |
| GPS Spoofing suave (fora da escala do treino) | 0% | **95,4%** |
| DoS (freeze) | 0% | 0% |
| FDI (eph_loc/eph_gps ×50) | 0% | **100%** |

(Falso alarme do autoencoder: 1,0% fora do ataque, contra 4,4% do
classificador — também menor.)

Confirma a hipótese central do trabalho: nos dois vetores onde o
classificador fechado falhava por a magnitude do ataque estar fora do que
foi visto em treino (spoofing suave) ou por ser uma classe inexistente
(FDI), o autoencoder detecta quase perfeitamente, porque não depende de
reconhecer um rótulo específico — só de o padrão se desviar do que é
"Normal". Dois achados negativos também são relevantes e citáveis:

- **DoS freeze continua em 0%.** O modo `freeze` reduz a variância dos dados
  (congela valores num platô constante) em vez de aumentá-la — o erro de
  reconstrução cai abaixo da média do voo Normal (0,05 vs. 0,34) em vez de
  subir. O autoencoder aprendeu a penalizar desvio, não "baixa variância";
  um ataque que torna o sinal mais "liso" que o normal escapa da deteção por
  erro de reconstrução simples.
- **Replay caiu de 23% para 9%.** Esperado: o trecho replayado é telemetria
  real (só fora de ordem no tempo), então reconstrói bem — é o vetor mais
  difícil para as duas abordagens, e motiva citar deteção baseada em
  contexto temporal mais amplo (não só a janela isolada) como trabalho
  futuro adicional.

---

# Ramo ciber — Dataset T-ITS (MAVLink/Wi-Fi)

Cobertura equivalente à do ramo físico (acima), agora para
`best_model_cyber.keras` (LSTM, 3 classes: Benign / DoS attack / Replay,
Dataset T-ITS).

**Diferença estrutural importante.** O Dataset T-ITS é tráfego de rede
capturado em sessões — `timestamp_c` tem saltos grandes entre blocos de
captura (não é um único voo contínuo como o PX4). Por isso os ataques
sintéticos do ramo ciber usam janelas por **índice de linha**
(`--attack-start-row`/`--duration-rows`) sobre a subsequência `benign`
ordenada por tempo, em vez de segundos decorridos.

**Diferença de interpretação em relação ao ramo físico.** Aqui, `DoS attack`
e `Replay` **são classes reais** do dataset (ao contrário do ramo físico,
onde Replay e FDI não existem como rótulo — ver aviso no topo deste
README). Os ataques sintéticos abaixo não testam um vetor totalmente
desconhecido: testam **generalização de magnitude/forma** — um DoS mais
suave ou mais agressivo que o único log real de treino, e um replay
"canônico" (retransmissão exata de tráfego benigno, sem as
particularidades da sessão de captura rotulada `Replay` no dataset).

## DoS attack (ciber)

`tests/attacks/dos_attack_cyber.py` encolhe o tamanho dos pacotes
(`frame.len`/`ip.len`/`udp.length`/`data.len`, divididos por
`--size-divisor`) e acelera o ritmo de captura (`time_since_last_packet`
dividido por `--rate-multiplier`) numa janela de linhas sobre tráfego
`benign` real — a mesma assinatura observada no log real de `DoS attack`
(frame.len médio ~44 vs. ~127 em benign, ver `DOCUMENTO.md` §3.2/§4.2).

```bash
python -m tests.attacks.dos_attack_cyber \
    --attack-start-row 500 --duration-rows 60 \
    --rate-multiplier 2 --size-divisor 1.5 \
    --out tests/outputs/dos_cyber/benign_dos_suave.csv

python -m tests.attacks.dos_attack_cyber \
    --attack-start-row 500 --duration-rows 60 \
    --rate-multiplier 20 --size-divisor 4 \
    --out tests/outputs/dos_cyber/benign_dos_agressivo.csv

python -m tests.eval.evaluate_model_cyber \
    --attack-csv tests/outputs/dos_cyber/benign_dos_suave.csv \
    --scaler tests/eval/cyber_scaler.joblib
```

### Achados — DoS (ciber)

| Cenário | `rate-multiplier` / `size-divisor` | frame.len médio no ataque | Taxa de deteção |
|---|---|---|---|
| DoS suave | 2 / 1,5 | 90,5 (benign: 127,1) | **1,4%** |
| DoS agressivo (próximo da escala real, ~44) | 20 / 4 | 33,9 | **26,1%** |

Mesmo no cenário agressivo, cuja magnitude já se aproxima do log real de
`DoS attack`, a deteção fica bem abaixo do desempenho reportado no notebook
para o conjunto de teste real — e, mais revelador: **nenhuma janela atacada
foi classificada como "DoS attack"**. As 18 janelas sinalizadas (de 69) no
cenário agressivo foram classificadas como **Replay**, não como DoS. Isso é
o mesmo padrão de overfitting à instância já visto no ramo físico, mas
manifestado de outra forma: o modelo não aprendeu "pacotes pequenos e
rápidos = DoS", aprendeu a reconhecer estatisticamente a sessão de captura
específica rotulada `DoS attack` no treino — um DoS sintético com
características de rede plausíveis, mas gerado de outra forma, é confundido
com a classe adjacente mais parecida (Replay), não reconhecido pelo nome
correto.

## Replay attack (ciber)

`tests/attacks/replay_attack_cyber.py` grava um bloco de pacotes benignos
(`--source-start-row`) e o retransmite mais tarde (`--attack-start-row`),
sobrescrevendo FEATS_V2 durante `--duration-rows` linhas — um replay
"canônico": mesma distribuição de tamanho/protocolo do tráfego legítimo, só
fora de ordem no tempo (o único sinal que muda é `time_since_last_packet`).

```bash
python -m tests.attacks.replay_attack_cyber \
    --source-start-row 50 --attack-start-row 500 --duration-rows 60 \
    --out tests/outputs/replay_cyber/benign_replay.csv
```

### Achados — Replay (ciber)

**0% de deteção** — as 69 janelas que tocam o trecho reinjetado foram
100% classificadas como `Benign`. Consistente com o achado do ramo físico e
com a nota do §3.2 do `DOCUMENTO.md`: sem contexto de sessão/nonce nas
features, um replay de tráfego legítimo é estatisticamente quase idêntico
ao benigno — a única pista (timing) não foi suficiente para o modelo treinado.

## Síntese — ramo ciber

| Ataque | Classe real do dataset T-ITS? | Testado em | Taxa de deteção |
|---|---|---|---|
| DoS suave | Sim (`DoS attack`), mas magnitude sintética suave | fora da escala do treino | 1,4% |
| DoS agressivo | Sim (`DoS attack`), magnitude próxima do treino | dentro da escala do treino | 26,1% (confundido com Replay) |
| Replay canônico | Sim (`Replay`), mas gerado sinteticamente (retransmissão literal) | variação de forma | 0% |

Mesma conclusão central do ramo físico: mesmo em classes vistas em treino,
a generalização é frágil a variações de magnitude/forma que não reproduzem
exatamente a instância de treino — reforça, com um segundo ramo
independente, a tese de overfitting à instância que motiva tanto discutir
deteção de anomalia (autoencoder) quanto reconhecer isso como limitação
central do TCC.

## Próximos passos

- Treinar um autoencoder equivalente para o ramo ciber (mesmo espírito de
  `tests/eval/train_autoencoder.py`, mas sobre `FEATS_V2`/`benign`) e
  reavaliar os 3 CSVs acima por erro de reconstrução — teste direto de se a
  vantagem observada no ramo físico se repete aqui.
- Investigar um sinal complementar ao erro de reconstrução para o caso do
  DoS freeze do ramo físico (ex.: penalizar também baixa variância/entropia
  da janela, não só o MSE de reconstrução).

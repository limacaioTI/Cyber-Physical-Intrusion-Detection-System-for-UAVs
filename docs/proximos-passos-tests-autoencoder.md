# Próximos passos: `tests/` e Autoencoder

> Documento de planejamento. Consolida o que falta implementar na pasta
> `tests/` e como a introdução de um autoencoder (melhoria sugerida pelo
> orientador) se conecta aos achados já documentados em `tests/README.md`.

---

## 1. Contexto — o que `tests/` já provou

A pasta `tests/` não é uma suite de testes de software: é um laboratório de
ataques que injeta anomalias controladas sobre voos "Normal" reais do
PX4-QUAD-SITL e mede como o modelo LSTM (3 classes: Normal / GPS Spoofing /
Ping DoS) reage.

**Classes reais do dataset vs. ataques sintéticos.** O PX4-QUAD-SITL só tem
3 pastas de log — Normal, GPS Spoofing, Ping DoS — logo só 3 classes reais
de treino. Replay e FDI **não existem** como classe no dataset (o FDI,
inclusive, é citado no referencial teórico do próprio TCC como vetor sem
rótulo dedicado nos datasets usados); os scripts `replay_attack.py` e
`fdi_attack.py` geram esses dois cenários sinteticamente, injetando o padrão
de ataque em cima de um voo Normal real. Não são uma 4ª/5ª classe do
dataset — são testes de generalização: como o IDS reage a um ataque fora do
repertório de treino, o cenário mais realista para um atacante que não está
limitado ao dataset de treino do defensor.

Achado central já registrado:

| Ataque | Classe real do dataset PX4? | Visto no treino? | Taxa de deteção |
|---|---|---|---|
| Replay | Não — sintético, sobre voo Normal | Não (rótulo inexistente) | 23% (confundido com Normal) |
| GPS Spoofing suave (fora da escala do treino) | Sim (`GPS Spoofing`) | Sim, mas em outra escala | 0% |
| GPS Spoofing agressivo (escala do treino) | Sim (`GPS Spoofing`) | Sim | 46,6% |
| DoS (gaps ou freeze) | Sim (`Ping DoS`) | Sim | 0% |
| FDI (degrau em eph_loc/eph_gps ou x/y) | Não — sintético, sobre voo Normal | Não (rótulo inexistente) | 0% |

Conclusão do próprio README: mesmo nas classes vistas em treino, a deteção só
funciona quando o ataque sintético reproduz de perto a magnitude do único log
usado como exemplo — evidência de **overfitting à instância**, não ao
fenômeno. Essa conclusão é o gancho direto para a proposta do autoencoder
(seção 3).

---

## 2. Pendências em `tests/`

Extraído da seção "Próximos passos" de `tests/README.md`, organizado por
prioridade.

### 2.1 `fdi_attack.py` — ✅ implementado

`tests/attacks/fdi_attack.py` injeta um degrau abrupto (fixo, sem rampa) em
colunas-alvo (`--mode absolute/offset/scale`), diferenciando-se de replay
(repete o passado) e spoofing (drift gradual). Testado com dois cenários
(injeção de incerteza `eph_loc`/`eph_gps` e injeção de posição falsa `x`/`y`):
**0% de deteção** nos dois, mesmo achado do Replay — resultado documentado em
`tests/README.md`.

### 2.2 Persistir o `StandardScaler` do treino — ✅ implementado

`tests/eval/fit_scaler.py` reconstrói o scaler uma única vez (mesma lógica
que já existia em `evaluate_model.py`) e persiste via `joblib.dump`.
`evaluate_model.py` agora aceita `--scaler <caminho>`: carrega o scaler
salvo se o arquivo existir, senão reconstrói do zero (comportamento anterior
preservado como fallback). Uso:

```bash
python -m tests.eval.fit_scaler --out tests/eval/px4_scaler.joblib
python -m tests.eval.evaluate_model --attack-csv <csv> --scaler tests/eval/px4_scaler.joblib
```

### 2.3 Cobertura equivalente para o ramo ciber — ✅ implementado

`tests/common/features_cyber.py`, `tests/attacks/dos_attack_cyber.py`,
`tests/attacks/replay_attack_cyber.py`, `tests/eval/fit_scaler_cyber.py` e
`tests/eval/evaluate_model_cyber.py` replicam, para o ramo ciber (Dataset
T-ITS, `best_model_cyber.keras`), o mesmo laboratório já existente no ramo
físico. Diferença de interpretação: no T-ITS, DoS e Replay **são classes
reais** de treino (ao contrário do ramo físico), então os testes aqui medem
generalização de magnitude/forma, não um vetor totalmente desconhecido.
Resultado (detalhes completos em `tests/README.md`):

| Ataque | Taxa de deteção |
|---|---|
| DoS suave (fora da escala do treino) | 1,4% |
| DoS agressivo (escala do treino) | 26,1% — e nenhuma janela reconhecida como "DoS attack": as sinalizadas foram confundidas com Replay |
| Replay canônico (retransmissão literal de benign) | 0% |

Confirma, com um segundo ramo independente, a mesma tese de overfitting à
instância já documentada no ramo físico — o modelo do ramo ciber também não
generaliza para variações do padrão de ataque fora da instância exata de
treino.

### 2.4 Harness de avaliação para o autoencoder (prioridade alta, depende da seção 3)

`evaluate_model.py` hoje assume um classificador `Dense(3, softmax)` e reporta
a predição de classe. Para avaliar o autoencoder, é preciso um modo de
avaliação por **erro de reconstrução com threshold**, não por argmax de
classe. Ver seção 3.3.

---

## 3. Autoencoder — a melhoria com redes neurais

### 3.1 Por que essa arquitetura, e não outra

O orientador sugeriu explorar um novo modelo com redes neurais como melhoria
de teste. Entre as opções avaliadas (CNN-LSTM híbrida, Transformer leve,
autoencoder), o autoencoder é o que ataca diretamente a limitação que os
próprios testes da seção 1 documentaram: um classificador fechado
(softmax sobre rótulos conhecidos) não tem "não sei" — ele força qualquer
entrada, vista ou não em treino, em uma das classes conhecidas. É exatamente
essa limitação, e não uma questão de arquitetura de rede (LSTM vs. outra
RNN), que explica os 23% de deteção do Replay e os 0% do spoofing suave.

Um autoencoder (ou LSTM-Autoencoder) treinado **só com voos Normal** aprende
a reconstruir o padrão de telemetria legítima. Qualquer sequência que se
desvie do que o modelo aprendeu — seja um ataque conhecido em escala
diferente, seja um ataque nunca visto (como Replay) — tende a produzir erro
de reconstrução alto, sem depender de ter visto aquele rótulo específico em
treino. Isso é precisamente o que falta na classificação fechada atual.

### 3.2 Como se encaixa no pipeline existente

O autoencoder reaproveita quase toda a infraestrutura já construída:

- **Dados de entrada**: mesmas janelas temporais construídas por
  `tests/common/features.py` / pipeline do notebook (`FEATS`, `WINDOW`,
  `build_windows`) — sem mudança de features ou de formato.
- **Treino**: diferente do LSTM classificador, treina só com janelas de voo
  Normal (não precisa dos rótulos de ataque como target — o próprio input é
  o target, minimizando o erro de reconstrução).
- **Arquitetura**: LSTM encoder → vetor latente → LSTM decoder, mantendo a
  mesma dimensão de entrada/saída (janela × features). Reaproveita a mesma
  normalização (`StandardScaler`, ver 2.2).
- **Decisão**: em vez de softmax + argmax, define-se um **threshold de erro
  de reconstrução** (ex.: percentil 95 do erro sobre janelas Normais de
  validação) — janelas acima do threshold são marcadas como anômalas.

### 3.3 Avaliação — reaproveitando o laboratório de ataques

O ganho mais concreto do autoencoder para a narrativa do TCC é poder ser
testado exatamente contra os mesmos CSVs sintéticos já gerados em
`tests/outputs/`, usando a mesma lógica de "taxa de deteção durante o ataque
vs. taxa de falso alarme fora dele" já implementada em `evaluate_model.py` —
só troca a fonte da predição (erro de reconstrução > threshold, em vez de
argmax ≠ Normal). **Implementado e medido** (`tests/eval/train_autoencoder.py`
+ `tests/eval/evaluate_autoencoder.py`, arquivos novos, não sobrescreveram
nada existente):

| Ataque | Deteção — LSTM classificador (softmax) | Deteção — Autoencoder |
|---|---|---|
| Replay | 23% | 9% |
| GPS Spoofing suave | 0% | **95,4%** |
| DoS (freeze) | 0% | 0% |
| FDI | 0% | **100%** |

Confirma empiricamente a tese central do TCC: nos dois vetores fora do
repertório de treino do classificador (spoofing fora de escala, FDI), a
deteção por erro de reconstrução resolve quase completamente o problema —
deteção de anomalia não-supervisionada generaliza melhor que classificação
fechada para ataques desconhecidos ou de magnitude variável. Dois achados
negativos, também citáveis: o DoS freeze permanece em 0% nos dois modelos
(o modo *freeze* reduz variância em vez de aumentá-la, então o erro de
reconstrução cai abaixo da média em vez de subir); e o Replay piorou de 23%
para 9% no autoencoder (o trecho replayado é telemetria real, reconstrói
bem — é o vetor mais difícil para as duas abordagens). Detalhes completos em
`tests/README.md`.

### 3.4 Passos de implementação sugeridos

1. Novo notebook ou script de treino do autoencoder LSTM, reaproveitando
   `load_merged`/`add_derived_features`/`build_windows` de
   `tests/common/features.py`, treinando só sobre janelas de voo Normal.
2. Persistir modelo (`.keras`) — o scaler já pode ser reaproveitado via
   `tests/eval/fit_scaler.py` (pendência 2.2, já implementada).
3. Definir threshold de erro de reconstrução (percentil sobre validação
   Normal) e documentar a escolha.
4. Estender ou duplicar `tests/eval/evaluate_model.py` para um modo
   "autoencoder" (erro de reconstrução + threshold em vez de argmax) —
   resolve a pendência 2.4.
5. Rodar contra os 5 CSVs já existentes em `tests/outputs/` (replay,
   spoofing suave/agressivo, DoS, FDI eph/posição) e preencher a tabela da
   seção 3.3.

---

## 4. Resumo de prioridades

| Item | Prioridade | Status |
|---|---|---|
| Treinar autoencoder LSTM | Alta | ✅ Implementado (`tests/eval/train_autoencoder.py`) |
| Harness de avaliação por erro de reconstrução | Alta | ✅ Implementado (`tests/eval/evaluate_autoencoder.py`) |
| Persistir `StandardScaler` do treino | Média | ✅ Implementado (`tests/eval/fit_scaler.py`) |
| `fdi_attack.py` | Média | ✅ Implementado (`tests/attacks/fdi_attack.py`) |
| Investigar sinal complementar ao MSE para o caso DoS freeze | Média/baixa | Pendente |
| Ataques sintéticos para o ramo ciber (T-ITS) | Média/baixa | ✅ Implementado (`tests/attacks/*_cyber.py`, `tests/eval/*_cyber.py`) |
| Autoencoder para o ramo ciber | Baixa | Pendente (opcional, fora do escopo desta rodada) |

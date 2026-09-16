# Próximos passos: `tests/` e Autoencoder

> Documento de planejamento. Consolida o que falta implementar na pasta
> `tests/` e como a introdução de um autoencoder (melhoria sugerida pelo
> orientador) se conecta aos achados já documentados em `tests/README.md`.

---

## 1. Contexto — o que `tests/` já provou

A pasta `tests/` não é uma suite de testes de software: é um laboratório de
ataques sintéticos que injeta anomalias controladas sobre voos "Normal" reais
do PX4-QUAD-SITL e mede como o modelo LSTM (3 classes: Normal / GPS Spoofing /
Ping DoS) reage.

Achado central já registrado:

| Ataque | Visto no treino? | Taxa de deteção |
|---|---|---|
| Replay | Não (classe inexistente) | 23% (confundido com Normal) |
| GPS Spoofing suave (fora da escala do treino) | Sim, mas em outra escala | 0% |
| GPS Spoofing agressivo (escala do treino) | Sim | 46,6% |
| DoS (gaps ou freeze) | Sim | 0% |
| FDI (degrau em eph_loc/eph_gps ou x/y) | Não (classe inexistente) | 0% |

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

### 2.3 Cobertura equivalente para o ramo ciber (prioridade média)

Todo o laboratório de ataques sintéticos hoje cobre só o **ramo físico**
(PX4-QUAD-SITL). O ramo ciber (Dataset T-ITS, MAVLink/Wi-Fi) não tem
equivalente — não há script que gere DoS/Replay sintéticos sobre tráfego de
rede real e avalie o LSTM do ramo ciber contra eles. Sem isso, a análise de
generalização do TCC fica assimétrica: temos evidência de overfitting à
instância só de um dos dois ramos. Vale ao menos um `dos_attack_ciber.py`
(inundação de pacotes sintética sobre uma captura T-ITS benigna) para
equilibrar a análise.

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
`tests/outputs/` (replay, GPS spoofing suave e agressivo, DoS gaps/freeze,
FDI eph e FDI posição), usando a mesma lógica de "taxa de deteção durante o
ataque vs. taxa de falso alarme fora dele" já implementada em
`evaluate_model.py` — só troca a fonte da predição (erro de reconstrução >
threshold, em vez de argmax ≠ Normal). Isso permite montar diretamente uma
tabela comparativa classificador vs. autoencoder:

| Ataque | Deteção — LSTM classificador (softmax) | Deteção — Autoencoder (esperado) |
|---|---|---|
| Replay | 23% | a medir |
| GPS Spoofing suave | 0% | a medir |
| GPS Spoofing agressivo | 46,6% | a medir |
| DoS | 0% | a medir |
| FDI | 0% | a medir |

Essa tabela é a peça central de evidência experimental que falta no TCC: se
o autoencoder detectar melhor o Replay (classe nunca vista) e o spoofing
suave (fora da escala de treino), isso confirma empiricamente a tese de que
deteção de anomalia não-supervisionada generaliza melhor que classificação
fechada para ataques desconhecidos ou de magnitude variável — a limitação
central já identificada em `tests/README.md`.

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
| Treinar autoencoder LSTM | Alta | Pendente |
| Harness de avaliação por erro de reconstrução | Alta | Pendente (depende do autoencoder treinado) |
| Persistir `StandardScaler` do treino | Média | ✅ Implementado (`tests/eval/fit_scaler.py`) |
| `fdi_attack.py` | Média | ✅ Implementado (`tests/attacks/fdi_attack.py`) |
| Ataques sintéticos para o ramo ciber (T-ITS) | Média/baixa | Pendente |

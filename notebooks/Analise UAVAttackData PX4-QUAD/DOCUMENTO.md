# Documentação — análise UAVAttackData (PX4-QUAD-SITL)

Este ficheiro resume **o que cada notebook faz**, **o que os dados permitem concluir**, **o que não dá para afirmar** com estes ficheiros sozinhos, e **perguntas típicas de orientador / banca** (no mesmo espírito do [`Analise Dataset T-ITS/DOCUMENTO.md`](../Analise%20Dataset%20T-ITS/DOCUMENTO.md)).

---

## Artefatos (caminhos relativos a esta pasta)

| Ficheiro | Conteúdo |
|----------|-----------|
| [`Infos_gps_position.ipynb`](Infos_gps_position.ipynb) | `vehicle_gps_position` — unidades, cadência, séries, boxplots |
| [`Infos_local_position.ipynb`](Infos_local_position.ipynb) | `vehicle_local_position` — trajetória, `r_xy`, `eph` loc vs GPS, limitações de `dt` |
| [`Infos_fusao_gps_local_ekf.ipynb`](Infos_fusao_gps_local_ekf.ipynb) | `merge_asof`: local + GPS + `ekf2_innovations` — discrepâncias e inovações |
| [`Infos_lstm_fusao_px4.ipynb`](Infos_lstm_fusao_px4.ipynb) | Janelas multivariadas + LSTM 3 classes + `classification_report` |
| Dados brutos | [`../../data/UAVAttackData/Simulated - OTU Survey/PX4-QUAD-SITL`](../../data/UAVAttackData/Simulated%20-%20OTU%20Survey/PX4-QUAD-SITL) |
| Ramo rede (outro eixo do TCC) | [`../Analise Dataset T-ITS/`](../Analise%20Dataset%20T-ITS/) e `docs/resumo.md` na raiz do projeto |

---

## 1. O que é este ramo do trabalho (em uma frase)

Logs **exportados do PX4** (simulação **QUAD-SITL**, inquérito OTU) com pastas **Normal**, **GPS Spoofing** e **Ping DoS**: séries temporais multivariadas para estudar o lado **“físico / estimação”** de um CPS com UAV, complementar ao IDS em **tráfego de rede** (`Dataset_T-ITS`).

---

## 2. Resultados do `Infos_lstm_fusao_px4.ipynb` (última execução registada no notebook)

### 2.1 Dados e janelas

| Grandeza | Valor |
|----------|--------|
| Tabela fusionada `merged` | **44 957** linhas × **113** colunas (após merges) |
| Linhas após `dropna` nas features | **44 957** |
| **Janela** `WINDOW` | **40** timesteps |
| **Features** por passo | **11** (`x`, `y`, `z`, `vx`, `vy`, `vz`, `eph_loc`, `eph_gps`, `innov_norm`, `dv_xy`, `r_xy`) |
| Janelas **treino** (80% inicial de **cada** voo) | **35 845** |
| Janelas **teste** (20% final de **cada** voo) | **8 872** |

Contagem de janelas-teste por classe: Normal **2 913**; GPS Spoofing **3 051**; Ping DoS **2 908**.

### 2.2 Treino da rede

- Arquitetura: **LSTM(48)** → **Dropout(0,25)** → **Dense(3, softmax)**.
- Treino: **15 épocas**, `batch_size=64`, `validation_split=0,1` **sobre o conjunto de treino** (não sobre o teste temporal final).
- **Observação:** a **acurácia de validação** oscila muito (ordem de **0,25–0,53**) ao longo das épocas — típico quando o conjunto de validação é uma **fatia aleatória** das janelas de treino (mistura instantes de **vários** voos/condições) e o modelo tende a **ajustar-se ao treino**. Para o TCC, vale **explicitar** isto ou trocar para validação **por voo** ou **temporal contígua**.

### 2.3 Métricas no conjunto de teste (partição temporal 80/20 **por voo**)

`classification_report` (dígitos do notebook):

| Classe | Precision | Recall | F1 | Support |
|--------|-----------|--------|-----|---------|
| **Normal** | 0,806 | 0,849 | **0,827** | 2913 |
| **GPS Spoofing** | 0,437 | 0,637 | **0,519** | 3051 |
| **Ping DoS** | 0,498 | 0,231 | **0,316** | 2908 |
| **Acurácia global** | — | — | **0,574** | 8872 |
| **Macro F1** | — | — | **~0,554** | — |

**Leitura rápida:**

- **Normal:** melhor equilíbrio precisão/recall — o modelo **identifica** relativamente bem o voo nominal no bloco final de cada log.
- **GPS Spoofing:** recall **maior** que precisão → muitos alarmes “Spoofing” podem ser **falsos** se olharmos só precisão, mas o filtro **encontra** uma fração razoável dos verdadeiros spoofing no teste.
- **Ping DoS:** **recall baixo (~0,23)** — a classe mais fraca; alinha com a EDA (**Normal** e **Ping DoS** parecem próximos** em várias features** enquanto **Spoofing** destaca-se em **trajetória / `r_xy`**).

*(Recomendação:* acrescentar no notebook uma **matriz de confusão** para ver se Ping DoS é confundido sobretudo com Normal.)

---

## 3. Síntese transversal — o que **conseguimos identificar**

| Fenómeno | Onde aparece | Evidência |
|----------|----------------|-----------|
| **Spoofing de GPS** como “fuga” horizontal da solução estimada | `Infos_local_position`, fusão, LSTM | **`r_xy` máximo ~10⁴–10⁵ m** no Spoofing vs **~10² m** nos outros; F1 de Spoofing no LSTM **moderado** mas não nulo. |
| **Cadência de log** estável | GPS, local, fusão | **`dt` ≈ 0,10 s** igual nas três pastas — **não** é discriminador de ataque. |
| **Fusão temporal coerente** entre tópicos | `Infos_fusao_gps_local_ekf` | `merge_asof` em `timestamp` sem duplicados; colunas `eph_loc` / `eph_gps`, inovações e velocidades alinhadas. |
| **Baseline de ML multivariado** | `Infos_lstm_fusao_px4` | Pipeline janelas + scaler + LSTM + relatório — **reproduzível** para a monografia. |

---

## 4. O que **não** conseguimos (ou não devemos) afirmar só com estes ficheiros

| Limite | Motivo |
|--------|--------|
| **Generalização a “qualquer” DoS ou spoofing** | Apenas **um log por classe**; parâmetros de ataque e missão fixos neste conjunto. |
| **Separar DoS de Normal “por ritmo”** | `dt` e muitas distribuições **sobrepostas**; DoS de enlace pode **não** espelhar-se em `vehicle_gps_position` / `local_position` da mesma forma que em **tráfego PCAP**. |
| **Ligar linha-a-linha a `Dataset_T-ITS.csv`** | São **fontes e colunas diferentes**; a ligação no TCC é **narrativa** (ciber + físico) salvo **prova** de coleta conjunta na bibliografia. |
| **“Acurácia de validação = desempenho real”** | `validation_split` aleatório nas janelas de treino **mistura** contextos; o número útil para o texto é o **teste temporal por voo** (secção 2.3). |
| **Causalidade “o EKF provou X”** sem leitura do paper OTU | Os rótulos vêm das **pastas experimentais**; detalhe do setup está na **publicação / README** do dataset. |

---

## 5. Perguntas que o orientador pode fazer — e linhas de resposta

### 5.1 Por que usam `ekf2_innovations` e não `estimator_innovations`?

Neste export PX4 o ficheiro chama-se **`…_ekf2_innovations_0.csv`**. O conceito é o mesmo família “inovações do filtro”; cite o **nome real do ficheiro** no método.

### 5.2 O que é o `merge_asof` e por que não um `merge` inner?

GPS e EKF2 têm **menos amostras** que `vehicle_local_position`. O `merge_asof` alinha o **último valor GPS/EKF disponível até aquele timestamp** (`backward`), coerente com “amostragem mais lenta” dos outros tópicos.

### 5.3 Por que o recall de Ping DoS é baixo na LSTM?

Porque **Normal** e **Ping DoS** partilham **regimes parecidos** em posição/velocidade/incerteza **neste** SITL; o modelo **confunde** as duas classes. Reforce com **EDA** (`r_xy`, trajetórias) e, se houver tempo, **baseline** (Random Forest) ou **mais features** (telemetria adicional, `vehicle_status`, etc.).

### 5.4 O split temporal por voo elimina todo o vazamento?

**Reduz** vazamento “vizinho imediato” treino↔teste **no mesmo ficheiro**. Não substitui **novos voos** na generalização. Diga isso explicitamente na **Discussão / limitações**.

### 5.5 Quantas épocas e qual arquitetura “bastam”?

Para o TCC basta **justificar** o protótipo (pequeno, rápido). Se o orientador pedir robustez: **early stopping**, **repetir com seeds**, **matriz de confusão**, **F1 macro** e comparação com **RF**.

### 5.6 Isto opera em tempo real?

**Não** neste pipeline: é **offline** sobre CSV. Para tempo real seria preciso **latência** medida (inferência + ingestão) — **trabalho futuro**.

### 5.7 Como isto se articula com o IDS em rede (T-ITS)?

**Complementaridade:** rede deteta padrões de pacotes; **PX4** deteta **inconsistência de estado** (spoofing visível em trajetória). **Fusão multimodal** (duas fontes alinhadas no tempo de missão) é **hipótese de trabalho futuro**, não merge automático dos CSV sem desenho experimental.

### 5.8 Por que `r_xy` é relativo ao **primeiro** ponto do ficheiro?

É uma escolha de **referência interna ao log** para medir **deriva horizontal acumulada** sem depender de um mapa global. O spoofing mostra **explosão** dessa métrica; convenha que é **proxy**, não distância geodésica oficial.

---

## 6. Checklist antes da defesa

- [ ] Matriz de confusão no `Infos_lstm_fusao_px4.ipynb` (ou aqui referenciada).
- [ ] Uma frase no texto: **val_split aleatório** vs métrica de **teste temporal**.
- [ ] Citação ao **paper / IEEE DataPort** do UAV-Attack ou OTU Survey conforme o teu relatório bibliográfico.
- [ ] Tabela “o que identificámos / não identificámos” (podes copiar §3–§4 para a monografia).

---

*Documento gerado para a pasta `Analise UAVAttackData PX4-QUAD`. Atualize os números da secção 2 se voltar a treinar com outras seeds ou hiperparâmetros.*

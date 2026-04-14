# Resumo do trabalho com o dataset (notebook `Infos_data.ipynb`)

Documento de apoio ao TCC: consolida o que já foi executado no notebook e lista análises e melhorias possíveis com o mesmo dataset.

---

## 1. O que já foi feito

### 1.1 Carregamento e visão geral dos dados

- Leitura do arquivo **`data/Dataset_T-ITS.csv`** com `pandas` (`sep=","`, `low_memory=False`).
- **`df.info()`**: inspeção de **54.783 linhas**, **38 colunas** e tipos (inicialmente todos como texto).
- Colunas com cara de **exportação de tráfego** (estilo Wireshark): `timestamp_c`, `frame.*`, `wlan.*`, `llc.*`, `ip.*`, `tcp.*`, `udp.*`, `data.*`, `time_since_last_packet` e **`class`** (rótulo do experimento).
- **`value_counts()`** na coluna `class`: distribuição entre **Replay**, **DoS attack**, **benign** e duas ocorrências do valor literal **`class`** (provável cabeçalho ou ruído no CSV).

### 1.2 Pré-processamento para análise e modelo

- Conversão para numérico de **`frame.len`**, **`ip.len`** e **`data.len`** (`errors="coerce"`).
- Construção de **`df_clean`**: remoção de linhas com `NaN` nessas três colunas ou em **`class`**.
- **`time_since_last_packet`** convertido para numérico para análise temporal.

### 1.3 Análises exploratórias (consultas aos dados)

- **Estatísticas por classe** (`groupby('class')`): média, desvio padrão, máximo e mínimo de `frame.len`, `ip.len` e `data.len` em `df_clean`.
- **Análise temporal por classe**: mesmas agregações para `time_since_last_packet` (com ressalva de que, no estado atual do notebook, a tabela pode incluir a linha espúria `class` com `NaN` se o agrupamento usar o frame antes do filtro estrito de rótulos).
- **Inspeção Replay vs DoS** (células após `df_clean`): cobertura (% não nulo) por classe nas colunas **TCP/UDP, WLAN, `data.*`, LLC** e campos IP extra; resumo de **categorias** (`frame.protocols`, MACs, `data.data`); estatísticas e **Mann–Whitney U** em colunas numéricas com amostra suficiente; comprimento do hex em `data.data` como proxy de payload; **boxplots em escala log** para colunas escolhidas (`udp.length`, `tcp.window_size`, etc., quando há dados).

### 1.4 Preparação para a rede LSTM

- **Features** utilizadas no modelo: **`frame.len`**, **`ip.len`**, **`time_since_last_packet`**.
- **Normalização** com **`MinMaxScaler`** sobre essas três colunas em `df_clean`.
- **Mapeamento de rótulos**: benign → 0, DoS attack → 1, Replay → 2.
- **Janelas deslizantes** de tamanho **10**: cada amostra é um tensor *(10 timesteps × 3 features)*; o rótulo é o da observação no passo seguinte à janela.
- **Partição treino/teste**: `train_test_split` com **80% / 20%**, `random_state=42` e **`stratify=y`** para manter proporções das classes.

### 1.5 Modelo, treino e avaliação

- Arquitetura **`Sequential`** (Keras/TensorFlow): camada **`Input`**, **LSTM (50 unidades)**, **Dropout (0,2)** e **`Dense(3, softmax)`** para as três classes.
- Compilação: otimizador **Adam**, perda **`sparse_categorical_crossentropy`**, métrica **acurácia**.
- Treino: **20 épocas**, `batch_size=32`, **`validation_split=0,1`** sobre o conjunto de treino.
- **Avaliação no teste**: **`classification_report`** (precisão, recall, F1 por classe) e **matriz de confusão** com `seaborn`/`matplotlib`.

### 1.6 Principais achados descritos no notebook (para discussão no TCC)

- **Tamanhos de pacote**: em média, tráfego **benigno** tende a apresentar **valores maiores** de `frame.len`, `ip.len` e `data.len` do que **DoS** e **Replay**; ataques associam-se a pacotes menores em média, com alta variabilidade.
- **Ritmo entre pacotes**: **benign** com **intervalo médio maior** entre pacotes; **DoS** e **Replay** com intervalos médios **menores** (tráfego mais denso no tempo).
- **Desempenho do classificador** (última execução registrada no notebook): acurácia global em torno de **65%**; **benign** com bom F1; **DoS** com recall relativamente alto e precisão mais baixa; **Replay** com **recall baixo** — principal fragilidade apontada pelas métricas. *Como transformar isso em argumento na monografia, ver **§3.1**.*

---

## 2. O que ainda podemos fazer neste dataset

Itens abaixo não substituem o que já está no notebook; são **extensões** úteis para método, texto do TCC ou novas versões do experimento.

### 2.1 Qualidade e rastreabilidade dos dados

- **Filtrar rótulos válidos** explicitamente (`benign`, `DoS attack`, `Replay`) e **descartar** linhas com `class == "class"` ou outros valores estranhos.
- **Tabela de contagem de linhas** após cada etapa (carga bruta → `df_clean` → linhas com tempo válido → número de sequências geradas).
- **Mapa ou contagem de valores ausentes** por coluna (e, se fizer sentido, por classe), para justificar imputação ou exclusão.

### 2.2 Análises exploratórias adicionais

- **Histogramas / KDE** das features numéricas **por classe**.
- **Boxplot de `time_since_last_packet` por classe com eixo Y em escala logarítmica** (recomendado para a **Seção 2.2** da monografia): em escala **linear**, intervalos de DoS muito próximos de zero e picos de tráfego benigno (ex.: ordem de dezenas de segundos) comprimem a visualização da variabilidade do ataque; em **log**, as **assinaturas temporais** por classe ficam mais legíveis e ajudam a justificar o uso de modelo sequencial (LSTM), ao mostrar que os regimes temporais não se confundem trivialmente.
- **Distribuição de `ip.proto`**, **portas TCP/UDP** ou padrões em **`frame.protocols`** por classe (relevante para enlace tipo MAVLink/UDP).
- **Matriz de correlação** entre features numéricas para detectar redundância.
- **Matriz de confusão normalizada por linha** (taxa de erro condicional à classe verdadeira) para interpretar confusões DoS ↔ Replay ↔ benign.

### 2.3 Modelagem e treino

- **Baseline tabular** (ex.: Random Forest ou regressão logística) com as mesmas features ou agregadas por janela, para comparar com a LSTM.
- **Mais features da pilha** (ex.: `ip.ttl`, `ip.proto`, `wlan.duration`, `udp.length`), com **imputação** (ex.: 0) quando a camada não existir no frame.
- **Seletividade de atributos (para a Seção 2.3 — modelagem):** no contexto **MAVLink**, o comprimento do payload (no CSV, proxy por **`data.len`**) é um indicador ligado ao **conteúdo / tamanho da mensagem** transportada. Já camadas como **`ip.ttl`** ou **`wlan.duration`** deslocam o foco do IDS de um modelo predominantemente baseado em **conteúdo** (tamanhos de pacote e payload) para um modelo enriquecido pelo **contexto de rede** (enlace Wi-Fi, encaminhamento IP). Vale **explicitar essa distinção** no texto ao incluir ou comparar conjuntos de features.
- **`class_weight` balanceado** (ou outra estratégia de desbalanceamento) no `fit` da rede, para tentar melhorar **recall de Replay** sem ignorar o custo em falsos alarmes.
- **Curvas de aprendizado** (loss e acurácia treino vs. validação) a partir do objeto `history`.
- **Métricas complementares**: F1 macro, recall macro, ou curvas ROC/PR em setting multiclasse (one-vs-rest), se couber no escopo.

### 2.4 Metodologia e limitações (texto do TCC)

- **Split aleatório vs. temporal (“armadilha” do `train_test_split`):** se o CSV for **uma captura contínua**, sortear linhas ao acaso pode colocar no treino o pacote *N* e no teste o pacote *N+1* — vizinhos quase idênticos em cenários de inundação — e o modelo pode **se aproximar de memorização de vizinhança** em vez de generalizar o padrão do ataque. No texto do TCC, isso pode ser apresentado como **limitação do protocolo experimental** com este dataset ou como motivação para **split por bloco temporal** ou por sessão, em trabalhos futuros.
- **O que já mitiga parcialmente o viés:** uso de **`stratify=y`** garante **representatividade proporcional das classes** em treino e teste; isso **não elimina** o vazamento temporal entre janelas vizinhas, mas **evita** que uma classe domine um dos conjuntos por acaso do sorteio — convém **declarar explicitamente** no método o que foi feito e o que não foi (ex.: estratificação sim, divisão temporal não).
- Registrar **versões** de Python, TensorFlow/Keras e `random_state` para reprodutibilidade.

---

## 3. Argumentação sugerida para o texto final do TCC

Sugestões para **converter** os resultados do notebook em **linha de argumento acadêmica** nas seções típicas da monografia (ajuste os números à estrutura da sua instituição).

### 3.1 Justificativa do modelo e baixo recall em Replay (≈ Seções 1.5 / 1.6 ou Discussão)

- **Replay** reproduz tráfego **legítimo previamente observado**; em muitos instantes, pacotes isolados ou sequências curtas **parecem normais** estatisticamente.
- Argumento: o **recall baixo** para Replay, com **janela de apenas 10 timesteps**, indica que a distinção **não** se resolve só com estatística de poucos pacotes consecutivos — coerente com a **sofisticação** do ataque (mimetizar o legítimo).
- Isso **justifica trabalhos futuros** ou complementares no próprio TCC: testar **janelas mais longas** (ex.: **30 timesteps**) ou outras formas de **memória contextual**, para capturar desvios que só aparecem em horizonte temporal maior (ordem de mensagens, repetição de sequências, etc.).

### 3.2 Visualização forte para métodos / dados (≈ Seção 2.2)

- Incluir **boxplot de `time_since_last_packet` por classe** com **eixo em escala logarítmica** (detalhe técnico na **§2.2** acima): reforça visualmente que **regimes temporais** diferem entre benign e ataques, apoiando a escolha de arquitetura **recorrente**.

### 3.3 Enriquecimento da modelagem (≈ Seção 2.3)

- Ao discutir inclusão de features da pilha, usar o quadro **conteúdo** (`data.len` / payload) vs. **contexto de rede** (`ip.ttl`, `wlan.duration`, etc.) da **§2.3** acima — mostra **consciência metodológica** e liga o trabalho ao ecossistema **UAV / MAVLink**.

### 3.4 Limitações honestas do protocolo experimental (≈ Seção 2.4)

- Declarar a **limitação do split aleatório** em captura contínua (**§2.4** acima) e, em contrapartida, o papel do **`stratify=y`** na **equidade entre classes** — transparência que avaliadores costumam valorizar.

---

## 4. Referência rápida

| Artefato        | Localização                          |
|-----------------|--------------------------------------|
| Notebook        | `notebooks/Infos_data.ipynb`         |
| Dados (CSV)     | `data/Dataset_T-ITS.csv`             |
| Telemetria PX4  | `data/UAVAttackData/` (ver **§6**)   |
| Ignorar no Git  | `data/.gitignore` (`*.csv`, etc.)    |


---

## 5. Mapa rápido monografia ↔ este documento

| Tópico na monografia | Onde ler neste `resumo.md` |
|----------------------|----------------------------|
| Por que Replay é difícil / janela maior | **§3.1** |
| Figura temporal (boxplot log) | **§2.2** (fazer no notebook) + **§3.2** (texto) |
| Features: conteúdo vs. contexto de rede | **§2.3** (parágrafo seletividade) + **§3.3** |
| Split aleatório, viés, estratificação | **§2.4** + **§3.4** |
| Plano UAVAttackData (arquivos, consultas, objetivos) | **§6** |

---

## 6. Plano de estudo — `data/UAVAttackData/`

Este bloco alinha o uso do dataset **UAV-Attack** (telemetria / logs PX4) aos **objetivos do README** do repositório: IDS **ciber-físico**, com ramo **physical** (estados de voo e sensores) complementando o ramo **cyber** (rede / `Dataset_T-ITS`).

### 6.1 O que queremos (objetivos)

- **Demonstrar** que sinais de **telemetria e estimação** (posição GPS, posição local, inovações do estimador) carregam **padrões temporais** distinguíveis entre **voo normal** e **cenários de ataque** relevantes ao TCC (**GPS spoofing**, **DoS de enlace** no simulador, e opcionalmente **GPS jamming** em voo real).
- **Alimentar** uma linha de modelagem **LSTM** (ou baseline + LSTM) sobre **sequências multivariadas** alinhadas no tempo — coerente com a promessa de analisar **séries temporais** do lado físico do CPS.
- **Conectar** explicitamente à narrativa **híbrida**: estes arquivos cobrem o **monitoramento físico**; **Replay** e **FDI** finos continuam mais naturalmente ligados a **dados de rede** (outro dataset), salvo interpretação estendida no texto.

### 6.2 Quais arquivos / pastas usar (escopo fechado inicial)

**Eixo principal (simulação, um veículo — reduz variáveis e texto):**

| Condição   | Caminho (relativo a `data/UAVAttackData/`) |
|------------|-----------------------------------------------|
| Normal     | `Simulated - OTU Survey/PX4-QUAD-SITL/Normal/` |
| GPS Spoofing | `Simulated - OTU Survey/PX4-QUAD-SITL/GPS Spoofing/` |
| Ping DoS   | `Simulated - OTU Survey/PX4-QUAD-SITL/Ping DoS/` |

*Justificativa:* o README cita **GPS spoofing** e **DoS**; **Ping DoS** é o análogo de DoS disponível nessa árvore; **QUAD** é um caso multimotor representativo sem multiplicar avião/VTOL no primeiro ciclo.

**Arquivos dentro de cada pasta:** para **cada voo** (prefixo de nome comum antes de `_<tópico>_0.csv`), usar **apenas** estes tópicos (CSV), por serem os mais ligados a posição, GPS e coerência do filtro:

| Tópico (sufixo no nome do ficheiro) | Motivo |
|-------------------------------------|--------|
| `vehicle_gps_position_0.csv`        | Medidas GNSS brutas — alvo direto de spoofing/jamming. |
| `vehicle_local_position_0.csv`      | Estado estimado local (x, y, z, velocidades) — “física” do voo. |
| `vehicle_global_position_0.csv`     | Coerência global / altitude — útil para comparar com GPS. |
| `estimator_innovations_0.csv`       | Inovações do EKF — frequentemente sensíveis a inconsistência sensorial. |
| `estimator_status_0.csv` (opcional) | Flags / diagnóstico do estimador — reforço para anomalia. |

**Não** é necessário, na primeira versão, carregar todos os dezenas de CSV por voo (bateria, RC, etc.) — só os acima, salvo exploração futura.

**Pastas `Processed` (live):** em `Live GPS Spoofing and Jamming/.../Processed/`, se existir CSV **já agregado** (ex. merge só GPS), usar como **segunda linha de experimento** ou **validação qualitativa**, citando no método que é derivado dos logs brutos.

**Ficheiros `.ulg`:** binário PX4; prioridade é **CSV** já exportado. Só considerar `.ulg` se faltar coluna no CSV e houver ferramenta de extração no fluxo do TCC.

### 6.3 Quais consultas fazer e por quê

| Consulta / etapa | O que fazer | Motivo |
|------------------|------------|--------|
| **Inventário** | Listar, por pasta de condição, **quantos voos** (prefixos únicos) e se os 4–5 tópicos acima existem em cada um. | Garantir **reprodutibilidade** e saber se há desbalanceamento entre classes. |
| **Schema** | `head`, `dtypes`, contagem de `NaN` por coluna nos CSV escolhidos. | Definir **limpeza** e colunas numéricas para séries. |
| **Sincronização temporal** | Identificar coluna de **tempo** comum (`timestamp` ou equivalente PX4); alinhar tópicos por **merge_asof** ou janelas. | LSTM multivariada exige **mesmo eixo temporal** (ou features por janela consistente). |
| **EDA por classe** | Estatísticas (média, std, min, max) e **boxplots** de variáveis-chave **por rótulo** (Normal / Spoofing / DoS). | Mostrar **diferenças de regime** entre condições — argumento na **Seção de dados**. |
| **Séries** | Plotar **linha do tempo** (ex. posição local, componentes GPS) para um voo de cada classe. | Ilustrar **comportamento qualitativo** sob ataque (divergência, ruído, saturação). |
| **Janelas + rótulo** | Construir sequências de comprimento *T* (ex. 10 ou 30) com vetor de features por passo; rótulo = condição experimental da pasta. | Igualar o **pipeline** ao do notebook de rede (LSTM), permitindo **comparar** ou **fundir** depois. |
| **Partição** | Treino/teste; idealmente **por voo** (grupo), não por linhas aleatórias do mesmo voo, para reduzir **vazamento**. | Alinhado à discussão de **§2.4** sobre split temporal / dependência entre amostras. |
| **Modelo** | LSTM (e opcionalmente Random Forest em features agregadas) para classificação 3-classes. | Responde ao objetivo do README (**LSTM** + **detecção**). |

### 6.4 O que estamos procurando (hipóteses / sinais)

- **GPS Spoofing:** descompasso entre **`vehicle_gps_position`** e **`vehicle_local_position`** ou **inovações** do estimador fora do padrão do voo Normal.
- **Ping DoS:** possível **degradação** de taxa de atualização, **buracos** temporais ou **comportamento de controle** mais ruidoso — depende do que o log capturar; a consulta confirma **quais colunas** realmente discriminam.
- **Consistência:** se Normal vs ataque **não** se separam bem só com estes tópicos, isso vira **limitação** ou motivação para **mais tópicos** / **janela maior** — também é resultado válido para o TCC.

### 6.5 O que este plano não cobre (explícito)

- **Replay** e **FDI** como rótulos nesta pasta — não há pastas homónimas; tratá-los no **dataset de rede** ou como trabalho futuro **multimodal**.
- **Generalização entre veículos** (PLANE, VTOL, etc.) — fica para extensão após fechar o eixo **QUAD-SITL**.
- **Fusão em tempo real rede + PX4** — objetivo de alto nível do README; o passo atual é **caracterizar e modelar** o ramo físico com clareza.

---

*Ajuste os caminhos se trocar `PX4-QUAD-SITL` por outro veículo; mantenha a mesma tabela de tópicos e consultas para o documento permanecer coerente.*

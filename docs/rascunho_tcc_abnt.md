# Sistema de Detecção de Intrusão Ciber-Físico para Veículos Aéreos Não Tripulados

**Autor:** Caio de Souza Lima  
**Instituição:** Universidade Federal Fluminense (UFF)  
**Curso:** Sistemas de Informação  
**Orientador:** Raphael Machado
**Ano:** 2026

---

> **Nota de uso deste rascunho:** este arquivo Markdown segue a estrutura e as convenções de citação da ABNT
> (NBR 10520 para citações; NBR 6023 para referências; NBR 6024 para numeração de seções).
> Margens, fonte e espaçamento (NBR 14724) devem ser aplicados ao transferir para Word ou LaTeX/abnTeX2.
> Números entre colchetes marcam trechos que precisam de revisão ou complemento antes da entrega.

---

## 1 INTRODUÇÃO

### 1.1 Contextualização

Os Veículos Aéreos Não Tripulados (UAVs), popularmente conhecidos como drones, tornaram-se plataformas
de uso crescente em aplicações civis e militares, incluindo monitoramento de infraestrutura, agricultura
de precisão, entrega de cargas, operações de busca e resgate e vigilância de fronteiras. Essa expansão
foi acompanhada de uma diversificação das arquiteturas de comunicação e controle: os UAVs modernos operam
como sistemas ciber-físicos (CPS, do inglês *Cyber-Physical Systems*), nos quais subsistemas computacionais
e de rede estão diretamente acoplados a componentes físicos como motores, atuadores e sensores de navegação
(YU et al., 2024).

A natureza ciber-física dos UAVs introduz uma superfície de ataque dupla. Do lado ciber, os protocolos de
telemetria e comando — em especial o MAVLink, amplamente adotado em plataformas de código aberto como PX4
e ArduPilot — são transmitidos sobre redes Wi-Fi sem autenticação robusta em muitos ambientes de pesquisa e
operação comercial, expondo o enlace a ataques de saturação (*Denial of Service*, DoS), repetição de
mensagens (*Replay*) e injeção de dados falsos (*False Data Injection*, FDI) (HASSLER; MUGHAL; ISMAIL, 2024).
Do lado físico, sensores como o receptor GNSS são vulneráveis a interferência e falsificação de sinal
(*GPS Spoofing*), cuja consequência direta é a corrupção da estimativa de posição e velocidade produzida
pelo filtro de Kalman estendido (EKF) embarcado.

### 1.2 Problema e Motivação

A literatura de detecção de intrusão em UAVs concentra-se predominantemente em uma das camadas do sistema:
abordagens orientadas à rede analisam metadados de pacotes e sequências de mensagens, enquanto abordagens
orientadas ao estado físico inspecionam a telemetria de voo. Poucos trabalhos propõem uma arquitetura
híbrida que monitore ambos os canais de forma complementar, apesar de ataques sofisticados poderem
atravessar as duas camadas simultaneamente (HASSLER; MUGHAL; ISMAIL, 2024; YU et al., 2024).

Adicionalmente, a disponibilidade de datasets públicos com rótulos de ataque confiáveis em ambas as
dimensões é limitada. Uma análise sistemática de datasets para IDS em UAVs identificou lacunas na cobertura
de ataques físicos e na padronização de protocolos de avaliação (MOHAMMED; FOURATI, 2025), o que reforça a
necessidade de experimentos reprodutíveis com fontes abertas.

### 1.3 Objetivos

**Objetivo geral:** desenvolver e avaliar um protótipo de IDS híbrido para UAVs que combine detecção de
anomalias em tráfego de rede (ramo ciber) e em dados de telemetria e estimação de estado (ramo físico),
utilizando arquiteturas LSTM como modelo principal e Random Forest como baseline de comparação.

**Objetivos específicos:**

1. Implementar e avaliar um classificador LSTM sobre o *Dataset T-ITS* para detecção de DoS e Replay em
   tráfego MAVLink/Wi-Fi;
2. Implementar e avaliar um classificador LSTM sobre logs de telemetria PX4-QUAD-SITL para detecção de
   GPS Spoofing e Ping DoS;
3. Comparar o desempenho do LSTM com o baseline Random Forest em cada ramo, usando métricas de precisão,
   revocação e F1-score macro;
4. Documentar as limitações metodológicas e identificar direções de trabalhos futuros para a fusão
   decisória dos dois ramos.

### 1.4 Organização do Trabalho

Este trabalho está organizado da seguinte forma. O Capítulo 2 apresenta o referencial teórico sobre
sistemas ciber-físicos, vetores de ataque em UAVs, IDS baseados em aprendizado de máquina e arquiteturas
LSTM. O Capítulo 3 descreve a metodologia, incluindo os datasets utilizados, o pré-processamento, a
construção das janelas temporais e o protocolo de avaliação. O Capítulo 4 apresenta os resultados
comparativos dos modelos. O Capítulo 5 discute os achados. O Capítulo 6 expõe as limitações e propõe
trabalhos futuros. O Capítulo 7 conclui o trabalho.

---

## 2 REFERENCIAL TEÓRICO

### 2.1 Sistemas Ciber-Físicos e UAVs

Sistemas ciber-físicos são definidos como integrações de processos computacionais e físicos, nos quais
sensores, atuadores e controladores interagem com o mundo físico por meio de infraestrutura de comunicação
(YU et al., 2024). UAVs são instâncias paradigmáticas de CPS: o controlador de voo (firmware PX4 ou
ArduPilot) integra leituras de IMU, barômetro, magnetômetro e GPS para estimar o estado do veículo por
meio de um EKF, enquanto recebe comandos e envia telemetria via protocolo MAVLink sobre enlace rádio ou
Wi-Fi.

A arquitetura MAVLink encapsula mensagens tipadas (ID + payload + checksum) em datagramas UDP/IP,
transmitidos tipicamente em frequências ISM (2,4 GHz ou 5,8 GHz). A ausência de mecanismos de
autenticação e cifragem nativos em muitos sistemas torna o enlace suscetível a ataques passivos
(escuta) e ativos (injeção, replay, saturação) executados por qualquer dispositivo com acesso ao
meio físico.

### 2.2 Principais Vetores de Ataque

**Denial of Service (DoS):** inundação de pacotes no canal de comunicação visando saturar a CPU do
controlador de voo ou o canal de rede, impedindo a recepção de comandos legítimos e degradando a
atualização de setpoints de controle.

**Replay:** captura e retransmissão de mensagens MAVLink legítimas previamente observadas. A
consequência é a repetição de comandos ou estados fora do contexto temporal original, podendo causar
comportamento incorreto sem que o conteúdo individual de qualquer pacote pareça anômalo.

**GPS Spoofing:** transmissão de sinais GNSS falsificados que desviam a estimativa de posição do
receptor. O EKF, ao incorporar as medidas corrompidas, diverge progressivamente do estado real do
veículo, produzindo trajetórias e velocidades estimadas inconsistentes com o modelo dinâmico.

**False Data Injection (FDI):** manipulação direta de dados de telemetria na camada de aplicação,
alterando leituras de sensores ou estados internos do controlador sem necessariamente comprometer
o enlace físico. [Este vetor não possui rótulo dedicado nos datasets empregados neste trabalho
e é tratado apenas no referencial teórico.]

### 2.3 Detecção de Intrusão Baseada em Aprendizado de Máquina

Sistemas de detecção de intrusão (IDS) clássicos baseiam-se em assinaturas ou regras definidas
manualmente, o que os torna pouco eficazes frente a ataques novos ou variantes. Abordagens baseadas
em aprendizado de máquina (ML) extraem automaticamente padrões discriminativos a partir de dados
rotulados, possibilitando a detecção de anomalias sem especificação explícita de regras (MOHAMMED;
FOURATI, 2025).

Classificadores tabulares como Random Forest operam sobre vetores de features estáticos por amostra
e demonstram desempenho robusto em datasets de tamanho moderado com menos risco de overfitting do
que modelos profundos. No entanto, ao achatar janelas temporais em vetores de entrada, esses modelos
perdem a noção explícita de ordenação sequencial — informação relevante para ataques cujo sinal
depende da evolução temporal das variáveis observadas.

### 2.4 Redes LSTM para Séries Temporais

As redes neurais recorrentes do tipo Long Short-Term Memory (LSTM) foram propostas para superar a
limitação de gradiente evanescente das RNNs clássicas, permitindo que o modelo mantenha e atualize
seletivamente memória de longo prazo por meio de portões de entrada, esquecimento e saída (HOCHREITER;
SCHMIDHUBER, 1997 *apud* [inserir fonte secundária se necessário]). No contexto de IDS, LSTMs são
adequadas para capturar dependências temporais em sequências de pacotes ou amostras de telemetria,
permitindo que o classificador avalie padrões que só se manifestam ao longo de múltiplos passos de
tempo — como a recorrência de sequências de IDs de mensagem característica de um Replay ou a divergência
progressiva de estado típica de GPS Spoofing.

### 2.5 Datasets Públicos para IDS em UAVs

Dois datasets abertos constituem a base experimental deste trabalho:

**Dataset T-ITS** (*Cyber-Physical Dataset for UAVs Under Normal Operations and Cyber-Attacks*,
IEEE DataPort): contém capturas de tráfego Wi-Fi em estilo Wireshark com rótulos de experimento
(benign, DoS attack, Replay), provenientes de cenários controlados com drones e estação de controle
em laboratório. Os campos exportados incluem metadados de rede (tamanhos de frame, campos IP, UDP,
TCP, WLAN) e intervalo entre pacotes (HASSLER; MUGHAL; ISMAIL, 2024).

**UAVAttackData** (*UAV Attack Dataset*, IEEE DataPort): conjunto de logs PX4 exportados em CSV
a partir de simulações SITL (*Software in the Loop*) e voos reais. O subconjunto utilizado neste
trabalho corresponde ao inquérito OTU com quadricóptero simulado (PX4-QUAD-SITL), com três pastas
rotuladas: Normal, GPS Spoofing e Ping DoS. Cada pasta contém o log de um único voo subdividido
em múltiplos tópicos PX4 (posição local, posição GPS, inovações EKF2, entre outros).

---

## 3 METODOLOGIA

### 3.1 Arquitetura do IDS Híbrido Proposto

O IDS proposto é composto por dois detectores independentes — denominados ramo ciber e ramo físico —
cada um treinado sobre uma fonte de dados distinta e avaliado separadamente. A Figura 1 ilustra a
arquitetura geral.

[INSERIR FIGURA 1 — Diagrama da arquitetura do IDS híbrido com os dois ramos]

**Figura 1 — Arquitetura do IDS híbrido ciber-físico para UAVs**

Fonte: Elaborado pelo autor (2026).

O caráter híbrido do IDS reside na complementaridade entre os dois ramos: o ramo ciber monitora
padrões de comunicação e é sensível a ataques volumétricos e de repetição de mensagens; o ramo
físico monitora a coerência do estado estimado do veículo e é sensível a manipulações de sensores.
A fusão decisória dos dois detectores em um único pipeline com relógio comum constitui trabalho
futuro, condicionado à disponibilidade de datasets com coleta simultânea de ambas as fontes de dados
sob os mesmos cenários de ataque.

### 3.2 Ramo Ciber — Dataset T-ITS

#### 3.2.1 Descrição dos Dados

O arquivo `Dataset_T-ITS.csv` contém 54.783 entradas e 38 colunas, com todas as colunas inicialmente
no tipo `str`. A coluna `class` apresenta a distribuição de rótulos descrita na Tabela 1.

**Tabela 1 — Distribuição de rótulos no Dataset T-ITS**

| Classe | Quantidade | Proporção (%) |
|---|---|---|
| Replay | 12.006 | 36,2 |
| DoS attack | 11.671 | 35,2 |
| benign | 9.425 | 28,4 |
| class (ruído) | 2 | < 0,1 |
| **Total** | **33.104** | **100,0** |

Fonte: Elaborado pelo autor (2026). Dados: HASSLER; MUGHAL; ISMAIL (2024).

*Nota: as duas ocorrências do valor literal `class` correspondem a cabeçalhos duplicados no CSV de
origem e são descartadas durante o pré-processamento.*

#### 3.2.2 Pré-processamento e Seleção de Features

O pré-processamento compreende as seguintes etapas: (i) conversão das colunas numéricas relevantes
(`frame.len`, `ip.len`, `data.len`, `time_since_last_packet`, `wlan.fc.type`, `wlan.duration`,
`udp.length`) com `pd.to_numeric(errors='coerce')`; (ii) remoção de linhas com NaN nas três colunas
base (`frame.len`, `ip.len`, `time_since_last_packet`) e em `class`; (iii) imputação pela mediana
nas colunas estendidas que não fazem parte do conjunto base; (iv) ordenação pelo campo `timestamp_c`
(valor numérico relativo) para garantir a correta partição temporal.

O conjunto final de features selecionadas (`FEATS_V2`) é apresentado na Tabela 2.

**Tabela 2 — Features do ramo ciber e sua interpretação**

| Feature | Interpretação |
|---|---|
| `frame.len` | Tamanho total do frame capturado (enlace + IP + payload) |
| `ip.len` | Tamanho do datagrama IP |
| `time_since_last_packet` | Intervalo de tempo entre pacotes consecutivos |
| `wlan.fc.type` | Tipo de frame 802.11 (dados, controle, gerenciamento) |
| `wlan.duration` | Campo de duração NAV do frame WLAN |
| `udp.length` | Comprimento do datagrama UDP |
| `data.len` | Tamanho do payload de camada de aplicação |

Fonte: Elaborado pelo autor (2026).

#### 3.2.3 Construção das Janelas e Partição

Janelas deslizantes de tamanho `window = 10` timesteps são construídas sobre as linhas ordenadas por
`timestamp_c`, produzindo 33.092 amostras no formato (10, 7). A normalização MinMaxScaler é ajustada
exclusivamente sobre o conjunto de treino e aplicada ao conjunto de teste para evitar vazamento de
informação estatística.

A partição treino/teste é realizada de forma temporal por classe: para cada rótulo, as amostras
ordenadas por `timestamp_c` são divididas em 80% de treino (primeiros instantes) e 20% de teste
(últimos instantes). Esse procedimento mantém a separação temporal dentro de cada classe e garante
representação de todas as classes nos dois conjuntos.

Os 10% finais do bloco de treino (não aleatórios) são separados como conjunto de validação para
monitoramento do *early stopping* durante o treino.

#### 3.2.4 Modelos

**LSTM:** arquitetura Sequential (Keras/TensorFlow) composta por camada `Input(shape=(10, 7))`,
`LSTM(50, return_sequences=False)`, `Dropout(0,2)` e `Dense(3, activation='softmax')`. Compilação
com otimizador Adam, perda `sparse_categorical_crossentropy` e métrica acurácia. Treinamento com
até 100 épocas, `batch_size=32`, `EarlyStopping(monitor='val_loss', patience=5)` e
`ModelCheckpoint` para salvar o melhor modelo por `val_loss`.

**Random Forest (baseline):** `RandomForestClassifier(n_estimators=200, random_state=42)` do
scikit-learn, treinado sobre as janelas achatadas no formato (N, 10 × 7 = 70 features).

### 3.3 Ramo Físico — UAVAttackData PX4-QUAD-SITL

#### 3.3.1 Descrição dos Dados e Fusão Temporal

Os logs PX4 são exportados em CSV por tópico. Para cada uma das três condições experimentais
(Normal, GPS Spoofing, Ping DoS), são utilizados os seguintes tópicos: `vehicle_local_position`,
`vehicle_gps_position` e `ekf2_innovations`. Os tópicos são alinhados temporalmente por
`merge_asof` com `direction='backward'`, tendo `vehicle_local_position` como âncora (maior
taxa de amostragem). O resultado é um DataFrame de 44.957 linhas e 113 colunas.

A Tabela 3 apresenta a distribuição de amostras por condição no DataFrame fusionado.

**Tabela 3 — Distribuição de amostras por condição no dataset PX4-QUAD-SITL**

| Condição | Linhas |
|---|---|
| GPS Spoofing | 15.453 |
| Normal | 14.765 |
| Ping DoS | 14.739 |
| **Total** | **44.957** |

Fonte: Elaborado pelo autor (2026). Dados: HASSLER; MUGHAL; ISMAIL (2024).

#### 3.3.2 Features Derivadas e Selecionadas

Além das colunas brutas dos tópicos, são derivadas três features de diagnóstico:

- `innov_norm`: norma L2 dos campos `vel_pos_innov[0]`, `[1]` e `[2]` do tópico EKF2 — mede o
  estresse do filtro face ao modelo de medida;
- `dv_xy`: módulo da diferença entre a velocidade horizontal estimada pela posição local e a
  velocidade GPS — indicador de discrepância entre fontes;
- `r_xy`: distância horizontal acumulada desde o primeiro ponto do voo, calculada sobre `x` e
  `y` da posição local — principal separador do cenário GPS Spoofing, que exibe deriva na
  ordem de 10⁴ m contra menos de 10² m nos demais cenários.

O conjunto final de features (`FEATS`) compreende 11 variáveis: `x`, `y`, `z`, `vx`, `vy`,
`vz`, `eph_loc`, `eph_gps`, `innov_norm`, `dv_xy` e `r_xy`.

#### 3.3.3 Construção das Janelas e Partição

Janelas deslizantes de tamanho `WINDOW = 40` timesteps são construídas separadamente para cada
condição (um voo por pasta), com partição temporal 80/20 dentro de cada arquivo de log. Os
conjuntos de treino e teste são então concatenados entre as três condições. A normalização
StandardScaler é ajustada sobre o conjunto de treino e aplicada ao teste.

A Tabela 4 apresenta o volume de janelas por conjunto e condição.

**Tabela 4 — Volume de janelas por conjunto e condição (ramo físico)**

| Condição | Janelas treino | Janelas teste |
|---|---|---|
| Normal | 11.772 | 2.913 |
| GPS Spoofing | 12.322 | 3.051 |
| Ping DoS | 11.751 | 2.908 |
| **Total** | **35.845** | **8.872** |

Fonte: Elaborado pelo autor (2026).

#### 3.3.4 Modelos

**LSTM:** arquitetura Sequential com `Input(shape=(40, 11))`, `LSTM(48, return_sequences=False)`,
`Dropout(0,25)` e `Dense(3, activation='softmax')`. Treinamento com até 100 épocas,
`batch_size=64`, `EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)` e
semente aleatória fixada em 42. A validação utiliza os últimos 10% do bloco de treino
concatenado (sem `validation_split` aleatório do Keras).

**Random Forest (baseline):** `RandomForestClassifier(n_estimators=200, random_state=42)`,
treinado sobre janelas achatadas no formato (N, 40 × 11 = 440 features).

### 3.4 Protocolo de Avaliação

Os modelos são avaliados no conjunto de teste por meio das seguintes métricas, calculadas com
`sklearn.metrics`:

- **Precision, Recall e F1-score por classe** — relatório completo via `classification_report`;
- **F1-score macro** — média não ponderada do F1 entre classes, penalizando desempenho desigual
  entre rótulos independentemente do desbalanceamento;
- **Matriz de confusão** — visualizada como mapa de calor para identificar os pares de classes
  mais frequentemente confundidos.

A comparação entre LSTM e RF utiliza o F1-score macro como métrica principal de ordenação, por
ser a métrica que melhor reflete o desempenho equilibrado entre classes desbalanceadas.

---

## 4 RESULTADOS

### 4.1 Ramo Ciber — Dataset T-ITS

**Tabela 5 — Resultados comparativos LSTM vs. Random Forest — Ramo ciber (Dataset T-ITS)**

| Classe | Modelo | Precision | Recall | F1-Score |
|---|---|---|---|---|
| Benign | LSTM | 0,764 | **0,978** | 0,858 |
| Benign | RF | 0,759 | 0,979 | 0,855 |
| DoS attack | LSTM | 0,590 | **0,829** | 0,690 |
| DoS attack | RF | **0,608** | 0,574 | 0,591 |
| Replay | LSTM | **0,733** | 0,284 | 0,409 |
| Replay | RF | 0,599 | **0,495** | **0,542** |
| **Macro avg** | **LSTM** | 0,696 | 0,697 | 0,652 |
| **Macro avg** | **RF** | 0,655 | 0,683 | **0,663** |

Fonte: Elaborado pelo autor (2026). Conjunto de teste: 6.620 janelas.

A Figura 2 apresenta as curvas de aprendizado (loss e acurácia de treino e validação) do modelo
LSTM no ramo ciber, e a Figura 3 exibe a matriz de confusão sobre o conjunto de teste.

[INSERIR `learning_curves_ramo_ciber.png`]

**Figura 2 — Curvas de aprendizado do LSTM — Ramo ciber (Dataset T-ITS)**

Fonte: Elaborado pelo autor (2026).

[INSERIR `confusion_matrix_cyber.png`]

**Figura 3 — Matriz de confusão do LSTM — Ramo ciber (Dataset T-ITS)**

Fonte: Elaborado pelo autor (2026).

No ramo ciber, os dois modelos obtiveram desempenho similar em F1-score macro (LSTM: 0,652; RF:
0,663), com o RF superando marginalmente o LSTM. A classe com melhor desempenho em ambos os
modelos foi Benign, com F1 acima de 0,85. A classe DoS attack foi detectada com recall alto
pelo LSTM (0,829), enquanto o RF apresentou recall menor (0,574) e precisão ligeiramente superior.
Replay foi a classe mais problemática: o LSTM atingiu recall de apenas 0,284, embora com precisão
razoável (0,733); o RF obteve recall maior (0,495) e F1 superior (0,542 vs. 0,409).

### 4.2 Ramo Físico — UAVAttackData PX4-QUAD-SITL

**Tabela 6 — Resultados comparativos LSTM vs. Random Forest — Ramo físico (PX4-QUAD-SITL)**

| Classe | Modelo | Precision | Recall | F1-Score |
|---|---|---|---|---|
| Normal | LSTM | **0,862** | **0,822** | **0,841** |
| Normal | RF | 0,851 | 0,800 | 0,825 |
| GPS Spoofing | LSTM | 0,451 | **0,744** | 0,561 |
| GPS Spoofing | RF | **0,529** | 0,684 | **0,597** |
| Ping DoS | LSTM | 0,461 | 0,166 | 0,245 |
| Ping DoS | RF | **0,699** | **0,526** | **0,600** |
| **Macro avg** | **LSTM** | 0,591 | 0,578 | 0,549 |
| **Macro avg** | **RF** | 0,693 | 0,670 | **0,674** |

Fonte: Elaborado pelo autor (2026). Conjunto de teste: 8.872 janelas.

A Figura 4 apresenta as curvas de aprendizado do LSTM no ramo físico, e a Figura 5 exibe a
matriz de confusão sobre o conjunto de teste.

[INSERIR `learning_curves_ramo_fisico.png`]

**Figura 4 — Curvas de aprendizado do LSTM — Ramo físico (PX4-QUAD-SITL)**

Fonte: Elaborado pelo autor (2026).

[INSERIR `confusion_matrix_px4.png`]

**Figura 5 — Matriz de confusão do LSTM — Ramo físico (PX4-QUAD-SITL)**

Fonte: Elaborado pelo autor (2026).

No ramo físico, o RF superou substancialmente o LSTM em F1-score macro (0,674 vs. 0,549). A
diferença foi mais expressiva na classe Ping DoS, onde o RF atingiu F1=0,600 contra 0,245 do
LSTM. O modelo LSTM obteve recall mais alto para GPS Spoofing (0,744 vs. 0,684), mas com
precisão inferior (0,451 vs. 0,529), resultando em F1 menor. A classe Normal foi a melhor
detectada por ambos os modelos.

---

## 5 DISCUSSÃO

### 5.1 Desempenho Comparativo LSTM vs. Random Forest

No ramo físico, o Random Forest obteve F1-macro de 0,674 contra 0,549 da LSTM, com a diferença
mais expressiva na classe Ping DoS (RF F1=0,600 vs. LSTM F1=0,245). Essa inversão de desempenho
está diretamente associada a dois fatores observáveis no processo de treino. Primeiro, a LSTM
exibiu overfitting severo desde a primeira época: a acurácia de treino atingiu 0,774 enquanto a
acurácia de validação permanecia em 0,215, com *early stopping* acionado na sexta época e melhor
*checkpoint* restaurado da primeira. Esse comportamento é sintomático de regime de dados limitados
— há apenas um voo por classe no subconjunto PX4-QUAD-SITL utilizado, o que resulta em
aproximadamente 11.800 janelas de treino por condição após o split temporal 80/20. Redes recorrentes
com estado oculto aprendem dependências temporais de longo alcance, mas exigem diversidade de
trajetórias para generalizar; com uma única missão por rótulo, a LSTM tende a memorizar a sequência
específica do voo de treino. Segundo, o principal discriminador entre as três condições experimentais
é a variável `r_xy` — distância horizontal acumulada desde o início do voo —, que no cenário GPS
Spoofing atinge máximos na ordem de 10⁴ m contra menos de 10² m nos demais cenários. Essa diferença
é estatisticamente capturável por árvores de decisão em uma janela achatada, sem que o modelo precise
rastrear a evolução temporal passo a passo. Portanto, na configuração de dados atual, o RF explora
com eficácia o sinal discriminativo de trajetória disponível nas features de cada janela, enquanto a
LSTM gasta capacidade paramétrica modelando dependências temporais para as quais não há amostras
suficientes de generalização.

### 5.2 Dificuldades por Classe

No ramo ciber, a classe Replay apresentou o pior desempenho de ambos os modelos — F1=0,409 para a
LSTM (recall de 0,284) e F1=0,542 para o RF (recall de 0,495) —, enquanto as classes Benign e DoS
atingiram F1 acima de 0,69 em ambos os classificadores. Essa dificuldade tem origem na natureza do
próprio ataque: o Replay consiste na retransmissão de tráfego legítimo previamente capturado, de modo
que pacotes individuais ou sequências curtas são estatisticamente indistinguíveis do tráfego benigno
quando observados pelas features de rede disponíveis. A análise estatística por classe confirma essa
proximidade: o Replay apresenta médias de `frame.len` (49,2) e `data.len` (13,8) próximas às do
benign (127,1 e 74,1 respectivamente), enquanto o DoS se distingue por valores sistematicamente
menores e cadência mais densa (`time_since_last_packet` médio de 0,051 s contra 0,435 s do benign).
Adicionalmente, a janela de 10 *timesteps* empregada captura menos de um segundo de tráfego à
cadência típica do dataset — horizonte insuficiente para revelar o padrão definitório do Replay, que
é a recorrência de sequências de IDs ou payloads já observados em instâncias anteriores. Essa
limitação é estrutural ao protocolo de janelas curtas: o recall baixo do Replay indica que a detecção
desse vetor de ataque demanda janelas temporais mais longas ou features semânticas que exponham a
repetição de conteúdo, como sequências de IDs de mensagens MAVLink.

### 5.3 Complementaridade dos Dois Ramos e Implicações para o IDS Híbrido

A análise conjunta dos dois ramos revela uma complementaridade que sustenta a arquitetura híbrida
proposta, ainda que cada ramo individualmente apresente limitações distintas. No ramo ciber, a LSTM
obtém vantagem sobre o RF no recall de DoS (0,829 vs. 0,574) e mantém F1-macro competitivo, sendo
a classe Replay — cujo vetor de ataque é semântico e temporalmente distribuído — a principal fonte
de confusão. No ramo físico, ambos os modelos detectam GPS Spoofing com recall superior a 0,68,
mas o Ping DoS permanece como classe ambígua, pois os logs de telemetria simulados mostram
sobreposição significativa entre condições Normal e Ping DoS nas features de posição e velocidade.
Esse perfil de erros cruzados — um ramo fraco em Replay, outro fraco em Ping DoS — é compatível com
a proposta de IDS com dupla frente de detecção: um ataque que passa despercebido no tráfego de rede
pode deixar assinatura no estado físico do voo, e vice-versa. É importante delimitar, contudo, que
este protótipo valida os dois detectores de forma independente sobre fontes de dados distintas; a
fusão das saídas decisórias em um único fluxo temporal calibrado constitui trabalho futuro,
condicionado à disponibilidade de datasets com coleta simultânea de tráfego de rede e telemetria de
voo sob os mesmos cenários de ataque.

---

## 6 LIMITAÇÕES E TRABALHOS FUTUROS

### 6.1 Limitações do Trabalho

As principais limitações deste trabalho são descritas a seguir.

**Escassez de voos por classe no ramo físico.** O subconjunto PX4-QUAD-SITL utilizado contém apenas
um log por condição experimental (Normal, GPS Spoofing, Ping DoS). O split temporal 80/20 é realizado
dentro do mesmo arquivo de voo, de modo que o conjunto de teste corresponde à porção final do mesmo
log de treino — e não a um voo inteiramente novo. A generalização a outros voos, parâmetros de ataque
ou veículos não está demonstrada estatisticamente.

**Vazamento temporal residual no ramo ciber.** O split por classe preserva a ordem temporal dentro
de cada rótulo, mas não garante que instâncias de classes distintas que são temporalmente adjacentes
no CSV estejam corretamente segregadas entre treino e teste. Em capturas contínuas, pacotes vizinhos
de classes diferentes podem apresentar alta correlação, o que pode inflar parcialmente as métricas
de teste.

**Protótipo offline.** Todo o fluxo de dados é pós-captura (CSV/notebooks). Não há medição de
latência de inferência, ingestão em tempo real nem política de alarmes operacional. O sistema não
pode ser qualificado como IDS em tempo real sem esses componentes adicionais.

**"Híbrido" sem fusão temporal calibrada.** A arquitetura proposta combina dois detectores
independentes avaliados em fontes de dados distintas coletadas em protocolos experimentais diferentes.
A integração em um único serviço que consuma rede e telemetria com relógio comum ultrapassa o escopo
deste trabalho e é tratada como trabalho futuro.

**Ausência de FDI e Replay em telemetria.** Os vetores False Data Injection e Replay de telemetria
não possuem rótulos dedicados nos datasets utilizados; esses ataques são abordados apenas no nível
conceitual do referencial teórico.

### 6.2 Trabalhos Futuros

Com base nas limitações identificadas, propõem-se as seguintes direções para trabalhos futuros:

1. **Expansão do ramo físico:** coletar ou utilizar datasets com múltiplos voos por condição de
   ataque, permitindo partição por voo inteiro (treino em voos 1–N, teste em voo N+1) e avaliação
   robusta de generalização;
2. **Ablação do tamanho de janela:** comparar sistematicamente janelas de 10, 20 e 30 timesteps
   no ramo ciber, especificamente para quantificar o impacto no recall da classe Replay;
3. **Estabilidade estatística:** repetir o treino LSTM com múltiplas sementes aleatórias e reportar
   F1-macro médio ± desvio padrão em vez de resultado de semente única;
4. **Split temporal por bloco** no Dataset T-ITS, se a ordenação temporal do arquivo for confirmada
   como contígua por experimento;
5. **Fusão decisória tardia:** desenho de política de alarmes que combine as saídas de probabilidade
   dos dois ramos quando houver datasets com marcação temporal alinhável entre tráfego de rede e
   telemetria de voo.

---

## 7 CONCLUSÃO

Este trabalho apresentou o desenvolvimento e a avaliação de um protótipo de IDS híbrido ciber-físico
para UAVs, estruturado em dois ramos complementares de detecção baseados em aprendizado de máquina.

No ramo ciber, um classificador LSTM foi treinado sobre o Dataset T-ITS para detecção de DoS e Replay
em tráfego MAVLink/Wi-Fi, obtendo F1-macro de 0,652 com recall elevado para DoS (0,829) e desempenho
limitado para Replay (F1=0,409) — resultado coerente com a natureza semântica do ataque, que imita
estatisticamente o tráfego legítimo em janelas curtas. No ramo físico, um classificador LSTM foi
treinado sobre logs de telemetria PX4-QUAD-SITL fusionados com inovações do EKF, alcançando F1-macro
de 0,549 com detecção razoável de GPS Spoofing (F1=0,561) e desempenho fraco para Ping DoS
(F1=0,245), em função da sobreposição entre Normal e Ping DoS nas features de posição e velocidade
neste dataset simulado.

Em ambos os ramos, o baseline Random Forest superou ou empatou com a LSTM em F1-macro, com diferença
mais pronunciada no ramo físico (RF: 0,674 vs. LSTM: 0,549). Esse resultado é atribuído principalmente
ao regime de dados limitados — um único voo por classe — que favorece modelos menos paramétricos com
menor risco de overfitting.

Alcançou-se a demonstração de duas frentes de detecção baseadas em LSTM — tráfego tabular e estado
estimado PX4 — com documentação explícita das classes, das métricas e das limitações metodológicas.
O caráter híbrido do IDS, no sentido de monitorização conjunta ciber e física, traduz-se neste TCC em
dois ramos metodológicos e na discussão de como integrá-los; a fusão temporal em um único fluxo de
decisão permanece como trabalho futuro. As principais limitações são a escassez de voos por classe no
ramo físico, a ausência de correlação temporal direta entre os dois datasets e a natureza offline do
protótipo.

---

## REFERÊNCIAS

HASSLER, Samuel Chase; MUGHAL, Umair Ahmad; ISMAIL, Muhammad. Cyber-physical intrusion detection
system for unmanned aerial vehicles. **IEEE Transactions on Intelligent Transportation Systems**,
[S.l.], v. 25, n. 6, p. 6106–6107, jun. 2024. DOI: 10.1109/TITS.2023.3339728.

MOHAMMED, Ahmad Burhan; FOURATI, Lamia Chaari. Investigation on datasets toward intelligent
intrusion detection systems for intra and inter-UAVs communication systems. **Computers & Security**,
[S.l.], v. 150, p. 104215, 2025. DOI: 10.1016/j.cose.2024.104215.

MUGHAL, Umair Ahmad. **Cyber-physical dataset for UAVs under normal operations and cyber-attacks**.
[S.l.]: IEEE DataPort, 2024. Disponível em: https://ieee-dataport.org/documents/cyber-physical-dataset-uavs-under-normal-operations-and-cyber-attacks. Acesso em: [inserir data].

YU, Zhenhua et al. Cybersecurity of unmanned aerial vehicles: a survey. **IEEE Aerospace and
Electronic Systems Magazine**, [S.l.], p. 182–183, set. 2024. DOI: 10.1109/MAES.2023.3318226.

---

*Fim do rascunho. Itens marcados com [inserir ...] devem ser preenchidos antes da entrega.*

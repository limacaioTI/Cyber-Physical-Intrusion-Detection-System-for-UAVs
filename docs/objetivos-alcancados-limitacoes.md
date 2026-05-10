# Objetivos alcançados vs. limitações

Este texto consolida o **alinhamento** entre os objetivos declarados no `README.md` e o **estado atual** do trabalho (notebooks em `notebooks/`, dados em `data/`). Serve como base para **Resultados**, **Discussão** ou **Conclusões** da monografia.

---

## Quadro rápido (objetivos do README)

| Objetivo (README) | Grau de alcance | Onde aparece no trabalho |
|-------------------|-----------------|---------------------------|
| **Monitorar** tráfego de rede (âmbito MAVLink) e estados físicos (telemetria) | **Parcialmente** | Ramo rede: CSV estilo Wireshark (`Dataset_T-ITS`). Ramo físico: logs PX4 (posição GPS, local, EKF2). *Captura simultânea no mesmo artefacto*: não — são **duas fontes** independentes. |
| **Analisar** com **LSTM** sobre sequências temporais | **Alcançado** | Modelos LSTM no ramo rede e no ramo fusão PX4 (`Infos_lstm_fusao_px4.ipynb`); janelas deslizantes e normalização conforme método. |
| **Detectar** normal vs. ataque (DoS, spoofing, replay, FDI); tempo **quase real** | **Parcialmente** | **DoS**, **Replay** e **benign** no tráfego; **GPS Spoofing** e **Ping DoS** nos logs PX4. **FDI** não tratado empiricamente com rótulo dedicado neste conjunto de dados. **Tempo real:** protótipo **offline** sobre CSV — não há medição de latência nem implantação em pipeline contínuo. |
| **Validar IDS híbrido** | **Parcialmente** | “Híbrido” neste trabalho corresponde a **dois detectores complementares** (cyber + physical) descritos e avaliados em separado, com **fusão decisória em tempo único** ainda não implementada nem possível linha-a-linha entre T-ITS e PX4 sem desenho experimental comum documentado nas fontes. |

---

## 1. Objetivos alcançados (contribuições concretas)

### 1.1 Ramo ciber (tráfego de rede)

- Construir um **pipeline reprodutível** de carga de dados, limpeza (`df_clean`), EDA por classe e modelo **LSTM** para classificação **multiclasse** (ex.: benign, DoS attack, Replay).
- Caracterizar limitações já observadas (ex.: **confusão** entre ataques sobretudo com poucas features, utilidade da inspeção **Replay vs DoS** com métricas adicionais quando necessário).

### 1.2 Ramo físico / estimação (telemetria PX4)

- Explorar `vehicle_gps_position` e `vehicle_local_position` (**unidades**, cadência, trajetória, **`r_xy`**, interpretação sob **GPS Spoofing** vs. Normal/Ping DoS).
- Implementar **`merge_asof`** entre local, GPS e **`ekf2_innovations`**, gerando métricas de **stress** da fusão (`innov_norm`, discrepâncias de velocidade horizontal).
- Prototipar **LSTM** sobre janelas multivariadas com **partição temporal 80/20 dentro de cada voo**, evitando o pior caso de embaralhamento dentro do mesmo ficheiro.

### 1.3 Documentação e coerência com o CPS

- Documentos de apoio (`docs/resumo.md`, `DOCUMENTO.md` na pasta PX4-T-ITS e na pasta UAVAttackData) registam **métricas**, **lacunas bibliográficas** e **perguntas típicas de orientador**.

---

## 2. Limitações (mérito acadêmico e fronteira do trabalho)

### 2.1 Dados e rotulagem

- **Um ficheiro de voo por classe** nos cenários QUAD-SITL analisados: a **generalização** a outros voos ou parâmetros de ataque **não está demonstrada** estatisticamente.
- **`Dataset_T-ITS`** e logs **PX4** não foram recolhidos no mesmo protocolo expondo **um único fluxo temporal** rede–fusão correlacionável; a articulação no texto é por **complementaridade conceitual** (IDS do duplo ramo), não fusão física já calibrada.
- **FDI**, **Replay** em telemetria e **MAVLink Sequence Dataset** aparecem no âmbito do trabalho só na revisão/objetivos gerais, **salvo uso explícito** futuro nos notebooks ou na monografia.

### 2.2 Metodologia de avaliação

- **`train_test_split` aleatório** no ramo rede (quando utilizado assim) permite **vazamento temporal** em capturas contínuas; no ramo PX4 o split **dentro-do-voo** mitiga apenas parte do problema (**não** substitui “voo novo no teste”).
- **`validation_split` aleatório** durante o treino da LSTM no PX4 **não** coincide com o teste temporal final — os números de **referência para o TCC** devem ser os do **conjunto de teste** definido pela partição temporal, não o pico oscilante de `val_accuracy` durante o `fit`.

### 2.3 Desenvolvimento e “tempo quase real”

- Todo o fluxo atual é **pós‑captura** (CSV/notebooks): **não** há ingestão em tempo real, **IDs operacionais** de alarme, nem políticas de custo **FP/FN** implementadas.
- **“IDS híbrido”** operacional (um único serviço que consome rede + telemetria com relógio comum) **ultrapassa** o que está codificado; o trabalho posiciona-se como **prototipagem e validação de conceito** em dados públicos.

---

## 3. Frases prontas para Conclusão / Discussão

- *“Alcançou-se a demonstração de duas frentes de deteção baseadas em LSTM — tráfego tabular e estado estimado PX4 — com documentação explícita das classes e das métricas.”*
- *“O carácter híbrido do IDS, no sentido de monitorização conjunta cyber e physical, traduz-se neste TCC em **dois ramos metodológicos** e na discussão de como integrá-los; a fusão temporal em um único fluxo de decisão permanece como trabalho futuro.”*
- *“As principais limitações são a escassez de voos por classe em PX4, a ausência de correlação temporal direta com o dataset de rede, e a natureza offline do protótipo.”*

---

## 4. Trabalhos futuros (encaixam no README sem conflito)

1. Expansão de **bases** por classe e **aval por voo** (teste apenas em logs não usados no treino).
2. **Matrizes de confusão** sistemáticas e **baseline** (ex.: Random Forest) nos dois ramos.
3. **Split temporal/bloco** no `Dataset_T-ITS`, se a ordenação temporal for preservada no arquivo.
4. Desenho de **política de alarmes** e, se aplicável, **fusão tardia** quando existir registos com marcação temporal alinhável.
5. Estudo opcional sobre **FDI** / **dataset de sequências MAVLink** se houver inclusão bibliográfica e dados disponíveis.

---

*Última redação pensada para acompanhar o `README.md` e os notebooks atualmente no repositório. Ajuste números de métricas à última execução dos notebooks se o orientador pedir valores exatos na monografia.*

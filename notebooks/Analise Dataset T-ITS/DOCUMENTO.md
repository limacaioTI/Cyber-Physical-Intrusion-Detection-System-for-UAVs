# Documentação — infraestrutura, ataques e dados (`Infos_data.ipynb`)

Este documento parte das **perguntas que você elaborou** e acrescenta **respostas enxutas** para estudar ou colar adaptado na monografia. Quando algo **não está no CSV** nem no notebook, marcamos como *complementar* ou *confirmar na fonte*.

**Artefatos do projeto**

| Artefato | Caminho |
|----------|---------|
| Notebook | [`Infos_data.ipynb`](Infos_data.ipynb) |
| CSV (rede) | [`../data/Dataset_T-ITS.csv`](../data/Dataset_T-ITS.csv) |
| Detalhes do dataset / licença | [`../data/README.md`](../data/README.md) |
| Resumo metodológico longo | [`../docs/resumo.md`](../docs/resumo.md) |

---

## 1. Sobre a infraestrutura e o sinal

### 1.1 Qual é o protocolo de aplicação? (MAVLink)

**Resposta (contexto UAV típico):** em muitos quadros abertos (PX4, ArduPilot), o **MAVLink** é o protocolo de **comando e telemetria** sobre IP/UDP (ou serial). Ele **encapsula mensagens** pequenas e tipadas (ID + payload + checksum) dentro de **datagramas UDP** (e abaixo disso, **IP** e enlace **802.11**).

**No seu CSV:** as colunas `udp.*`, `data.*`, `ip.*` e `frame.*` são compatíveis com **exportação de tráfego** nesse estilo; o notebook não decodifica MAVLink byte a byte — trabalha com **proxy de rede** (tamanhos, tempos, campos de cabeçalho).

### 1.2 Meio físico? Wi‑Fi 802.11 — frequências e vulnerabilidade

**Frequências comuns (ISM):** ~**2,4 GHz** e ~**5 GHz** em drones de consumo e em muitos laboratórios; **5,8 GHz** também aparece em vídeo/controle em alguns sistemas.

**Por que Wi‑Fi costuma ser mais “exposto” que rádio proprietário?** Padrão **conhecido**, ecossistema de **ferramentas** (captura, injeção, fuzzing), **alcance** útil em ambiente de teste e, em muitos ensaios, **sem criptografia de enlace forte** ou com configuração fraca. Rádio proprietário tende a **ofuscar** camada física e protocolo, o que **não** significa ser “mais seguro por definição”, só **menos documentado** para o atacante genérico.

### 1.3 Tráfego criptografado ou em claro?

**No laboratório / em muitos datasets de IDS:** o tráfego é **observável em claro** na camada que o Wireshark exporta (L3/L4/payload), justamente para **pesquisa** e rótulos de ataque.

**Exemplo que você citou (Tello EDU):** drones de educação frequentemente usam **Wi‑Fi em claro** ou app proprietário — **facilita** replay, injeção e análise, mas **não** prova que *este* dataset use Tello; **confirme no paper / documentação do dataset** que você cita no TCC.

### 1.4 Topologia da rede?

**Cenário típico de ensaio:** **estação de controle** ↔ **AP ou modo ad-hoc** ↔ **drone** (pode ser **ponto a ponto lógico** através de um AP, ou **Wi‑Fi direto**). O dataset tabular **não** traz diagrama — descreva a topologia **como no artigo experimental** ou como **hipótese** do seu cenário-alvo.

---

## 2. Sobre o dispositivo (o drone)

### 2.1 Limitações de hardware e IDS na estação de controle

**Argumento válido:** plataformas leves (**ex.: menor capacidade CPU/RAM**) mal aguentam ML pesado **embarcado** + voo tempo real. Um **IDS na GCS** (computador solo) observa **o que chega pela rede**, com mais **margem de processamento** — trade-off: **latência** e **ponto único de monitoração**.

### 2.2 Perda do link — fail-safe?

**Em geral (conceito):** firmwares modernos aplicam **failsafe** configurável (**RTL**, **Land**, **Hold**, última posição, etc.). O **comportamento exato** depende do **veículo, firmware e parâmetro** — na banca, evite afirmar “sempre pousa” sem citar manual/PX4 do **tipo** de UAV do experimento da fonte.

### 2.3 Sensores e como rede “engana” indiretamente

**Hover/estabilização:** frequentemente IMU, barômetro, compass, GPS GNSS em outdoor, etc. **Ataques de rede** não “mentem” para o acelerômetro diretamente, mas podem **atrasar ou corromper comandos/telemetria**, gerar **comandos falsos** (replay/injeção) ou **DoS** que impede atualização de setpoints — o efeito **físico** surge por **perda de controle** ou **estado errado**.

---

## 3. Sobre os ataques (vetores)

### 3.1 DoS técnico — UDP? Precisa estar autenticado?

**DoS sobre enlace UDP (MAVLink):** comum haver **inundação de pacotes** ou **consumo de canal** para ** Saturar CPU** ou **perder mensagens válidas**.

**Precisa estar “logado”?** Para **consumir canal** ou **inundar** na mesma célula Wi‑Fi / alcance RF, frequentemente **basta estar no meio físico adequado** (mesmo BSS ou interferência forte), nem sempre há **autenticação forte** impedindo *ruído* na camada física/DL. **Replay/injeção** detalhes dependem da **pilha usada no experimento** — **citado no paper do dataset**.

### 3.2 DoS vs Replay neste cenário

| | DoS | Replay |
|--|-----|--------|
| **Meta típica** | Disponibilidade (saturation, latency) | Integridade/autenticidade (**repetir**/reenviar comandos ou telemetria) |
| **Sinal nos dados** | Picos de taxa, `time_since_last_packet` menor, padrões de volume | Mensagens **válidas** repetidas ou fora de **ordem**/contexto temporal |

**Drone “como diferencia” comando repetido:** em prática, **filtros**, **sessão**, **nonce**, timestamps de missão ou ** políticas de segurança** — muitos sistemas antigos são **fracos**. No **ML** do seu trabalho: **sem** esse contexto nas features, Replay **aproxima-se** estatisticamente do benign (**baixo recall** — ver `docs/resumo.md` §3.1).

### 3.3 Ponto de entrada do atacante

**Possibilidades de ensaio acadêmico:** (i) cliente associado ao Wi‑Fi, (ii) **modo monitor** + injeção (depende legalmente do ambiente), (iii) **interferência** sem “conectar”. **O dataset** indica **rótulo** (`class`), não o **papel** exato do atacante — use a **publicação** para descrever o vetor.

---

## 4. Sobre a inteligência de dados (ciber-físico e colunas)

### 4.1 Por que “ciber-físicos”?

**Ciber:** medidas derivadas de **comunicação** (pacotes, tempos, protocolos). **Físico:** **efeito** no sistema (trajetória, estabilidade, aborto de missão) — no **seu CSV atual**, o foco é ramo **ciber** (rede); o ramo **físico** pode ser explorado com **telemetria PX4** (`docs/resumo.md` §6 e `UAVAttackData`), se estiver no escopo.

### 4.2 Significado das colunas escolhidas no modelo

| Feature | O que informa (intuição) |
|---------|---------------------------|
| `frame.len` | Tamanho **bruto** do frame capturado — mistura **cabeçalhos de enlace + MAC + IP + payload** (depende do que o export inclui). |
| `ip.len` | Tamanho do **datagrama IP** — útil quando o framing sobe bem com IP. |
| `time_since_last_packet` | **Ritmo** da captura; ataques volumosos mudam distribuições de intervalo. |

**Intenção do atacante:** as colunas são **proxies comportamentais**, não uma leitura direta da “mente” do adversário — o que aparece são **mudanças de padrão** aprendidas.

### 4.3 Janela temporal (windowing)

**Por que não um só pacote?** Um pacote pode ser **ambigüo** entre classes (especialmente **Replay vs DoS** ou **Replay vs benign**). **sequências curtas** dão chance à LSTM capturar **transições**. **Limite atual:** `window_size=10` pode ser curto para Replay — mencionar na discussão (**janela maior**, mais features ou multimodal).

---

## 5. Sobre aplicabilidade (perguntas típicas de banca)

### 5.1 IDS em tempo real vs pós-mortem?

**Estado atual (notebook treina Keras sobre CSV offline):** é **análise batch / pós-captura**, não um pipeline provado em **linha de produção** com latência SLA.

**Para argumentar tempo real:** seria preciso **taxa de amostragem**, **tamanho do modelo**, **hardware** e **latência de inferência** medidos — **trabalho futuro** se não tiver números.

### 5.2 Custo de falso positivo

**Risco operacional:** falso positivo pode levar **corte conservador do link**, **panic mode** ou **interrupção manual** — em sistema real, política deve ser **graduada** (alerta vs bloqueio). Na monografia: **custos diferentes** FP vs FN (quadro de cenários).

---

## 6. Perguntas a amarrar com a bibliografia obrigatória

Marque ✅ quando você tiver **página/seção do paper** ou **README do IEEE DataPort** que responda:

- [ ] Equipamentos exatos (drone / firmware / cenário RF) da coleta empírica da base **`Dataset_T-ITS.csv`**.
- [ ] Como foram gerados os rótulos **DoS**, **Replay** e **benign** (ferramenta, posição do atacante, duração).
- [ ] Se há **split temporal oficial** recomendado ou **ordem preservada** no CSV para avaliação.

---

*Versão atual: incorpora suas cinco secções originais, com formatação e respostas de apoio. Ajuste trechos marcados como “confirmar na fonte” com citações reais antes da defesa.*
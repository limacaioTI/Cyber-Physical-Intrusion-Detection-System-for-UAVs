# Sistema de Detecção de Intrusão Ciber-Físico para UAVs

> Abordagem com **redes neurais recorrentes (LSTM)** para detecção de anomalias em comunicações **MAVLink** e dados de **telemetria**.

---

## Visão geral

Este trabalho parte de pesquisas recentes (2024–2025) sobre segurança de **Veículos Aéreos Não Tripulados (UAVs)**. Em síntese:

- **Vulnerabilidade:** UAVs são sistemas ciber-físicos (CPS) expostos a ataques que atingem rede (*cyber*) e sensores (*physical*).
- **Limitação:** muitos sistemas de segurança tratam só dados de rede, sem o comportamento físico do voo.
- **Oportunidade:** *machine learning*, em especial **LSTM**, ajuda a capturar padrões temporais e a identificar ataques como *GPS spoofing* e injeção de dados falsos.

---

## Objetivos do TCC

Desenvolver e validar um **IDS híbrido** que:

1. **Monitore** — captura simultânea do tráfego de rede (protocolo MAVLink) e estados físicos (telemetria: altitude, aceleração, posição).
2. **Analise** — arquitetura **LSTM** sobre sequências temporais desses dados.
3. **Detecte** — classificação de anomalias em tempo quase real, distinguindo voo normal de cenários de ataque, por exemplo:

   - DoS (*Denial of Service*)
   - *GPS spoofing*
   - *Replay attacks*
   - *False Data Injection* (FDI)

> Sem drone físico para coleta: treino e validação usam **datasets e literatura** indicados abaixo.

---

## Fontes de dados

| Fonte | Descrição |
|--------|-----------|
| **UAV-Attack Dataset** | Base ciber-física (Hassler et al., 2024) com registros de ataques. |
| **MAVLink Sequence Dataset** | Sequências de IDs de mensagens para comportamento de rede. |

---

## Referências (base teórica)

- *Cyber-Physical Intrusion Detection System for Unmanned Aerial Vehicles* (IEEE, 2024).
- *Cybersecurity of Unmanned Aerial Vehicles: A Survey* (IEEE, 2024).
- *Investigation on datasets toward intelligent IDS* (*Computers & Security*, 2025).

---

## Tecnologias

| Área | Ferramentas |
|------|-------------|
| Linguagem | Python 3.x |
| Deep learning | TensorFlow / Keras (LSTM) |
| Dados | Pandas, NumPy |
| Visualização | Matplotlib, Seaborn |
| Ambiente | Google Colab / Jupyter Notebook |

---

## Estrutura do repositório

Árvore atual do projeto (pastas vazias versionadas com `.gitkeep` até receberem arquivos):

```
TCC/
├── data/
│   ├── .gitignore   # Ignora *.csv, *.npy, *.pcap
│   └── README.md    # Links e notas sobre os datasets
├── docs/
│   └── resumo.md  # Resumo do notebook + ideias de análises futuras
├── notebooks/     # Jupyter: análise exploratória e modelo LSTM
├── src/
│   └── requirements.txt
└── README.md
```

---

## Autoria

**Autor:** [Seu Nome]  
**Orientador(a):** [Nome do orientador]  
**Instituição:** [Nome da instituição] — Trabalho de Conclusão de Curso (TCC)

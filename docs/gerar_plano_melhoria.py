from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont("Arial",        "/System/Library/Fonts/Supplemental/Arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold",   "/System/Library/Fonts/Supplemental/Arial Bold.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Italic", "/System/Library/Fonts/Supplemental/Arial Italic.ttf"))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic")

OUTPUT = "/Users/caiolima/Documents/TCC/docs/plano_melhoria_tcc.pdf"

doc = SimpleDocTemplate(
    OUTPUT, pagesize=A4,
    leftMargin=2.5*cm, rightMargin=2.5*cm,
    topMargin=2.5*cm, bottomMargin=2.5*cm,
)
W, H = A4

# Paleta de cores
AZUL         = colors.HexColor("#1a3a5c")
AZUL_CLARO   = colors.HexColor("#2e6da4")
VERDE        = colors.HexColor("#1a6b3c")
VERDE_CLARO  = colors.HexColor("#d4edda")
VERDE_BORDA  = colors.HexColor("#28a745")
VERMELHO     = colors.HexColor("#7b1111")
VERMELHO_CL  = colors.HexColor("#f8d7da")
VERMELHO_BD  = colors.HexColor("#c0392b")
AMARELO_CL   = colors.HexColor("#fff3cd")
AMARELO_BD   = colors.HexColor("#e67e22")
CINZA_BG     = colors.HexColor("#f4f6f9")
CINZA_BORDA  = colors.HexColor("#c8d4e3")
CINZA_TEXTO  = colors.HexColor("#444444")

def s(nome, fn="Arial", fs=10, cor=CINZA_TEXTO, **kw):
    kw.setdefault("leading", fs * 1.45)
    return ParagraphStyle(nome, fontName=fn, fontSize=fs, textColor=cor, **kw)

titulo_s    = s("Titulo",    "Arial-Bold", 18, AZUL,       spaceAfter=4, leading=24, alignment=TA_CENTER)
subtit_s    = s("Subtitulo", "Arial",      10, AZUL_CLARO, spaceAfter=2, leading=14, alignment=TA_CENTER)
secao_s     = s("Secao",     "Arial-Bold", 13, AZUL,       spaceBefore=14, spaceAfter=5, leading=18)
subsecao_s  = s("Subsecao",  "Arial-Bold", 10.5, AZUL_CLARO, spaceBefore=8, spaceAfter=3, leading=14)
corpo_s     = s("Corpo",     "Arial",      9.5, CINZA_TEXTO, leading=14, spaceAfter=4, alignment=TA_JUSTIFY)
ok_s        = s("Ok",        "Arial",      9.5, VERDE,       leading=14, spaceAfter=3, leftIndent=12, alignment=TA_JUSTIFY)
ruim_s      = s("Ruim",      "Arial",      9.5, VERMELHO,    leading=14, spaceAfter=3, leftIndent=12, alignment=TA_JUSTIFY)
aviso_s     = s("Aviso",     "Arial",      9.5, AMARELO_BD,  leading=14, spaceAfter=3, leftIndent=12, alignment=TA_JUSTIFY)
rodape_s    = s("Rodape",    "Arial",       8, colors.grey, leading=10, alignment=TA_CENTER)
cel_hdr     = s("CelHdr",    "Arial-Bold",  9, colors.white, leading=12)
cel_bod     = s("CelBod",    "Arial",       8.5, CINZA_TEXTO, leading=12)
cel_verde   = s("CelVerde",  "Arial",       8.5, VERDE,       leading=12)
cel_verm    = s("CelVerm",   "Arial",       8.5, VERMELHO,    leading=12)
cel_amar    = s("CelAmar",   "Arial",       8.5, AMARELO_BD,  leading=12)

BASE_STYLE = TableStyle([
    ("BACKGROUND",    (0,0),(-1,0), AZUL),
    ("ROWBACKGROUNDS",(0,1),(-1,-1),[CINZA_BG, colors.white]),
    ("GRID",          (0,0),(-1,-1), 0.4, CINZA_BORDA),
    ("VALIGN",        (0,0),(-1,-1), "TOP"),
    ("LEFTPADDING",   (0,0),(-1,-1), 6),
    ("RIGHTPADDING",  (0,0),(-1,-1), 6),
    ("TOPPADDING",    (0,0),(-1,-1), 5),
    ("BOTTOMPADDING", (0,0),(-1,-1), 5),
])

def ph(t): return Paragraph(t, cel_hdr)
def pc(t): return Paragraph(t, cel_bod)
def pv(t): return Paragraph(t, cel_verde)
def pvr(t): return Paragraph(t, cel_verm)
def pa(t): return Paragraph(t, cel_amar)

def tab(hdr, rows, fracs):
    cw = [(W - 5*cm)*f for f in fracs]
    all_rows = [[ph(c) for c in hdr]] + rows
    t = Table(all_rows, colWidths=cw, repeatRows=1)
    t.setStyle(BASE_STYLE)
    return t

def hr(cor=CINZA_BORDA, e=0.8):
    return HRFlowable(width="100%", thickness=e, color=cor, spaceAfter=4, spaceBefore=2)

def box(paragraphs, bg, borda):
    """Caixa colorida em torno de parágrafos usando tabela de 1 célula."""
    content = []
    for p in paragraphs:
        content.append(p)
    inner = Table([[content]], colWidths=[(W - 5*cm)])
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(0,0), bg),
        ("BOX",        (0,0),(0,0), 1, borda),
        ("LEFTPADDING",(0,0),(0,0), 8),
        ("RIGHTPADDING",(0,0),(0,0), 8),
        ("TOPPADDING", (0,0),(0,0), 6),
        ("BOTTOMPADDING",(0,0),(0,0), 6),
        ("VALIGN",     (0,0),(0,0), "TOP"),
    ]))
    return inner

# ---------------------------------------------------------------------------
story = []

# CAPA
story.append(Paragraph("Plano de Melhoria — TCC", titulo_s))
story.append(Paragraph(
    "Sistema de Detecção de Intrusão Ciber-Físico para UAVs", subtit_s))
story.append(Paragraph(
    "Análise aprofundada: o que foi feito, o que está bom, o que precisa melhorar e o que falta",
    subtit_s))
story.append(Paragraph("Caio de Souza Lima — UFF | 18 de maio de 2026", subtit_s))
story.append(hr(AZUL, 1.5))
story.append(Spacer(1, 6))

# RESUMO EXECUTIVO
story.append(Paragraph("Resumo Executivo", secao_s))
story.append(Paragraph(
    "Este documento consolida uma análise completa do estado atual do TCC com base na leitura "
    "do README, de todos os notebooks, documentos de apoio (docs/) e rascunho ABNT. "
    "O trabalho está em estágio avançado: os dois ramos do IDS híbrido (ciber e físico) foram "
    "implementados, avaliados e já possuem um rascunho de monografia praticamente completo. "
    "Os pontos de melhoria são bem definidos e alcançáveis antes da defesa.",
    corpo_s))
story.append(Spacer(1, 4))

# QUADRO GERAL DE STATUS
story.append(Paragraph("Quadro Geral de Status por Área", subsecao_s))

status_rows = [
    [pc("Ramo Ciber (Dataset T-ITS)"),         pv("✔ Implementado e avaliado"), pv("LSTM + RF, split temporal, 7 features, resultados documentados")],
    [pc("Ramo Físico (PX4-QUAD-SITL)"),        pv("✔ Implementado e avaliado"), pv("4 notebooks, merge_asof, 11 features derivadas, LSTM + RF, resultados documentados")],
    [pc("Rascunho ABNT da monografia"),         pv("✔ Muito avançado"),          pv("Cap. 1–7 escritos, tabelas de resultados preenchidas, referências parcialmente completas")],
    [pc("Documentação de apoio (docs/)"),       pv("✔ Muito detalhada"),         pv("resumo.md, objetivos-alcancados-limitacoes.md, DOCUMENTO.md em cada pasta")],
    [pc("Baseline (Random Forest)"),            pv("✔ Implementado"),            pv("Comparação LSTM vs RF em ambos os ramos com F1-macro")],
    [pc("MAVLink Sequence Dataset"),            pvr("✗ Não utilizado"),          pvr("Previsto no README mas sem notebook nem análise até o momento")],
    [pc("FDI (False Data Injection)"),          pvr("✗ Apenas teórico"),         pvr("Sem dataset com rótulo FDI — tratado só no referencial teórico")],
    [pc("Ablação de tamanho de janela"),        pa("⚠ Código pronto, não rodado"), pa("RUN_WINDOW_ABLATION = False no notebook ciber")],
    [pc("Figura 1 (diagrama arquitetura)"),     pa("⚠ Faltando"),               pa("Rascunho ABNT tem [INSERIR FIGURA 1] — não foi criada")],
    [pc("Fusão decisória dos dois ramos"),      pa("⚠ Trabalho futuro"),         pa("Descrita como objetivo, mas não implementada — corretamente declarada como limitação")],
    [pc("IDS em tempo real (latência)"),        pa("⚠ Não medido"),             pa("Pipeline offline sobre CSV; latência de inferência não foi calculada")],
]
story.append(tab(
    ["Área / Componente", "Status", "Observação"],
    status_rows,
    [0.30, 0.18, 0.52],
))
story.append(Spacer(1, 10))

# ============================================================
# SEÇÃO 1 — O QUE JÁ ESTÁ FEITO
# ============================================================
story.append(PageBreak())
story.append(hr(AZUL, 1.5))
story.append(Paragraph("1. O Que Já Está Feito", secao_s))
story.append(Paragraph(
    "Esta seção detalha tudo o que foi implementado e documentado, servindo como registro "
    "do avanço real do trabalho.", corpo_s))

story.append(Paragraph("1.1 Ramo Ciber — Dataset T-ITS", subsecao_s))
feito_ciber = [
    [pc("Carregamento e inspeção"), pc("54.783 linhas, 38 colunas lidas com pandas. df.info(), value_counts(), estatísticas por classe.")],
    [pc("Limpeza dos dados"), pc("Conversão numérica de 7 colunas base com pd.to_numeric(errors='coerce'); imputação pela mediana nas colunas estendidas; remoção de NaN nas colunas base e em 'class'.")],
    [pc("Análise exploratória (EDA)"), pc("Estatísticas por classe (média, std, min, max) para frame.len, ip.len, data.len, time_since_last_packet. Inspeção Replay vs DoS com cobertura por camada, Mann-Whitney U, boxplots em escala log.")],
    [pc("Feature engineering"), pc("FEATS_V2: 7 features (frame.len, ip.len, time_since_last_packet, wlan.fc.type, wlan.duration, udp.length, data.len).")],
    [pc("Janelas deslizantes"), pc("window=10 timesteps, ordenação por timestamp_c, 33.092 amostras no formato (10, 7).")],
    [pc("Split temporal"), pc("80/20 por classe, ordenado por timestamp_c — evita vazamento temporal. Validação nos últimos 10% do treino (não aleatório).")],
    [pc("Normalização"), pc("MinMaxScaler ajustado só no treino e aplicado ao teste — sem vazamento de escala.")],
    [pc("Modelo LSTM"), pc("Input(10,7) → LSTM(50) → Dropout(0.2) → Dense(3, softmax). EarlyStopping(patience=5) + ModelCheckpoint. Até 100 épocas.")],
    [pc("Baseline RF"), pc("RandomForestClassifier(n_estimators=200) treinado sobre janelas achatadas (N, 70 features).")],
    [pc("Métricas"), pc("classification_report (precision, recall, F1 por classe), F1-macro, matriz de confusão visual.")],
    [pc("Artefatos salvos"), pc("best_model_cyber.keras, confusion_matrix_cyber.png, learning_curves_ramo_ciber.png.")],
    [pc("Resultados obtidos"), pc("LSTM F1-macro = 0,652 | RF F1-macro = 0,663. Benign F1 > 0,85. DoS recall alto na LSTM (0,829). Replay: principal fragilidade (LSTM F1=0,409, RF F1=0,542).")],
]
story.append(tab(["Etapa", "Detalhe"], feito_ciber, [0.28, 0.72]))
story.append(Spacer(1, 8))

story.append(Paragraph("1.2 Ramo Físico — UAVAttackData PX4-QUAD-SITL", subsecao_s))
feito_fisico = [
    [pc("4 notebooks distintos"), pc("Infos_gps_position.ipynb, Infos_local_position.ipynb, Infos_fusao_gps_local_ekf.ipynb, Infos_lstm_fusao_px4.ipynb — cada um com foco crescente de exploração a modelo.")],
    [pc("Fusão temporal (merge_asof)"), pc("Alinhamento de vehicle_local_position + vehicle_gps_position + ekf2_innovations pelo timestamp com direction='backward'. 44.957 linhas × 113 colunas.")],
    [pc("Features derivadas"), pc("innov_norm: norma L2 das inovações do EKF. dv_xy: discrepância de velocidade horizontal GPS vs local. r_xy: deriva horizontal acumulada desde o início do voo (principal separador de GPS Spoofing).")],
    [pc("Conjunto final de features"), pc("11 variáveis: x, y, z, vx, vy, vz, eph_loc, eph_gps, innov_norm, dv_xy, r_xy.")],
    [pc("Janelas deslizantes"), pc("WINDOW=40 timesteps. Split temporal 80/20 dentro de cada voo (por condição). Treino: 35.845 janelas, Teste: 8.872 janelas.")],
    [pc("Normalização"), pc("StandardScaler ajustado só no treino.")],
    [pc("Modelo LSTM"), pc("Input(40,11) → LSTM(48) → Dropout(0,25) → Dense(3, softmax). EarlyStopping(patience=5, restore_best_weights=True). Semente fixada em 42.")],
    [pc("Baseline RF"), pc("RandomForestClassifier(n_estimators=200) com janelas achatadas (N, 440 features).")],
    [pc("Artefatos salvos"), pc("best_model_px4.keras, confusion_matrix_px4.png, learning_curves_ramo_fisico.png.")],
    [pc("Resultados obtidos"), pc("LSTM F1-macro = 0,549 | RF F1-macro = 0,674. GPS Spoofing detectado com recall moderado (LSTM 0,744). Ping DoS: classe mais fraca (LSTM recall 0,166). RF superou LSTM significativamente.")],
]
story.append(tab(["Etapa", "Detalhe"], feito_fisico, [0.28, 0.72]))
story.append(Spacer(1, 8))

story.append(Paragraph("1.3 Rascunho ABNT da Monografia", subsecao_s))
feito_rascunho = [
    [pc("Capítulo 1 — Introdução"),          pc("Contextualização, problema, motivação, objetivos gerais e específicos, organização do trabalho. Com citações ABNT.")],
    [pc("Capítulo 2 — Referencial Teórico"), pc("CPS e UAVs, vetores de ataque (DoS, Replay, GPS Spoofing, FDI), IDS baseado em ML, LSTM, datasets públicos.")],
    [pc("Capítulo 3 — Metodologia"),         pc("Arquitetura do IDS híbrido, ramo ciber (seções 3.2.1 a 3.2.4), ramo físico (seções 3.3.1 a 3.3.4), protocolo de avaliação. Tabelas de features, volumes de dados, distribuição de classes.")],
    [pc("Capítulo 4 — Resultados"),          pc("Tabela 5 (LSTM vs RF ramo ciber) e Tabela 6 (LSTM vs RF ramo físico) preenchidas com números reais. Referências às figuras das curvas e matrizes.")],
    [pc("Capítulo 5 — Discussão"),           pc("Desempenho comparativo, dificuldades por classe, complementaridade dos dois ramos.")],
    [pc("Capítulo 6 — Limitações"),          pc("Escassez de voos, vazamento temporal residual, protótipo offline, híbrido sem fusão temporal, ausência de FDI.")],
    [pc("Capítulo 7 — Conclusão"),           pc("Síntese dos dois ramos, resultados finais, limitações declaradas, trabalhos futuros.")],
    [pc("Referências"),                      pc("4 referências principais em formato ABNT. Algumas com data de acesso a preencher.")],
]
story.append(tab(["Capítulo", "Conteúdo"], feito_rascunho, [0.25, 0.75]))
story.append(Spacer(1, 8))

story.append(Paragraph("1.4 Documentação de Apoio", subsecao_s))
feito_docs = [
    [pc("docs/resumo.md"), pc("Análise detalhada do dataset T-ITS: EDA, modelagem, argumentação para o texto da monografia, plano de estudo do UAVAttackData.")],
    [pc("docs/objetivos-alcancados-limitacoes.md"), pc("Alinhamento entre os objetivos do README e o estado atual do trabalho. Frases prontas para conclusão e lista de trabalhos futuros.")],
    [pc("notebooks/.../DOCUMENTO.md"), pc("Documentação por pasta de análise: o que o notebook faz, resultados, limitações e perguntas típicas de banca (T-ITS e PX4).")],
    [pc("data/README.md"), pc("Links para download dos datasets com notas sobre licenças.")],
]
story.append(tab(["Arquivo", "Conteúdo"], feito_docs, [0.32, 0.68]))

# ============================================================
# SEÇÃO 2 — O QUE ESTÁ BOM
# ============================================================
story.append(PageBreak())
story.append(hr(AZUL, 1.5))
story.append(Paragraph("2. O Que Está Bom — Pontos Fortes do Trabalho", secao_s))
story.append(Paragraph(
    "Aspectos que já estão sólidos e podem ser apresentados com confiança ao professor.",
    corpo_s))

bom_rows = [
    [pv("Rascunho ABNT praticamente completo"),
     pc("7 capítulos escritos com linguagem acadêmica, citações ABNT, tabelas de resultados reais e discussão crítica. Poucos trechos [inserir...] faltando.")],
    [pv("Dois ramos implementados e funcionando"),
     pc("Ramo ciber e ramo físico com pipelines completos, reprodutíveis, com normalização correta e modelos treinados.")],
    [pv("Split temporal correto"),
     pc("80/20 por classe ordenado por timestamp — não usa train_test_split aleatório. Isso é um diferencial metodológico importante para defender na banca.")],
    [pv("EarlyStopping + ModelCheckpoint"),
     pc("Treinamento robusto com parada antecipada e salvamento do melhor modelo por val_loss.")],
    [pv("Baseline Random Forest"),
     pc("Comparação LSTM vs RF implementada e documentada nos dois ramos — mostra maturidade metodológica.")],
    [pv("Features derivadas inteligentes (ramo físico)"),
     pc("r_xy, innov_norm e dv_xy são contribuições analíticas próprias que capturam a física do voo sob ataque, especialmente o GPS Spoofing.")],
    [pv("Documentação honesta das limitações"),
     pc("O trabalho declara claramente: 1 voo por classe, ausência de fusão temporal calibrada, protótipo offline. Isso é o que avaliadores esperam e valorizam.")],
    [pv("Normalização sem vazamento"),
     pc("MinMaxScaler e StandardScaler ajustados só no treino e aplicados ao teste — prática correta e explicitamente documentada.")],
    [pv("Discussão da complementaridade dos ramos"),
     pc("O Capítulo 5 articula bem por que rede e física se complementam: ramo ciber fraco em Replay, ramo físico fraco em Ping DoS — argumento central do IDS híbrido.")],
    [pv("Figuras salvas como PNG de alta resolução"),
     pc("confusion_matrix_cyber.png, learning_curves_ramo_ciber.png, confusion_matrix_px4.png, learning_curves_ramo_fisico.png — prontas para inserir no documento Word/LaTeX.")],
]
story.append(tab(["Ponto Forte", "Por quê é sólido"], bom_rows, [0.30, 0.70]))

# ============================================================
# SEÇÃO 3 — O QUE PRECISA MELHORAR
# ============================================================
story.append(PageBreak())
story.append(hr(AZUL, 1.5))
story.append(Paragraph("3. O Que Precisa Melhorar", secao_s))
story.append(Paragraph(
    "Problemas identificados que impactam a qualidade do trabalho e podem ser apontados na banca. "
    "Ordenados por prioridade.", corpo_s))

story.append(Paragraph("3.1 Problemas de Desempenho dos Modelos", subsecao_s))
melhorar_modelos = [
    [pvr("Recall baixo de Replay (LSTM: 0,284 | RF: 0,495)"),
     pc("Alta prioridade"),
     pc("Janela de 10 timesteps é curta demais para capturar o padrão definitório do Replay (repetição de sequências). Testar janela=20 e janela=30 (código já existe, RUN_WINDOW_ABLATION=False).")],
    [pvr("F1 baixo de Ping DoS no ramo físico (LSTM: 0,245 | RF: 0,600)"),
     pc("Alta prioridade"),
     pc("Normal e Ping DoS se sobrepõem nas features de posição/velocidade nos logs SITL simulados. Adicionar features de status (vehicle_status, commander_state) pode ajudar. Também declarar claramente como limitação do dataset.")],
    [pvr("LSTM inferior ao RF no ramo físico (F1-macro 0,549 vs 0,674)"),
     pc("Média prioridade"),
     pc("Causa: apenas 1 voo por classe → overfitting severo (acurácia treino 0,774 vs validação 0,215). Documentar isso na discussão, que já está escrito. Tentar LSTM com mais Dropout ou regularização L2.")],
    [pvr("Validação aleatória no ramo físico"),
     pc("Média prioridade"),
     pc("O notebook Infos_lstm_fusao_px4.ipynb usa validation_split=0,1 aleatório dentro do treino. O DOCUMENTO.md já aponta: a métrica correta é o teste temporal, não o val_accuracy oscilante durante o fit. Alterar para validação temporal contígua.")],
]
story.append(tab(
    ["Problema", "Prioridade", "Ação recomendada"],
    melhorar_modelos, [0.30, 0.14, 0.56],
))
story.append(Spacer(1, 8))

story.append(Paragraph("3.2 Problemas no Texto da Monografia", subsecao_s))
melhorar_texto = [
    [pvr("Figura 1 faltando (diagrama da arquitetura)"),
     pc("Alta prioridade"),
     pc("O rascunho tem [INSERIR FIGURA 1 — Diagrama da arquitetura do IDS híbrido]. Essa figura é essencial para o Cap. 3 e qualquer avaliador vai pedir. Pode ser feita no draw.io, PowerPoint ou matplotlib.")],
    [pvr("Figuras 4 e 5 do ramo físico faltando no rascunho"),
     pc("Alta prioridade"),
     pc("As figuras curvas de aprendizado e matriz de confusão do ramo físico já foram geradas (PNGs existem) mas os [INSERIR ...] no Cap. 4 não foram substituídos.")],
    [pvr("Trechos [inserir ...] nas referências"),
     pc("Alta prioridade"),
     pc("Referência do IEEE DataPort com 'Acesso em: [inserir data]' e citação secundária do LSTM 'inserir fonte secundária'. Preencher antes da entrega.")],
    [pvr("Tabela 1 inconsistente"),
     pc("Média prioridade"),
     pc("A distribuição de rótulos no Cap. 3 mostra Total = 33.104, mas o df tem 54.783 linhas no total. Acrescentar nota explicando que 33.104 é o subconjunto com todas as colunas válidas para o modelo.")],
    [pvr("Ausência de curvas ROC/PR"),
     pc("Baixa prioridade"),
     pc("Mencionadas como opcionais no resumo.md. Para um TCC de graduação, F1-macro e matriz de confusão já são suficientes. Adicionar se o orientador pedir.")],
]
story.append(tab(
    ["Problema", "Prioridade", "Ação recomendada"],
    melhorar_texto, [0.30, 0.14, 0.56],
))
story.append(Spacer(1, 8))

story.append(Paragraph("3.3 Problemas Metodológicos Menores", subsecao_s))
melhorar_metodo = [
    [pa("Ablação de janela não executada"),
     pc("Média prioridade"),
     pc("RUN_WINDOW_ABLATION = False. O código está pronto no notebook. Executar comparação entre window=10, 20, 30 e reportar F1-macro por janela em uma tabela simples — fortalece o argumento sobre Replay.")],
    [pa("Estabilidade estatística (seed única)"),
     pc("Baixa prioridade"),
     pc("Toda avaliação usa random_state=42 (uma única execução). Repetir com 3–5 seeds e reportar média ± desvio padrão é recomendado, mas pode ficar como trabalho futuro em TCC de graduação.")],
    [pa("Matriz de confusão normalizada por linha"),
     pc("Baixa prioridade"),
     pc("A matriz atual mostra contagens absolutas. Normalizar por linha (taxa de erro por classe verdadeira) facilita a interpretação visual e é mais informativa. Uma linha de código no notebook.")],
    [pa("Citação da topologia de rede do Dataset T-ITS"),
     pc("Baixa prioridade"),
     pc("O DOCUMENTO.md aponta: equipamentos exatos, como foram gerados os rótulos e posição do atacante devem vir do paper/DataPort. Confirmar e citar no Cap. 3.")],
]
story.append(tab(
    ["Problema", "Prioridade", "Ação recomendada"],
    melhorar_metodo, [0.30, 0.14, 0.56],
))

# ============================================================
# SEÇÃO 4 — O QUE ESTÁ FALTANDO
# ============================================================
story.append(PageBreak())
story.append(hr(AZUL, 1.5))
story.append(Paragraph("4. O Que Está Faltando (Lacunas em Aberto)", secao_s))
story.append(Paragraph(
    "Itens previstos nos objetivos ou mencionados no README que ainda não foram implementados. "
    "Alguns são obrigatórios para fechar o escopo; outros podem ser declarados como trabalho futuro.",
    corpo_s))

faltando_rows = [
    [pvr("MAVLink Sequence Dataset"),
     pvr("Obrigatório citar"),
     pc("Previsto no README como segunda fonte de dados principal. Não há notebook nem análise. Opções: (a) analisar e usar; (b) declarar explicitamente no texto que foi previsto mas ficou fora do escopo por limitação de tempo — com justificativa.")],
    [pvr("Figura 1 — Diagrama da arquitetura do IDS"),
     pvr("Obrigatório"),
     pc("Sem essa figura, o Cap. 3 fica incompleto. É um diagrama simples mostrando os dois ramos (ciber: T-ITS → LSTM/RF; físico: PX4 → fusão → LSTM/RF) e a camada de decisão futura. Pode ser feito em draw.io.")],
    [pvr("Inserção das figuras PNGs no rascunho ABNT"),
     pvr("Obrigatório"),
     pc("Os quatro PNGs gerados pelos notebooks (curvas e matrizes dos dois ramos) precisam ser inseridos no documento Word/LaTeX nos marcadores [INSERIR ...] do Cap. 4.")],
    [pvr("Datas de acesso nas referências"),
     pvr("Obrigatório ABNT"),
     pc("Referência do IEEE DataPort exige 'Acesso em: DD mês. AAAA'. Preencher com a data real em que o dataset foi acessado.")],
    [pa("Ablação de janela temporal (window=10/20/30)"),
     pa("Recomendado"),
     pc("Código pronto no notebook (RUN_WINDOW_ABLATION = True). Executar e reportar em nova tabela no Cap. 4. Fortalece muito a argumentação sobre o Replay.")],
    [pa("Análise do MAVLink Sequence Dataset"),
     pa("Recomendado"),
     pc("Mesmo que não seja incluída no modelo final, uma análise exploratória curta justifica por que esse dataset não foi usado (ou como seria usado em trabalho futuro).")],
    [pa("Fusão decisória dos dois ramos"),
     pa("Trabalho futuro"),
     pc("Corretamente descrito como trabalho futuro no rascunho. Não é obrigatório implementar — apenas declarar claramente as condições necessárias (datasets com coleta simultânea).")],
    [pa("IDS em tempo quase real"),
     pa("Trabalho futuro"),
     pc("Medição de latência de inferência e pipeline de ingestão contínua. Corretamente descrito como trabalho futuro — não é necessário implementar para o TCC.")],
]
story.append(tab(
    ["O que falta", "Classificação", "O que fazer"],
    faltando_rows, [0.28, 0.16, 0.56],
))

# ============================================================
# SEÇÃO 5 — PLANO DE AÇÃO PRIORIZADO
# ============================================================
story.append(PageBreak())
story.append(hr(AZUL, 1.5))
story.append(Paragraph("5. Plano de Ação Priorizado", secao_s))
story.append(Paragraph(
    "Lista de tarefas ordenadas por urgência. As tarefas obrigatórias precisam ser concluídas "
    "antes da entrega. As recomendadas fortalecem o trabalho. As opcionais ficam para trabalhos futuros.",
    corpo_s))

story.append(Paragraph("Tarefas Obrigatórias (antes da entrega)", subsecao_s))
obrig = [
    ["1", pc("Criar Figura 1 — Diagrama da arquitetura do IDS híbrido"), pc("draw.io / PowerPoint / matplotlib — 2 caixas (ramo ciber + ramo físico) + setas + camada de decisão futura.")],
    ["2", pc("Inserir as 4 figuras PNG no rascunho ABNT"), pc("Substituir os 4 marcadores [INSERIR ...] no Cap. 4 pelos PNGs gerados pelos notebooks.")],
    ["3", pc("Preencher datas de acesso nas referências"), pc("Completar 'Acesso em: [inserir data]' na referência do IEEE DataPort no Cap. 7.")],
    ["4", pc("Resolver inconsistência da Tabela 1"), pc("Adicionar nota explicando que 33.104 é o subconjunto válido para o modelo, dentro dos 54.783 totais do CSV.")],
    ["5", pc("Posicionar o MAVLink Sequence Dataset no texto"), pc("Adicionar parágrafo no Cap. 3 ou 6 explicando por que não foi utilizado (escopo) e como seria usado em trabalho futuro.")],
    ["6", pc("Corrigir validação aleatória no ramo físico"), pc("No notebook Infos_lstm_fusao_px4.ipynb: trocar validation_split=0,1 por validação contígua nos últimos 10% do treino concatenado.")],
]
story.append(tab(
    ["#", "Tarefa", "Como fazer"],
    [[pc(r[0])] + r[1:] for r in obrig], [0.05, 0.35, 0.60],
))
story.append(Spacer(1, 8))

story.append(Paragraph("Tarefas Recomendadas (fortalecem o trabalho)", subsecao_s))
recom = [
    ["7",  pc("Executar ablação de janela temporal"), pc("No notebook ramo ciber, alterar RUN_WINDOW_ABLATION = True. Comparar F1-macro para window=10, 20, 30. Adicionar tabela no Cap. 4.")],
    ["8",  pc("Adicionar matriz de confusão normalizada"), pc("Em ambos os notebooks: adicionar confusion_matrix(normalize='true') para mostrar taxas de erro por classe, não contagens brutas.")],
    ["9",  pc("Adicionar features extras no ramo físico"), pc("Tentar vehicle_status_0.csv ou commander_state_0.csv para ajudar a separar Ping DoS de Normal.")],
    ["10", pc("Verificar citação da topologia do Dataset T-ITS"), pc("Confirmar no paper de Hassler et al. (2024) o drone utilizado, firmware e como os rótulos foram gerados.")],
]
story.append(tab(
    ["#", "Tarefa", "Como fazer"],
    [[pc(r[0])] + r[1:] for r in recom], [0.05, 0.35, 0.60],
))
story.append(Spacer(1, 8))

story.append(Paragraph("Tarefas Opcionais (trabalhos futuros — não obrigatórias)", subsecao_s))
opcio = [
    ["11", pc("Repetir treino LSTM com múltiplas seeds"), pc("3–5 seeds, reportar F1-macro médio ± desvio padrão.")],
    ["12", pc("Curvas ROC/PR multiclasse"), pc("one-vs-rest com sklearn.metrics.roc_auc_score — útil se o orientador pedir.")],
    ["13", pc("Análise exploratória do MAVLink Sequence Dataset"), pc("Mesmo que não entre no modelo, mostrar consciência sobre a fonte.")],
    ["14", pc("Fusão decisória dos dois ramos"), pc("Combinação das probabilidades de saída dos dois detectores — condicionada a datasets com coleta simultânea.")],
]
story.append(tab(
    ["#", "Tarefa", "Como fazer"],
    [[pc(r[0])] + r[1:] for r in opcio], [0.05, 0.35, 0.60],
))

# ============================================================
# SEÇÃO 6 — ANÁLISE DOS RESULTADOS
# ============================================================
story.append(PageBreak())
story.append(hr(AZUL, 1.5))
story.append(Paragraph("6. Análise Crítica dos Resultados Atuais", secao_s))

story.append(Paragraph("6.1 Ramo Ciber — Resultados Consolidados", subsecao_s))
result_ciber = [
    [ph("Classe"), ph("LSTM Precision"), ph("LSTM Recall"), ph("LSTM F1"), ph("RF Precision"), ph("RF Recall"), ph("RF F1")],
    [pc("Benign"),     pc("0,764"), pv("0,978"), pv("0,858"), pc("0,759"), pv("0,979"), pv("0,855")],
    [pc("DoS attack"), pc("0,590"), pv("0,829"), pv("0,690"), pc("0,608"), pa("0,574"), pa("0,591")],
    [pc("Replay"),     pc("0,733"), pvr("0,284"), pvr("0,409"), pc("0,599"), pa("0,495"), pa("0,542")],
    [pc("Macro avg"),  pc("0,696"), pc("0,697"), pa("0,652"),  pc("0,655"), pc("0,683"), pv("0,663")],
]
cw6 = [(W-5*cm)*f for f in [0.16,0.14,0.14,0.14,0.14,0.14,0.14]]
t6 = Table(result_ciber, colWidths=cw6, repeatRows=1)
t6.setStyle(TableStyle([
    ("BACKGROUND", (0,0),(-1,0), AZUL),
    ("GRID", (0,0),(-1,-1), 0.4, CINZA_BORDA),
    ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ("LEFTPADDING",(0,0),(-1,-1),4),
    ("RIGHTPADDING",(0,0),(-1,-1),4),
    ("TOPPADDING",(0,0),(-1,-1),4),
    ("BOTTOMPADDING",(0,0),(-1,-1),4),
    ("ROWBACKGROUNDS",(0,1),(-1,-1),[CINZA_BG, colors.white]),
]))
story.append(t6)
story.append(Paragraph(
    "Interpretação: Benign bem detectado pelos dois modelos. DoS com recall alto na LSTM (0,829) mas precário no RF (0,574). "
    "Replay é o grande problema: recall 0,284 na LSTM. Causa estrutural — janela de 10 timesteps é curta demais "
    "para identificar repetição de sequências. RF ligeiramente melhor em F1-macro.",
    corpo_s))
story.append(Spacer(1, 8))

story.append(Paragraph("6.2 Ramo Físico — Resultados Consolidados", subsecao_s))
result_fisico = [
    [ph("Classe"), ph("LSTM Precision"), ph("LSTM Recall"), ph("LSTM F1"), ph("RF Precision"), ph("RF Recall"), ph("RF F1")],
    [pc("Normal"),       pv("0,862"), pv("0,822"), pv("0,841"), pc("0,851"), pc("0,800"), pc("0,825")],
    [pc("GPS Spoofing"),  pa("0,451"), pv("0,744"), pa("0,561"), pc("0,529"), pc("0,684"), pv("0,597")],
    [pc("Ping DoS"),      pa("0,461"), pvr("0,166"), pvr("0,245"), pv("0,699"), pc("0,526"), pv("0,600")],
    [pc("Macro avg"),     pc("0,591"), pc("0,578"), pvr("0,549"), pv("0,693"), pv("0,670"), pv("0,674")],
]
t7 = Table(result_fisico, colWidths=cw6, repeatRows=1)
t7.setStyle(TableStyle([
    ("BACKGROUND", (0,0),(-1,0), AZUL),
    ("GRID", (0,0),(-1,-1), 0.4, CINZA_BORDA),
    ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ("LEFTPADDING",(0,0),(-1,-1),4),
    ("RIGHTPADDING",(0,0),(-1,-1),4),
    ("TOPPADDING",(0,0),(-1,-1),4),
    ("BOTTOMPADDING",(0,0),(-1,-1),4),
    ("ROWBACKGROUNDS",(0,1),(-1,-1),[CINZA_BG, colors.white]),
]))
story.append(t7)
story.append(Paragraph(
    "Interpretação: RF supera LSTM significativamente neste ramo (F1-macro 0,674 vs 0,549). "
    "Causa principal: overfitting severo da LSTM com apenas 1 voo por classe. "
    "GPS Spoofing moderadamente detectado pelos dois (r_xy é o principal discriminador). "
    "Ping DoS é a classe mais fraca — Normal e Ping DoS se sobrepõem nas features de posição/velocidade nos logs SITL.",
    corpo_s))
story.append(Spacer(1, 8))

story.append(Paragraph("6.3 Argumento Central que Sustenta o IDS Híbrido", subsecao_s))
story.append(Paragraph(
    "Os resultados dos dois ramos, lidos em conjunto, demonstram a complementaridade que justifica "
    "a arquitetura híbrida:", corpo_s))
for ponto in [
    "No ramo ciber, <b>DoS</b> é bem detectado (LSTM recall 0,829) mas <b>Replay é difícil</b> (LSTM recall 0,284). "
    "Replay imita estatisticamente o tráfego legítimo — só seria distinguível com janelas maiores ou análise de conteúdo MAVLink.",
    "No ramo físico, <b>GPS Spoofing</b> é o mais detectável (LSTM recall 0,744, RF recall 0,684) graças à feature r_xy "
    "(deriva horizontal de 10⁴ m no Spoofing vs 10² m no Normal). <b>Ping DoS</b> é ambíguo nos logs de telemetria simulada.",
    "A complementaridade é real: um ataque invisível no tráfego de rede pode deixar rastro na telemetria física, e vice-versa. "
    "Isso é o argumento central do TCC e está bem escrito no Cap. 5 do rascunho.",
]:
    story.append(Paragraph(f"• {ponto}", ok_s))
story.append(Spacer(1, 10))

# RODAPÉ
story.append(hr(AZUL, 1.5))
story.append(Paragraph(
    "TCC — Sistema de Detecção de Intrusão Ciber-Físico para UAVs | "
    "Caio de Souza Lima | UFF | 2026 — Documento gerado em 18 de maio de 2026",
    rodape_s))

doc.build(story)
print(f"PDF gerado: {OUTPUT}")

"""
Gera Relatorio_LinkedIn.pdf — versão carrossel para LinkedIn.
Formato quadrado 25×25 cm, 8 slides visuais e texto enxuto.
"""

from pathlib import Path
from datetime import datetime
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Image, Table,
    TableStyle, PageBreak,
)

AUTOR = "Valter Micas"
MESES_PT = {1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
            5: "maio", 6: "junho", 7: "julho", 8: "agosto",
            9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro"}


def data_pt():
    d = datetime.today()
    return f"{d.day} de {MESES_PT[d.month]} de {d.year}"


BASE = Path("/Users/valtermicas/Documents/projetos/materiais_perigosos")
OUT = BASE / "analise"
FIG = OUT / "figuras"
PDF = OUT / "Relatorio_LinkedIn.pdf"

# Página quadrada 25×25 cm
PAGE = (25 * cm, 25 * cm)
PAGE_W, PAGE_H = PAGE
MARGIN = 1.6 * cm

# Cores
RED = colors.HexColor("#922b21")
RED_DARK = colors.HexColor("#641e16")
BLUE = colors.HexColor("#1f3a5f")
GRAY = colors.HexColor("#566573")
LIGHT = colors.HexColor("#fdf2e9")
WHITE = colors.white

# Estilos
ss = getSampleStyleSheet()
S = {
    "kicker": ParagraphStyle("kicker", fontName="Helvetica-Bold", fontSize=12,
                             leading=16, textColor=RED, spaceAfter=4),
    "title_xl": ParagraphStyle("title_xl", fontName="Helvetica-Bold", fontSize=34,
                                leading=40, textColor=RED_DARK, spaceAfter=10),
    "title_lg": ParagraphStyle("title_lg", fontName="Helvetica-Bold", fontSize=26,
                                leading=32, textColor=RED_DARK, spaceAfter=8),
    "title_md": ParagraphStyle("title_md", fontName="Helvetica-Bold", fontSize=20,
                                leading=26, textColor=RED_DARK, spaceAfter=6),
    "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=14,
                                leading=20, textColor=BLUE, spaceAfter=6),
    "lead": ParagraphStyle("lead", fontName="Helvetica", fontSize=13,
                            leading=20, textColor=colors.HexColor("#212f3d"),
                            spaceAfter=6),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=11.5,
                            leading=17, textColor=colors.HexColor("#212f3d"),
                            spaceAfter=4),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=9.5,
                             leading=13, textColor=GRAY),
    "meta": ParagraphStyle("meta", fontName="Helvetica-Oblique", fontSize=10,
                            leading=14, textColor=GRAY),
    "stat_num": ParagraphStyle("stat_num", fontName="Helvetica-Bold", fontSize=42,
                                leading=46, textColor=RED, alignment=TA_CENTER),
    "stat_label": ParagraphStyle("stat_label", fontName="Helvetica", fontSize=12,
                                  leading=16, textColor=GRAY, alignment=TA_CENTER),
    "quote": ParagraphStyle("quote", fontName="Helvetica-Bold", fontSize=18,
                             leading=24, textColor=RED_DARK, alignment=TA_CENTER,
                             spaceBefore=10, spaceAfter=10),
}


def slide_chrome(canvas, doc):
    """Cabeçalho fino + rodapé com assinatura + nº de slide."""
    canvas.saveState()
    # Faixa superior
    canvas.setFillColor(RED)
    canvas.rect(0, PAGE_H - 0.45 * cm, PAGE_W, 0.45 * cm, fill=1, stroke=0)
    # Rodapé
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(GRAY)
    canvas.drawString(MARGIN, 0.8 * cm,
                      f"Valter Micas  ·  Desafio LX Data Lab 0125  ·  Lisboa")
    canvas.drawRightString(PAGE_W - MARGIN, 0.8 * cm, f"{doc.page} / 8")
    canvas.setStrokeColor(colors.HexColor("#e5e7e9"))
    canvas.setLineWidth(0.6)
    canvas.line(MARGIN, 1.25 * cm, PAGE_W - MARGIN, 1.25 * cm)
    canvas.restoreState()


def cover_chrome(canvas, doc):
    """Fundo de capa cheio."""
    canvas.saveState()
    canvas.setFillColor(LIGHT)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # Bloco vermelho lateral
    canvas.setFillColor(RED)
    canvas.rect(0, 0, 1.5 * cm, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(RED_DARK)
    canvas.rect(0, 0, PAGE_W, 0.6 * cm, fill=1, stroke=0)
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def img(name, width_cm):
    p = FIG / name
    im = Image(str(p))
    iw, ih = im.imageWidth, im.imageHeight
    w = width_cm * cm
    h = w * ih / iw
    im.drawWidth = w
    im.drawHeight = h
    im._restrictSize(w, h)
    return im


def stat_card(num, label, num_color=RED):
    """Cartão estatístico: nº grande + descrição."""
    s_num = ParagraphStyle("n", parent=S["stat_num"], textColor=num_color)
    t = Table([[Paragraph(num, s_num)], [Paragraph(label, S["stat_label"])]],
              colWidths=[6.5 * cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#d5dbdb")),
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    return t


# ---------------------------------------------------------------------------
# Documento
# ---------------------------------------------------------------------------
doc = BaseDocTemplate(
    str(PDF), pagesize=PAGE,
    leftMargin=MARGIN, rightMargin=MARGIN,
    topMargin=1.6 * cm, bottomMargin=1.6 * cm,
    title="Risco no transporte ferroviário de matérias perigosas — Lisboa",
    author=AUTOR,
    subject="Desafio LX Data Lab 0125 — versão resumida para LinkedIn",
)
cover_frame = Frame(0, 0, PAGE_W, PAGE_H,
                    leftPadding=2.2 * cm, rightPadding=1.6 * cm,
                    topPadding=2.0 * cm, bottomPadding=1.6 * cm)
slide_frame = Frame(MARGIN, MARGIN + 0.3 * cm,
                    PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN - 0.3 * cm,
                    leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
doc.addPageTemplates([
    PageTemplate(id="cover", frames=[cover_frame], onPage=cover_chrome),
    PageTemplate(id="slide", frames=[slide_frame], onPage=slide_chrome),
])
from reportlab.platypus import NextPageTemplate

story = []

# =====================================================================
# SLIDE 1 — Capa
# =====================================================================
story.append(Spacer(1, 1.5 * cm))
story.append(Paragraph("DESAFIO LX DATA LAB · 0125", S["kicker"]))
story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph(
    "E se descarrilasse hoje um comboio com matérias perigosas em Lisboa?",
    S["title_xl"]))
story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph(
    "Análise estatística e mapeamento de risco do transporte ferroviário "
    "de matérias perigosas no corredor <b>Parque das Nações ↔ Alcântara</b>.",
    S["lead"]))
story.append(Spacer(1, 1.6 * cm))
# Box autor
autor_table = Table([
    [Paragraph("<b>Autor</b>", S["meta"])],
    [Paragraph(f"<font size='24' color='#922b21'><b>{AUTOR}</b></font>", S["lead"])],
    [Paragraph("Análise para o Serviço Municipal de Proteção Civil de Lisboa (SMPC)",
               S["small"])],
    [Paragraph(data_pt(), S["small"])],
], colWidths=[15 * cm])
autor_table.setStyle(TableStyle([
    ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    # Espaçamento generoso entre linhas
    ("TOPPADDING", (0, 0), (0, 0), 8),
    ("BOTTOMPADDING", (0, 0), (0, 0), 6),
    ("TOPPADDING", (0, 1), (0, 1), 4),
    ("BOTTOMPADDING", (0, 1), (0, 1), 14),
    ("TOPPADDING", (0, 2), (0, 2), 4),
    ("BOTTOMPADDING", (0, 2), (0, 2), 12),
    ("TOPPADDING", (0, 3), (0, 3), 4),
    ("BOTTOMPADDING", (0, 3), (0, 3), 4),
    ("LINEABOVE", (0, 0), (0, 0), 1.2, RED),
]))
story.append(autor_table)
story.append(Spacer(1, 2 * cm))
story.append(Paragraph(
    "<i>Versão resumida · 8 slides · Relatório técnico completo (23 págs) disponível mediante pedido.</i>",
    S["small"]))
story.append(NextPageTemplate("slide"))
story.append(PageBreak())

# =====================================================================
# SLIDE 2 — Contexto
# =====================================================================
story.append(Paragraph("01  ·  CONTEXTO", S["kicker"]))
story.append(Paragraph("O corredor ferroviário de Lisboa", S["title_lg"]))
story.append(Paragraph(
    "Da Linha do Norte (vinda de Leixões) à Linha de Cintura, os comboios com matérias "
    "perigosas atravessam todo o tecido urbano de Lisboa, com paragem em Alcântara.",
    S["body"]))
story.append(Spacer(1, 0.3 * cm))

# Três cartões estatísticos em linha
stats_row = Table([[
    stat_card("100", "viagens analisadas<br/>(1998–2002)"),
    stat_card("2 555", "registos detalhados<br/>de matérias"),
    stat_card("98 %", "passam por<br/>Alcântara"),
]], colWidths=[7 * cm, 7 * cm, 7 * cm])
stats_row.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
]))
story.append(stats_row)
story.append(Spacer(1, 0.3 * cm))
story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph(
    "<b>43,8 %</b> das matérias são <b>líquidos inflamáveis</b> (classe 3) — tintas, "
    "adesivos, resinas. Restantes: gases (16 %), corrosivos (13 %), tóxicos (12 %).",
    S["body"]))
story.append(Spacer(1, 0.2 * cm))
story.append(img("h3_origem_destino.png", width_cm=14))
story.append(Paragraph(
    "Matriz de fluxos — a esmagadora maioria das viagens é Leixões → Alcântara.",
    S["small"]))
story.append(PageBreak())

# =====================================================================
# SLIDE 3 — Achado #1: Governance dos dados
# =====================================================================
story.append(Paragraph("02  ·  ACHADO #1", S["kicker"]))
story.append(Paragraph("Os dados precisavam de governance", S["title_lg"]))
story.append(Spacer(1, 0.2 * cm))

# Bloco com número grande à esquerda + texto à direita
big_style = ParagraphStyle("big", fontName="Helvetica-Bold", fontSize=64,
                           leading=66, textColor=RED, alignment=TA_CENTER)
big = Table([[
    Paragraph("81 %", big_style),
    Paragraph(
        "das 2 555 linhas tinham o <b>Nº Perigo (código Kemler)</b> indevidamente "
        "colocado na coluna CLASSE. Sem detetar e corrigir, qualquer análise produziria "
        "números errados.",
        S["lead"]),
]], colWidths=[6 * cm, 15.5 * cm])
big.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("BOX", (0, 0), (0, 0), 0.6, colors.HexColor("#d5dbdb")),
    ("BACKGROUND", (0, 0), (0, 0), WHITE),
]))
story.append(big)
story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph(
    "Limpeza e normalização <b>auditáveis</b>:",
    S["body"]))
story.append(Paragraph(
    "•  validação contra o conjunto válido ADR/RID (16 classes possíveis)<br/>"
    "•  parser de <b>pior caso</b> para o Nº Perigo — alternativas, dígitos duplicados, prefixo X<br/>"
    "•  nomes canónicos: <b>240+ variantes → 186 produtos</b> únicos<br/>"
    "•  cada correção rastreável (CLASSE_LIMPEZA, ONU_LIMPEZA)",
    S["body"]))
story.append(Spacer(1, 0.3 * cm))

# Tabela exemplo do parser
exemplo = Table([
    ["Nº Perigo original", "Pior caso", "Significado"],
    ["30 ou 33", "33", "Inflamabilidade INTENSIFICADA"],
    ["60 ou 66", "66", "Toxicidade INTENSIFICADA"],
    ["X462", "X462", "Reage perigosamente com água"],
], colWidths=[6 * cm, 4 * cm, 11 * cm])
exemplo.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), RED),
    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 11),
    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bdc3c7")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
]))
story.append(exemplo)
story.append(PageBreak())

# =====================================================================
# SLIDE 4 — Achado #2: Janela temporal
# =====================================================================
story.append(Spacer(1, 0.2 * cm))
story.append(Paragraph("03  ·  ACHADO #2", S["kicker"]))
story.append(Paragraph("A janela de risco é estreita e previsível", S["title_lg"]))
story.append(Spacer(1, 0.2 * cm))
stats_row2 = Table([[
    stat_card("98 %", "das viagens em<br/>dias úteis"),
    stat_card("19h–23h", "concentração total<br/>das partidas"),
    stat_card("0", "viagens<br/>ao domingo"),
]], colWidths=[7 * cm, 7 * cm, 7 * cm])
stats_row2.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
]))
story.append(stats_row2)
story.append(Spacer(1, 0.4 * cm))
story.append(img("h1_dia_hora.png", width_cm=21.5))
story.append(Paragraph(
    "Mapa de calor Dia × Hora — 100 % do risco temporal em 4 horas / 4 dias úteis.",
    S["small"]))
story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph(
    "<b>Implicação:</b> permite organizar escalas dedicadas de prontidão noturna no "
    "corredor e libertar o fim-de-semana para inspeções, exercícios e manutenção.",
    S["body"]))
story.append(PageBreak())

# =====================================================================
# SLIDE 5 — Achado #3: Dois Top 10 distintos
# =====================================================================
story.append(Spacer(1, 0.2 * cm))
story.append(Paragraph("04  ·  ACHADO #3", S["kicker"]))
story.append(Paragraph("Dois Top 10 muito diferentes", S["title_lg"]))
story.append(Paragraph(
    "Ordenar por frequência ou por pior caso produz <b>listas completamente distintas</b>. "
    "Exige dois eixos de planeamento.",
    S["body"]))
story.append(Spacer(1, 0.3 * cm))

# Top 10 frequência (resumido)
freq_data = [
    ["#", "Por FREQUÊNCIA", "Classe", "Kemler"],
    ["1", "Tintas / aparentadas", "3", "33"],
    ["2", "Adesivos com líq. inflamável", "3", "33"],
    ["3", "Aerossóis", "2", "26"],
    ["4", "Resina em solução", "3", "33"],
    ["5", "Diisocianato de tolueno", "6.1", "60"],
]
risk_data = [
    ["#", "Por RISCO (pior caso)", "Classe", "Kemler"],
    ["1", "Fosforeto de alumínio", "4.3", "X462"],
    ["2", "Metilacetileno+propadieno", "2", "239"],
    ["3", "Acetato de vinilo estab.", "3", "339"],
    ["4", "Etildiclorossilano", "4.3", "X338"],
    ["5", "Alquifenois líquidos", "8", "88"],
]


def top_table(data, header_color):
    t = Table(data, colWidths=[0.8 * cm, 6.4 * cm, 1.4 * cm, 1.8 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d5dbdb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("FONTNAME", (3, 1), (3, -1), "Helvetica-Bold"),
    ]))
    return t


grid = Table([[top_table(freq_data, RED), top_table(risk_data, RED_DARK)]],
             colWidths=[10.5 * cm, 10.5 * cm])
grid.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
]))
story.append(grid)
story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph(
    "À esquerda dominam as <b>tintas e adesivos</b> (classe 3) — onde concentrar "
    "treino sistemático.<br/>"
    "À direita dominam matérias raras mas <b>de pior caso extremo</b> "
    "(prefixo X, raio de 1 600 m) — onde criar fichas nominais de intervenção.",
    S["body"]))
story.append(PageBreak())

# =====================================================================
# SLIDE 6 — Mapa de impacto
# =====================================================================
story.append(Spacer(1, 0.2 * cm))
story.append(Paragraph("05  ·  IMPACTO", S["kicker"]))
story.append(Paragraph("Que distâncias evacuar?", S["title_lg"]))
story.append(Paragraph(
    "Simulação 2D do impacto radial em redor do ponto de acidente. "
    "Três anéis correspondem aos cenários de evacuação imediata, alargada e incêndio.",
    S["body"]))
story.append(img("h6_impacto_pior_caso.png", width_cm=13))

# Tabela de buffer
buffer = Table([
    ["Cenário", "Buffer", "Aplicação"],
    ["Evacuação imediata", "100 m", "Cordão de segurança automático"],
    ["Acidente grave", "500 m", "Confirmação de derrame ou ignição próxima"],
    ["Incêndio (Top 10)", "800 m", "Inclui hospitais, escolas, lares, edifícios altos"],
    ["Extremo (gases liquefeitos)", "1 600 m", "ONU 1969 / 1060 — BLEVE"],
], colWidths=[6 * cm, 2.8 * cm, 12.2 * cm])
buffer.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), RED),
    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 10.5),
    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bdc3c7")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
    ("ALIGN", (1, 1), (1, -1), "CENTER"),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("TEXTCOLOR", (1, 1), (1, -1), RED_DARK),
]))
story.append(buffer)
story.append(PageBreak())

# =====================================================================
# SLIDE 7 — Estações críticas
# =====================================================================
story.append(Spacer(1, 0.2 * cm))
story.append(Paragraph("06  ·  CORREDOR", S["kicker"]))
story.append(Paragraph("Estações mais expostas", S["title_lg"]))
story.append(Paragraph(
    "Ranking de risco potencial cruzando o Top 10 das matérias com a densidade urbana "
    "em redor de cada estação do corredor <b>Parque das Nações ↔ Alcântara</b>.",
    S["body"]))
story.append(Spacer(1, 0.2 * cm))
story.append(img("h9_ranking_estacoes.png", width_cm=21.5))
story.append(Spacer(1, 0.3 * cm))

# Estações no pódio (sem emojis - usar números ordinais grandes)
def podio_cell(rank, nome, desc):
    return Paragraph(
        f"<font size='30' color='#922b21'><b>{rank}.</b></font> "
        f"<font size='18' color='#641e16'><b>{nome}</b></font><br/>"
        f"<font size='10.5' color='#566573'>{desc}</font>",
        S["body"])


podio = Table([[
    podio_cell("1", "Entrecampos", "transporte multimodal,<br/>alta densidade"),
    podio_cell("2", "Roma–Areeiro", "forte residencial<br/>+ comercial"),
    podio_cell("3", "Sete Rios", "hospital + jardim<br/>zoológico + interface"),
]], colWidths=[7 * cm, 7 * cm, 7 * cm])
podio.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
]))
story.append(podio)
story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph(
    "<b>Estas três estações</b> devem ter postos de comando avançado pré-definidos "
    "e rotas de evacuação modeladas com prioridade.",
    S["body"]))
story.append(PageBreak())

# =====================================================================
# SLIDE 8 — Conclusões + CTA
# =====================================================================
story.append(Spacer(1, 0.2 * cm))
story.append(Paragraph("07  ·  CONCLUSÕES", S["kicker"]))
story.append(Paragraph("O que fazer agora?", S["title_lg"]))
story.append(Spacer(1, 0.2 * cm))

recos = [
    ("Governance dos dados",
     "Validação por lista pendente contra ADR/RID na origem dos registos."),
    ("Planeamento dual",
     "Treino para os 10 mais frequentes + fichas nominais para os 10 de pior caso."),
    ("Buffer de 800 m como padrão",
     "Cruzar com GeoJSON da rede; extender a 1 600 m em comboios com gases liquefeitos."),
    ("Calibração com BUE Lisboa",
     "Cadastro de edifícios sensíveis + modelos ALOHA/CAMEO."),
]
for i, (t, b) in enumerate(recos, 1):
    row = Table([[
        Paragraph(f"<font color='#922b21' size='20'><b>{i}</b></font>", S["body"]),
        Paragraph(f"<b>{t}</b><br/><font size='10.5' color='#566573'>{b}</font>", S["body"]),
    ]], colWidths=[1.3 * cm, 20.2 * cm])
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(row)

story.append(Spacer(1, 0.25 * cm))

# CTA box
cta = Table([[
    Paragraph(
        "<b>Pipeline 100 % reprodutível em Python</b> "
        "(pandas, matplotlib, seaborn, reportlab) · Limpeza auditável · "
        "Parser Kemler pior caso · Índice de risco composto · 9 mapas de calor.<br/>"
        f"<br/><b>Relatório técnico completo (23 páginas) disponível mediante pedido — "
        f"<font color='#922b21'>{AUTOR}</font></b>",
        S["body"]),
]], colWidths=[21.5 * cm])
cta.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
    ("BOX", (0, 0), (-1, -1), 1.2, RED),
    ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ("TOPPADDING", (0, 0), (-1, -1), 8),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
]))
story.append(cta)
story.append(Spacer(1, 0.15 * cm))
story.append(Paragraph(
    "<font color='#566573'>#LXDataLab · #ProteçãoCivil · #DataScience · "
    "#Lisboa · #Python · #RiscoFerroviário</font>",
    S["small"]))

doc.build(story)
print(f"PDF LinkedIn gerado: {PDF}")
print(f"Tamanho: {PDF.stat().st_size / 1024:.1f} KB")

"""
Gera o relatório técnico em PDF (analise/Relatorio_Tecnico.pdf) a partir
dos CSVs e PNGs produzidos por desafio.py.
"""

from pathlib import Path
from datetime import datetime
import pandas as pd

AUTOR = "Valter Micas"

MESES_PT = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
    5: "maio", 6: "junho", 7: "julho", 8: "agosto",
    9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
}


def data_pt(d=None):
    d = d or datetime.today()
    return f"{d.day} de {MESES_PT[d.month]} de {d.year}"


def data_pt_curta(d=None):
    d = d or datetime.today()
    return d.strftime("%Y-%m-%d")

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Image, Table,
    TableStyle, PageBreak, KeepTogether, NextPageTemplate
)

BASE = Path("/Users/valtermicas/Documents/projetos/materiais_perigosos")
OUT = BASE / "analise"
FIG = OUT / "figuras"
PDF = OUT / "Relatorio_Tecnico.pdf"

# ---------------------------------------------------------------------------
# Estilos
# ---------------------------------------------------------------------------
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="Cover_Title", fontName="Helvetica-Bold", fontSize=24,
    leading=30, alignment=TA_CENTER, textColor=colors.HexColor("#922b21"),
    spaceAfter=18,
))
styles.add(ParagraphStyle(
    name="Cover_Sub", fontName="Helvetica", fontSize=14,
    leading=20, alignment=TA_CENTER, textColor=colors.HexColor("#2c3e50"),
    spaceAfter=18,
))
styles.add(ParagraphStyle(
    name="Cover_Meta", fontName="Helvetica-Oblique", fontSize=11,
    leading=16, alignment=TA_CENTER, textColor=colors.HexColor("#566573"),
))
styles.add(ParagraphStyle(
    name="H1", fontName="Helvetica-Bold", fontSize=16,
    leading=22, textColor=colors.HexColor("#922b21"),
    spaceBefore=18, spaceAfter=10, keepWithNext=True,
))
styles.add(ParagraphStyle(
    name="H2", fontName="Helvetica-Bold", fontSize=13,
    leading=18, textColor=colors.HexColor("#1f3a5f"),
    spaceBefore=12, spaceAfter=6, keepWithNext=True,
))
styles.add(ParagraphStyle(
    name="H3", fontName="Helvetica-Bold", fontSize=11,
    leading=15, textColor=colors.HexColor("#34495e"),
    spaceBefore=6, spaceAfter=3, keepWithNext=True,
))
styles.add(ParagraphStyle(
    name="Body", parent=styles["Normal"], fontName="Helvetica",
    fontSize=9.5, leading=14, alignment=TA_JUSTIFY, spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="Bul", parent=styles["Body"],
    leftIndent=14, bulletIndent=4, spaceAfter=3,
))
styles.add(ParagraphStyle(
    name="CodeBlk", fontName="Courier", fontSize=8.5, leading=11,
    textColor=colors.HexColor("#212f3d"), leftIndent=12,
    backColor=colors.HexColor("#f4f6f7"),
    borderColor=colors.HexColor("#d5dbdb"), borderWidth=0.5,
    borderPadding=4, spaceBefore=4, spaceAfter=8,
))
styles.add(ParagraphStyle(
    name="Caption", fontName="Helvetica-Oblique", fontSize=8.5,
    leading=11, alignment=TA_CENTER, textColor=colors.HexColor("#566573"),
    spaceBefore=2, spaceAfter=12,
))

PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm


# ---------------------------------------------------------------------------
# Frames + Page numbering
# ---------------------------------------------------------------------------
def header_footer(canvas, doc):
    canvas.saveState()
    # rodapé
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#7b7d7d"))
    canvas.drawString(MARGIN, 1.0 * cm,
                      f"Risco no transporte ferroviário de matérias perigosas — Lisboa  ·  {AUTOR}")
    canvas.drawRightString(PAGE_W - MARGIN, 1.0 * cm, f"Página {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#d5d8dc"))
    canvas.line(MARGIN, 1.4 * cm, PAGE_W - MARGIN, 1.4 * cm)
    # cabeçalho
    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.setFillColor(colors.HexColor("#922b21"))
    canvas.drawString(MARGIN, PAGE_H - 1.2 * cm, "Relatório técnico — Desafio LX Data Lab 0125")
    canvas.setFillColor(colors.HexColor("#7b7d7d"))
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 1.2 * cm, data_pt_curta())
    canvas.line(MARGIN, PAGE_H - 1.4 * cm, PAGE_W - MARGIN, PAGE_H - 1.4 * cm)
    canvas.restoreState()


def cover_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#fdf2e9"))
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#922b21"))
    canvas.rect(0, PAGE_H - 6 * cm, PAGE_W, 0.6 * cm, fill=1, stroke=0)
    canvas.rect(0, 2 * cm, PAGE_W, 0.3 * cm, fill=1, stroke=0)
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def img(path, width_cm=16):
    p = FIG / path
    im = Image(str(p))
    iw, ih = im.imageWidth, im.imageHeight
    w = width_cm * cm
    h = w * ih / iw
    im.drawWidth = w
    im.drawHeight = h
    im._restrictSize(w, h)
    return im


def figure(name, caption, width_cm=16):
    return KeepTogether([
        img(name, width_cm=width_cm),
        Paragraph(caption, styles["Caption"]),
    ])


def df_to_table(df, col_widths=None, header_bg="#922b21", header_fg="#ffffff",
                font_size=8, align_right_cols=None, row_height=None,
                wrap_cols=None):
    """Constrói uma Table a partir de um DataFrame. wrap_cols indexes get Paragraph wrap."""
    align_right_cols = align_right_cols or []
    wrap_cols = wrap_cols or []
    head = list(df.columns.astype(str))
    body = df.values.tolist()
    # Convert wrap_cols cells to Paragraph for line wrapping
    wrap_style = ParagraphStyle("cell", fontName="Helvetica", fontSize=font_size,
                                leading=font_size + 2)
    formatted = []
    formatted.append(head)
    for row in body:
        new_row = []
        for i, v in enumerate(row):
            if isinstance(v, float):
                if abs(v) >= 1000:
                    s = f"{v:,.0f}".replace(",", " ")
                elif v == int(v):
                    s = f"{int(v)}"
                else:
                    s = f"{v:.2f}"
            else:
                s = "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)
            if i in wrap_cols:
                new_row.append(Paragraph(s, wrap_style))
            else:
                new_row.append(s)
        formatted.append(new_row)
    t = Table(formatted, colWidths=col_widths, rowHeights=row_height, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(header_fg)),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bdc3c7")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#fbeee6")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for c in align_right_cols:
        style.append(("ALIGN", (c, 1), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(style))
    return t


# ---------------------------------------------------------------------------
# Carregar dados
# ---------------------------------------------------------------------------
df_classe = pd.read_csv(OUT / "02_por_classe.csv")
df_dia = pd.read_csv(OUT / "03a_por_dia_semana.csv").rename(columns={df_classe.columns[0]: "Dia"})
df_dia.columns = ["Dia", "Nº viagens", "% do total"]
df_hora = pd.read_csv(OUT / "03b_por_hora.csv")
df_hora.columns = ["Hora", "Nº viagens"]
df_hora = df_hora[df_hora["Nº viagens"] > 0]
df_top10 = pd.read_csv(OUT / "04_top10_materias.csv")
df_top10_risco = pd.read_csv(OUT / "04b_top10_risco.csv")
df_corredor = pd.read_csv(OUT / "06_risco_corredor_estacoes.csv")
df_corredor_total = pd.read_csv(OUT / "06b_risco_total_estacao.csv")
df_corredor_total.columns = ["Estação", "Risco total"]


# ---------------------------------------------------------------------------
# Construção do documento
# ---------------------------------------------------------------------------
doc = BaseDocTemplate(
    str(PDF), pagesize=A4,
    leftMargin=MARGIN, rightMargin=MARGIN,
    topMargin=2.0 * cm, bottomMargin=2.0 * cm,
    title="Relatório técnico — Risco no transporte ferroviário de matérias perigosas",
    author=AUTOR,
    subject="Desafio LX Data Lab 0125 — Análise para SMPC Lisboa",
)
cover_frame = Frame(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN,
                    leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
body_frame = Frame(MARGIN, MARGIN + 0.5 * cm, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN - 0.5 * cm,
                   leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

LAND_W, LAND_H = landscape(A4)
land_margin = 1.5 * cm
land_frame = Frame(land_margin, land_margin + 0.5 * cm,
                   LAND_W - 2 * land_margin, LAND_H - 2 * land_margin - 0.5 * cm,
                   leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)


def header_footer_landscape(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#7b7d7d"))
    canvas.drawString(land_margin, 1.0 * cm,
                      f"Risco no transporte ferroviário de matérias perigosas — Lisboa  ·  {AUTOR}")
    canvas.drawRightString(LAND_W - land_margin, 1.0 * cm, f"Página {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#d5d8dc"))
    canvas.line(land_margin, 1.4 * cm, LAND_W - land_margin, 1.4 * cm)
    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.setFillColor(colors.HexColor("#922b21"))
    canvas.drawString(land_margin, LAND_H - 1.0 * cm, "Relatório técnico — Desafio LX Data Lab 0125")
    canvas.setFillColor(colors.HexColor("#7b7d7d"))
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(LAND_W - land_margin, LAND_H - 1.0 * cm, data_pt_curta())
    canvas.line(land_margin, LAND_H - 1.2 * cm, LAND_W - land_margin, LAND_H - 1.2 * cm)
    canvas.restoreState()


doc.addPageTemplates([
    PageTemplate(id="cover", frames=[cover_frame], onPage=cover_page, pagesize=A4),
    PageTemplate(id="body", frames=[body_frame], onPage=header_footer, pagesize=A4),
    PageTemplate(id="land", frames=[land_frame], onPage=header_footer_landscape,
                 pagesize=landscape(A4)),
])

story = []

# ---------------- CAPA ----------------
story.append(Spacer(1, 4.5 * cm))
story.append(Paragraph("Determinação de áreas potencialmente afetadas em caso de acidente "
                       "com transporte ferroviário de mercadorias perigosas",
                       styles["Cover_Title"]))
story.append(Paragraph("Relatório técnico — análise estatística e mapeamento de risco",
                       styles["Cover_Sub"]))
story.append(Spacer(1, 1.2 * cm))
story.append(Paragraph("Desafio LX Data Lab · 0125",
                       styles["Cover_Sub"]))
story.append(Paragraph("Promotor: Serviço Municipal de Proteção Civil de Lisboa (SMPC)",
                       styles["Cover_Meta"]))
story.append(Spacer(1, 2.5 * cm))
story.append(Paragraph(
    "Pipeline reprodutível: <font face='Courier'>analise/desafio.py</font><br/>"
    "Dados originais: amostras fornecidas pelo SMPC (1998–2002, "
    "100 viagens · 2 555 registos de matérias)<br/>"
    "Versão 2 · normalização ADR/RID · parser Kemler pior caso · "
    "índice de risco composto · 9 mapas de calor",
    styles["Cover_Meta"]))
story.append(Spacer(1, 1.8 * cm))
story.append(Paragraph("Autor", styles["Cover_Meta"]))
story.append(Paragraph(f"<b><font size='16' color='#922b21'>{AUTOR}</font></b>",
                       styles["Cover_Meta"]))
story.append(Spacer(1, 0.8 * cm))
story.append(Paragraph(data_pt(), styles["Cover_Meta"]))

story.append(NextPageTemplate("body"))
story.append(PageBreak())

# ---------------- ÍNDICE ----------------
story.append(Paragraph("Índice", styles["H1"]))
toc_items = [
    ("1. Sumário executivo", 3),
    ("2. Metodologia", 4),
    ("    2.1 Fontes de dados", 4),
    ("    2.2 Limpeza e normalização", 4),
    ("    2.3 Parser de pior caso — código Kemler", 5),
    ("    2.4 Índice de risco composto", 6),
    ("3. Resultados das análises pedidas", 6),
    ("    3.1 Matérias por classe ADR/RID", 6),
    ("    3.2 Viagens por dia da semana", 7),
    ("    3.3 Distribuição horária", 8),
    ("    3.4 Top 10 — por frequência", 8),
    ("    3.5 Top 10 — por risco (pior caso)", 9),
    ("4. Mapas de calor", 10),
    ("    4.1 Janela temporal — Dia × Hora", 10),
    ("    4.2 Severidade — Classe × Nº Perigo", 11),
    ("    4.3 Matriz de fluxo — Origem × Destino", 12),
    ("    4.4 Perfil de risco normalizado — Top 15", 13),
    ("    4.5 Correlações entre indicadores", 14),
    ("    4.6 Mapa de impacto espacial — pior caso", 15),
    ("    4.7 Painel de impacto — Top 10", 16),
    ("5. Corredor Parque das Nações ↔ Alcântara", 17),
    ("6. Conclusões e recomendações", 19),
    ("Anexo — Ficheiros gerados", 20),
]
toc_table = Table([[Paragraph(t, styles["Body"]), str(p)] for t, p in toc_items],
                  colWidths=[14 * cm, 2 * cm])
toc_table.setStyle(TableStyle([
    ("FONTSIZE", (0, 0), (-1, -1), 10),
    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ("LINEBELOW", (0, 0), (-1, -1), 0.2, colors.HexColor("#ebedef")),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))
story.append(toc_table)
story.append(PageBreak())

# ---------------- 1. SUMÁRIO EXECUTIVO ----------------
story.append(Paragraph("1. Sumário executivo", styles["H1"]))
story.append(Paragraph(
    "Este estudo caracteriza o risco do transporte ferroviário de matérias perigosas com "
    "paragem no corredor Parque das Nações ↔ Alcântara, em Lisboa, com base nas duas "
    "amostras disponibilizadas pelo SMPC: o registo de viagens (100 viagens entre "
    "1998-06-29 e 2002-03-28) e o registo detalhado das matérias transportadas "
    "(2 555 linhas, 1 701 IDs distintos).",
    styles["Body"]))
story.append(Paragraph(
    "O pipeline aplicou limpeza exaustiva (detectando que 81 % das linhas tinham o "
    "Nº Perigo indevidamente colocado na coluna Classe), normalizou as classes contra "
    "o conjunto ADR/RID válido, implementou um parser que devolve sempre o pior cenário "
    "para o código Kemler, e calculou um índice de risco composto por linha. "
    "Foram produzidos 4 gráficos clássicos e 9 mapas de calor, incluindo a simulação "
    "espacial 2D do impacto de um acidente.",
    styles["Body"]))

res = pd.read_csv(OUT / "00_resumo.csv")
res.columns = ["Indicador", "Valor"]
# Formatar valores conhecidos
def _fmt(v):
    try:
        f = float(v)
        if f == int(f) and abs(f) > 100:
            return f"{int(f):,}".replace(",", " ")
        if 0 < f < 1:
            return f"{f:.3f}"
        return v
    except (ValueError, TypeError):
        return v
res["Valor"] = res["Valor"].apply(_fmt)
NICE = {
    "viagens_amostra": "Viagens (amostra de transportes)",
    "viagens_paragem_alcantara": "Viagens com paragem em Alcântara",
    "materias_linhas": "Linhas de matérias",
    "materias_ids_distintos": "IDs distintos no registo de matérias",
    "produtos_canonicos_distintos": "Produtos canónicos distintos (após dedupe)",
    "classes_distintas_validas": "Classes ADR/RID distintas (após normalização)",
    "quantidade_total_kg": "Quantidade total movimentada (kg)",
    "classe_dominante": "Classe dominante",
    "raio_evac_max_global_m": "Raio de evacuação máximo registado (m)",
    "risco_indice_max": "Índice de risco máximo (escala 0–1)",
    "risco_indice_medio": "Índice de risco médio (escala 0–1)",
    "kemler_intensificados": "Linhas com Kemler intensificado (dígito duplo)",
    "kemler_com_X": "Linhas com prefixo X (reage com água)",
}
res["Indicador"] = res["Indicador"].map(lambda x: NICE.get(x, x))
story.append(df_to_table(res, col_widths=[10.5 * cm, 6 * cm],
                         align_right_cols=[1], font_size=9))
story.append(Spacer(1, 6))
story.append(Paragraph(
    "<b>Conclusão operacional:</b> o corredor concentra 100 % dos transportes da amostra "
    "numa janela noturna estreita (19h–23h, dias úteis), atravessa zonas de densidade "
    "urbana muito alta (Entrecampos, Sete Rios, Roma–Areeiro) e impõe um buffer de "
    "planeamento de <b>800 m</b> para os 10 produtos mais frequentes, com extensão a "
    "<b>1 600 m</b> no cenário extremo de gases liquefeitos sob pressão.",
    styles["Body"]))
story.append(PageBreak())

# ---------------- 2. METODOLOGIA ----------------
story.append(Paragraph("2. Metodologia", styles["H1"]))

story.append(Paragraph("2.1 Fontes de dados", styles["H2"]))
fontes = pd.DataFrame({
    "Ficheiro": ["Amostra_Registo do Transporte Ferroviario…xlsx",
                 "Amostra_Registo das matérias transportadas.xlsx"],
    "Linhas": [100, 2555],
    "Período/IDs": ["1998-06-29 → 2002-03-28", "1 701 IDs distintos a partir do ID 1646"],
    "Conteúdo": ["Uma linha por viagem (data, hora, origem, destino, qtd total)",
                 "Detalhe por produto (ONU, classe, Kemler, raios, explosão)"],
})
story.append(df_to_table(fontes, col_widths=[5.5 * cm, 1.6 * cm, 4 * cm, 5.4 * cm],
                         font_size=8.5, wrap_cols=[0, 2, 3]))
story.append(Paragraph(
    "<b>Nota crítica de integridade:</b> os <font face='Courier'>ID</font> das duas amostras "
    "não se sobrepõem (transportes 0001‑0060; matérias 1646+). Como 98 % das viagens "
    "da amostra de transportes têm paragem em Alcântara, a amostra de matérias é "
    "tratada como representativa do universo \"viagens com paragem em Alcântara\".",
    styles["Body"]))

story.append(Paragraph("2.2 Limpeza e normalização", styles["H2"]))
limpeza = pd.DataFrame({
    "Operação": [
        "Strip + colapso de espaços + remoção de chars zero-width",
        "Conversão para datetime/time",
        "Validação de Nº ONU (inteiro de 4 dígitos)",
        "Normalização de CLASSE contra conjunto ADR/RID válido",
        "Forma canónica de produto (sem acentos, lowercase)",
        "Conversão numérica forçada com tracking de NaN",
        "Normalização de origem/destino (acentos)",
    ],
    "Coluna(s)": [
        "todas string", "DATA, HORA PARTIDA, HORA CHEGADA", "Nº ONU",
        "CLASSE", "TIPO PRODUTO", "quantidades e raios", "ORIGEM, DESTINO",
    ],
    "Resultado": [
        "aplicado a 100 % das linhas",
        "0 erros de parsing",
        "1 inválido (mantido e sinalizado)",
        "2 074 / 2 555 corrigidas (81 %) — Kemler na coluna Classe",
        "186 produtos canónicos a partir de 240+ variantes",
        "NaN preservados, sem imputação",
        "Alcantara ≡ Alcântara",
    ],
})
story.append(df_to_table(limpeza, col_widths=[6.8 * cm, 4.2 * cm, 5.5 * cm],
                         font_size=8, wrap_cols=[0, 1, 2]))
story.append(Paragraph(
    "Cada linha tem agora colunas auditáveis: "
    "<font face='Courier'>ONU_NORM, ONU_LIMPEZA, CLASSE_NORM, CLASSE_LIMPEZA, PRODUTO_CANON</font>. "
    "Tabelas limpas em <font face='Courier'>analise/clean/</font>.",
    styles["Body"]))

story.append(Paragraph("2.3 Parser de pior caso — código Kemler (Nº Perigo)", styles["H2"]))
story.append(Paragraph(
    "O algarismo da placa cor-de-laranja do RID codifica a natureza do perigo. O algoritmo "
    "implementado satisfaz o requisito de <b>cenário menos favorável</b>:",
    styles["Body"]))
story.append(Paragraph("Faz <i>split</i> por <font face='Courier'>ou / or / / / , / +</font> para obter alternativas.", styles["Bul"], bulletText="•"))
story.append(Paragraph("Detecta prefixo <b>X</b> (reage perigosamente com água).", styles["Bul"], bulletText="•"))
story.append(Paragraph("Detecta dígitos duplicados (intensificação — ex.: 33, 66, 88).", styles["Bul"], bulletText="•"))
story.append(Paragraph("Ordena por severidade decrescente: <i>X</i> &gt; sem X &gt; mais dígitos &gt; intensificado &gt; valor numérico maior.", styles["Bul"], bulletText="•"))
story.append(Paragraph("Devolve o código vencedor + descrição textual dos riscos.", styles["Bul"], bulletText="•"))

kemler = pd.DataFrame({
    "Dígito Kemler": ["2", "3", "4", "5", "6", "7", "8", "9", "0", "duplicado (33, 66…)", "Prefixo X"],
    "Significado": [
        "Gás sob pressão / emissão por reação química",
        "Inflamabilidade (líquido / gás / autoaquecimento)",
        "Inflamabilidade de sólido",
        "Comburente",
        "Toxicidade / infeção",
        "Radioatividade",
        "Corrosividade",
        "Reação espontânea violenta",
        "Sem perigo secundário",
        "Risco intensificado",
        "Reage perigosamente com água",
    ],
})
story.append(df_to_table(kemler, col_widths=[3.5 * cm, 13 * cm], font_size=9, wrap_cols=[1]))

story.append(Paragraph("<b>Verificação:</b>", styles["Body"]))
story.append(Paragraph("<font face='Courier'>\"30 ou 33\"</font> &rarr; escolhido <b>33</b> (inflamabilidade intensificada). ✓", styles["Bul"], bulletText="•"))
story.append(Paragraph("<font face='Courier'>\"60 ou 66\"</font> &rarr; escolhido <b>66</b> (toxicidade intensificada). ✓", styles["Bul"], bulletText="•"))
story.append(Paragraph("<font face='Courier'>\"X462\"</font> (Fosforeto de alumínio) &rarr; mantém o X &rarr; severidade máxima. ✓", styles["Bul"], bulletText="•"))
story.append(Paragraph("Total na amostra: <b>1 065 registos com Kemler intensificado</b> (41,7 %) e <b>2 com prefixo X</b>.", styles["Body"]))

story.append(Paragraph("2.4 Índice de risco composto", styles["H2"]))
story.append(Paragraph(
    "Para cada linha foi calculado um índice de risco normalizado em [0, 1]:",
    styles["Body"]))
story.append(Paragraph(
    "risco_indice = 0.40 · severidade_kemler_norm<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; + 0.30 · log<sub>10</sub>(quantidade_kg)_norm<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; + 0.20 · raio_evac_norm<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; + 0.10 · risco_explosão (0/1)",
    styles["CodeBlk"]))
story.append(Paragraph(
    "onde <font face='Courier'>severidade_kemler</font> = nº de dígitos não-zero distintos do "
    "código pior caso + 1,5 (se X) + 0,5 (se intensificado). "
    "A quantidade é tomada em escala logarítmica para evitar saturação por outliers. "
    "Os pesos são transparentes e configuráveis no script.",
    styles["Body"]))

story.append(PageBreak())

# ---------------- 3. RESULTADOS ----------------
story.append(Paragraph("3. Resultados das análises pedidas pelo desafio", styles["H1"]))

# 3.1 Classe
story.append(Paragraph("3.1 Identificação das matérias por classe ADR/RID", styles["H2"]))
story.append(Paragraph(
    "Após normalização (recuperando ~81 % das linhas que tinham o campo "
    "<font face='Courier'>CLASSE</font> ocupado com o Nº Perigo):",
    styles["Body"]))
df_c = df_classe.copy()
df_c.columns = ["Classe", "Nº reg.", "Viagens", "Quantidade (kg)", "Risco médio", "Risco máx.", "% reg."]
df_c["Risco médio"] = df_c["Risco médio"].round(2)
df_c["Risco máx."] = df_c["Risco máx."].round(2)
story.append(df_to_table(df_c, col_widths=[6.3 * cm, 1.6 * cm, 1.6 * cm, 2.6 * cm, 1.6 * cm, 1.4 * cm, 1.4 * cm],
                         font_size=8, align_right_cols=[1, 2, 3, 4, 5, 6], wrap_cols=[0]))
story.append(Spacer(1, 4))
story.append(figure("g1_classes.png", "Figura 1 — Registos por classe ADR/RID (após normalização)."))

story.append(Paragraph(
    "<b>Leitura:</b> a frequência é dominada pela classe 3 (líquidos inflamáveis, 43,8 %). "
    "Mas o maior risco médio por linha é da classe <b>4.3</b> (matérias que libertam gases "
    "inflamáveis em contacto com água) — única classe da amostra que combina prefixo X com "
    "incêndio. Exige atenção específica no plano de combate (evitar uso de água; usar pó "
    "químico ou espuma seca).",
    styles["Body"]))

story.append(PageBreak())

# 3.2 Dia da semana
story.append(Paragraph("3.2 Viagens por dia da semana", styles["H2"]))
story.append(df_to_table(df_dia, col_widths=[5 * cm, 4 * cm, 4 * cm],
                         font_size=9.5, align_right_cols=[1, 2]))
story.append(Spacer(1, 4))
story.append(figure("g2_dia_semana.png",
                    "Figura 2 — Viagens com matérias perigosas por dia da semana. "
                    "98 % concentradas em dias úteis; fim‑de‑semana praticamente nulo."))
story.append(PageBreak())

# 3.3 Hora
story.append(Paragraph("3.3 Distribuição horária", styles["H2"]))
story.append(Paragraph(
    "100 % das partidas estão concentradas em quatro horas do dia (19h, 21h, 22h, 23h), "
    "com pico claro às 19h.",
    styles["Body"]))
story.append(df_to_table(df_hora, col_widths=[4 * cm, 4 * cm], font_size=10,
                         align_right_cols=[1]))
story.append(Spacer(1, 4))
story.append(figure("g3_hora.png", "Figura 3 — Distribuição horária da hora de partida (amostra)."))

story.append(PageBreak())

# 3.4 Top 10 frequência
story.append(Paragraph("3.4 Top 10 matérias — por frequência", styles["H2"]))
t = df_top10.copy()
t = t[["tipo_produto", "onu", "classe", "codigo_pior", "nr_transportes",
       "quantidade_kg", "raio_evac", "risco_indice_max"]]
t.columns = ["Matéria", "ONU", "Classe", "Kemler pior", "Nº transp.",
             "Qtd. (kg)", "Raio evac. (m)", "Risco"]
t["Classe"] = t["Classe"].astype(str).str.replace(".0", "", regex=False)
t["Risco"] = t["Risco"].round(2)
story.append(df_to_table(t, col_widths=[5.5 * cm, 1.3 * cm, 1.3 * cm, 1.8 * cm,
                                        1.6 * cm, 2 * cm, 1.6 * cm, 1.4 * cm],
                         font_size=8, align_right_cols=[4, 5, 6, 7], wrap_cols=[0]))
story.append(Spacer(1, 4))
story.append(figure("g4_top10.png", "Figura 4 — Top 10 matérias mais transportadas (amostra normalizada)."))

story.append(PageBreak())

# 3.5 Top 10 risco
story.append(Paragraph("3.5 Top 10 matérias — por risco (cenário menos favorável)", styles["H2"]))
story.append(Paragraph(
    "O <b>Top 10 por risco é completamente diferente do Top 10 por frequência</b>. "
    "Materiais raros mas de pior caso (Fosforeto de alumínio com Kemler <b>X462</b>, "
    "Etildiclorossilano <b>X338</b> — ambos classe 4.3) e gases liquefeitos sob pressão "
    "(Metilacetileno + propadieno, raio de evacuação de 1 600 m) saltam para o topo.",
    styles["Body"]))
t2 = df_top10_risco.copy()
t2 = t2[["tipo_produto", "onu", "classe", "codigo_pior", "nr_transportes",
         "quantidade_kg", "raio_evac", "risco_indice_max"]]
t2.columns = ["Matéria", "ONU", "Classe", "Kemler pior", "Nº transp.",
              "Qtd. (kg)", "Raio evac. (m)", "Risco"]
t2["Classe"] = t2["Classe"].astype(str).str.replace(".0", "", regex=False)
t2["Risco"] = t2["Risco"].round(3)
story.append(df_to_table(t2, col_widths=[5.5 * cm, 1.3 * cm, 1.3 * cm, 1.8 * cm,
                                         1.6 * cm, 2 * cm, 1.6 * cm, 1.4 * cm],
                         font_size=8, align_right_cols=[4, 5, 6, 7], wrap_cols=[0]))
story.append(Paragraph(
    "<b>Implicação operacional:</b> estes 10 produtos devem ser listados nominalmente nos "
    "planos de emergência, com fichas de intervenção específicas e protocolos de combate "
    "dedicados (em especial os de classe 4.3, em que o uso de água é contraindicado).",
    styles["Body"]))

story.append(PageBreak())

# ---------------- 4. MAPAS DE CALOR ----------------
story.append(Paragraph("4. Mapas de calor", styles["H1"]))

story.append(Paragraph("4.1 Janela temporal — Dia × Hora", styles["H2"]))
story.append(figure("h1_dia_hora.png",
                    "Figura 5 — Mapa de calor Dia × Hora. 100 % do risco temporal "
                    "concentra-se em 4 horas/4 dias úteis."))
story.append(Paragraph(
    "Pico absoluto às 19h de quarta-feira/sexta e 22h de terça/quarta. O fim-de-semana "
    "é uma \"ilha verde\" — janela útil para inspeções, exercícios e manutenção do "
    "corredor ferroviário.",
    styles["Body"]))
story.append(PageBreak())

story.append(Paragraph("4.2 Severidade — Classe × Nº Perigo (pior caso)", styles["H2"]))
story.append(figure("h2_classe_perigo.png",
                    "Figura 6 — Cruzamento entre Classe ADR/RID e 1º dígito do Kemler pior caso."))
story.append(Paragraph(
    "Permite verificar coerência interna (classe 3 deve ter Kemler a iniciar em 3) e "
    "detetar registos suspeitos (ex.: classe 8 com Kemler iniciado em 2 é provavelmente "
    "um erro de digitação a investigar).",
    styles["Body"]))
story.append(PageBreak())

story.append(Paragraph("4.3 Matriz de fluxo — Origem × Destino", styles["H2"]))
story.append(figure("h3_origem_destino.png",
                    "Figura 7 — Mapa de calor de fluxos rota a rota.", width_cm=13))
story.append(Paragraph(
    "A esmagadora maioria das viagens é <b>Leixões → Alcântara</b> (via Linha do Norte + "
    "Linha de Cintura). Existem secundárias Alcântara → Leixões e Alcântara ↔ "
    "Valença/Valença do Minho (exportação para Espanha).",
    styles["Body"]))
story.append(PageBreak())

story.append(Paragraph("4.4 Perfil de risco normalizado — Top 15 matérias", styles["H2"]))
story.append(figure("h4_produtos_risco.png",
                    "Figura 8 — Perfil de risco normalizado [0–1] para o Top 15 matérias × 5 indicadores."))
story.append(Paragraph(
    "Visualmente, uma linha completamente vermelha identificaria um produto perigoso em "
    "todos os indicadores — <b>não existe na amostra</b>: produtos de alta frequência "
    "(tintas) têm raio médio, produtos de risco máximo (fosforeto) têm baixa frequência. "
    "O trade-off frequência × severidade justifica o <b>planeamento dual</b> (exercícios "
    "para os frequentes, protocolos especiais para os severos).",
    styles["Body"]))
story.append(PageBreak())

story.append(Paragraph("4.5 Correlações entre indicadores", styles["H2"]))
story.append(figure("h5_correlacoes.png", "Figura 9 — Matriz de correlação de Pearson.", width_cm=14))
story.append(Paragraph(
    "Correlação positiva entre <font face='Courier'>RAIO INCENDIO</font> e "
    "<font face='Courier'>RISCO EXPLOSAO</font> (~0,7) confirma consistência interna. "
    "Correlação fraca entre <font face='Courier'>QUANTIDADE</font> e "
    "<font face='Courier'>kemler_severidade</font> (~0,1) confirma que <b>frequência/"
    "quantidade e severidade são dimensões ortogonais</b> — justifica os dois Top 10.",
    styles["Body"]))
story.append(PageBreak())

story.append(Paragraph("4.6 Mapa de impacto espacial — pior caso do Top 10", styles["H2"]))
story.append(figure("h6_impacto_pior_caso.png",
                    "Figura 10 — Simulação 2D do impacto radial (grelha 20m × 20m, "
                    "3,6 km × 3,6 km centrada no ponto de acidente).", width_cm=14))
story.append(Paragraph(
    "Três anéis concêntricos: <b>100 m</b> (evacuação imediata — interior em vermelho "
    "intenso), <b>500 m</b> (acidente grave — laranja/amarelo) e <b>800 m</b> "
    "(cenário de incêndio — verde claro a amarelo). A intensidade do risco cai por zonas "
    "(1.0 → 0.66 → 0.33 → 0). Sobreposto à planta urbana, identifica imediatamente os "
    "quarteirões a evacuar em cada zona.",
    styles["Body"]))
story.append(PageBreak())

story.append(NextPageTemplate("land"))
story.append(PageBreak())
story.append(Paragraph("4.7 Painel de impacto — Top 10 matérias", styles["H2"]))
story.append(Paragraph(
    "Mapa de impacto individual para cada uma das 10 matérias mais frequentes "
    "(raios em metros; ponto de acidente no centro). Permite comparar visualmente "
    "o alcance: a maioria converge para o raio de 800 m, mas o <b>Árgon líquido "
    "refrigerado</b> tem raio mínimo de 100 m (asfixia/BLEVE) e os <b>Aerossóis</b> "
    "têm raio máximo intermédio de 500 m.",
    styles["Body"]))
story.append(img("h7_impacto_top10.png", width_cm=26))
story.append(Paragraph(
    "Figura 11 — Painel de mapas de impacto para o Top 10 das matérias mais transportadas. "
    "Linha branca: raio mínimo (evacuação imediata). Linha amarela: raio máximo (acidente "
    "grave). Linha vermelha: raio de incêndio (pior caso). Estrela preta: ponto de acidente.",
    styles["Caption"]))
story.append(NextPageTemplate("body"))
story.append(PageBreak())

# ---------------- 5. CORREDOR ----------------
story.append(Paragraph("5. Corredor Parque das Nações ↔ Alcântara", styles["H1"]))

story.append(Paragraph("5.1 Modelo de exposição por estação", styles["H2"]))
story.append(Paragraph(
    "Para as 10 estações da Linha de Cintura/Norte entre Parque das Nações e Alcântara, "
    "foi calculada uma medida de risco potencial:",
    styles["Body"]))
story.append(Paragraph(
    "risco_estacao(matéria) = risco_indice_max · (raio_evac / 800) · densidade_urbana",
    styles["CodeBlk"]))
story.append(Paragraph(
    "A <font face='Courier'>densidade_urbana</font> é um proxy manual (0,55–1,00) baseado "
    "no tecido urbano em redor de cada estação. <b>Carece de calibração</b> com dados "
    "de cadastro / população real (BUE Lisboa, BGRI 2021).",
    styles["Body"]))

story.append(figure("h8_corredor_estacoes.png",
                    "Figura 12 — Mapa de calor de risco potencial: estações × Top 10 matérias."))
story.append(PageBreak())

story.append(Paragraph("5.2 Ranking das estações", styles["H2"]))
df_corredor_total["Risco total"] = df_corredor_total["Risco total"].round(2)
story.append(df_to_table(df_corredor_total, col_widths=[8 * cm, 5 * cm],
                         font_size=10, align_right_cols=[1]))
story.append(figure("h9_ranking_estacoes.png",
                    "Figura 13 — Ranking das 10 estações do corredor por risco potencial."))
story.append(Paragraph(
    "<b>Prioridade operacional:</b> Entrecampos, Roma–Areeiro e Sete Rios devem ter "
    "postos de comando avançado pré-definidos e rotas de evacuação modeladas com prioridade.",
    styles["Body"]))

story.append(Paragraph("5.3 Corredor de evacuação proposto", styles["H2"]))
ev = pd.DataFrame({
    "Cenário": [
        "Evacuação imediata",
        "Evacuação alargada",
        "Cenário incêndio (pior caso Top 10)",
        "Cenário extremo (pior matéria da amostra)",
    ],
    "Buffer ao eixo (m)": ["100", "500", "800", "1 600"],
    "Justificação": [
        "Máximo do RAIO MINIMO no Top 10",
        "Máximo do RAIO MAXIMO no Top 10",
        "RAIO INCENDIO adotado por todas as 10 matérias",
        "Isobutano (ONU 1969) — BLEVE de gás liquefeito",
    ],
})
story.append(df_to_table(ev, col_widths=[5.5 * cm, 3.5 * cm, 7.5 * cm],
                         font_size=9, align_right_cols=[1], wrap_cols=[0, 2]))
story.append(Paragraph(
    "O <b>valor de planeamento</b> para a Linha de Cintura deve ser <b>800 m de cada lado "
    "do eixo ferroviário</b>, com aumento excecional para <b>1 600 m</b> quando o comboio "
    "transporta gases liquefeitos sob pressão (classe 2, ONU 1969 e 1060).",
    styles["Body"]))

story.append(PageBreak())

# ---------------- 6. CONCLUSÕES ----------------
story.append(Paragraph("6. Conclusões e recomendações", styles["H1"]))
conclusoes = [
    ("Qualidade dos dados precisa de governance",
     "81 % das linhas tinham o Nº Perigo na coluna CLASSE — sintoma de validação "
     "ausente na introdução. Recomenda-se introduzir validação por lista pendente "
     "contra a lista RID na origem dos registos."),
    ("Janela de risco estreita e previsível",
     "98 % das viagens em dias úteis, 19h–23h. Permite organizar escalas dedicadas "
     "de prontidão noturna no corredor; libera o fim-de-semana para exercícios."),
    ("Dois Top 10 distintos — frequência e severidade",
     "Exige dois eixos de planeamento: (a) treino sistemático para os 10 mais "
     "frequentes (tintas, adesivos, aerossóis...); (b) protocolos nominais e fichas "
     "de intervenção para os 10 de risco máximo (Fosforeto de alumínio, "
     "Etildiclorossilano, Metilacetileno+propadieno)."),
    ("Corredor de 800 m como buffer padrão; 1 600 m em cenário extremo",
     "Sobrepor estas faixas ao GeoJSON da Rede Ferroviária do SMPC (não fornecido "
     "nesta amostra) isola os quarteirões a evacuar e os candidatos a zonas de apoio."),
    ("Estações críticas: Entrecampos, Roma–Areeiro, Sete Rios",
     "Devem ter planos específicos por estação com rotas de evacuação, hospitais e escolas "
     "pré-mapeadas e zonas de apoio fora do raio de 800 m."),
    ("Próximos passos sugeridos",
     "(i) Cruzar o buffer de 800/1 600 m com o cadastro BUE de Lisboa para quantificar "
     "população exposta. (ii) Calibrar a simulação 2D com modelo ALOHA/CAMEO usando as "
     "quantidades médias por matéria. (iii) Substituir o proxy de densidade urbana por "
     "dados reais de população residente + flutuante (BGRI 2021/DGT)."),
]
for i, (t, b) in enumerate(conclusoes, 1):
    story.append(Paragraph(f"<b>{i}. {t}</b>", styles["H3"]))
    story.append(Paragraph(b, styles["Body"]))

story.append(PageBreak())

# ---------------- ANEXO ----------------
story.append(Paragraph("Anexo — Ficheiros gerados", styles["H1"]))
story.append(Paragraph(
    "Toda a análise é reprodutível executando "
    "<font face='Courier'>python3 analise/desafio.py</font> seguido de "
    "<font face='Courier'>python3 analise/gerar_pdf.py</font>.",
    styles["Body"]))
anexo = pd.DataFrame({
    "Ficheiro": [
        "analise/desafio.py",
        "analise/gerar_pdf.py",
        "analise/RELATORIO.md",
        "analise/Relatorio_Tecnico.pdf",
        "analise/00_resumo.csv",
        "analise/02_por_classe.csv",
        "analise/03a_por_dia_semana.csv",
        "analise/03b_por_hora.csv",
        "analise/04_top10_materias.csv",
        "analise/04b_top10_risco.csv",
        "analise/06_risco_corredor_estacoes.csv",
        "analise/06b_risco_total_estacao.csv",
        "analise/h1_dia_hora.csv",
        "analise/h2_classe_perigo.csv",
        "analise/h3_origem_destino.csv",
        "analise/clean/materias_clean.csv",
        "analise/clean/transportes_clean.csv",
        "analise/figuras/g1..g4 (4 PNG)",
        "analise/figuras/h1..h9 (9 PNG)",
    ],
    "Descrição": [
        "Pipeline completo: carregamento, limpeza, parser Kemler, índice de risco, gráficos.",
        "Conversor que gera este PDF a partir dos CSVs e PNGs.",
        "Relatório em Markdown (idêntico em conteúdo a este PDF).",
        "Este relatório técnico em PDF.",
        "Indicadores resumo (top do sumário executivo).",
        "Distribuição por classe ADR/RID normalizada.",
        "Distribuição de viagens por dia da semana.",
        "Distribuição horária de viagens.",
        "Top 10 matérias por frequência.",
        "Top 10 matérias por índice de risco composto.",
        "Risco potencial por estação × matéria.",
        "Risco total por estação (soma do Top 10).",
        "Matriz Dia × Hora (mapa de calor h1).",
        "Matriz Classe × dígito Kemler (mapa de calor h2).",
        "Matriz Origem × Destino (mapa de calor h3).",
        "Registo de matérias com colunas auditáveis após limpeza.",
        "Registo de viagens normalizado.",
        "Gráficos clássicos: classes, dias, hora, top 10.",
        "Mapas de calor: temporal, severidade, fluxo, perfil, correlações, impacto, painel, corredor, ranking.",
    ],
})
story.append(df_to_table(anexo, col_widths=[6.5 * cm, 10 * cm],
                         font_size=8, wrap_cols=[0, 1]))

# ---------------------------------------------------------------------------
# Gerar PDF
# ---------------------------------------------------------------------------
doc.build(story)
print(f"PDF gerado em: {PDF}")
print(f"Tamanho: {PDF.stat().st_size / 1024:.1f} KB")

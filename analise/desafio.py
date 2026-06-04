"""
Desafio LX Data Lab — Risco no transporte ferroviário de matérias perigosas (Lisboa).

Pipeline completo:
  1.  Carregamento das duas amostras (Transportes / Matérias)
  2.  Limpeza e normalização rigorosa
        - Strip de strings e correção de acentos
        - Validação de Nº ONU (4 dígitos numéricos)
        - Normalização da CLASSE contra o conjunto válido ADR/RID
        - Normalização do TIPO PRODUTO (case-insensitive, agrupamento por nome canónico)
        - Tratamento de NaN e tipos
  3.  Parser de pior caso para Nº PERIGO (código Kemler)
        - "X" prefixo (reage perigosamente com água) → pior caso
        - Dígitos duplicados (33, 66, 88...) → intensificação
        - Alternativas "ou/or/ /,"  → escolher o pior
  4.  Severidade do Kemler e Índice de Risco composto
  5.  Análises descritivas e mapas de calor
  6.  Simulação espacial de impacto de acidente (grelhas 2D)
  7.  Distribuição do risco pelas estações do corredor Parque das Nações ↔ Alcântara

Saídas:
  - analise/clean/*.csv    → tabelas limpas/normalizadas
  - analise/figuras/*.png  → gráficos e heat maps
  - analise/*.csv          → resultados de análise
  - analise/RELATORIO.md   → relatório consolidado (escrito noutro passo)
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
BASE = Path("/Users/valtermicas/Documents/projetos/materiais_perigosos")
OUT = BASE / "analise"
CLEAN = OUT / "clean"
FIG = OUT / "figuras"
for d in (OUT, CLEAN, FIG):
    d.mkdir(exist_ok=True)

FILE_TRANSP = BASE / "Amostra_Registo do Transporte Ferroviario de Materias Perigosas.xlsx"
FILE_MATER = BASE / "Amostra_Registo das matérias transportadas.xlsx"

sns.set_theme(style="whitegrid", rc={"axes.titleweight": "bold"})

VALID_CLASSES = {
    "1": "Explosivos",
    "2": "Gases",
    "2.1": "Gases inflamáveis",
    "2.2": "Gases não inflamáveis, não tóxicos",
    "2.3": "Gases tóxicos",
    "3": "Líquidos inflamáveis",
    "4.1": "Sólidos inflamáveis",
    "4.2": "Matérias sujeitas a inflamação espontânea",
    "4.3": "Em contacto c/ água libertam gases inflamáveis",
    "5.1": "Matérias comburentes",
    "5.2": "Peróxidos orgânicos",
    "6.1": "Matérias tóxicas",
    "6.2": "Matérias infeciosas",
    "7": "Matérias radioativas",
    "8": "Matérias corrosivas",
    "9": "Matérias e objetos perigosos diversos",
}

# Significado dos algarismos do código Kemler (ADR/RID)
KEMLER_DIGIT = {
    2: "Gás sob pressão",
    3: "Inflamabilidade (líquido/gás)",
    4: "Inflamabilidade de sólido",
    5: "Comburente",
    6: "Toxicidade / infeção",
    7: "Radioatividade",
    8: "Corrosividade",
    9: "Reação espontânea violenta",
}

# ---------------------------------------------------------------------------
# 1. Carregamento
# ---------------------------------------------------------------------------
print("[1/7] A carregar amostras...")
transp_raw = pd.read_excel(FILE_TRANSP, sheet_name="Tabela1")
mater_raw = pd.read_excel(FILE_MATER, sheet_name="subtabela")
print(f"   Transportes: {len(transp_raw)} linhas | Matérias: {len(mater_raw)} linhas")


# ---------------------------------------------------------------------------
# 2. Limpeza e normalização
# ---------------------------------------------------------------------------
def strip_accents(s: str) -> str:
    if not isinstance(s, str):
        return s
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def clean_str(x):
    if not isinstance(x, str):
        return x
    x = x.replace("​", "").replace("\xa0", " ").strip()
    x = re.sub(r"\s+", " ", x)
    return x if x else None


def canonical_product(name: str | None) -> str | None:
    """Forma canónica de um nome de produto para agrupamento (lowercase, sem acentos, espaços normalizados)."""
    if not isinstance(name, str):
        return None
    return strip_accents(name).lower().strip()


VALID_CLASSES_SET = set(VALID_CLASSES.keys())


def normalize_classe(raw) -> tuple[str, str]:
    """Devolve (classe_normalizada, observacao_limpeza)."""
    if pd.isna(raw):
        return "N/D", "vazia"
    s = str(raw).strip()
    if s in VALID_CLASSES_SET:
        return s, "ok"
    # Tentar subclasse Major.minor (ex. 4.1.2 -> 4.1)
    m = re.match(r"^(\d)\.(\d)", s)
    if m:
        cand = f"{m.group(1)}.{m.group(2)}"
        if cand in VALID_CLASSES_SET:
            return cand, f"truncado de '{s}' (provável Nº perigo na coluna classe)"
        # caso 3.5, 3.31 etc — usar só major
        major = m.group(1)
        if major in VALID_CLASSES_SET:
            return major, f"recuperado major de '{s}' (provável Nº perigo na coluna)"
    # Major isolado
    if s and s[0].isdigit() and s[0] in VALID_CLASSES_SET:
        return s[0], f"recuperado primeiro dígito de '{s}'"
    return "N/D", f"não reconhecido: '{s}'"


def validate_onu(raw) -> tuple[str | None, str]:
    """Nº ONU deve ser inteiro de 4 dígitos (ADR/RID)."""
    if pd.isna(raw):
        return None, "vazia"
    s = re.sub(r"\D", "", str(raw))
    if len(s) == 4:
        return s, "ok"
    if 0 < len(s) < 4:
        return s.zfill(4), f"padded de '{raw}'"
    return None, f"inválido: '{raw}'"


# Aplicar limpeza às MATÉRIAS
mat = mater_raw.copy()
mat.columns = [c.strip() for c in mat.columns]

for col in ["TIPO PRODUTO", "OBSERVAÇÕES"]:
    mat[col] = mat[col].map(clean_str)

mat["ID"] = mat["ID"].astype(str).str.strip()
mat["QUANTIDADE (Kg)"] = pd.to_numeric(mat["QUANTIDADE (Kg)"], errors="coerce")
for col in ["RAIO MINIMO", "RAIO MAXIMO", "RAIO INCENDIO"]:
    mat[col] = pd.to_numeric(mat[col], errors="coerce")
mat["RISCO EXPLOSAO"] = mat["RISCO EXPLOSAO"].fillna(False).astype(bool)

mat[["ONU_NORM", "ONU_LIMPEZA"]] = mat["Nº ONU"].apply(
    lambda v: pd.Series(validate_onu(v), index=["ONU_NORM", "ONU_LIMPEZA"])
)
mat[["CLASSE_NORM", "CLASSE_LIMPEZA"]] = mat["CLASSE"].apply(
    lambda v: pd.Series(normalize_classe(v), index=["CLASSE_NORM", "CLASSE_LIMPEZA"])
)
mat["CLASSE_DESC"] = mat["CLASSE_NORM"].map(lambda c: f"{c} — {VALID_CLASSES.get(c, 'N/D')}")
mat["PRODUTO_CANON"] = mat["TIPO PRODUTO"].map(canonical_product)

print(f"[2/7] Limpeza concluída.")
print(f"   - ONU inválidos: {(mat['ONU_NORM'].isna()).sum()}")
print(f"   - Classe normalizada (corrigida): {(mat['CLASSE_LIMPEZA'] != 'ok').sum()}")
print(f"   - Distribuição da limpeza CLASSE:")
print(mat["CLASSE_LIMPEZA"].value_counts().head(10).to_string())


# Aplicar limpeza aos TRANSPORTES
tr = transp_raw.copy()
tr.columns = [c.strip() for c in tr.columns]
for col in ["ORIGEM", "DESTINO", "OBSERVAÇÕES", "Nº COMBOIO"]:
    tr[col] = tr[col].map(clean_str)
tr["ID"] = tr["ID"].astype(str).str.zfill(4)
tr["DATA"] = pd.to_datetime(tr["DATA"], errors="coerce")
tr["HORA_PARTIDA_H"] = tr["HORA PARTIDA"].apply(
    lambda t: t.hour if pd.notna(t) and hasattr(t, "hour") else None
)
tr["HORA_CHEGADA_H"] = tr["HORA CHEGADA"].apply(
    lambda t: t.hour if pd.notna(t) and hasattr(t, "hour") else None
)
tr["ANO"] = tr["DATA"].dt.year
DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
tr["DIA_SEMANA_NUM"] = tr["DATA"].dt.dayofweek
tr["DIA_SEMANA"] = tr["DIA_SEMANA_NUM"].map(lambda x: DIAS[int(x)] if pd.notna(x) else None)
tr["QUANTIDADE TOTAL (Kg)"] = pd.to_numeric(tr["QUANTIDADE TOTAL (Kg)"], errors="coerce")

# Normalizar origens/destinos (sem acentos, lower) para agrupamento
def norm_local(s):
    if not isinstance(s, str):
        return s
    return strip_accents(s).strip().title()


tr["ORIGEM_N"] = tr["ORIGEM"].map(norm_local)
tr["DESTINO_N"] = tr["DESTINO"].map(norm_local)

# Guardar as tabelas limpas
mat.to_csv(CLEAN / "materias_clean.csv", index=False)
tr.to_csv(CLEAN / "transportes_clean.csv", index=False)


# ---------------------------------------------------------------------------
# 3. Parser pior caso Nº PERIGO
# ---------------------------------------------------------------------------
def parse_perigo_worst(raw) -> dict:
    """Devolve dicionário com:
        codigo_pior : str  (e.g. '33', 'X423')
        valor_pior  : int  (numérico para ranking)
        risco_agua  : bool (prefixo X)
        intensificado : bool (dígito duplicado, e.g. 33, 66, 88)
        alternativas : list[str]
        riscos      : list[str]  descrições por dígito
    """
    if pd.isna(raw):
        return {
            "codigo_pior": None, "valor_pior": np.nan,
            "risco_agua": False, "intensificado": False,
            "alternativas": [], "riscos": [],
        }
    s = str(raw).strip().upper().replace(" ", "")
    # Separar alternativas em "OU", "OR", "/", ","
    parts = re.split(r"OU|OR|/|,|\+", s)
    parts = [p.strip() for p in parts if p.strip()]
    codes = []
    for p in parts:
        has_x = p.startswith("X")
        if has_x:
            p = p[1:]
        # manter apenas dígitos
        digits = re.sub(r"\D", "", p)
        if not digits:
            continue
        intensified = any(digits[i] == digits[i + 1] for i in range(len(digits) - 1))
        # Severidade ordenada: X > sem X; depois pelo número.
        codes.append({
            "code": ("X" if has_x else "") + digits,
            "num": int(digits),
            "x": has_x,
            "intens": intensified,
            "ndigits": len(digits),
        })
    if not codes:
        return {
            "codigo_pior": None, "valor_pior": np.nan,
            "risco_agua": False, "intensificado": False,
            "alternativas": [], "riscos": [],
        }
    # Ordenação por severidade: X > non-X; mais dígitos > menos dígitos; intensificado > não; valor numérico maior
    codes.sort(key=lambda c: (c["x"], c["ndigits"], c["intens"], c["num"]), reverse=True)
    worst = codes[0]
    # Riscos descritivos por dígito do worst
    digit_chars = str(worst["num"])
    riscos = []
    seen = set()
    for ch in digit_chars:
        d = int(ch)
        if d == 0 or d in seen:
            continue
        seen.add(d)
        if d in KEMLER_DIGIT:
            riscos.append(f"{d}: {KEMLER_DIGIT[d]}")
    if worst["x"]:
        riscos.insert(0, "X: reage perigosamente com água")
    if worst["intens"]:
        riscos.append("dígito duplicado: risco intensificado")
    return {
        "codigo_pior": worst["code"],
        "valor_pior": worst["num"] + (1000 if worst["x"] else 0) + (50 if worst["intens"] else 0),
        "risco_agua": worst["x"],
        "intensificado": worst["intens"],
        "alternativas": [c["code"] for c in codes],
        "riscos": riscos,
    }


parsed = mat["Nº PERIGO"].apply(parse_perigo_worst).apply(pd.Series)
mat = pd.concat([mat, parsed], axis=1)
mat["alternativas"] = mat["alternativas"].apply(lambda L: " | ".join(L) if isinstance(L, list) else "")
mat["riscos"] = mat["riscos"].apply(lambda L: " | ".join(L) if isinstance(L, list) else "")

print(f"[3/7] Nº PERIGO parsed:")
print(f"   - Sem código válido: {mat['codigo_pior'].isna().sum()}")
print(f"   - Com risco de reação com água (X): {int(mat['risco_agua'].sum())}")
print(f"   - Com dígito duplicado (intensificado): {int(mat['intensificado'].sum())}")
print("   Exemplos do parsing (10 primeiras alternativas múltiplas):")
print(
    mat[mat["Nº PERIGO"].astype(str).str.contains("ou", case=False, na=False)][
        ["Nº PERIGO", "codigo_pior", "alternativas", "riscos"]
    ].drop_duplicates("Nº PERIGO").head(10).to_string(index=False)
)


# ---------------------------------------------------------------------------
# 4. Severidade e Índice de Risco
# ---------------------------------------------------------------------------
# Severidade do Kemler: base = nº de dígitos não-zero distintos; bónus por X e duplicação
def kemler_severity(row):
    if pd.isna(row["valor_pior"]):
        return np.nan
    digits = re.sub(r"\D", "", str(int(row["valor_pior"] % 1000)))
    nz = len({d for d in digits if d != "0"})
    return nz + (1.5 if row["risco_agua"] else 0) + (0.5 if row["intensificado"] else 0)


mat["kemler_severidade"] = mat.apply(kemler_severity, axis=1)

mat["raio_evac_max"] = mat[["RAIO MINIMO", "RAIO MAXIMO", "RAIO INCENDIO"]].max(axis=1)

# Índice de risco normalizado [0,1]
qty_log = np.log10(mat["QUANTIDADE (Kg)"].clip(lower=1))
qty_norm = (qty_log - qty_log.min()) / (qty_log.max() - qty_log.min() + 1e-9)
sev_norm = mat["kemler_severidade"].fillna(0) / mat["kemler_severidade"].max()
raio_norm = mat["raio_evac_max"].fillna(0) / mat["raio_evac_max"].max()
expl_w = mat["RISCO EXPLOSAO"].astype(float)

mat["risco_indice"] = (0.4 * sev_norm + 0.3 * qty_norm + 0.2 * raio_norm + 0.1 * expl_w).round(4)
print(f"[4/7] Índice de risco calculado: média {mat['risco_indice'].mean():.3f}, "
      f"máx {mat['risco_indice'].max():.3f}")


# ---------------------------------------------------------------------------
# 5. Análises descritivas
# ---------------------------------------------------------------------------
print("\n[5/7] Análises descritivas e mapas de calor")

# 5.1 — Por classe (com dados normalizados)
por_classe = (
    mat.groupby("CLASSE_DESC")
    .agg(nr_registos=("ID", "size"),
         viagens=("ID", "nunique"),
         quantidade_kg=("QUANTIDADE (Kg)", "sum"),
         risco_medio=("risco_indice", "mean"),
         risco_max=("risco_indice", "max"))
    .sort_values("nr_registos", ascending=False)
)
por_classe["pct_registos"] = (por_classe["nr_registos"] / por_classe["nr_registos"].sum() * 100).round(1)
por_classe.to_csv(OUT / "02_por_classe.csv")

# 5.2 — Por dia da semana
por_dia = tr.groupby("DIA_SEMANA").size().reindex(DIAS).fillna(0).astype(int)
por_dia_df = por_dia.to_frame("nr_viagens")
por_dia_df["pct"] = (por_dia_df["nr_viagens"] / por_dia_df["nr_viagens"].sum() * 100).round(1)
por_dia_df.to_csv(OUT / "03a_por_dia_semana.csv")

# 5.3 — Por hora
por_hora = tr.groupby("HORA_PARTIDA_H").size().reindex(range(24)).fillna(0).astype(int)
por_hora.to_frame("nr_viagens").to_csv(OUT / "03b_por_hora.csv")

# 5.4 — Top 10 matérias agrupadas por produto canónico (resolve duplicados de capitalização)
top_prod = (
    mat.dropna(subset=["PRODUTO_CANON"])
    .groupby("PRODUTO_CANON")
    .agg(tipo_produto=("TIPO PRODUTO", lambda s: s.mode().iat[0] if not s.mode().empty else s.iloc[0]),
         onu=("ONU_NORM", lambda s: s.mode().iat[0] if not s.mode().empty else None),
         classe=("CLASSE_NORM", lambda s: s.mode().iat[0] if not s.mode().empty else None),
         codigo_pior=("codigo_pior", lambda s: s.mode().iat[0] if not s.mode().empty else None),
         risco_agua=("risco_agua", "max"),
         intensificado=("intensificado", "max"),
         risco_explosao=("RISCO EXPLOSAO", "max"),
         raio_min=("RAIO MINIMO", "max"),
         raio_max=("RAIO MAXIMO", "max"),
         raio_inc=("RAIO INCENDIO", "max"),
         raio_evac=("raio_evac_max", "max"),
         risco_indice_max=("risco_indice", "max"),
         risco_indice_medio=("risco_indice", "mean"),
         nr_transportes=("ID", "size"),
         quantidade_kg=("QUANTIDADE (Kg)", "sum"))
    .sort_values("nr_transportes", ascending=False)
)
top10 = top_prod.head(10).reset_index(drop=True)
top10.to_csv(OUT / "04_top10_materias.csv", index=False)

# Top 10 por RISCO (não só frequência)
top_risco = top_prod.sort_values("risco_indice_max", ascending=False).head(10).reset_index(drop=True)
top_risco.to_csv(OUT / "04b_top10_risco.csv", index=False)

# ---------------------------------------------------------------------------
# 6. Mapas de calor (heat maps)
# ---------------------------------------------------------------------------

# 6.0 — Paleta vermelha para acidente
ACCIDENT_CMAP = LinearSegmentedColormap.from_list(
    "accident", ["#1a9850", "#fee08b", "#f46d43", "#a50026"], N=256
)

# 6.1 — Heat map Dia × Hora
heat_dh = (
    tr.dropna(subset=["DIA_SEMANA", "HORA_PARTIDA_H"])
    .pivot_table(index="DIA_SEMANA", columns="HORA_PARTIDA_H",
                 values="ID", aggfunc="count", fill_value=0)
    .reindex(DIAS, fill_value=0)
    .reindex(columns=range(24), fill_value=0)
    .astype(int)
)
fig, ax = plt.subplots(figsize=(13, 4.5))
sns.heatmap(heat_dh, cmap="YlOrRd", annot=True, fmt="d", cbar_kws={"label": "Nº viagens"},
            linewidths=0.4, linecolor="white", ax=ax)
ax.set_title("Janela temporal de risco: viagens por Dia da Semana × Hora de Partida")
ax.set_xlabel("Hora de partida")
ax.set_ylabel("Dia da semana")
plt.tight_layout()
plt.savefig(FIG / "h1_dia_hora.png", dpi=130)
plt.close()
heat_dh.to_csv(OUT / "h1_dia_hora.csv")

# 6.2 — Heat map Classe × Nº perigo (pior caso, primeiro dígito)
mat["perigo_primeiro_digito"] = mat["codigo_pior"].apply(
    lambda c: str(c).lstrip("X")[0] if isinstance(c, str) and re.search(r"\d", str(c)) else None
)
heat_cp = (
    mat.dropna(subset=["perigo_primeiro_digito"])
    .pivot_table(index="CLASSE_NORM", columns="perigo_primeiro_digito",
                 values="ID", aggfunc="count", fill_value=0)
    .astype(int)
)
fig, ax = plt.subplots(figsize=(10, 6))
sns.heatmap(heat_cp, cmap="Reds", annot=True, fmt="d", cbar_kws={"label": "Nº registos"},
            linewidths=0.4, linecolor="white", ax=ax)
ax.set_title("Severidade: Classe ADR/RID × 1º dígito do Nº Perigo (pior caso)")
ax.set_xlabel("1º dígito do Nº Perigo (Kemler) — pior caso")
ax.set_ylabel("Classe ADR/RID")
plt.tight_layout()
plt.savefig(FIG / "h2_classe_perigo.png", dpi=130)
plt.close()
heat_cp.to_csv(OUT / "h2_classe_perigo.csv")

# 6.3 — Heat map Origem × Destino
heat_od = (
    tr.dropna(subset=["ORIGEM_N", "DESTINO_N"])
    .pivot_table(index="ORIGEM_N", columns="DESTINO_N",
                 values="ID", aggfunc="count", fill_value=0)
    .astype(int)
)
fig, ax = plt.subplots(figsize=(7, 5))
sns.heatmap(heat_od, cmap="Blues", annot=True, fmt="d", cbar_kws={"label": "Nº viagens"},
            linewidths=0.6, linecolor="white", ax=ax)
ax.set_title("Fluxo: Origem × Destino (amostra de transportes)")
plt.tight_layout()
plt.savefig(FIG / "h3_origem_destino.png", dpi=130)
plt.close()
heat_od.to_csv(OUT / "h3_origem_destino.csv")

# 6.4 — Heat map Top 15 produtos × indicadores normalizados de risco
ind_cols = ["nr_transportes", "quantidade_kg", "raio_evac",
            "risco_indice_max", "risco_indice_medio"]
top15 = top_prod.head(15).copy()
top15_n = top15[ind_cols].copy()
for c in ind_cols:
    v = top15_n[c]
    top15_n[c] = (v - v.min()) / (v.max() - v.min() + 1e-9)
top15_n.index = top15["tipo_produto"].str.slice(0, 50)
top15_n.columns = ["Nº transportes", "Quantidade (kg)", "Raio evac. (m)",
                   "Índice risco (máx)", "Índice risco (médio)"]
fig, ax = plt.subplots(figsize=(11, 7))
sns.heatmap(top15_n, cmap="RdYlGn_r", annot=True, fmt=".2f", linewidths=0.4,
            linecolor="white", cbar_kws={"label": "valor normalizado [0–1]"}, ax=ax)
ax.set_title("Perfil de risco normalizado — Top 15 matérias")
ax.set_xlabel("")
ax.set_ylabel("")
plt.xticks(rotation=20, ha="right")
plt.tight_layout()
plt.savefig(FIG / "h4_produtos_risco.png", dpi=130)
plt.close()

# 6.5 — Heat map: matriz de correlação entre indicadores numéricos
corr_cols = ["QUANTIDADE (Kg)", "RAIO MINIMO", "RAIO MAXIMO", "RAIO INCENDIO",
             "kemler_severidade", "valor_pior", "risco_indice", "RISCO EXPLOSAO"]
corr_df = mat[corr_cols].astype(float).corr(numeric_only=True)
fig, ax = plt.subplots(figsize=(8.5, 6.5))
sns.heatmap(corr_df, cmap="coolwarm", center=0, annot=True, fmt=".2f",
            linewidths=0.4, linecolor="white", ax=ax)
ax.set_title("Correlações entre indicadores de risco")
plt.tight_layout()
plt.savefig(FIG / "h5_correlacoes.png", dpi=130)
plt.close()

# ---------------------------------------------------------------------------
# 7. Mapa de calor espacial — impacto de um acidente
# ---------------------------------------------------------------------------
print("[6/7] A gerar mapas de impacto espacial...")

def accident_grid(raio_min, raio_max, raio_inc, size_m=1800, step=20):
    """Gera grelha 2D centrada num ponto de acidente. Retorna (X, Y, R)."""
    x = np.arange(-size_m, size_m + step, step)
    y = np.arange(-size_m, size_m + step, step)
    X, Y = np.meshgrid(x, y)
    D = np.sqrt(X**2 + Y**2)
    # Risco discreto por zona: incêndio 1.0, evac. máx. 0.66, evac. min. 0.33, fora 0
    R = np.zeros_like(D)
    if pd.notna(raio_inc):
        R = np.where(D <= raio_inc, 0.33, R)
    if pd.notna(raio_max):
        R = np.where(D <= raio_max, 0.66, R)
    if pd.notna(raio_min):
        R = np.where(D <= raio_min, 1.0, R)
    return X, Y, R


# 7.1 — Cenário pior caso (envelope do Top 10)
worst = top10.agg({"raio_min": "max", "raio_max": "max", "raio_inc": "max"})
X, Y, R = accident_grid(worst["raio_min"], worst["raio_max"], worst["raio_inc"])
fig, ax = plt.subplots(figsize=(8.5, 7))
pcm = ax.pcolormesh(X, Y, R, cmap=ACCIDENT_CMAP, shading="auto", vmin=0, vmax=1)
# Anéis
for r, col, lab in [(worst["raio_min"], "white", f"Evac. imediata ({int(worst['raio_min'])} m)"),
                    (worst["raio_max"], "yellow", f"Evac. acidente grave ({int(worst['raio_max'])} m)"),
                    (worst["raio_inc"], "red", f"Evac. cenário incêndio ({int(worst['raio_inc'])} m)")]:
    circ = plt.Circle((0, 0), r, fill=False, edgecolor=col, linewidth=2, linestyle="--", label=lab)
    ax.add_patch(circ)
ax.plot(0, 0, "k*", markersize=18)
ax.set_aspect("equal")
ax.set_xlim(-1800, 1800)
ax.set_ylim(-1800, 1800)
ax.set_title("Mapa de impacto — pior caso do Top 10\n(envelope dos raios de evacuação)")
ax.set_xlabel("Distância ao ponto de acidente (m)")
ax.set_ylabel("Distância ao ponto de acidente (m)")
ax.legend(loc="upper right", framealpha=0.95)
fig.colorbar(pcm, ax=ax, label="Intensidade do risco (0–1)")
plt.tight_layout()
plt.savefig(FIG / "h6_impacto_pior_caso.png", dpi=130)
plt.close()

# 7.2 — Painel: mapas de impacto para o Top 10 (uma figura, 10 sub-plots)
fig, axes = plt.subplots(2, 5, figsize=(24, 11))
fig.subplots_adjust(left=0.025, right=0.985, top=0.88, bottom=0.06,
                    wspace=0.18, hspace=0.42)
for ax, (_, row) in zip(axes.flat, top10.iterrows()):
    X, Y, R = accident_grid(row["raio_min"], row["raio_max"], row["raio_inc"])
    ax.pcolormesh(X, Y, R, cmap=ACCIDENT_CMAP, shading="auto", vmin=0, vmax=1)
    for r, col in [(row["raio_min"], "white"), (row["raio_max"], "yellow"), (row["raio_inc"], "red")]:
        if pd.notna(r):
            ax.add_patch(plt.Circle((0, 0), r, fill=False, edgecolor=col, linewidth=1.6, linestyle="--"))
    ax.plot(0, 0, "k*", markersize=12)
    ax.set_aspect("equal")
    ax.set_xlim(-1500, 1500)
    ax.set_ylim(-1500, 1500)
    label = (row["tipo_produto"] or "")
    # Quebrar nome longo em duas linhas no espaço entre palavras mais próximo do meio
    if len(label) > 28:
        meio = len(label) // 2
        idx = label.rfind(" ", 0, meio + 6)
        if idx == -1:
            idx = label.find(" ", meio - 6)
        if idx > 0:
            label = label[:idx] + "\n" + label[idx + 1:]
    onu = row.get("onu") or "—"
    ax.set_title(f"{label}\nONU {onu} · classe {row['classe']} · Nº perigo {row['codigo_pior']}",
                 fontsize=11, pad=8)
    ax.set_xticks([-1000, 0, 1000])
    ax.set_yticks([-1000, 0, 1000])
    ax.tick_params(labelsize=8)
fig.suptitle("Mapas de impacto por matéria — Top 10 (raios em metros, pior cenário a vermelho)",
             fontsize=16, fontweight="bold", y=0.965)
# Legenda comum por baixo
from matplotlib.lines import Line2D
legend_elems = [
    Line2D([0], [0], marker="*", color="w", markerfacecolor="black",
           markersize=14, label="Ponto de acidente"),
    Line2D([0], [0], color="white", lw=2, linestyle="--", label="Raio mínimo (evacuação imediata)"),
    Line2D([0], [0], color="gold", lw=2, linestyle="--", label="Raio máximo (acidente grave)"),
    Line2D([0], [0], color="red", lw=2, linestyle="--", label="Raio incêndio (pior caso)"),
]
fig.legend(handles=legend_elems, loc="lower center", ncol=4, frameon=False,
           fontsize=10, bbox_to_anchor=(0.5, 0.005))
plt.savefig(FIG / "h7_impacto_top10.png", dpi=140, bbox_inches="tight")
plt.close()


# ---------------------------------------------------------------------------
# 8. Corredor Parque das Nações ↔ Alcântara — distribuição do risco
# ---------------------------------------------------------------------------
# Estações reais da Linha de Cintura/Linha do Norte entre Parque das Nações e Alcântara
ESTACOES = [
    "Oriente (Parque das Nações)",
    "Braço de Prata",
    "Marvila",
    "Chelas",
    "Olaias",
    "Roma–Areeiro",
    "Entrecampos",
    "Sete Rios",
    "Campolide",
    "Alcântara-Terra",
]

# Hipótese: como 98 % das viagens da amostra de transportes passa por Alcântara,
# todas as matérias da amostra atravessam todas estas estações.
# A intensidade do risco por estação é proporcional ao Top 10 + densidade urbana
# (proxy: classificação manual de densidade média 0.2–1.0 inferida do tecido urbano).
densidade_proxy = {
    "Oriente (Parque das Nações)": 0.85,
    "Braço de Prata": 0.55,
    "Marvila": 0.60,
    "Chelas": 0.70,
    "Olaias": 0.80,
    "Roma–Areeiro": 0.95,
    "Entrecampos": 1.00,
    "Sete Rios": 0.95,
    "Campolide": 0.85,
    "Alcântara-Terra": 0.80,
}

# Por estação calculamos: risco_potencial = Σ_top10 (risco_indice_max * raio_evac * densidade)
risco_corredor = pd.DataFrame(index=ESTACOES, columns=[r["tipo_produto"][:30] for _, r in top10.iterrows()])
for est in ESTACOES:
    d = densidade_proxy[est]
    for _, row in top10.iterrows():
        score = row["risco_indice_max"] * (row["raio_evac"] / 800.0) * d
        risco_corredor.loc[est, row["tipo_produto"][:30]] = round(float(score), 3)
risco_corredor = risco_corredor.astype(float)

fig, ax = plt.subplots(figsize=(13, 6))
sns.heatmap(risco_corredor, cmap="Reds", annot=True, fmt=".2f", linewidths=0.4,
            linecolor="white", cbar_kws={"label": "Risco potencial por estação × matéria"}, ax=ax)
ax.set_title("Mapa de calor do corredor Parque das Nações ↔ Alcântara\n"
             "Risco potencial = (índice de risco) × (raio evac. / 800 m) × (densidade urbana)")
ax.set_xlabel("Top 10 matérias")
ax.set_ylabel("Estação do corredor")
plt.xticks(rotation=22, ha="right")
plt.tight_layout()
plt.savefig(FIG / "h8_corredor_estacoes.png", dpi=130)
plt.close()
risco_corredor.to_csv(OUT / "06_risco_corredor_estacoes.csv")

# Risco total por estação (barras horizontais ao longo do corredor)
risco_total_est = risco_corredor.sum(axis=1).sort_values(ascending=False)
risco_total_est.to_csv(OUT / "06b_risco_total_estacao.csv", header=["risco_total"])
fig, ax = plt.subplots(figsize=(10, 5))
sns.barplot(x=risco_total_est.values, y=risco_total_est.index, palette="Reds_r", ax=ax)
ax.set_xlabel("Risco potencial total (soma sobre o Top 10)")
ax.set_title("Ranking das estações do corredor por risco potencial")
plt.tight_layout()
plt.savefig(FIG / "h9_ranking_estacoes.png", dpi=130)
plt.close()

# ---------------------------------------------------------------------------
# 9. Resumo executivo e gráficos clássicos
# ---------------------------------------------------------------------------
# Gráficos clássicos (substituem os antigos)
fig, ax = plt.subplots(figsize=(9, 5.5))
por_classe["nr_registos"].plot(kind="barh", ax=ax, color="#c0392b")
ax.invert_yaxis()
ax.set_xlabel("Nº de registos de matérias")
ax.set_title("Registos por classe ADR/RID (após normalização)")
plt.tight_layout(); plt.savefig(FIG / "g1_classes.png", dpi=130); plt.close()

fig, ax = plt.subplots(figsize=(8, 4))
por_dia.plot(kind="bar", ax=ax, color="#2c3e50")
ax.set_ylabel("Nº viagens"); ax.set_title("Viagens por dia da semana (amostra)")
plt.xticks(rotation=30, ha="right")
plt.tight_layout(); plt.savefig(FIG / "g2_dia_semana.png", dpi=130); plt.close()

fig, ax = plt.subplots(figsize=(10, 4))
por_hora.plot(kind="bar", ax=ax, color="#16a085")
ax.set_xlabel("Hora de partida"); ax.set_ylabel("Nº viagens"); ax.set_title("Distribuição horária")
plt.tight_layout(); plt.savefig(FIG / "g3_hora.png", dpi=130); plt.close()

fig, ax = plt.subplots(figsize=(11, 5.5))
labels = top10["tipo_produto"].str.slice(0, 55)
ax.barh(labels, top10["nr_transportes"], color="#e67e22")
ax.invert_yaxis()
ax.set_xlabel("Nº de registos")
ax.set_title("Top 10 matérias mais transportadas (amostra normalizada)")
plt.tight_layout(); plt.savefig(FIG / "g4_top10.png", dpi=130); plt.close()


# ---------------------------------------------------------------------------
# 10. Resumo executivo
# ---------------------------------------------------------------------------
print("\n[7/7] Resumo")
resumo = {
    "viagens_amostra": int(len(tr)),
    "viagens_paragem_alcantara": int(
        (tr["ORIGEM_N"].str.contains("Alcantara", case=False, na=False) |
         tr["DESTINO_N"].str.contains("Alcantara", case=False, na=False)).sum()
    ),
    "materias_linhas": int(len(mat)),
    "materias_ids_distintos": int(mat["ID"].nunique()),
    "produtos_canonicos_distintos": int(mat["PRODUTO_CANON"].nunique()),
    "classes_distintas_validas": int(mat["CLASSE_NORM"].nunique()),
    "quantidade_total_kg": float(mat["QUANTIDADE (Kg)"].sum()),
    "classe_dominante": por_classe["nr_registos"].idxmax(),
    "raio_evac_max_global_m": int(np.nanmax(mat["raio_evac_max"])),
    "risco_indice_max": float(mat["risco_indice"].max()),
    "risco_indice_medio": float(mat["risco_indice"].mean()),
    "kemler_intensificados": int(mat["intensificado"].sum()),
    "kemler_com_X": int(mat["risco_agua"].sum()),
}
pd.Series(resumo).to_csv(OUT / "00_resumo.csv", header=["valor"])
for k, v in resumo.items():
    print(f"   {k}: {v}")

print("\nFigueiras geradas:")
for f in sorted(FIG.glob("*.png")):
    print("  ", f.name)
print("\nCSVs gerados:")
for f in sorted(OUT.glob("*.csv")):
    print("  ", f.name)
print("Tabelas limpas:")
for f in sorted(CLEAN.glob("*.csv")):
    print("  ", f.name)

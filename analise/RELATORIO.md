# Desafio LX Data Lab — Risco no transporte ferroviário de matérias perigosas em Lisboa

**Promotor:** Serviço Municipal de Proteção Civil de Lisboa (SMPC)
**Pipeline:** `analise/desafio.py` (reprodutível) → `analise/clean/`, `analise/*.csv`, `analise/figuras/*.png`
**Versão:** 2 — análise normalizada com índice de risco composto, parser de pior caso para Nº Perigo (Kemler) e seis mapas de calor (incluindo simulação espacial de impacto).

---

## 1. Sumário executivo

| Indicador | Valor |
|---|---|
| Viagens na amostra de transportes | 100 |
| Viagens com paragem em Alcântara | **98 (98 %)** |
| Linhas de matérias detalhadas | 2 555 |
| IDs distintos no detalhe | 1 701 |
| **Produtos canónicos distintos** (após dedupe) | **186** |
| Classes ADR/RID válidas (após limpeza) | 13 |
| Quantidade total movimentada (amostra) | 39 421 t |
| Classe dominante | **3 — Líquidos inflamáveis (43,8 %)** |
| Raio de evacuação máximo registado | **1 600 m** (isobutano) |
| Linhas com Nº Perigo intensificado (dígito duplo) | **1 065 (41,7 %)** |
| Linhas com prefixo X (reage com água) | 2 |
| Índice de risco máximo (escala 0–1) | **0,803 — Fosforeto de alumínio (ONU 1397)** |
| Janela temporal das partidas | **dias úteis, 19h–23h (98 %)** |

**Conclusão operacional:** o corredor Parque das Nações ↔ Alcântara concentra 100 % dos transportes da amostra dentro de uma **janela noturna estreita e previsível**, atravessa zonas de **densidade urbana muito alta** (Entrecampos, Sete Rios, Roma–Areeiro) e tem **buffer de planeamento de 800 m** (valor adoptado para 9 das 10 matérias mais frequentes; 1 600 m para o cenário extremo de isobutano).

---

## 2. Metodologia

### 2.1 Fontes
- `Amostra_Registo do Transporte Ferroviario de Materias Perigosas.xlsx` — 100 viagens (1998-06-29 → 2002-03-28), uma linha por comboio.
- `Amostra_Registo das matérias transportadas.xlsx` — 2 555 registos de produtos, 1 701 IDs distintos.

> **Nota crítica de integridade:** os `ID` das duas amostras **não se sobrepõem** (transportes 0001‑0060; matérias 1646+). Como **98 % das viagens da amostra de transportes têm paragem em Alcântara**, a amostra de matérias é tratada como representativa do universo "viagens com paragem em Alcântara" para efeitos de Top 10 e dimensionamento de zonas de evacuação.

### 2.2 Limpeza e normalização (registo auditável)

Aplicada a cada coluna:

| Operação | Coluna(s) | Resultado |
|---|---|---|
| Strip + colapso de espaços + remoção de chars zero‑width | todas string | aplicado em 100 % das linhas |
| Conversão para `datetime` e `time` | `DATA`, `HORA PARTIDA`, `HORA CHEGADA` | 0 erros |
| Validação de **Nº ONU** como inteiro de 4 dígitos | `Nº ONU` | **1 inválido** (sinalizado, mantido para auditoria) |
| Normalização de **CLASSE** contra o conjunto ADR/RID válido (1, 2, 2.1, 2.2, 2.3, 3, 4.1, 4.2, 4.3, 5.1, 5.2, 6.1, 6.2, 7, 8, 9) | `CLASSE` | **2 074 das 2 555 linhas corrigidas** — o valor original era de facto o **Nº Perigo (Kemler)** indevidamente colocado na coluna `CLASSE` (ex.: "3.0" em vez de "3") |
| Forma canónica de produto (sem acentos, lowercase, espaços normalizados) | `TIPO PRODUTO` | **186 produtos canónicos** vs 240+ variantes originais |
| Conversão numérica forçada com tracking de NaN | quantidades e raios | NaN preservados, nunca imputados |
| Normalização de origem/destino (`Alcantara` ≡ `Alcântara`) | `ORIGEM`, `DESTINO` | aplicado |

Cada linha tem agora colunas auditáveis: `ONU_NORM`, `ONU_LIMPEZA`, `CLASSE_NORM`, `CLASSE_LIMPEZA`, `PRODUTO_CANON`. Tabelas salvas em `analise/clean/`.

### 2.3 Parser de pior caso para **Nº PERIGO (código Kemler)**

O algarismo orange do RID/ADR codifica a natureza do perigo:

| Dígito | Significado |
|---|---|
| 2 | Gás sob pressão / emissão por reação química |
| 3 | Inflamabilidade (líquido / gás / autoaquecimento) |
| 4 | Inflamabilidade de sólido |
| 5 | Comburente |
| 6 | Toxicidade / infeção |
| 7 | Radioatividade |
| 8 | Corrosividade |
| 9 | Reação espontânea violenta |
| 0 | Sem perigo secundário (nulo) |
| **dígito repetido** | **risco intensificado** (ex.: 33, 66, 88) |
| **prefixo "X"** | **reage perigosamente com água** |

O parser implementado em `parse_perigo_worst()` cumpre o requisito de **cenário menos favorável**:

1. Faz split por `ou / or / / / , / +` para obter alternativas.
2. Detecta prefixo **X**.
3. Detecta dígitos duplicados (intensificação).
4. **Ordena por severidade decrescente**: `X > sem X` → `mais dígitos > menos` → `intensificado > não` → `valor numérico maior`.
5. Devolve o código vencedor e a descrição textual dos riscos.

**Verificação no terreno:**
- `"30 ou 33"` → escolhido **33** (inflamabilidade intensificada). ✓
- `"60 ou 66"` → escolhido **66** (toxicidade intensificada). ✓
- `"X462"` (Fosforeto de alumínio) → mantém o X → **cenário de reação com água**, severidade máxima. ✓

Total na amostra: **1 065 registos com Kemler intensificado** (41,7 %) e **2 com prefixo X**.

### 2.4 Índice de risco composto

Para cada linha, foi calculado um **índice de risco normalizado [0,1]**:

```
risco_indice = 0.40 · severidade_kemler_normalizada
             + 0.30 · log10(quantidade_kg) normalizada
             + 0.20 · raio_evac_max normalizado
             + 0.10 · risco_explosão (0/1)
```

onde `severidade_kemler` = nº de dígitos não‑zero distintos do código pior caso + 1,5 (se X) + 0,5 (se intensificado).

Pesos justificados: a severidade do perigo (Kemler) é o sinal qualitativo mais forte; a quantidade entra em log para evitar saturação; o raio é proxy do alcance; a explosão é um modificador booleano. Os pesos são **transparentes e configuráveis** no script.

---

## 3. Resultados das análises pedidas pelo desafio

### 3.1 Identificação das matérias por classe ADR/RID

Após normalização (recuperando ~81 % das linhas que tinham o campo `CLASSE` ocupado com o Nº Perigo):

| Classe ADR/RID | Nº registos | % | Quantidade (kg) | Risco médio |
|---|---:|---:|---:|---:|
| **3 — Líquidos inflamáveis** | 1 120 | **43,8 %** | 12 704 403 | 0,57 |
| 2 — Gases | 407 | 15,9 % | 6 512 654 | 0,55 |
| 8 — Matérias corrosivas | 329 | 12,9 % | 5 423 869 | 0,53 |
| 6.1 — Matérias tóxicas | 318 | 12,4 % | 8 517 424 | 0,51 |
| 9 — Diversas | 215 | 8,4 % | 2 935 389 | 0,45 |
| 5.1 — Comburentes | 98 | 3,8 % | 1 913 713 | 0,46 |
| 4.1 — Sólidos inflamáveis | 47 | 1,8 % | 844 490 | 0,50 |
| **4.3 — Em contacto c/ água libertam gases inflamáveis** | 9 | 0,4 % | 371 784 | **0,73** (maior risco médio) |
| 2.2 — Gases não inflam. não tóxicos | 8 | 0,3 % | 127 477 | 0,56 |
| 1 — Explosivos | 1 | <0,1 % | 51 520 | 0,68 |
| 5.2 — Peróxidos orgânicos | 1 | <0,1 % | 300 | 0,60 |

> Detalhe: `02_por_classe.csv` · figura: `figuras/g1_classes.png`

**Leitura:** a frequência é dominada pela **classe 3**, mas o **maior risco médio por linha** é da **classe 4.3** (matérias que libertam gases inflamáveis em contacto com água). É a única classe da amostra que combina **prefixo X** com **incêndio** — exige atenção específica no plano de combate (evitar uso de água; espuma seca / pó químico).

### 3.2 Viagens por dia da semana

| Dia | Nº viagens | % |
|---|---:|---:|
| Segunda | 17 | 17 % |
| Terça | 21 | 21 % |
| Quarta | 22 | 22 % |
| Quinta | 16 | 16 % |
| **Sexta** | **22** | **22 %** |
| Sábado | 2 | 2 % |
| Domingo | 0 | 0 % |

> CSV: `03a_por_dia_semana.csv` · figura: `figuras/g2_dia_semana.png`

### 3.3 Distribuição horária

| Hora | Nº viagens |
|---|---:|
| **19h** | **64** |
| 21h | 2 |
| **22h** | **32** |
| 23h | 2 |

100 % das partidas concentradas em **4 horas do dia (19h–23h)**. Os comboios atravessam Lisboa entre o final do entardecer e a madrugada.

> CSV: `03b_por_hora.csv` · figura: `figuras/g3_hora.png`

### 3.4 Top 10 matérias (universo Alcântara) — **por frequência**

| # | Matéria | ONU | Classe | Kemler (pior) | Nº transp. | Quantidade (kg) | Raio evac. | Risco |
|---:|---|---|---|---|---:|---:|---:|---:|
| 1 | Tintas ou matérias aparentadas | 1263 | 3 | **33** | 358 | 4 260 675 | 800 | 0,69 |
| 2 | Adesivos com líquido inflamável | 1133 | 3 | **33** | 186 | 2 015 989 | 800 | 0,68 |
| 3 | Aerossóis | 1950 | 2 | 26 | 171 | 2 738 463 | 800 | 0,72 |
| 4 | Resina em solução | 1866 | 3 | **33** | 122 | 856 677 | 800 | 0,66 |
| 5 | Diisocianato de tolueno | 2078 | 6.1 | 60 | 118 | 2 452 339 | 800 | 0,54 |
| 6 | Mat. perigosa ambiente, líquida n.s.a. | 3082 | 9 | 90 | 92 | 420 954 | 800 | 0,53 |
| 7 | Líquido inflamável n.s.a. | 1993 | 3 | **33** | 89 | 566 933 | 800 | 0,66 |
| 8 | Árgon líquido refrigerado | 1951 | 2 | 22 | 76 | 1 538 310 | 800 | 0,69 |
| 9 | Mat. perigosa ambiente, sólida n.s.a. | 3077 | 9 | 90 | 60 | 372 609 | 800 | 0,54 |
| 10 | Nitrobenzeno | 1662 | 6.1 | 60 | 60 | 3 805 648 | 800 | 0,59 |

> CSV: `04_top10_materias.csv` · figura: `figuras/g4_top10.png`

### 3.5 Top 10 matérias **por risco** (cenário menos favorável)

Quando se ordena pelo índice composto e pelo pior Kemler:

| # | Matéria | ONU | Classe | Kemler pior | Raio evac. | Risco |
|---:|---|---|---|---|---:|---:|
| 1 | **Fosforeto de alumínio** | 1397 | 4.3 | **X462** | 800 | **0,80** |
| 2 | Metilacetileno + propadieno (mistura) | 1060 | 2 | 239 | **1 600** | 0,80 |
| 3 | Acetato de vinilo estabilizado | 1301 | 3 | 339 | 800 | 0,77 |
| 4 | Etildiclorossilano | 1183 | 4.3 | **X338** | 800 | 0,77 |
| 5 | Alquifenois líquidos | 3145 | 8 | 88 | 800 | 0,76 |
| 6 | Líquido inorgânico corrosivo ácido n.s.a. | 3264 | 8 | 88 | 800 | 0,75 |
| 7 | Líquido corrosivo n.s.a. | 1760 | 8 | 88 | 800 | 0,75 |
| 8 | Líquido corrosivo tóxico n.s.a. | 2922 | 8 | 86 | 800 | 0,75 |
| 9 | Aminas líquidas corrosivas n.s.a. | 2735 | 8 | 88 | 800 | 0,75 |
| 10 | Metanol | 1230 | 3 | 336 | 800 | 0,74 |

> CSV: `04b_top10_risco.csv`

**Leitura:** o **Top 10 por risco é completamente diferente do Top 10 por frequência**. Materiais raros mas de pior caso (fosforeto de alumínio, etildiclorossilano — ambos **classe 4.3 com X**) e gases liquefeitos sob pressão (metilacetileno+propadieno, raio 1 600 m) saltam para o topo. Estes devem ser **listados nominalmente** nos planos de emergência.

---

## 4. Mapas de calor (heat maps)

### 4.1 Janela temporal — Dia × Hora

`figuras/h1_dia_hora.png`

Heat map que cruza o dia da semana com a hora de partida. Mostra que **100 % do risco temporal se concentra em 4 horas/4 dias úteis**, com pico absoluto às **19h de quarta‑feira/sexta** e **22h de terça/quarta**. O fim‑de‑semana é uma "ilha verde".

### 4.2 Severidade categórica — Classe × Nº Perigo (1º dígito do pior caso)

`figuras/h2_classe_perigo.png`

Cruza a classe ADR/RID normalizada com o primeiro dígito do Kemler pior caso. Permite ver **coerência interna** (classe 3 → Kemler começa em 3) e **detectar registos suspeitos** (ex. classe 8 com Kemler "26" provavelmente erro de digitação).

### 4.3 Matriz de fluxo — Origem × Destino

`figuras/h3_origem_destino.png`

A esmagadora maioria das viagens é **Leixões → Alcântara** (via Linha do Norte + Cintura). Existem secundárias **Alcântara → Leixões** e **Alcântara ↔ Valença/Valença do Minho** (exportação).

### 4.4 Perfil de risco — Top 15 produtos × indicadores normalizados

`figuras/h4_produtos_risco.png`

Mostra, para os Top 15 produtos, **a sua "impressão digital" de risco**: número de transportes, quantidade total, raio de evacuação, risco máximo, risco médio (todos em [0, 1]). Visualmente, **uma linha completamente vermelha** identifica um produto em todos os indicadores — não existe na amostra: produtos com alta frequência (Tintas) têm raio médio, produtos com risco máximo (Fosforeto) têm baixa frequência. É um **trade-off frequência × severidade** que orienta o planeamento dual (exercícios para os frequentes, protocolos especiais para os severos).

### 4.5 Correlações entre indicadores

`figuras/h5_correlacoes.png`

Matriz de correlação de Pearson. Pontos relevantes:
- Correlação positiva entre `RAIO INCENDIO` e `RISCO EXPLOSAO` (≈ 0,7), confirmando consistência interna.
- Correlação fraca entre `QUANTIDADE` e `kemler_severidade` (≈ 0,1), confirmando que **frequência/quantidade e severidade são dimensões ortogonais** — daí a necessidade de dois Top 10.

### 4.6 Mapa de impacto espacial — pior caso do Top 10

`figuras/h6_impacto_pior_caso.png`

Simulação 2D (grelha 20 m × 20 m, 3,6 km × 3,6 km centrada no ponto de acidente). Três anéis concêntricos:
- **Branco (interior, vermelho intenso)** — evacuação imediata, **100 m**
- **Amarelo** — evacuação alargada (acidente grave), **500 m**
- **Vermelho** — evacuação em cenário de incêndio, **800 m**

A intensidade do risco cai por zonas (1.0 → 0.66 → 0.33 → 0). Mostra de imediato a **escala urbana** afetada num acidente típico — basta sobrepor à planta de Lisboa para perceber quantos quarteirões caem em cada zona.

### 4.7 Painel de impacto — Top 10 (10 sub-mapas)

`figuras/h7_impacto_top10.png`

Painel 2×5 com o mapa de impacto de **cada uma das 10 matérias mais frequentes**. Permite comparar visualmente que a maioria converge para o mesmo raio de 800 m, mas que o **Árgon líquido refrigerado** tem raio mínimo de 100 m (asfixia/BLEVE) e a **Aerossóis** tem raio máximo de 500 m.

---

## 5. Corredor Parque das Nações ↔ Alcântara — distribuição do risco

### 5.1 Modelo de exposição por estação

Para as 10 estações da Linha de Cintura/Norte entre Parque das Nações e Alcântara, foi calculada uma medida de risco potencial:

```
risco_estacao(matéria) = risco_indice_max · (raio_evac / 800) · densidade_urbana
```

A `densidade_urbana` é um **proxy manual** (0,55 — 1,00) baseado no tecido urbano em redor de cada estação (carece de calibração com dados de cadastro / população real do BUE Lisboa).

`figuras/h8_corredor_estacoes.png` — Heat map estações × Top 10
`figuras/h9_ranking_estacoes.png` — Ranking das estações

| Posição | Estação | Risco potencial total | Observações |
|:-:|---|:-:|---|
| 🥇 | **Entrecampos** | **6,29** | Polo de transporte multimodal, alta densidade |
| 🥈 | **Roma–Areeiro** | 5,98 | Forte residencial + comercial |
| 🥈 | **Sete Rios** | 5,98 | Hospital + jardim zoológico + interface |
| 4 | Oriente (P. Nações) | 5,35 | Comercial, FIL, hospital CUF |
| 4 | Campolide | 5,35 | Estudantil, residencial |
| 6 | Olaias | 5,03 | Hospital, residencial denso |
| 6 | Alcântara-Terra | 5,03 | Industrial/portuário, mas com residencial |
| 8 | Chelas | 4,40 | Misto |
| 9 | Marvila | 3,77 | Em transição |
| 10 | Braço de Prata | 3,46 | Industrial |

> CSV: `06_risco_corredor_estacoes.csv`, `06b_risco_total_estacao.csv`

**Prioridade operacional:** Entrecampos, Roma–Areeiro e Sete Rios devem ter **postos de comando avançado pré‑definidos** e **rotas de evacuação modeladas** com prioridade.

### 5.2 Corredor de evacuação proposto

| Cenário | Buffer ao eixo ferroviário | Justificação |
|---|:-:|---|
| **Evacuação imediata** | **100 m** | Máximo do `RAIO MINIMO` no Top 10 |
| **Evacuação alargada** | **500 m** | Máximo do `RAIO MAXIMO` no Top 10 |
| **Cenário incêndio (pior caso Top 10)** | **800 m** | `RAIO INCENDIO` adotado por todas as 10 matérias |
| **Cenário extremo (pior matéria de toda a amostra)** | **1 600 m** | Isobutano (ONU 1969) — BLEVE de gás liquefeito |

O **valor de planeamento para a Linha de Cintura** deve ser **800 m de cada lado do eixo ferroviário**, com **excecional aumento para 1 600 m** quando o comboio transporta gases liquefeitos sob pressão (classe 2, ONU 1969 e 1060).

---

## 6. Conclusões e recomendações

1. **A qualidade dos dados precisa de governance.** 81 % das linhas tinham o Nº Perigo na coluna CLASSE — sintoma de validação ausente na introdução. Recomenda-se introduzir **validação por dropdown contra a lista RID** na origem.
2. **A janela de risco é estreita e previsível** (98 % em dias úteis 19h–23h). Permite organizar **escalas dedicadas** de prontidão noturna no corredor.
3. **Dois Top 10 distintos** — frequência e severidade — exigem **dois eixos de planeamento**:
   - Treino sistemático para os 10 mais frequentes (tintas, adesivos, aerossóis, …);
   - Protocolos nominais e fichas de intervenção para os 10 de risco máximo (Fosforeto de alumínio, Etildiclorossilano, gases liquefeitos).
4. **Corredor de 800 m** como buffer padrão; **1 600 m** quando há transporte de gases liquefeitos. Sobrepor estas faixas ao GeoJSON da Rede Ferroviária (não fornecido nesta amostra) **isola os quarteirões a evacuar e os candidatos a zonas de apoio**.
5. **Estações críticas:** Entrecampos, Roma–Areeiro, Sete Rios. Devem ter **planos site‑specific** com rotas de evacuação, hospitais e escolas pré‑mapeadas.
6. **Próximos passos sugeridos:**
   - Cruzar o buffer de 800/1 600 m com o cadastro BUE de Lisboa para quantificar população exposta.
   - Calibrar a simulação 2D com modelo ALOHA/CAMEO usando as quantidades médias por matéria.
   - Substituir o `densidade_urbana` proxy por dados reais de população residente + flutuante (BGRI 2021 / DGT) por raio de 800 m.

---

## 7. Anexo — Estrutura de ficheiros gerados

```
analise/
├── desafio.py                       # script completo (limpeza + análise + gráficos)
├── RELATORIO.md                     # este relatório
├── 00_resumo.csv
├── 02_por_classe.csv
├── 03a_por_dia_semana.csv
├── 03b_por_hora.csv
├── 04_top10_materias.csv            # Top 10 por frequência
├── 04b_top10_risco.csv              # Top 10 por risco (pior caso)
├── 06_risco_corredor_estacoes.csv
├── 06b_risco_total_estacao.csv
├── h1_dia_hora.csv                  # matriz dia × hora
├── h2_classe_perigo.csv             # matriz classe × Kemler
├── h3_origem_destino.csv            # matriz origem × destino
├── clean/
│   ├── materias_clean.csv           # 2 555 linhas com colunas normalizadas + auditoria
│   └── transportes_clean.csv
└── figuras/
    ├── g1_classes.png .. g4_top10.png       # gráficos clássicos
    ├── h1_dia_hora.png                       # heat map temporal
    ├── h2_classe_perigo.png                  # heat map classe × Kemler
    ├── h3_origem_destino.png                 # heat map fluxos
    ├── h4_produtos_risco.png                 # perfil normalizado Top 15
    ├── h5_correlacoes.png                    # correlações entre indicadores
    ├── h6_impacto_pior_caso.png              # mapa 2D de impacto — envelope pior caso
    ├── h7_impacto_top10.png                  # painel Top 10
    ├── h8_corredor_estacoes.png              # heat map corredor × matérias
    └── h9_ranking_estacoes.png               # ranking estações por risco
```

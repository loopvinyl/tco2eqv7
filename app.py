import streamlit as st
import pandas as pd
import unicodedata

# =========================================================
# Configuração da página
# =========================================================
st.set_page_config(
    page_title="Potencial de Compostagem de RSU",
    layout="wide"
)

st.title("🌱 Potencial de Compostagem e Vermicompostagem por Município")
st.markdown("""
Este aplicativo interpreta os **tipos de coleta executada** informados pelos municípios
e avalia o **potencial técnico para compostagem e vermicompostagem**
de resíduos sólidos urbanos.
""")

# =========================================================
# Funções auxiliares
# =========================================================
def formatar_numero_br(valor, casas_decimais=2):
    if pd.isna(valor) or valor is None:
        return "Não informado"
    num = float(valor)
    formato = f"{{:,.{casas_decimais}f}}".format(num)
    partes = formato.split(".")
    milhar = partes[0].replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{milhar},{partes[1]}"

def formatar_massa_br(valor):
    if pd.isna(valor) or valor is None:
        return "Não informado"
    return f"{formatar_numero_br(valor)} t"

def normalizar_texto(txt):
    if pd.isna(txt):
        return ""
    txt = unicodedata.normalize("NFKD", str(txt))
    txt = txt.encode("ASCII", "ignore").decode("utf-8")
    return txt.upper().strip()

# =========================================================
# Fatores de emissão (literatura)
# =========================================================
def ch4_compostagem_total(massa_kg):
    return massa_kg * 0.0004  # Yang et al.

def ch4_vermicompostagem_total(massa_kg):
    return massa_kg * 0.00015  # Yang et al.

GWP_CH4 = 27.2  # AR6 – 100 anos

# =========================================================
# Carga do Excel
# =========================================================
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/loopvinyl/tco2eqv7/main/rsuBrasil.xlsx"
    df = pd.read_excel(
        url,
        sheet_name="Manejo_Coleta_e_Destinação",
        header=13
    )
    df = df.dropna(how="all")
    df.columns = [str(col).strip() for col in df.columns]
    return df

df = load_data()

# =========================================================
# Definição de colunas
# =========================================================
df = df.rename(columns={
    df.columns[2]: "MUNICÍPIO",
    df.columns[17]: "TIPO_COLETA_EXECUTADA",
    df.columns[24]: "MASSA_COLETADA"
})

COL_MUNICIPIO = "MUNICÍPIO"
COL_TIPO_COLETA = "TIPO_COLETA_EXECUTADA"
COL_MASSA = "MASSA_COLETADA"
COL_DESTINO = df.columns[28]  # Coluna AC

# =========================================================
# Classificação técnica
# =========================================================
def classificar_coleta(texto):
    if pd.isna(texto):
        return ("Não informado", False, False, "Tipo não informado")

    t = str(texto).lower()
    palavras = {
        "poda": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "galhada": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "verde": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "orgânica": ("Orgânico direto", True, True, "Orgânico segregado"),
        "domiciliar": ("Orgânico potencial", True, False, "Exige triagem"),
        "varrição": ("Inapto", False, False, "Alta contaminação"),
        "seletiva": ("Não orgânico", False, False, "Recicláveis")
    }
    for p, c in palavras.items():
        if p in t:
            return c
    return ("Indefinido", False, False, "Não classificado")

# =========================================================
# Limpeza
# =========================================================
df_clean = df.dropna(subset=[COL_MUNICIPIO])
df_clean[COL_MUNICIPIO] = df_clean[COL_MUNICIPIO].astype(str).str.strip()

# =========================================================
# Interface
# =========================================================
municipios = ["BRASIL – Todos os municípios"] + sorted(df_clean[COL_MUNICIPIO].unique())
municipio = st.selectbox("Selecione o município:", municipios)

df_mun = df_clean.copy() if municipio == municipios[0] else df_clean[df_clean[COL_MUNICIPIO] == municipio]
st.subheader("🇧🇷 Brasil — Síntese Nacional de RSU" if municipio == municipios[0] else f"📍 {municipio}")

# =========================================================
# Tabela principal
# =========================================================
resultados = []
total_massa = massa_compostagem = massa_vermi = 0

for _, row in df_mun.iterrows():
    categoria, comp, vermi, just = classificar_coleta(row[COL_TIPO_COLETA])
    massa = pd.to_numeric(row[COL_MASSA], errors="coerce") or 0
    total_massa += massa
    if comp:
        massa_compostagem += massa
    if vermi:
        massa_vermi += massa

    resultados.append({
        "Tipo de coleta": row[COL_TIPO_COLETA],
        "Massa": formatar_massa_br(massa),
        "Categoria": categoria,
        "Compostagem": "✅" if comp else "❌",
        "Vermicompostagem": "✅" if vermi else "❌",
        "Justificativa": just
    })

st.dataframe(pd.DataFrame(resultados), use_container_width=True)

# =========================================================
# 🌳 Podas e galhadas – Destinação
# =========================================================
st.markdown("---")
st.subheader("🌳 Destinação das podas e galhadas de áreas verdes públicas")

df_podas = df_mun[
    df_mun[COL_TIPO_COLETA].astype(str)
    .str.contains("áreas verdes públicas", case=False, na=False)
].copy()

if not df_podas.empty:
    df_podas["MASSA_FLOAT"] = pd.to_numeric(df_podas[COL_MASSA], errors="coerce").fillna(0)
    total_podas = df_podas["MASSA_FLOAT"].sum()

    df_podas_destino = (
        df_podas.groupby(COL_DESTINO)["MASSA_FLOAT"]
        .sum()
        .reset_index()
    )

    df_podas_destino["Percentual (%)"] = df_podas_destino["MASSA_FLOAT"] / total_podas * 100
    df_podas_destino = df_podas_destino.sort_values("Percentual (%)", ascending=False)

    st.metric("Massa total de podas e galhadas", f"{formatar_numero_br(total_podas)} t")

    st.dataframe(
        df_podas_destino.assign(
            **{
                "Massa (t)": df_podas_destino["MASSA_FLOAT"].apply(formatar_numero_br),
                "Percentual (%)": df_podas_destino["Percentual (%)"].apply(formatar_numero_br)
            }
        )[[COL_DESTINO, "Massa (t)", "Percentual (%)"]],
        use_container_width=True
    )
# =========================================================
# 🔥 Emissões evitadas – tCO₂eq (desvio do aterro)
# =========================================================
st.subheader("🔥 Emissões evitadas por desvio do aterro (tCO₂eq)")

# -------------------------------
# Parâmetros do MODELO V8
# -------------------------------
GWP_CH4 = 27.2                # AR6 – 100 anos
PRECO_CARBONO_EUR = 90.0      # €/tCO2eq (modelo V8)
EUR_BRL = 5.40                # cotação média €
ANOS = 20

massa_aterro_t = df_podas_destino.loc[
    df_podas_destino[COL_DESTINO].apply(normalizar_texto) == "ATERRO SANITARIO",
    "MASSA_FLOAT"
].sum()

if massa_aterro_t > 0:
    DOC, MCF, F, OX, Ri = 0.15, 1.0, 0.5, 0.1, 0.0
    DOCf = 0.0147 * 25 + 0.28

    massa_kg = massa_aterro_t * 1000

    # -------------------------------
    # CH₄ no aterro (IPCC 2006)
    # -------------------------------
    ch4_aterro = (
        massa_kg * DOC * DOCf * MCF * F * (16 / 12)
        * (1 - Ri) * (1 - OX)
    ) / 1000

    # -------------------------------
    # CH₄ nos tratamentos biológicos
    # -------------------------------
    ch4_comp = ch4_compostagem_total(massa_kg) / 1000
    ch4_vermi = ch4_vermicompostagem_total(massa_kg) / 1000

    # -------------------------------
    # Emissões evitadas (tCO₂eq)
    # -------------------------------
    evitado_comp_co2eq = (ch4_aterro - ch4_comp) * GWP_CH4
    evitado_vermi_co2eq = (ch4_aterro - ch4_vermi) * GWP_CH4

    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Emissões evitadas – Compostagem",
            f"{formatar_numero_br(evitado_comp_co2eq)} tCO₂eq"
        )
    with col2:
        st.metric(
            "Emissões evitadas – Vermicompostagem",
            f"{formatar_numero_br(evitado_vermi_co2eq)} tCO₂eq"
        )

    # =========================================================
    # 💰 Valoração econômica – MODELO V8 (20 anos)
    # =========================================================
    st.markdown("### 💰 Valoração econômica das emissões evitadas")
    st.caption(
        f"Preço automático do carbono: **€ {PRECO_CARBONO_EUR}/tCO₂eq** | "
        f"GWP CH₄ = 27,2 (AR6) | Horizonte: {ANOS} anos"
    )

    # Projeção temporal
    comp_20a = evitado_comp_co2eq * ANOS
    vermi_20a = evitado_vermi_co2eq * ANOS

    # Valoração econômica (MODELO V8)
    valor_comp_eur = comp_20a * PRECO_CARBONO_EUR
    valor_vermi_eur = vermi_20a * PRECO_CARBONO_EUR

    valor_comp_brl = valor_comp_eur * EUR_BRL
    valor_vermi_brl = valor_vermi_eur * EUR_BRL

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🌱 Compostagem**")
        st.metric("tCO₂eq evitado (20 anos)", formatar_numero_br(comp_20a))
        st.metric("Valor econômico (€)", f"€ {formatar_numero_br(valor_comp_eur)}")
        st.metric("Valor econômico (R$)", f"R$ {formatar_numero_br(valor_comp_brl)}")

    with col2:
        st.markdown("**🐛 Vermicompostagem**")
        st.metric("tCO₂eq evitado (20 anos)", formatar_numero_br(vermi_20a))
        st.metric("Valor econômico (€)", f"€ {formatar_numero_br(valor_vermi_eur)}")
        st.metric("Valor econômico (R$)", f"R$ {formatar_numero_br(valor_vermi_brl)}")

    st.caption(
        "Cálculo de emissões evitadas e valoração econômica realizado "
        "conforme o MODELO V8: desvio do aterro sanitário para compostagem "
        "e vermicompostagem de podas e galhadas de áreas verdes públicas."
    )

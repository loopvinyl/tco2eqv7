import streamlit as st
import pandas as pd

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
# Funções auxiliares para formatação brasileira
# =========================================================
def formatar_numero_br(valor, casas_decimais=2):
    if pd.isna(valor) or valor is None:
        return "Não informado"
    try:
        num = float(valor)
        formato = f"{{:,.{casas_decimais}f}}".format(num)
        partes = formato.split(".")
        milhar = partes[0].replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{milhar},{partes[1]}"
    except:
        return "Não informado"

def formatar_massa_br(valor):
    if pd.isna(valor) or valor is None:
        return "Não informado"
    try:
        return f"{formatar_numero_br(valor)} t"
    except:
        return "Não informado"

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

if municipio == "BRASIL – Todos os municípios":
    df_mun = df_clean.copy()
    st.subheader("🇧🇷 Brasil — Síntese Nacional de RSU")
else:
    df_mun = df_clean[df_clean[COL_MUNICIPIO] == municipio]
    st.subheader(f"📍 {municipio}")

# =========================================================
# Processamento principal
# =========================================================
resultados = []
total_massa = 0
massa_compostagem = 0
massa_vermi = 0

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
# 🌳 Destinação das podas e galhadas
# =========================================================
st.markdown("---")
st.subheader("🌳 Destinação das podas e galhadas de áreas verdes públicas")

df_podas = df_mun[
    df_mun[COL_TIPO_COLETA].astype(str).str.lower()
    .str.contains("áreas verdes públicas", na=False)
].copy()

if not df_podas.empty:
    df_podas["MASSA_FLOAT"] = pd.to_numeric(df_podas[COL_MASSA], errors="coerce").fillna(0)
    total_podas = df_podas["MASSA_FLOAT"].sum()

    df_podas_destino = (
        df_podas.groupby(COL_DESTINO)["MASSA_FLOAT"]
        .sum().reset_index()
    )

    df_podas_destino["Percentual (%)"] = df_podas_destino["MASSA_FLOAT"] / total_podas * 100
    df_podas_destino = df_podas_destino.sort_values("Percentual (%)", ascending=False)

    st.metric("Massa total de podas e galhadas", f"{formatar_numero_br(total_podas)} t")

    df_view = df_podas_destino.copy()
    df_view["Massa (t)"] = df_view["MASSA_FLOAT"].apply(formatar_numero_br)
    df_view["Percentual (%)"] = df_view["Percentual (%)"].apply(formatar_numero_br)

    st.dataframe(df_view[[COL_DESTINO, "Massa (t)", "Percentual (%)"]],
                 use_container_width=True)

    # =========================================================
    # 🔥 Potencial de Metano – ATERRO SANITARIO
    # =========================================================
    st.subheader("🔥 Potencial de geração de metano (CH₄) – Aterro Sanitário")

    df_aterro = df_podas_destino[
        df_podas_destino[COL_DESTINO].str.upper().str.contains("ATERRO", na=False)
    ]

    massa_aterro_t = df_aterro["MASSA_FLOAT"].sum()

    if massa_aterro_t > 0:
        # Parâmetros IPCC 2006
        DOC = 0.15
        MCF = 1.0
        F = 0.5
        OX = 0.1
        Ri = 0.0
        temperatura = 25  # °C padrão
        DOCf = 0.0147 * temperatura + 0.28

        massa_kg = massa_aterro_t * 1000
        ch4_por_kg = DOC * DOCf * MCF * F * (16 / 12) * (1 - Ri) * (1 - OX)
        ch4_total_t = (massa_kg * ch4_por_kg) / 1000

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Massa no aterro", f"{formatar_numero_br(massa_aterro_t)} t")
        with col2:
            st.metric("CH₄ potencial gerado", f"{formatar_numero_br(ch4_total_t)} t CH₄")
        with col3:
            st.metric("CH₄ evitável (compostagem)", f"{formatar_numero_br(ch4_total_t)} t CH₄")

        st.caption(
            "Cálculo baseado na metodologia IPCC 2006 (aterro sanitário, "
            "DOCf dependente da temperatura, k=0,06 ano⁻¹). "
            "Considera emissões de CH₄ desprezíveis para compostagem."
        )
    else:
        st.info("Não há massa de podas e galhadas destinada a aterro sanitário.")

else:
    st.info("Não há registros de podas e galhadas para este recorte.")

# =========================================================
# Rodapé
# =========================================================
st.markdown("---")
st.caption(
    "Classificação técnica baseada na origem do resíduo, segregação e adequação "
    "ao tratamento biológico (compostagem e vermicompostagem)."
)
st.caption("Fonte: SNIS – Sistema Nacional de Informações sobre Saneamento")

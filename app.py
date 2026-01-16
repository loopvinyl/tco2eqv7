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
        return f"{formatar_numero_br(float(valor), 2)} t"
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
# Definição de colunas principais
# =========================================================
df = df.rename(columns={
    df.columns[2]: "MUNICÍPIO",
    df.columns[17]: "TIPO_COLETA_EXECUTADA",
    df.columns[24]: "MASSA_COLETADA"
})

COL_MUNICIPIO = "MUNICÍPIO"
COL_TIPO_COLETA = "TIPO_COLETA_EXECUTADA"
COL_MASSA = "MASSA_COLETADA"

# =========================================================
# Detectar automaticamente coluna de unidade de destino
# =========================================================
COL_DESTINO = None
for col in df.columns:
    col_lower = col.lower()
    if "unidade" in col_lower and "destin" in col_lower:
        COL_DESTINO = col
        break

# =========================================================
# Classificação técnica
# =========================================================
def classificar_coleta(texto):
    if pd.isna(texto):
        return ("Não informado", False, False, "Tipo de coleta não informado")

    t = str(texto).lower()

    palavras_chave = {
        "poda": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "galhada": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "verde": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "vegetal": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "orgânica": ("Orgânico direto", True, True, "Orgânico segregado"),
        "indiferenciada": ("Orgânico potencial", True, False, "Exige triagem prévia"),
        "domiciliar": ("Orgânico potencial", True, False, "Exige triagem prévia"),
        "doméstico": ("Orgânico potencial", True, False, "Exige triagem prévia"),
        "varrição": ("Inapto", False, False, "Alta contaminação"),
        "limpeza": ("Inapto", False, False, "Alta contaminação"),
        "seletiva": ("Não orgânico", False, False, "Resíduos recicláveis"),
        "recicl": ("Não orgânico", False, False, "Resíduos recicláveis"),
        "seco": ("Não orgânico", False, False, "Resíduos recicláveis")
    }

    for palavra, classificacao in palavras_chave.items():
        if palavra in t:
            return classificacao

    return ("Indefinido", False, False, "Tipo não classificado automaticamente")

# =========================================================
# Limpeza de dados
# =========================================================
df_clean = df.dropna(subset=[COL_MUNICIPIO])
df_clean[COL_MUNICIPIO] = df_clean[COL_MUNICIPIO].astype(str).str.strip()

# =========================================================
# Interface
# =========================================================
municipios = ["BRASIL – Todos os municípios"] + sorted(
    df_clean[COL_MUNICIPIO].unique()
)

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
massa_vermicompostagem = 0

for _, row in df_mun.iterrows():
    categoria, comp, vermi, justificativa = classificar_coleta(row.get(COL_TIPO_COLETA))
    massa_float = pd.to_numeric(row.get(COL_MASSA), errors="coerce") or 0

    total_massa += massa_float
    if comp:
        massa_compostagem += massa_float
    if vermi:
        massa_vermicompostagem += massa_float

    resultados.append({
        "Tipo de coleta executada": row.get(COL_TIPO_COLETA),
        "Massa coletada": formatar_massa_br(row.get(COL_MASSA)),
        "Categoria técnica": categoria,
        "Compostagem": "✅" if comp else "❌",
        "Vermicompostagem": "✅" if vermi else "❌",
        "Justificativa técnica": justificativa
    })

df_result = pd.DataFrame(resultados)

# =========================================================
# Exibição principal
# =========================================================
st.dataframe(df_result, use_container_width=True)

st.subheader("📊 Síntese técnica")

perc_comp = (massa_compostagem / total_massa * 100) if total_massa > 0 else 0
perc_vermi = (massa_vermicompostagem / total_massa * 100) if total_massa > 0 else 0

col1, col2, col3 = st.columns(3)

col1.metric("Massa total coletada", f"{formatar_numero_br(total_massa)} t")
col2.metric(
    "Massa apta para compostagem",
    f"{formatar_numero_br(massa_compostagem)} t",
    f"{formatar_numero_br(perc_comp)}%"
)
col3.metric(
    "Massa apta para vermicompostagem",
    f"{formatar_numero_br(massa_vermicompostagem)} t",
    f"{formatar_numero_br(perc_vermi)}%"
)

# =========================================================
# Painel – Podas e galhadas (áreas verdes públicas)
# =========================================================
st.markdown("---")
st.subheader("🌳 Destinação das podas e galhadas de áreas verdes públicas")

if COL_DESTINO is None:
    st.warning("⚠️ Coluna de tipo de unidade de destino não encontrada no dataset.")
else:
    df_podas = df_mun[
        df_mun[COL_TIPO_COLETA].astype(str)
        .str.lower()
        .str.contains("áreas verdes públicas", na=False)
    ].copy()

    if df_podas.empty:
        st.info("ℹ️ Não há registros desse tipo de coleta para a seleção atual.")
    else:
        df_podas["MASSA_FLOAT"] = pd.to_numeric(
            df_podas[COL_MASSA], errors="coerce"
        ).fillna(0)

        total_podas = df_podas["MASSA_FLOAT"].sum()

        if total_podas == 0:
            st.warning("⚠️ Massa total igual a zero para podas e galhadas.")
        else:
            df_destino = (
                df_podas
                .groupby(COL_DESTINO, dropna=False)["MASSA_FLOAT"]
                .sum()
                .reset_index()
            )

            df_destino["Percentual (%)"] = df_destino["MASSA_FLOAT"] / total_podas * 100
            df_destino["Massa (t)"] = df_destino["MASSA_FLOAT"].apply(
                lambda x: formatar_numero_br(x)
            )
            df_destino["Percentual (%)"] = df_destino["Percentual (%)"].apply(
                lambda x: formatar_numero_br(x)
            )

            df_destino = df_destino[[COL_DESTINO, "Massa (t)", "Percentual (%)"]]

            st.metric(
                "Massa total de podas e galhadas",
                f"{formatar_numero_br(total_podas)} t"
            )

            st.dataframe(df_destino, use_container_width=True)

# =========================================================
# Rodapé
# =========================================================
st.markdown("---")
st.caption(
    "Classificação baseada na origem do resíduo, grau de segregação "
    "e adequação ao tratamento biológico (compostagem/vermicompostagem)."
)
st.caption("Fonte: SNIS - Sistema Nacional de Informações sobre Saneamento")

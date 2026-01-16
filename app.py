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
# Carregamento do Excel (configuração conhecida)
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
    return df

df = load_data()

# =========================================================
# Definição explícita das colunas
# =========================================================
COL_MUNICIPIO = "MUNICÍPIO"
COL_TIPO_COLETA = "Tipo de coleta executada"

# =========================================================
# Validação
# =========================================================
if COL_MUNICIPIO not in df.columns or COL_TIPO_COLETA not in df.columns:
    st.error("❌ As colunas esperadas não foram encontradas.")
    st.write("Colunas disponíveis:")
    st.write(df.columns.tolist())
    st.stop()

# =========================================================
# Função de classificação técnica
# =========================================================
def classificar_coleta(texto):
    if pd.isna(texto):
        return ("Não informado", False, False, "Tipo de coleta não informado")

    t = str(texto).lower()

    if "poda" in t or "galhada" in t or "área verde" in t:
        return ("Orgânico direto", True, True, "Resíduo vegetal limpo")

    if "orgânico" in t and "seletiva" in t:
        return ("Orgânico direto", True, True, "Orgânico segregado na origem")

    if "indiferenciada" in t or "convencional" in t or "domiciliar" in t:
        return ("Orgânico potencial", True, False, "Exige triagem prévia")

    if "limpeza urbana" in t or "varrição" in t:
        return ("Inapto", False, False, "Alta contaminação")

    if "seletiva" in t and ("recicl" in t or "seco" in t):
        return ("Não orgânico", False, False, "Resíduos recicláveis secos")

    return ("Indefinido", False, False, "Tipo não classificado automaticamente")

# =========================================================
# Interface
# =========================================================
municipios = sorted(df[COL_MUNICIPIO].dropna().unique())
municipio = st.selectbox("Selecione o município:", municipios)

df_mun = df[df[COL_MUNICIPIO] == municipio]

st.subheader(f"📍 {municipio}")

resultados = []

for _, row in df_mun.iterrows():
    categoria, comp, vermi, justificativa = classificar_coleta(row[COL_TIPO_COLETA])

    resultados.append({
        "Tipo de coleta executada": row[COL_TIPO_COLETA],
        "Categoria técnica": categoria,
        "Compostagem": "✅" if comp else "❌",
        "Vermicompostagem": "✅" if vermi else "❌",
        "Justificativa técnica": justificativa
    })

df_result = pd.DataFrame(resultados)

st.dataframe(df_result, use_container_width=True)

# =========================================================
# Síntese municipal
# =========================================================
st.subheader("📊 Síntese técnica municipal")

if (df_result["Compostagem"] == "✅").any():
    st.success("✔️ O município possui **potencial técnico para compostagem**.")
else:
    st.error("❌ Não foi identificado potencial técnico para compostagem.")

if (df_result["Vermicompostagem"] == "✅").any():
    st.success("🐛 O município possui **potencial técnico para vermicompostagem**.")
else:
    st.warning("⚠️ Não foram identificadas fontes adequadas para vermicompostagem.")

# =========================================================
# Rodapé
# =========================================================
st.markdown("---")
st.caption(
    "Classificação baseada na origem do resíduo, grau de segregação "
    "e adequação ao tratamento biológico (compostagem/vermicompostagem)."
)

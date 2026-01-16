import streamlit as st
import pandas as pd

# -----------------------------
# Configuração da página
# -----------------------------
st.set_page_config(
    page_title="Potencial de Compostagem de RSU",
    layout="wide"
)

st.title("🌱 Potencial de Compostagem e Vermicompostagem por Município")
st.markdown("""
Este aplicativo interpreta os **tipos de coleta executada** informados pelos municípios
e avalia o **potencial técnico para compostagem e vermicompostagem**.
""")

# -----------------------------
# Carregar dados
# -----------------------------
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/loopvinyl/tco2eqv7/main/rsuBrasil.xlsx"
    return pd.read_excel(url)

df = load_data()

# -----------------------------
# Ajuste de nomes de colunas
# (edite se necessário)
# -----------------------------
COL_MUNICIPIO = "Município"
COL_TIPO_COLETA = "Tipo de coleta executada"

# -----------------------------
# Função de classificação
# -----------------------------
def classificar_coleta(texto):
    if pd.isna(texto):
        return {
            "categoria": "Não informado",
            "compostagem": False,
            "vermicompostagem": False,
            "justificativa": "Tipo de coleta não informado"
        }

    t = texto.lower()

    if "poda" in t or "galhada" in t or "áreas verdes" in t:
        return {
            "categoria": "Orgânico direto",
            "compostagem": True,
            "vermicompostagem": True,
            "justificativa": "Resíduo vegetal limpo, ideal para compostagem"
        }

    if "orgânico" in t and "seletiva" in t:
        return {
            "categoria": "Orgânico direto",
            "compostagem": True,
            "vermicompostagem": True,
            "justificativa": "Orgânico segregado na origem"
        }

    if "indiferenciada" in t or "convencional" in t:
        return {
            "categoria": "Orgânico potencial",
            "compostagem": True,
            "vermicompostagem": False,
            "justificativa": "Contém orgânicos, mas exige triagem"
        }

    if "limpeza urbana" in t or "varrição" in t:
        return {
            "categoria": "Inapto",
            "compostagem": False,
            "vermicompostagem": False,
            "justificativa": "Alta contaminação"
        }

    if "seletiva" in t and "recicl" in t:
        return {
            "categoria": "Não orgânico",
            "compostagem": False,
            "vermicompostagem": False,
            "justificativa": "Resíduos secos recicláveis"
        }

    return {
        "categoria": "Indefinido",
        "compostagem": False,
        "vermicompostagem": False,
        "justificativa": "Tipo não reconhecido automaticamente"
    }

# -----------------------------
# Interface
# -----------------------------
municipios = sorted(df[COL_MUNICIPIO].dropna().unique())
municipio = st.selectbox("Selecione o município:", municipios)

df_mun = df[df[COL_MUNICIPIO] == municipio]

st.subheader(f"📍 {municipio}")

resultados = []

for _, row in df_mun.iterrows():
    tipo = row[COL_TIPO_COLETA]
    r = classificar_coleta(tipo)
    resultados.append({
        "Tipo de coleta": tipo,
        "Categoria": r["categoria"],
        "Compostagem": "✅" if r["compostagem"] else "❌",
        "Vermicompostagem": "✅" if r["vermicompostagem"] else "❌",
        "Justificativa técnica": r["justificativa"]
    })

df_result = pd.DataFrame(resultados)

st.dataframe(df_result, use_container_width=True)

# -----------------------------
# Síntese
# -----------------------------
st.subheader("📊 Síntese técnica")

if (df_result["Compostagem"] == "✅").any():
    st.success("✔️ O município possui potencial para compostagem.")
else:
    st.error("❌ O município NÃO apresenta potencial direto para compostagem.")

if (df_result["Vermicompostagem"] == "✅").any():
    st.success("🐛 Possui potencial para vermicompostagem.")
else:
    st.warning("⚠️ Não foram identificadas fontes adequadas para vermicompostagem.")

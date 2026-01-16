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
e avalia o **potencial técnico para compostagem e vermicompostagem** de resíduos sólidos urbanos.
""")

# =========================================================
# Carregamento dos dados
# =========================================================
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/loopvinyl/tco2eqv7/main/rsuBrasil.xlsx"
    return pd.read_excel(url)

df = load_data()

# =========================================================
# Função para encontrar colunas automaticamente
# =========================================================
def encontrar_coluna(df, palavras_chave):
    for col in df.columns:
        col_lower = col.lower()
        if all(p in col_lower for p in palavras_chave):
            return col
    return None

COL_MUNICIPIO = encontrar_coluna(df, ["munic"])
COL_TIPO_COLETA = encontrar_coluna(df, ["coleta"])

# =========================================================
# Validação das colunas
# =========================================================
if COL_MUNICIPIO is None or COL_TIPO_COLETA is None:
    st.error("❌ Não foi possível identificar automaticamente as colunas necessárias.")
    st.markdown("### Colunas encontradas no arquivo:")
    st.write(df.columns.tolist())
    st.stop()

# =========================================================
# Função de classificação técnica
# =========================================================
def classificar_coleta(texto):
    if pd.isna(texto):
        return {
            "categoria": "Não informado",
            "compostagem": False,
            "vermicompostagem": False,
            "justificativa": "Tipo de coleta não informado"
        }

    t = str(texto).lower()

    if "poda" in t or "galhada" in t or "área verde" in t:
        return {
            "categoria": "Orgânico direto",
            "compostagem": True,
            "vermicompostagem": True,
            "justificativa": "Resíduo vegetal limpo, excelente para compostagem"
        }

    if "orgânico" in t and "seletiva" in t:
        return {
            "categoria": "Orgânico direto",
            "compostagem": True,
            "vermicompostagem": True,
            "justificativa": "Orgânico segregado na origem"
        }

    if "indiferenciada" in t or "convencional" in t or "domiciliar" in t:
        return {
            "categoria": "Orgânico potencial",
            "compostagem": True,
            "vermicompostagem": False,
            "justificativa": "Contém orgânicos, mas exige triagem prévia"
        }

    if "limpeza urbana" in t or "varrição" in t:
        return {
            "categoria": "Inapto",
            "compostagem": False,
            "vermicompostagem": False,
            "justificativa": "Alta contaminação física e química"
        }

    if "seletiva" in t and ("recicl" in t or "seco" in t):
        return {
            "categoria": "Não orgânico",
            "compostagem": False,
            "vermicompostagem": False,
            "justificativa": "Resíduos recicláveis secos"
        }

    return {
        "categoria": "Indefinido",
        "compostagem": False,
        "vermicompostagem": False,
        "justificativa": "Tipo de coleta não reconhecido automaticamente"
    }

# =========================================================
# Interface do usuário
# =========================================================
municipios = sorted(df[COL_MUNICIPIO].dropna().unique())
municipio = st.selectbox("Selecione o município:", municipios)

df_mun = df[df[COL_MUNICIPIO] == municipio]

st.subheader(f"📍 {municipio}")

resultados = []

for _, row in df_mun.iterrows():
    tipo = row[COL_TIPO_COLETA]
    r = classificar_coleta(tipo)

    resultados.append({
        "Tipo de coleta executada": tipo,
        "Categoria técnica": r["categoria"],
        "Compostagem": "✅" if r["compostagem"] else "❌",
        "Vermicompostagem": "✅" if r["vermicompostagem"] else "❌",
        "Justificativa técnica": r["justificativa"]
    })

df_result = pd.DataFrame(resultados)

st.dataframe(df_result, use_container_width=True)

# =========================================================
# Síntese técnica
# =========================================================
st.subheader("📊 Síntese técnica municipal")

tem_compostagem = (df_result["Compostagem"] == "✅").any()
tem_vermi = (df_result["Vermicompostagem"] == "✅").any()

if tem_compostagem:
    st.success("✔️ O município apresenta **potencial técnico para compostagem**.")
else:
    st.error("❌ Não foi identificado potencial técnico direto para compostagem.")

if tem_vermi:
    st.success("🐛 O município apresenta **potencial técnico para vermicompostagem**.")
else:
    st.warning("⚠️ Não foram identificadas fontes adequadas para vermicompostagem.")

# =========================================================
# Rodapé técnico
# =========================================================
st.markdown("---")
st.caption(
    "Classificação baseada em origem do resíduo, grau de segregação e potencial técnico "
    "para tratamento biológico (compostagem/vermicompostagem)."
)

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
# Carregamento inteligente do Excel (SNIS-style)
# =========================================================
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/loopvinyl/tco2eqv7/main/rsuBrasil.xlsx"

    # Lê SEM cabeçalho
    raw = pd.read_excel(url, header=None)

    # Encontra a linha onde aparece "Município"
    header_row = None
    for i in range(len(raw)):
        row_as_str = raw.iloc[i].astype(str).str.lower().str.cat(sep=" ")
        if "munic" in row_as_str:
            header_row = i
            break

    if header_row is None:
        raise ValueError("Cabeçalho não encontrado no arquivo.")

    # Recarrega usando essa linha como cabeçalho
    df = pd.read_excel(url, header=header_row)

    # Remove linhas completamente vazias
    df = df.dropna(how="all")

    return df

df = load_data()

# =========================================================
# Função para encontrar colunas automaticamente
# =========================================================
def encontrar_coluna(df, palavras_chave):
    for col in df.columns:
        col_lower = str(col).lower()
        if all(p in col_lower for p in palavras_chave):
            return col
    return None

COL_MUNICIPIO = encontrar_coluna(df, ["munic"])
COL_TIPO_COLETA = encontrar_coluna(df, ["coleta"])

# =========================================================
# Validação
# =========================================================
if COL_MUNICIPIO is None or COL_TIPO_COLETA is None:
    st.error("❌ Não foi possível identificar as colunas necessárias.")
    st.markdown("### Colunas detectadas:")
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
        return ("Orgânico potencial", True, False, "Exige triagem")

    if "limpeza urbana" in t or "varrição" in t:
        return ("Inapto", False, False, "Alta contaminação")

    if "seletiva" in t and ("recicl" in t or "seco" in t):
        return ("Não orgânico", False, False, "Recicláveis secos")

    return ("Indefinido", False, False, "Tipo não reconhecido")

# =========================================================
# Interface
# =========================================================
municipios = sorted(df[COL_MUNICIPIO].dropna().unique())
municipio = st.selectbox("Selecione o município:", municipios)

df_mun = df[df[COL_MUNICIPIO] == municipio]

st.subheader(f"📍 {municipio}")

resultados = []

for _, row in df_mun.iterrows():
    categoria, comp, vermi, just = classificar_coleta(row[COL_TIPO_COLETA])

    resultados.append({
        "Tipo de coleta executada": row[COL_TIPO_COLETA],
        "Categoria técnica": categoria,
        "Compostagem": "✅" if comp else "❌",
        "Vermicompostagem": "✅" if vermi else "❌",
        "Justificativa": just
    })

df_result = pd.DataFrame(resultados)

st.dataframe(df_result, use_container_width=True)

# =========================================================
# Síntese
# =========================================================
st.subheader("📊 Síntese técnica")

if (df_result["Compostagem"] == "✅").any():
    st.success("✔️ O município possui potencial técnico para compostagem.")
else:
    st.error("❌ Não foi identificado potencial técnico para compostagem.")

if (df_result["Vermicompostagem"] == "✅").any():
    st.success("🐛 Possui potencial técnico para vermicompostagem.")
else:
    st.warning("⚠️ Não foram identificadas fontes adequadas para vermicompostagem.")

st.markdown("---")
st.caption("Classificação baseada na origem do resíduo e adequação ao tratamento biológico.")

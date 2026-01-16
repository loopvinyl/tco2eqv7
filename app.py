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
def formatar_numero_br(valor, casas_decimais=1):
    if pd.isna(valor) or valor is None:
        return "Não informado"
    try:
        num = float(valor)
        if num == 0:
            return "0"
        formato = f"{{:,.{casas_decimais}f}}".format(num)
        partes = formato.split(".")
        if len(partes) == 2:
            milhar = partes[0].replace(",", "X").replace(".", ",").replace("X", ".")
            return f"{milhar},{partes[1]}"
        else:
            return formato.replace(",", ".")
    except:
        return str(valor)

def formatar_massa_br(valor):
    if pd.isna(valor) or valor is None:
        return "Não informado"
    try:
        massa = float(valor)
        if massa == 0:
            return "0 t"
        elif massa < 1:
            return f"{formatar_numero_br(massa, 3)} t"
        elif massa < 100:
            return f"{formatar_numero_br(massa, 2)} t"
        elif massa < 1000:
            return f"{formatar_numero_br(massa, 1)} t"
        else:
            return f"{formatar_numero_br(massa, 0)} t"
    except:
        return str(valor)

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

# =========================================================
# Classificação técnica
# =========================================================
def classificar_coleta(texto):
    if pd.isna(texto):
        return ("Não informado", False, False, "Tipo de coleta não informado")

    t = str(texto).lower().strip()
    t_clean = ' '.join([word for word in t.split() if not word.isdigit()])

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
        if palavra in t_clean:
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
    df_clean[COL_MUNICIPIO].dropna().unique()
)

municipio = st.selectbox("Selecione o município:", municipios)

if municipio == "BRASIL – Todos os municípios":
    df_mun = df_clean.copy()
    st.subheader("🇧🇷 Brasil — Síntese Nacional de RSU")
else:
    df_mun = df_clean[df_clean[COL_MUNICIPIO] == municipio]
    if df_mun.empty:
        st.warning(f"⚠️ Não foram encontrados dados para {municipio}")
        st.stop()
    st.subheader(f"📍 {municipio}")

# =========================================================
# Processamento
# =========================================================
resultados = []
total_massa = 0
massa_compostagem = 0
massa_vermicompostagem = 0

for _, row in df_mun.iterrows():
    categoria, comp, vermi, justificativa = classificar_coleta(row.get(COL_TIPO_COLETA))
    massa_valor = row.get(COL_MASSA)

    try:
        massa_float = float(massa_valor) if not pd.isna(massa_valor) else 0
    except:
        massa_float = 0

    total_massa += massa_float
    if comp:
        massa_compostagem += massa_float
    if vermi:
        massa_vermicompostagem += massa_float

    resultados.append({
        "Tipo de coleta executada": row.get(COL_TIPO_COLETA, "Não informado"),
        "Massa coletada": formatar_massa_br(massa_valor),
        "Categoria técnica": categoria,
        "Compostagem": "✅" if comp else "❌",
        "Vermicompostagem": "✅" if vermi else "❌",
        "Justificativa técnica": justificativa
    })

df_result = pd.DataFrame(resultados)

# =========================================================
# Exibição
# =========================================================
if not df_result.empty:
    st.dataframe(df_result, use_container_width=True)

    st.subheader("📊 Síntese técnica")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Massa total coletada", f"{formatar_numero_br(total_massa,1)} t")
    col2.metric("Massa apta para compostagem", f"{formatar_numero_br(massa_compostagem,1)} t")
    col3.metric("Massa apta para vermicompostagem", f"{formatar_numero_br(massa_vermicompostagem,1)} t")
    col4.metric(
        "% Apto para compostagem",
        f"{formatar_numero_br((massa_compostagem/total_massa*100) if total_massa>0 else 0,1)}%"
    )

# =========================================================
# Rodapé
# =========================================================
st.markdown("---")
st.caption(
    "Classificação baseada na origem do resíduo, grau de segregação "
    "e adequação ao tratamento biológico (compostagem/vermicompostagem)."
)
st.caption(
    "Fonte: SNIS - Sistema Nacional de Informações sobre Saneamento | "
    f"Coluna de massa: {COL_MASSA}"
)

import streamlit as st
import pandas as pd

# =========================================================
# Configuración de la página
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
# Carga del Excel con configuración corregida
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
    
    # Limpiar nombres de columnas
    df.columns = [str(col).strip() for col in df.columns]
    
    return df

df = load_data()

# =========================================================
# Definición de columnas basada en la estructura real
# =========================================================
# De acuerdo a los datos mostrados:
# Columna 2: Nombre del municipio
# Columna 17: Tipo de coleta executada
# Columna Y (25ª coluna, índice 24): Massa coletada

# Renombrar columnas para mayor claridad
df = df.rename(columns={
    df.columns[2]: "MUNICÍPIO",
    df.columns[17]: "TIPO_COLETA_EXECUTADA",
    df.columns[24]: "MASSA_COLETADA"  # Coluna Y (25ª coluna)
})

COL_MUNICIPIO = "MUNICÍPIO"
COL_TIPO_COLETA = "TIPO_COLETA_EXECUTADA"
COL_MASSA = "MASSA_COLETADA"

# =========================================================
# Función para formatear la masa en toneladas
# =========================================================
def formatar_massa(valor):
    if pd.isna(valor):
        return "Não informado"
    try:
        # Suponiendo que la masa está en toneladas
        massa = float(valor)
        if massa == 0:
            return "0 t"
        elif massa < 1:
            return f"{massa:.3f} t".replace(".", ",")
        elif massa < 1000:
            return f"{massa:.1f} t".replace(".", ",")
        else:
            return f"{massa:,.0f} t".replace(",", ".")
    except:
        return str(valor)

# =========================================================
# Función de clasificación técnica (mejorada)
# =========================================================
def classificar_coleta(texto):
    if pd.isna(texto):
        return ("Não informado", False, False, "Tipo de coleta não informado")

    t = str(texto).lower().strip()
    
    # Limpiar texto de caracteres especiales y números
    t_clean = ' '.join([word for word in t.split() if not word.isdigit()])
    
    # Clasificaciones
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
    
    # Si no coincide con ninguna palabra clave
    return ("Indefinido", False, False, "Tipo não classificado automaticamente")

# =========================================================
# Limpieza de datos
# =========================================================
# Filtrar filas con datos válidos en municipio
df_clean = df.dropna(subset=[COL_MUNICIPIO])
df_clean[COL_MUNICIPIO] = df_clean[COL_MUNICIPIO].astype(str).str.strip()

# =========================================================
# Interfaz
# =========================================================
municipios = sorted(df_clean[COL_MUNICIPIO].dropna().unique())
if len(municipios) == 0:
    st.error("❌ Não foram encontrados municípios no dataset.")
    st.stop()

municipio = st.selectbox("Selecione o município:", municipios)

df_mun = df_clean[df_clean[COL_MUNICIPIO] == municipio]

if df_mun.empty:
    st.warning(f"⚠️ Não foram encontrados dados para {municipio}")
    st.stop()

st.subheader(f"📍 {municipio}")

resultados = []
total_massa = 0
massa_compostagem = 0
massa_vermicompostagem = 0

for _, row in df_mun.iterrows():
    categoria, comp, vermi, justificativa = classificar_coleta(row.get(COL_TIPO_COLETA, None))
    massa_valor = row.get(COL_MASSA, None)
    
    # Calcular valores para totais
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
        "Massa coletada": formatar_massa(massa_valor),
        "Categoria técnica": categoria,
        "Compostagem": "✅" if comp else "❌",
        "Vermicompostagem": "✅" if vermi else "❌",
        "Justificativa técnica": justificativa
    })

df_result = pd.DataFrame(resultados)

if not df_result.empty:
    st.dataframe(df_result, use_container_width=True)
    
    # =========================================================
    # Síntesis municipal
    # =========================================================
    st.subheader("📊 Síntese técnica municipal")
    
    tem_compostagem = any(df_result["Compostagem"] == "✅")
    tem_vermicompostagem = any(df_result["Vermicompostagem"] == "✅")
    
    # Resumo de massas
    st.markdown("### 📦 Resumo das Massas Coletadas")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Massa total coletada", f"{total_massa:,.1f} t".replace(",", "."))
    
    with col2:
        st.metric("Massa apta para compostagem", f"{massa_compostagem:,.1f} t".replace(",", "."))
    
    with col3:
        st.metric("Massa apta para vermicompostagem", f"{massa_vermicompostagem:,.1f} t".replace(",", "."))
    
    with col4:
        if total_massa > 0:
            percentual_comp = (massa_compostagem / total_massa * 100)
            st.metric("% Apto para compostagem", f"{percentual_comp:.1f}%")
        else:
            st.metric("% Apto para compostagem", "0%")
    
    # Potencial técnico
    st.markdown("### 🔍 Potencial Técnico")
    col1, col2 = st.columns(2)
    
    with col1:
        if tem_compostagem:
            st.success("✔️ **Potencial técnico para compostagem**")
            if massa_compostagem > 0:
                st.info(f"**Volume disponível:** {massa_compostagem:,.1f} t/ano".replace(",", "."))
        else:
            st.error("❌ Não foi identificado potencial técnico para compostagem.")
    
    with col2:
        if tem_vermicompostagem:
            st.success("🐛 **Potencial técnico para vermicompostagem**")
            if massa_vermicompostagem > 0:
                st.info(f"**Volume disponível:** {massa_vermicompostagem:,.1f} t/ano".replace(",", "."))
        else:
            st.warning("⚠️ Não foram identificadas fontes adequadas para vermicompostagem.")
    
    # Gráfico de distribuição (opcional)
    if total_massa > 0 and (massa_compostagem > 0 or massa_vermicompostagem > 0):
        st.markdown("### 📈 Distribuição das Massas")
        
        # Criar DataFrame para o gráfico
        distribuicao_data = {
            "Categoria": ["Total Coletado", "Apto Compostagem", "Apto Vermicompostagem"],
            "Massa (t)": [total_massa, massa_compostagem, massa_vermicompostagem]
        }
        df_distribuicao = pd.DataFrame(distribuicao_data)
        
        # Mostrar tabela de distribuição
        st.dataframe(df_distribuicao.style.format({"Massa (t)": "{:,.1f}".format}), 
                    use_container_width=True)
    
    # Estatísticas adicionais
    st.markdown("---")
    st.markdown("#### 📊 Estatísticas Detalhadas")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de tipos de coleta", len(df_result))
    with col2:
        st.metric("Tipos aptos para compostagem", sum(df_result["Compostagem"] == "✅"))
    with col3:
        st.metric("Tipos aptos para vermicompostagem", sum(df_result["Vermicompostagem"] == "✅"))
    
else:
    st.warning("⚠️ Não foram encontrados registros de coleta para análise.")

# =========================================================
# Pie de página
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

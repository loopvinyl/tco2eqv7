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
    """Formata número no padrão brasileiro: 1.234,56"""
    if pd.isna(valor) or valor is None:
        return "Não informado"
    
    try:
        num = float(valor)
        if num == 0:
            return f"0"
        
        # Formata com separador de milhar e decimal
        formato = f"{{:,.{casas_decimais}f}}".format(num)
        
        # Substitui vírgula por ponto e vice-versa
        partes = formato.split(".")
        if len(partes) == 2:
            milhar = partes[0].replace(",", "X").replace(".", ",").replace("X", ".")
            return f"{milhar},{partes[1]}"
        else:
            return formato.replace(",", ".")
    except:
        return str(valor)

def formatar_massa_br(valor):
    """Formata massa em toneladas no padrão brasileiro"""
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
# Carga do Excel com configuração corrigida
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
    
    # Limpar nomes de colunas
    df.columns = [str(col).strip() for col in df.columns]
    
    return df

df = load_data()

# =========================================================
# Definição de colunas baseada na estrutura real
# =========================================================
# De acordo com os dados mostrados:
# Coluna 2: Nome do município
# Coluna 17: Tipo de coleta executada
# Coluna Y (25ª coluna, índice 24): Massa coletada

# Renomear colunas para maior clareza
df = df.rename(columns={
    df.columns[2]: "MUNICÍPIO",
    df.columns[17]: "TIPO_COLETA_EXECUTADA",
    df.columns[24]: "MASSA_COLETADA"  # Coluna Y (25ª coluna)
})

COL_MUNICIPIO = "MUNICÍPIO"
COL_TIPO_COLETA = "TIPO_COLETA_EXECUTADA"
COL_MASSA = "MASSA_COLETADA"

# =========================================================
# Função de classificação técnica (melhorada)
# =========================================================
def classificar_coleta(texto):
    if pd.isna(texto):
        return ("Não informado", False, False, "Tipo de coleta não informado")

    t = str(texto).lower().strip()
    
    # Limpar texto de caracteres especiais e números
    t_clean = ' '.join([word for word in t.split() if not word.isdigit()])
    
    # Classificações
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
    
    # Se não coincide com nenhuma palavra-chave
    return ("Indefinido", False, False, "Tipo não classificado automaticamente")

# =========================================================
# Limpeza de dados
# =========================================================
# Filtrar linhas com dados válidos em município
df_clean = df.dropna(subset=[COL_MUNICIPIO])
df_clean[COL_MUNICIPIO] = df_clean[COL_MUNICIPIO].astype(str).str.strip()

# =========================================================
# Interface
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
        "Massa coletada": formatar_massa_br(massa_valor),
        "Categoria técnica": categoria,
        "Compostagem": "✅" if comp else "❌",
        "Vermicompostagem": "✅" if vermi else "❌",
        "Justificativa técnica": justificativa
    })

df_result = pd.DataFrame(resultados)

if not df_result.empty:
    st.dataframe(df_result, use_container_width=True)
    
    # =========================================================
    # Síntese municipal
    # =========================================================
    st.subheader("📊 Síntese técnica municipal")
    
    tem_compostagem = any(df_result["Compostagem"] == "✅")
    tem_vermicompostagem = any(df_result["Vermicompostagem"] == "✅")
    
    # Resumo de massas
    st.markdown("### 📦 Resumo das Massas Coletadas")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Massa total coletada", f"{formatar_numero_br(total_massa, 1)} t")
    
    with col2:
        st.metric("Massa apta para compostagem", f"{formatar_numero_br(massa_compostagem, 1)} t")
    
    with col3:
        st.metric("Massa apta para vermicompostagem", f"{formatar_numero_br(massa_vermicompostagem, 1)} t")
    
    with col4:
        if total_massa > 0:
            percentual_comp = (massa_compostagem / total_massa * 100)
            st.metric("% Apto para compostagem", f"{formatar_numero_br(percentual_comp, 1)}%")
        else:
            st.metric("% Apto para compostagem", "0%")
    
    # Potencial técnico
    st.markdown("### 🔍 Potencial Técnico")
    col1, col2 = st.columns(2)
    
    with col1:
        if tem_compostagem:
            st.success("✔️ **Potencial técnico para compostagem**")
            if massa_compostagem > 0:
                st.info(f"**Volume disponível:** {formatar_numero_br(massa_compostagem, 1)} t/ano")
        else:
            st.error("❌ Não foi identificado potencial técnico para compostagem.")
    
    with col2:
        if tem_vermicompostagem:
            st.success("🐛 **Potencial técnico para vermicompostagem**")
            if massa_vermicompostagem > 0:
                st.info(f"**Volume disponível:** {formatar_numero_br(massa_vermicompostagem, 1)} t/ano")
        else:
            st.warning("⚠️ Não foram identificadas fontes adequadas para vermicompostagem.")
    
    # Tabela de distribuição
    if total_massa > 0 and (massa_compostagem > 0 or massa_vermicompostagem > 0):
        st.markdown("### 📈 Distribuição das Massas")
        
        # Criar DataFrame para a tabela
        distribuicao_data = {
            "Categoria": ["Total Coletado", "Apto Compostagem", "Apto Vermicompostagem"],
            "Massa (t)": [
                formatar_numero_br(total_massa, 1),
                formatar_numero_br(massa_compostagem, 1),
                formatar_numero_br(massa_vermicompostagem, 1)
            ]
        }
        df_distribuicao = pd.DataFrame(distribuicao_data)
        
        # Mostrar tabela de distribuição
        st.dataframe(df_distribuicao, use_container_width=True)
    
    # Estatísticas adicionais
    st.markdown("---")
    st.markdown("#### 📊 Estatísticas Detalhadas")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de tipos de coleta", formatar_numero_br(len(df_result), 0))
    with col2:
        st.metric("Tipos aptos para compostagem", formatar_numero_br(sum(df_result["Compostagem"] == "✅"), 0))
    with col3:
        st.metric("Tipos aptos para vermicompostagem", formatar_numero_br(sum(df_result["Vermicompostagem"] == "✅"), 0))
    
else:
    st.warning("⚠️ Não foram encontrados registros de coleta para análise.")

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

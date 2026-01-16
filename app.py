import streamlit as st
import pandas as pd

# =========================================================
# Configuração da página
# =========================================================
st.set_page_config(
    page_title="Potencial de Compostagem de RSU",
    layout="wide"
)

st.title("🌱 Potencial de Compostagem e Vermicompostagem de RSU no Brasil")
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
df_clean = df.dropna(subset=[COL_MUNICIPIO])
df_clean[COL_MUNICIPIO] = df_clean[COL_MUNICIPIO].astype(str).str.strip()

# =========================================================
# Cálculos para o Brasil (antes da seleção de município)
# =========================================================
st.header("🇧🇷 Visão Nacional - Brasil")

# Calcular estatísticas nacionais
total_municipios = df_clean[COL_MUNICIPIO].nunique()

# Processar todos os dados para calcular totais nacionais
brasil_total_massa = 0
brasil_massa_compostagem = 0
brasil_massa_vermicompostagem = 0
brasil_total_tipos = 0
brasil_aptos_compostagem = 0
brasil_aptos_vermicompostagem = 0

# Processar cada linha para calcular totais
for _, row in df_clean.iterrows():
    categoria, comp, vermi, justificativa = classificar_coleta(row.get(COL_TIPO_COLETA, None))
    massa_valor = row.get(COL_MASSA, None)
    
    try:
        massa_float = float(massa_valor) if not pd.isna(massa_valor) else 0
    except:
        massa_float = 0
    
    brasil_total_massa += massa_float
    brasil_total_tipos += 1
    
    if comp:
        brasil_massa_compostagem += massa_float
        brasil_aptos_compostagem += 1
    
    if vermi:
        brasil_massa_vermicompostagem += massa_float
        brasil_aptos_vermicompostagem += 1

# =========================================================
# Estatísticas Nacionais
# =========================================================
st.subheader("📊 Estatísticas Nacionais")

# Métricas principais
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total de Municípios", formatar_numero_br(total_municipios, 0))

with col2:
    st.metric("Massa Total Coletada", f"{formatar_numero_br(brasil_total_massa, 1)} t")

with col3:
    st.metric("Massa Apta Compostagem", f"{formatar_numero_br(brasil_massa_compostagem, 1)} t")

with col4:
    if brasil_total_massa > 0:
        percentual_comp = (brasil_massa_compostagem / brasil_total_massa * 100)
        st.metric("% Apto Compostagem", f"{formatar_numero_br(percentual_comp, 1)}%")
    else:
        st.metric("% Apto Compostagem", "0%")

# Métricas secundárias
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Tipos de Coleta Analisados", formatar_numero_br(brasil_total_tipos, 0))

with col2:
    st.metric("Massa Apta Vermicompostagem", f"{formatar_numero_br(brasil_massa_vermicompostagem, 1)} t")

with col3:
    if brasil_total_massa > 0:
        percentual_vermi = (brasil_massa_vermicompostagem / brasil_total_massa * 100)
        st.metric("% Apto Vermicompostagem", f"{formatar_numero_br(percentual_vermi, 1)}%")
    else:
        st.metric("% Apto Vermicompostagem", "0%")

with col4:
    if brasil_total_tipos > 0:
        percentual_tipos_comp = (brasil_aptos_compostagem / brasil_total_tipos * 100)
        st.metric("% Tipos Apto Compostagem", f"{formatar_numero_br(percentual_tipos_comp, 1)}%")
    else:
        st.metric("% Tipos Apto Compostagem", "0%")

# Potencial técnico nacional
st.markdown("### 🔍 Potencial Técnico Nacional")
col1, col2 = st.columns(2)

with col1:
    if brasil_massa_compostagem > 0:
        st.success("✔️ **Potencial Nacional para Compostagem**")
        st.info(f"**Volume nacional disponível:** {formatar_numero_br(brasil_massa_compostagem, 1)} t/ano")
    else:
        st.error("❌ Não foi identificado potencial nacional para compostagem.")

with col2:
    if brasil_massa_vermicompostagem > 0:
        st.success("🐛 **Potencial Nacional para Vermicompostagem**")
        st.info(f"**Volume nacional disponível:** {formatar_numero_br(brasil_massa_vermicompostagem, 1)} t/ano")
    else:
        st.warning("⚠️ Não foram identificadas fontes adequadas para vermicompostagem.")

# Tabela de distribuição nacional
if brasil_total_massa > 0:
    st.markdown("### 📈 Distribuição Nacional das Massas")
    
    distribuicao_data = {
        "Categoria": ["Total Coletado", "Apto Compostagem", "Apto Vermicompostagem"],
        "Massa (t)": [
            formatar_numero_br(brasil_total_massa, 1),
            formatar_numero_br(brasil_massa_compostagem, 1),
            formatar_numero_br(brasil_massa_vermicompostagem, 1)
        ],
        "Percentual": [
            "100%",
            f"{formatar_numero_br((brasil_massa_compostagem/brasil_total_massa*100), 1)}%" if brasil_total_massa > 0 else "0%",
            f"{formatar_numero_br((brasil_massa_vermicompostagem/brasil_total_massa*100), 1)}%" if brasil_total_massa > 0 else "0%"
        ]
    }
    
    df_distribuicao_nacional = pd.DataFrame(distribuicao_data)
    st.dataframe(df_distribuicao_nacional, use_container_width=True)

st.markdown("---")

# =========================================================
# Seção para seleção de município (mantida idêntica)
# =========================================================
st.header("🏙️ Análise por Município")

municipios = sorted(df_clean[COL_MUNICIPIO].dropna().unique())
if len(municipios) == 0:
    st.error("❌ Não foram encontrados municípios no dataset.")
    st.stop()

municipio = st.selectbox("Selecione o município para análise detalhada:", municipios)

df_mun = df_clean[df_clean[COL_MUNICIPIO] == municipio]

if df_mun.empty:
    st.warning(f"⚠️ Não foram encontrados dados para {municipio}")
    st.stop()

st.subheader(f"📍 {municipio}")

# Processar dados do município selecionado (código original mantido)
resultados = []
mun_total_massa = 0
mun_massa_compostagem = 0
mun_massa_vermicompostagem = 0
mun_total_tipos = 0
mun_aptos_compostagem = 0
mun_aptos_vermicompostagem = 0

for _, row in df_mun.iterrows():
    categoria, comp, vermi, justificativa = classificar_coleta(row.get(COL_TIPO_COLETA, None))
    massa_valor = row.get(COL_MASSA, None)
    
    try:
        massa_float = float(massa_valor) if not pd.isna(massa_valor) else 0
    except:
        massa_float = 0
    
    mun_total_massa += massa_float
    mun_total_tipos += 1
    
    if comp:
        mun_massa_compostagem += massa_float
        mun_aptos_compostagem += 1
    
    if vermi:
        mun_massa_vermicompostagem += massa_float
        mun_aptos_vermicompostagem += 1

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
    # Síntese municipal (mantida idêntica)
    # =========================================================
    st.subheader("📊 Síntese técnica municipal")
    
    tem_compostagem = any(df_result["Compostagem"] == "✅")
    tem_vermicompostagem = any(df_result["Vermicompostagem"] == "✅")
    
    # Resumo de massas
    st.markdown("### 📦 Resumo das Massas Coletadas")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Massa total coletada", f"{formatar_numero_br(mun_total_massa, 1)} t")
    
    with col2:
        st.metric("Massa apta para compostagem", f"{formatar_numero_br(mun_massa_compostagem, 1)} t")
    
    with col3:
        st.metric("Massa apta para vermicompostagem", f"{formatar_numero_br(mun_massa_vermicompostagem, 1)} t")
    
    with col4:
        if mun_total_massa > 0:
            percentual_comp = (mun_massa_compostagem / mun_total_massa * 100)
            st.metric("% Apto para compostagem", f"{formatar_numero_br(percentual_comp, 1)}%")
        else:
            st.metric("% Apto para compostagem", "0%")
    
    # Potencial técnico
    st.markdown("### 🔍 Potencial Técnico")
    col1, col2 = st.columns(2)
    
    with col1:
        if tem_compostagem:
            st.success("✔️ **Potencial técnico para compostagem**")
            if mun_massa_compostagem > 0:
                st.info(f"**Volume disponível:** {formatar_numero_br(mun_massa_compostagem, 1)} t/ano")
        else:
            st.error("❌ Não foi identificado potencial técnico para compostagem.")
    
    with col2:
        if tem_vermicompostagem:
            st.success("🐛 **Potencial técnico para vermicompostagem**")
            if mun_massa_vermicompostagem > 0:
                st.info(f"**Volume disponível:** {formatar_numero_br(mun_massa_vermicompostagem, 1)} t/ano")
        else:
            st.warning("⚠️ Não foram identificadas fontes adequadas para vermicompostagem.")
    
    # Tabela de distribuição
    if mun_total_massa > 0 and (mun_massa_compostagem > 0 or mun_massa_vermicompostagem > 0):
        st.markdown("### 📈 Distribuição das Massas")
        
        distribuicao_data = {
            "Categoria": ["Total Coletado", "Apto Compostagem", "Apto Vermicompostagem"],
            "Massa (t)": [
                formatar_numero_br(mun_total_massa, 1),
                formatar_numero_br(mun_massa_compostagem, 1),
                formatar_numero_br(mun_massa_vermicompostagem, 1)
            ]
        }
        df_distribuicao = pd.DataFrame(distribuicao_data)
        st.dataframe(df_distribuicao, use_container_width=True)
    
    # Estatísticas adicionais
    st.markdown("---")
    st.markdown("#### 📊 Estatísticas Detalhadas")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de tipos de coleta", formatar_numero_br(mun_total_tipos, 0))
    with col2:
        st.metric("Tipos aptos para compostagem", formatar_numero_br(mun_aptos_compostagem, 0))
    with col3:
        st.metric("Tipos aptos para vermicompostagem", formatar_numero_br(mun_aptos_vermicompostagem, 0))
    
else:
    st.warning("⚠️ Não foram encontrados registros de coleta para análise.")

# =========================================================
# Comparação com média nacional
# =========================================================
if not df_result.empty and brasil_total_massa > 0 and mun_total_massa > 0:
    st.markdown("---")
    st.subheader("📊 Comparação com Média Nacional")
    
    # Calcular médias
    media_massa_municipio_brasil = brasil_total_massa / total_municipios if total_municipios > 0 else 0
    percentual_comp_brasil = (brasil_massa_compostagem / brasil_total_massa * 100) if brasil_total_massa > 0 else 0
    percentual_comp_municipio = (mun_massa_compostagem / mun_total_massa * 100) if mun_total_massa > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if media_massa_municipio_brasil > 0:
            proporcao_massa = (mun_total_massa / media_massa_municipio_brasil) * 100
            if proporcao_massa > 100:
                st.metric("Massa vs Média Nacional", f"{formatar_numero_br(proporcao_massa, 1)}%", 
                         delta=f"+{formatar_numero_br(proporcao_massa-100, 1)}%")
            else:
                st.metric("Massa vs Média Nacional", f"{formatar_numero_br(proporcao_massa, 1)}%", 
                         delta=f"-{formatar_numero_br(100-proporcao_massa, 1)}%", delta_color="inverse")
    
    with col2:
        if percentual_comp_brasil > 0:
            diferenca_comp = percentual_comp_municipio - percentual_comp_brasil
            if diferenca_comp > 0:
                st.metric("% Compostagem vs Nacional", f"{formatar_numero_br(percentual_comp_municipio, 1)}%", 
                         delta=f"+{formatar_numero_br(diferenca_comp, 1)}%")
            else:
                st.metric("% Compostagem vs Nacional", f"{formatar_numero_br(percentual_comp_municipio, 1)}%", 
                         delta=f"{formatar_numero_br(diferenca_comp, 1)}%", delta_color="inverse")
    
    with col3:
        st.metric("Posição Nacional", f"Entre {formatar_numero_br(total_municipios, 0)} municípios")

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
    f"Dados atualizados | Total de municípios analisados: {formatar_numero_br(total_municipios, 0)}"
)

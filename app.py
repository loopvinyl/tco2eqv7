import streamlit as st
import pandas as pd

# =========================================================
# Configuração da página
# =========================================================
st.set_page_config(
    page_title="Potencial de Compostagem de RSU",
    layout="wide"
)

st.title("🌱 Potencial de Compostagem e Vermicompostagem")
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
# Limpeza de dados
# =========================================================
# Filtrar linhas com dados válidos em município
df_clean = df.dropna(subset=[COL_MUNICIPIO])
df_clean[COL_MUNICIPIO] = df_clean[COL_MUNICIPIO].astype(str).str.strip()

# =========================================================
# Interface - Seleção de visão
# =========================================================
st.sidebar.header("🔍 Nível de Análise")

analise_nivel = st.sidebar.radio(
    "Selecione o nível de análise:",
    ["🇧🇷 Brasil (Visão Nacional)", "🏙️ Município Específico"]
)

# =========================================================
# VISÃO NACIONAL - BRASIL
# =========================================================
if analise_nivel == "🇧🇷 Brasil (Visão Nacional)":
    
    st.header("🇧🇷 Panorama Nacional - Potencial de Compostagem")
    
    # Calcula estatísticas nacionais
    total_municipios = df_clean[COL_MUNICIPIO].nunique()
    total_registros = len(df_clean)
    
    # Calcula totais de massa
    total_massa_nacional = df_clean[COL_MASSA].fillna(0).astype(float).sum()
    
    # Calcula distribuição por categoria
    categorias_nacionais = []
    for _, row in df_clean.iterrows():
        categoria, comp, vermi, justificativa = classificar_coleta(row.get(COL_TIPO_COLETA, None))
        massa_valor = row.get(COL_MASSA, 0)
        try:
            massa_float = float(massa_valor) if not pd.isna(massa_valor) else 0
        except:
            massa_float = 0
        
        categorias_nacionais.append({
            "categoria": categoria,
            "massa": massa_float,
            "compostagem": comp,
            "vermicompostagem": vermi
        })
    
    df_categorias_nacionais = pd.DataFrame(categorias_nacionais)
    
    # Agrega por categoria
    resumo_categorias = df_categorias_nacionais.groupby('categoria').agg({
        'massa': 'sum',
        'compostagem': lambda x: sum(x),
        'vermicompostagem': lambda x: sum(x)
    }).reset_index()
    
    resumo_categorias = resumo_categorias.rename(columns={
        'massa': 'Massa Total (t)',
        'compostagem': 'Registros Aptos Compostagem',
        'vermicompostagem': 'Registros Aptos Vermicompostagem'
    })
    
    # Calcula totais aptos
    massa_compostagem_nacional = resumo_categorias[
        resumo_categorias['Registros Aptos Compostagem'] > 0
    ]['Massa Total (t)'].sum()
    
    massa_vermicompostagem_nacional = resumo_categorias[
        resumo_categorias['Registros Aptos Vermicompostagem'] > 0
    ]['Massa Total (t)'].sum()
    
    # =========================================================
    # Métricas Nacionais
    # =========================================================
    st.subheader("📊 Métricas Nacionais Consolidadas")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Municípios Analisados", formatar_numero_br(total_municipios, 0))
    
    with col2:
        st.metric("Tipos de Coleta", formatar_numero_br(total_registros, 0))
    
    with col3:
        st.metric("Massa Total Coletada", f"{formatar_numero_br(total_massa_nacional, 0)} t")
    
    with col4:
        if total_massa_nacional > 0:
            percentual_comp_nacional = (massa_compostagem_nacional / total_massa_nacional * 100)
            st.metric("% Apto Compostagem", f"{formatar_numero_br(percentual_comp_nacional, 1)}%")
        else:
            st.metric("% Apto Compostagem", "0%")
    
    # =========================================================
    # Potencial Nacional
    # =========================================================
    st.subheader("🔍 Potencial Técnico Nacional")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.success(f"✅ **Potencial Nacional para Compostagem**")
        st.info(f"""
        **Volume disponível:** {formatar_numero_br(massa_compostagem_nacional, 0)} t/ano
        **Representa:** {formatar_numero_br((massa_compostagem_nacional/total_massa_nacional*100) if total_massa_nacional > 0 else 0, 1)}% da massa total
        """)
    
    with col2:
        st.success(f"🐛 **Potencial Nacional para Vermicompostagem**")
        st.info(f"""
        **Volume disponível:** {formatar_numero_br(massa_vermicompostagem_nacional, 0)} t/ano
        **Representa:** {formatar_numero_br((massa_vermicompostagem_nacional/total_massa_nacional*100) if total_massa_nacional > 0 else 0, 1)}% da massa total
        """)
    
    # =========================================================
    # Distribuição por Categoria
    # =========================================================
    st.subheader("📈 Distribuição Nacional por Categoria Técnica")
    
    # Formata a tabela
    resumo_categorias_formatado = resumo_categorias.copy()
    resumo_categorias_formatado['Massa Total (t)'] = resumo_categorias_formatado['Massa Total (t)'].apply(
        lambda x: formatar_numero_br(x, 0)
    )
    
    # Adiciona percentual da massa
    resumo_categorias_formatado['% da Massa Total'] = resumo_categorias['Massa Total (t)'].apply(
        lambda x: f"{formatar_numero_br((x/total_massa_nacional*100) if total_massa_nacional > 0 else 0, 1)}%"
    )
    
    st.dataframe(resumo_categorias_formatado, use_container_width=True)
    
    # =========================================================
    # Mapa de Calor de Potencial (simplificado)
    # =========================================================
    st.subheader("🗺️ Mapa de Potencial por Categoria")
    
    # Cria um resumo visual
    if total_massa_nacional > 0:
        categorias_ordenadas = resumo_categorias.sort_values('Massa Total (t)', ascending=False)
        
        for _, row in categorias_ordenadas.iterrows():
            categoria = row['categoria']
            massa = row['Massa Total (t)']
            percentual = (massa / total_massa_nacional * 100)
            
            col1, col2, col3 = st.columns([2, 3, 2])
            with col1:
                st.write(f"**{categoria}**")
            with col2:
                st.progress(min(percentual/100, 1.0))
            with col3:
                st.write(f"{formatar_numero_br(massa, 0)} t ({formatar_numero_br(percentual, 1)}%)")
    
    # =========================================================
    # Estatísticas Detalhadas
    # =========================================================
    st.markdown("---")
    st.subheader("📋 Estatísticas Detalhadas")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        municipios_com_organico = df_clean[
            df_clean[COL_TIPO_COLETA].astype(str).str.contains('orgânica|poda|verde|vegetal', case=False, na=False)
        ][COL_MUNICIPIO].nunique()
        st.metric("Municípios com coleta orgânica", formatar_numero_br(municipios_com_organico, 0))
    
    with col2:
        registros_aptos_comp = sum(df_categorias_nacionais['compostagem'])
        st.metric("Registros aptos compostagem", formatar_numero_br(registros_aptos_comp, 0))
    
    with col3:
        registros_aptos_verm = sum(df_categorias_nacionais['vermicompostagem'])
        st.metric("Registros aptos vermicompostagem", formatar_numero_br(registros_aptos_verm, 0))

# =========================================================
# VISÃO MUNICIPAL
# =========================================================
else:
    st.header("🏙️ Análise por Município")
    
    # Lista de municípios
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

# =========================================================
# Informações sobre os dados
# =========================================================
with st.expander("📚 Sobre os dados e metodologia"):
    st.markdown("""
    ### Metodologia de Classificação
    
    1. **Orgânico direto**: Resíduos vegetais limpos (poda, galhada, verde)
       - ✅ Apto para compostagem
       - ✅ Apto para vermicompostagem
    
    2. **Orgânico potencial**: Resíduos domiciliares/indiferenciados
       - ✅ Apto para compostagem (com triagem)
       - ❌ Não apto para vermicompostagem
    
    3. **Inapto**: Varrição, limpeza pública
       - ❌ Alta contaminação
       - ❌ Não recomendado para tratamento biológico
    
    4. **Não orgânico**: Coleta seletiva, recicláveis
       - ❌ Destinado à reciclagem
       - ❌ Não apto para tratamento biológico
    
    ### Base de Dados
    - **Fonte**: Sistema Nacional de Informações sobre Saneamento (SNIS)
    - **Período**: Dados mais recentes disponíveis
    - **Abrangência**: Municípios brasileiros com informações cadastradas
    
    ### Limitações
    - Dados dependem da qualidade do preenchimento municipal
    - Massas podem estar subestimadas ou superestimadas
    - Classificação automática pode não capturar nuances locais
    """)

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
            return "0"
        
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
# Interface - Seleção única
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
tipos_coleta = 0
tipos_aptos_compostagem = 0
tipos_aptos_vermicompostagem = 0

for _, row in df_mun.iterrows():
    categoria, comp, vermi, justificativa = classificar_coleta(row.get(COL_TIPO_COLETA, None))
    massa_valor = row.get(COL_MASSA, None)

    try:
        massa_float = float(massa_valor) if not pd.isna(massa_valor) else 0
    except:
        massa_float = 0

    total_massa += massa_float
    tipos_coleta += 1
    
    if comp:
        massa_compostagem += massa_float
        tipos_aptos_compostagem += 1
    
    if vermi:
        massa_vermicompostagem += massa_float
        tipos_aptos_vermicompostagem += 1

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
# Exibição - Mantendo o formato do seu exemplo
# =========================================================
if not df_result.empty:
    # Mostrar tabela (para Brasil pode ser muito grande, mas vamos manter)
    if municipio == "BRASIL – Todos os municípios":
        st.info(f"ℹ️ Exibindo dados agregados de {formatar_numero_br(len(df_result), 0)} registros de coleta de todo o Brasil.")
        # Para Brasil, talvez mostrar uma amostra ou resumo
        with st.expander("🔍 Ver detalhes de todos os registros (pode ser extenso)"):
            st.dataframe(df_result, use_container_width=True)
    else:
        st.dataframe(df_result, use_container_width=True)

    st.subheader("📊 Síntese técnica")

    # Métricas principais
    col1, col2, col3 = st.columns(3)

    perc_comp = (massa_compostagem / total_massa * 100) if total_massa > 0 else 0
    perc_vermi = (massa_vermicompostagem / total_massa * 100) if total_massa > 0 else 0

    col1.metric(
        "Massa total coletada",
        f"{formatar_numero_br(total_massa, 1)} t"
    )

    col2.metric(
        "Massa apta para compostagem",
        f"{formatar_numero_br(massa_compostagem, 1)} t",
        f"{formatar_numero_br(perc_comp, 1)}%"
    )

    col3.metric(
        "Massa apta para vermicompostagem",
        f"{formatar_numero_br(massa_vermicompostagem, 1)} t",
        f"{formatar_numero_br(perc_vermi, 1)}%"
    )

    # Métricas secundárias
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    col1.metric("Tipos de coleta analisados", formatar_numero_br(tipos_coleta, 0))
    
    col2.metric(
        "Tipos aptos para compostagem", 
        formatar_numero_br(tipos_aptos_compostagem, 0),
        f"{formatar_numero_br((tipos_aptos_compostagem/tipos_coleta*100) if tipos_coleta > 0 else 0, 1)}%"
    )
    
    col3.metric(
        "Tipos aptos para vermicompostagem", 
        formatar_numero_br(tipos_aptos_vermicompostagem, 0),
        f"{formatar_numero_br((tipos_aptos_vermicompostagem/tipos_coleta*100) if tipos_coleta > 0 else 0, 1)}%"
    )

    # Potencial técnico
    st.markdown("### 🔍 Potencial Técnico")
    
    tem_compostagem = massa_compostagem > 0
    tem_vermicompostagem = massa_vermicompostagem > 0
    
    if tem_compostagem:
        st.success(f"✔️ **Potencial para compostagem** — {formatar_numero_br(massa_compostagem, 1)} t/ano disponíveis")
    else:
        st.error("❌ Não foi identificado potencial para compostagem.")
    
    if tem_vermicompostagem:
        st.success(f"🐛 **Potencial para vermicompostagem** — {formatar_numero_br(massa_vermicompostagem, 1)} t/ano disponíveis")
    else:
        st.warning("⚠️ Não foram identificadas fontes adequadas para vermicompostagem.")

    # Tabela de distribuição
    if total_massa > 0:
        st.markdown("### 📈 Distribuição das Massas")
        
        distribuicao_data = {
            "Categoria": ["Total Coletado", "Apto Compostagem", "Apto Vermicompostagem"],
            "Massa (t)": [
                formatar_numero_br(total_massa, 1),
                formatar_numero_br(massa_compostagem, 1),
                formatar_numero_br(massa_vermicompostagem, 1)
            ],
            "Percentual": [
                "100%",
                f"{formatar_numero_br(perc_comp, 1)}%",
                f"{formatar_numero_br(perc_vermi, 1)}%"
            ]
        }
        
        df_distribuicao = pd.DataFrame(distribuicao_data)
        st.dataframe(df_distribuicao, use_container_width=True)
    
    # Informação adicional para Brasil
    if municipio == "BRASIL – Todos os municípios":
        total_municipios = df_clean[COL_MUNICIPIO].nunique()
        st.markdown("---")
        st.info(f"**ℹ️ Dados nacionais agregados de {formatar_numero_br(total_municipios, 0)} municípios brasileiros.**")

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

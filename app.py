import streamlit as st
import pandas as pd
import unicodedata

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
e avalia o **potencial técnico e climático** de resíduos sólidos urbanos.
""")

# =========================================================
# Constantes Técnicas (Baseadas no Script Modelo - AR6 IPCC)
# =========================================================
GWP_CH4_20 = 79.7  # Potencial de Aquecimento Global do Metano (20 anos)
ANOS_SIMULACAO = 20 # Horizonte temporal padrão do modelo

# =========================================================
# Funções auxiliares
# =========================================================
def formatar_numero_br(valor, casas_decimais=2):
    if pd.isna(valor) or valor is None:
        return "Não informado"
    try:
        num = float(valor)
        formato = f"{{:,.{casas_decimais}f}}".format(num)
        partes = formato.split(".")
        milhar = partes[0].replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{milhar},{partes[1]}"
    except:
        return "Não informado"

def formatar_massa_br(valor):
    if pd.isna(valor) or valor is None:
        return "Não informado"
    return f"{formatar_numero_br(valor)} t"

def normalizar_texto(txt):
    if pd.isna(txt):
        return ""
    txt = unicodedata.normalize("NFKD", str(txt))
    txt = txt.encode("ASCII", "ignore").decode("utf-8")
    return txt.upper().strip()

# =========================================================
# Funções de emissões de CH4 (Yang et al. 2017)
# =========================================================
def ch4_compostagem_total(massa_kg):
    return massa_kg * 0.0004  # kg CH4 / kg resíduo

def ch4_vermicompostagem_total(massa_kg):
    return massa_kg * 0.00015  # kg CH4 / kg resíduo

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
COL_DESTINO = df.columns[28]  # Coluna AC

# =========================================================
# Classificação técnica
# =========================================================
def classificar_coleta(texto):
    if pd.isna(texto):
        return ("Não informado", False, False, "Tipo não informado")

    t = str(texto).lower()
    palavras = {
        "poda": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "galhada": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "verde": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "orgânica": ("Orgânico direto", True, True, "Orgânico segregado"),
        "domiciliar": ("Orgânico potencial", True, False, "Exige triagem"),
        "varrição": ("Inapto", False, False, "Alta contaminação"),
        "seletiva": ("Não orgânico", False, False, "Recicláveis")
    }
    for p, c in palavras.items():
        if p in t:
            return c
    return ("Indefinido", False, False, "Não classificado")

# =========================================================
# Limpeza
# =========================================================
df_clean = df.dropna(subset=[COL_MUNICIPIO])
df_clean[COL_MUNICIPIO] = df_clean[COL_MUNICIPIO].astype(str).str.strip()

# =========================================================
# Interface
# =========================================================
municipios = ["BRASIL – Todos os municípios"] + sorted(df_clean[COL_MUNICIPIO].unique())
municipio = st.selectbox("Selecione o município:", municipios)

df_mun = df_clean.copy() if municipio == municipios[0] else df_clean[df_clean[COL_MUNICIPIO] == municipio]
st.subheader("🇧🇷 Brasil — Síntese Nacional de RSU" if municipio == municipios[0] else f"📍 {municipio}")

# =========================================================
# Tabela principal
# =========================================================
resultados = []
for _, row in df_mun.iterrows():
    categoria, comp, vermi, just = classificar_coleta(row[COL_TIPO_COLETA])
    massa = pd.to_numeric(row[COL_MASSA], errors="coerce") or 0

    resultados.append({
        "Tipo de coleta": row[COL_TIPO_COLETA],
        "Massa": formatar_massa_br(massa),
        "Categoria": categoria,
        "Compostagem": "✅" if comp else "❌",
        "Vermicompostagem": "✅" if vermi else "❌",
        "Justificativa": just
    })

st.dataframe(pd.DataFrame(resultados), use_container_width=True)

# =========================================================
# 🌳 Destinação e Impacto Climático
# =========================================================
st.markdown("---")
st.subheader("🌳 Destinação das podas e galhadas de áreas verdes")

df_podas = df_mun[df_mun[COL_TIPO_COLETA].astype(str).str.contains("áreas verdes públicas", case=False, na=False)].copy()

if not df_podas.empty:
    df_podas["MASSA_FLOAT"] = pd.to_numeric(df_podas[COL_MASSA], errors="coerce").fillna(0)
    total_podas = df_podas["MASSA_FLOAT"].sum()
    
    # Agrupamento por destino
    df_podas_destino = df_podas.groupby(COL_DESTINO)["MASSA_FLOAT"].sum().reset_index()
    
    massa_aterro_t = df_podas_destino.loc[
        df_podas_destino[COL_DESTINO].apply(normalizar_texto) == "ATERRO SANITARIO",
        "MASSA_FLOAT"
    ].sum()

    if massa_aterro_t > 0:
        # --- CÁLCULO BASEADO NO MODELO DE 20 ANOS ---
        # Parâmetros IPCC 2006 simplificados para Horizonte de 20 anos
        DOC, MCF, F, OX, Ri = 0.15, 1.0, 0.5, 0.1, 0.0
        DOCf = 0.0147 * ANOS_SIMULACAO + 0.28 
        massa_kg = massa_aterro_t * 1000
        
        # 1. Emissões no Aterro (Total acumulado e Média Anual)
        ch4_aterro_t = (massa_kg * DOC * DOCf * MCF * F * (16/12) * (1-Ri) * (1-OX)) / 1000
        co2eq_aterro_total = ch4_aterro_t * GWP_CH4_20
        co2eq_aterro_ano = co2eq_aterro_total / ANOS_SIMULACAO

        # 2. Emissões na Compostagem (Yang et al. 2017)
        ch4_comp_t = ch4_compostagem_total(massa_kg) / 1000
        co2eq_comp_total = ch4_comp_t * GWP_CH4_20
        co2eq_comp_ano = co2eq_comp_total / ANOS_SIMULACAO

        # 3. Emissões Evitadas (Média Anual)
        emissao_evitada_total = co2eq_aterro_total - co2eq_comp_total
        emissao_evitada_ano = emissao_evitada_total / ANOS_SIMULACAO

        # --- EXIBIÇÃO DAS MÉTRICAS ---
        st.write(f"**Análise de Impacto Climático (GWP20 - Horizonte de {ANOS_SIMULACAO} anos)**")
        
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Massa no Aterro", f"{formatar_numero_br(massa_aterro_t)} t")
        with m2:
            st.metric("Total Evitado (20 anos)", f"{formatar_numero_br(emissao_evitada_total)} tCO₂eq")
        with m3:
            st.metric("Média Evitada por Ano", f"{formatar_numero_br(emissao_evitada_ano)} tCO₂eq/ano", delta="Redução")

        st.info(f"💡 De acordo com o modelo, o desvio de podas para compostagem evita, em média, a emissão de **{formatar_numero_br(emissao_evitada_ano)} toneladas de CO₂eq por ano**.")
        
        st.caption(f"Cálculos utilizam GWP20={GWP_CH4_20} (IPCC AR6) e fatores de emissão de Yang et al. (2017).")
    else:
        st.info("Não há massa de podas destinada a aterro sanitário para calcular emissões evitadas.")
else:
    st.info("Não foram encontrados dados de podas/áreas verdes para este município.")

# =========================================================
# Rodapé
# =========================================================
st.markdown("---")
st.caption("Fonte: SNIS – Sistema Nacional de Informações sobre Saneamento. Metodologia de cálculo climatológico baseada no horizonte de 20 anos.")

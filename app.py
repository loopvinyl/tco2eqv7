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
e avalia o **potencial técnico para compostagem e vermicompostagem**
de resíduos sólidos urbanos.
""")

# =========================================================
# Funções auxiliares (MANTIDAS IDENTICAS)
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

def classificar_tipo_aterro(mcf):
    if mcf >= 1.0:
        return "Aterro Sanitário (Gerenciado)"
    elif mcf >= 0.5:
        return "Aterro Controlado"
    elif mcf >= 0.4:
        return "Lixão / Vazadouro"
    else:
        return "Não Aterro / Outros"

# =========================================================
# Funções de emissões de CH4 (MANTIDAS IDENTICAS)
# =========================================================
def ch4_compostagem_total(massa_kg):
    return massa_kg * 0.0004  # kg CH4 / kg resíduo

def ch4_vermicompostagem_total(massa_kg):
    return massa_kg * 0.00015  # kg CH4 / kg resíduo

def determinar_mcf_por_destino(destino):
    if pd.isna(destino):
        return 0.0
    destino_norm = normalizar_texto(destino)
    if "ATERRO SANITARIO" in destino_norm:
        return 1.0
    elif "ATERRO CONTROLADO" in destino_norm:
        return 0.5
    elif any(x in destino_norm for x in ["LIXAO", "VAZADOURO", "DESCARGA DIRETA"]):
        return 0.4
    return 0.0

def calcular_emissoes_aterro(massa_t, mcf, temperatura=25.0):
    DOC = 0.15
    DOCf = 0.0147 * temperatura + 0.28
    F = 0.5
    OX = 0.1
    Ri = 0.0
    massa_kg = massa_t * 1000
    ch4_kg = massa_kg * DOC * DOCf * mcf * F * (16/12) * (1 - Ri) * (1 - OX)
    return ch4_kg / 1000

# =========================================================
# Carga e Processamento (MANTIDOS IDENTICOS)
# =========================================================
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/loopvinyl/tco2eqv7/main/rsuBrasil.xlsx"
    df = pd.read_excel(url, sheet_name="Manejo_Coleta_e_Destinação", header=13)
    df = df.dropna(how="all")
    df.columns = [str(col).strip() for col in df.columns]
    return df

df = load_data()
df = df.rename(columns={
    df.columns[2]: "MUNICÍPIO",
    df.columns[17]: "TIPO_COLETA_EXECUTADA",
    df.columns[24]: "MASSA_COLETADA"
})

COL_MUNICIPIO, COL_TIPO_COLETA, COL_MASSA = "MUNICÍPIO", "TIPO_COLETA_EXECUTADA", "MASSA_COLETADA"
COL_DESTINO = df.columns[28]

def classificar_coleta(texto):
    if pd.isna(texto): return ("Não informado", False, False, "Tipo não informado")
    t = str(texto).lower()
    palavras = {
        "poda": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "galhada": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "verde": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "orgânica": ("Orgânico direto", True, True, "Orgânico segregado"),
        "domiciliar": ("Orgânico potencial", True, False, "Exige triagem"),
    }
    for p, c in palavras.items():
        if p in t: return c
    return ("Indefinido", False, False, "Não classificado")

df_clean = df.dropna(subset=[COL_MUNICIPIO])
df_clean[COL_MUNICIPIO] = df_clean[COL_MUNICIPIO].astype(str).str.strip()

municipios = ["BRASIL – Todos os municípios"] + sorted(df_clean[COL_MUNICIPIO].unique())
municipio = st.selectbox("Selecione o município:", municipios)
df_mun = df_clean.copy() if municipio == municipios[0] else df_clean[df_clean[COL_MUNICIPIO] == municipio]

# =========================================================
# CÁLCULOS E SEPARAÇÃO DE CENÁRIOS (ALTERAÇÃO AQUI)
# =========================================================
st.subheader("🌳 Destinação das podas e galhadas")
df_podas = df_mun[df_mun[COL_TIPO_COLETA].astype(str).str.contains("áreas verdes públicas", case=False, na=False)].copy()

if not df_podas.empty:
    df_podas["MASSA_FLOAT"] = pd.to_numeric(df_podas[COL_MASSA], errors="coerce").fillna(0)
    df_podas_destino = df_podas.groupby(COL_DESTINO)["MASSA_FLOAT"].sum().reset_index()
    df_podas_destino["MCF"] = df_podas_destino[COL_DESTINO].apply(determinar_mcf_por_destino)

    ch4_total_aterro_t = 0
    massa_total_aterro_t = 0
    
    for _, row in df_podas_destino.iterrows():
        if row["MCF"] > 0:
            ch4_total_aterro_t += calcular_emissoes_aterro(row["MASSA_FLOAT"], row["MCF"])
            massa_total_aterro_t += row["MASSA_FLOAT"]

    if massa_total_aterro_t > 0:
        # SEPARAÇÃO DOS CENÁRIOS
        massa_kg = massa_total_aterro_t * 1000
        GWP100 = 28

        # 1. Cenário Compostagem Termofílica
        ch4_emitido_comp = ch4_compostagem_total(massa_kg) / 1000
        ch4_evitado_comp = ch4_total_aterro_t - ch4_emitido_comp
        co2e_evitado_comp = ch4_evitado_comp * GWP100

        # 2. Cenário Vermicompostagem
        ch4_emitido_vermi = ch4_vermicompostagem_total(massa_kg) / 1000
        ch4_evitado_vermi = ch4_total_aterro_t - ch4_emitido_vermi
        co2e_evitado_vermi = ch4_evitado_vermi * GWP100

        st.markdown("### 📊 Emissões Evitadas por Tecnologia")
        
        tab1, tab2 = st.tabs(["🔥 Compostagem Termofílica", "🪱 Vermicompostagem"])
        
        with tab1:
            st.info("Cenário baseado em pilhas aeróbicas com revolvimento (Yang et al. 2017)")
            c1, c2, c3 = st.columns(3)
            c1.metric("CH₄ Evitado", f"{formatar_numero_br(ch4_evitado_comp, 1)} t")
            c2.metric("CO₂e Evitado", f"{formatar_numero_br(co2e_evitado_comp, 1)} t")
            c3.metric("Eficiência", f"{formatar_numero_br((ch4_evitado_comp/ch4_total_aterro_t)*100, 1)}%")

        with tab2:
            st.info("Cenário baseado em tratamento com minhocas (Yang et al. 2017)")
            v1, v2, v3 = st.columns(3)
            v1.metric("CH₄ Evitado", f"{formatar_numero_br(ch4_evitado_vermi, 1)} t")
            v2.metric("CO₂e Evitado", f"{formatar_numero_br(co2e_evitado_vermi, 1)} t")
            v3.metric("Eficiência", f"{formatar_numero_br((ch4_evitado_vermi/ch4_total_aterro_t)*100, 1)}%")
            
        st.caption(f"Cálculo baseado em {formatar_numero_br(massa_total_aterro_t)} t de podas que atualmente vão para aterros.")

else:
    st.info("Sem dados de podas para este município.")

# [MANTIDO O RESTANTE DO CÓDIGO DE RODAPÉ E NOTAS]

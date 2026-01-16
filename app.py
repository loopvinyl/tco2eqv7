import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(
    page_title="Potencial de Compostagem de RSU",
    layout="wide"
)

# =========================================================
# FORMATAÇÃO BRASILEIRA CORRIGIDA
# =========================================================
def formatar_br(valor, casas=2):
    try:
        v = float(valor)
        # Formata com separador de milhares (ponto) e decimal (vírgula)
        return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "Não informado"

def formatar_massa(valor):
    try:
        return f"{formatar_br(valor, 0)} t"
    except:
        return "Não informado"

def formatar_monetario(valor, simbolo="R$", casas=2):
    try:
        return f"{simbolo} {formatar_br(valor, casas)}"
    except:
        return "Não informado"

# =========================================================
# COTAÇÃO AUTOMÁTICA – CARBONO
# =========================================================
def obter_cotacao_carbono_investing():
    try:
        url = "https://www.investing.com/commodities/carbon-emissions"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"
        }
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.content, "html.parser")

        seletores = [
            '[data-test="instrument-price-last"]',
            '.text-2xl',
            '.instrument-price-last'
        ]

        for s in seletores:
            el = soup.select_one(s)
            if el:
                preco = el.text.strip().replace(",", "")
                return float(preco), "€", "Investing.com", True

        return None, None, None, False
    except:
        return None, None, None, False

def obter_cotacao_carbono():
    preco, moeda, fonte, ok = obter_cotacao_carbono_investing()
    if ok:
        return preco, moeda, fonte
    return 85.5, "€", "Referência"

def obter_cotacao_euro_real():
    try:
        r = requests.get("https://economia.awesomeapi.com.br/last/EUR-BRL", timeout=10)
        data = r.json()
        return float(data["EURBRL"]["bid"]), True
    except:
        return 5.50, False

# =========================================================
# INICIALIZAÇÃO SEGURA DO SESSION STATE
# =========================================================
if "preco_carbono" not in st.session_state:
    preco, moeda, fonte = obter_cotacao_carbono()
    eur_brl, _ = obter_cotacao_euro_real()

    st.session_state["preco_carbono"] = preco
    st.session_state["moeda_carbono"] = moeda
    st.session_state["fonte_carbono"] = fonte
    st.session_state["eur_brl"] = eur_brl

# =========================================================
# TÍTULO
# =========================================================
st.title("🌱 Potencial de Compostagem e Vermicompostagem por Município")
st.markdown(
    "Avaliação técnica, ambiental e econômica do desvio de **podas e galhadas de áreas verdes públicas** "
    "do **aterro sanitário** para **compostagem e vermicompostagem**."
)

# =========================================================
# CARGA DOS DADOS
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
    df.columns = [str(c).strip() for c in df.columns]
    return df

df = load_data()

# =========================================================
# COLUNAS REAIS DO EXCEL
# =========================================================
COL_TIPO = df.columns[17]
COL_MASSA = df.columns[24]
COL_DESTINO = df.columns[28]

df["MASSA_FLOAT"] = pd.to_numeric(df[COL_MASSA], errors="coerce").fillna(0)

# =========================================================
# FILTRO – PODAS E GALHADAS
# =========================================================
df_podas = df[
    df[COL_TIPO]
    .astype(str)
    .str.contains("podas|galhadas|áreas verdes", case=False, na=False)
]

massa_total_podas = df_podas["MASSA_FLOAT"].sum()

st.subheader("🌳 Destinação das podas e galhadas de áreas verdes públicas")
st.metric("Massa total de podas e galhadas", formatar_massa(massa_total_podas))

dist = (
    df_podas
    .groupby(COL_DESTINO, dropna=False)["MASSA_FLOAT"]
    .sum()
    .reset_index()
)

dist["Percentual (%)"] = dist["MASSA_FLOAT"] / massa_total_podas * 100
dist = dist.sort_values("Percentual (%)", ascending=False)

dist["Massa (t)"] = dist["MASSA_FLOAT"].apply(lambda x: formatar_br(x, 0))
dist["Percentual (%)"] = dist["Percentual (%)"].apply(lambda x: formatar_br(x, 2))

st.dataframe(
    dist[[COL_DESTINO, "Massa (t)", "Percentual (%)"]],
    use_container_width=True
)

# =========================================================
# METANO – ATERRO SANITÁRIO
# =========================================================
df_aterro = df_podas[
    df_podas[COL_DESTINO]
    .astype(str)
    .str.lower()
    .str.contains("aterro sanit")
]

massa_aterro = df_aterro["MASSA_FLOAT"].sum()

FATOR_CH4 = 0.062
GWP_CH4 = 28

ch4_gerado = massa_aterro * FATOR_CH4
co2eq_aterro = ch4_gerado * GWP_CH4

st.subheader("🔥 Potencial de geração de metano (CH₄) – Aterro Sanitário")
st.metric("Massa no aterro", formatar_massa(massa_aterro))
st.metric("CH₄ potencial", f"{formatar_br(ch4_gerado, 2)} t CH₄")
st.metric("Emissões", f"{formatar_br(co2eq_aterro, 2)} tCO₂eq")

# =========================================================
# EMISSÕES EVITADAS
# =========================================================
RED_COMP = 0.90
RED_VERMI = 0.95

evitado_comp = co2eq_aterro * RED_COMP
evitado_vermi = co2eq_aterro * RED_VERMI

st.subheader("♻️ Emissões Evitadas pelo Desvio do Ateriro")

c1, c2 = st.columns(2)
with c1:
    st.metric("Compostagem", f"{formatar_br(evitado_comp, 2)} tCO₂eq")
with c2:
    st.metric("Vermicompostagem", f"{formatar_br(evitado_vermi, 2)} tCO₂eq")

# =========================================================
# CONVERSÃO DE tCO2eq PARA € E R$
# =========================================================
st.subheader("💱 Conversão de tCO₂eq para Euros e Reais")

tab1, tab2 = st.tabs(["💰 Mercado de Carbono", "💱 Câmbio"])

with tab1:
    st.metric(
        "Preço do Carbono (tCO₂eq)",
        f"{st.session_state['moeda_carbono']} {formatar_br(st.session_state['preco_carbono'], 2)}",
        help=f"Fonte: {st.session_state['fonte_carbono']}"
    )

with tab2:
    st.metric(
        "Euro (EUR → BRL)",
        f"R$ {formatar_br(st.session_state['eur_brl'], 2)}"
    )

st.markdown(
    f"**Preço do carbono em Reais:** R$ "
    f"{formatar_br(st.session_state['preco_carbono'] * st.session_state['eur_brl'], 2)} / tCO₂eq"
)

# =========================================================
# VALORAÇÃO ECONÔMICA – 20 ANOS (CORRIGIDO)
# =========================================================
st.subheader("💰 Valor Econômico das Emissões Evitadas (20 anos)")

anos = 20
preco = st.session_state["preco_carbono"]
eurbrl = st.session_state["eur_brl"]

# Criar um layout organizado com colunas
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🍃 Compostagem")
    
    total_comp = evitado_comp * anos
    valor_eur_comp = total_comp * preco
    valor_brl_comp = valor_eur_comp * eurbrl
    
    st.markdown(f"**tCO₂eq evitado (20 anos):** {formatar_br(total_comp, 2)}")
    st.markdown(f"**Valor econômico (€):** € {formatar_br(valor_eur_comp, 2)}")
    st.markdown(f"**Valor econômico (R$):** R$ {formatar_br(valor_brl_comp, 2)}")

with col2:
    st.markdown("### 🐛 Vermicompostagem")
    
    total_vermi = evitado_vermi * anos
    valor_eur_vermi = total_vermi * preco
    valor_brl_vermi = valor_eur_vermi * eurbrl
    
    st.markdown(f"**tCO₂eq evitado (20 anos):** {formatar_br(total_vermi, 2)}")
    st.markdown(f"**Valor econômico (€):** € {formatar_br(valor_eur_vermi, 2)}")
    st.markdown(f"**Valor econômico (R$):** R$ {formatar_br(valor_brl_vermi, 2)}")

# =========================================================
# RESUMO DOS VALORES
# =========================================================
st.subheader("📊 Resumo Comparativo")

resumo_data = {
    "Tecnologia": ["Compostagem", "Vermicompostagem"],
    "tCO₂eq/ano": [formatar_br(evitado_comp, 2), formatar_br(evitado_vermi, 2)],
    "tCO₂eq/20 anos": [formatar_br(total_comp, 2), formatar_br(total_vermi, 2)],
    "Valor (€)": [formatar_br(valor_eur_comp, 2), formatar_br(valor_eur_vermi, 2)],
    "Valor (R$)": [formatar_br(valor_brl_comp, 2), formatar_br(valor_brl_vermi, 2)]
}

resumo_df = pd.DataFrame(resumo_data)
st.dataframe(resumo_df, use_container_width=True)

# =========================================================
# RODAPÉ
# =========================================================
st.markdown("---")
st.caption(
    "Cálculos baseados em fatores médios do IPCC. "
    "Preço do carbono e câmbio obtidos automaticamente em tempo real. "
    "Resultados indicativos para planejamento, viabilidade e políticas públicas."
)

import pandas as pd

# =========================================================
# 1. PARÂMETROS GERAIS (INVENTÁRIO)
# =========================================================

# GWP – IPCC AR6 (20 anos, conservador para resíduos)
GWP_CH4 = 79.7
GWP_N2O = 273

# Aterro sanitário (IPCC 2006)
MCF = 1.0
F = 0.5
OX = 0.1
DOCF = 0.5

# Compostagem (valores médios literatura – Yang et al.)
FATOR_CH4_COMPOST = 0.004   # t CH4 / t resíduo
FATOR_N2O_COMPOST = 0.0003  # t N2O / t resíduo

# =========================================================
# 2. FATORES POR TIPO DE RESÍDUO
# =========================================================

RESIDUOS = {
    "podas": {
        "DOC": 0.20,
        "descricao": "Podas e galhadas urbanas"
    },
    "organico_domiciliar": {
        "DOC": 0.15,
        "descricao": "Resíduo orgânico domiciliar"
    },
    "feira": {
        "DOC": 0.18,
        "descricao": "Resíduos de feiras livres"
    }
}

# =========================================================
# 3. FUNÇÕES DE CÁLCULO
# =========================================================

def emissoes_aterro(massa_t, DOC):
    """
    Emissões de CH4 no aterro (tCO2e)
    """
    ch4_t = massa_t * DOC * DOCF * MCF * F * (16/12) * (1 - OX)
    co2e = ch4_t * GWP_CH4
    return co2e


def emissoes_compostagem(massa_t):
    """
    Emissões residuais da compostagem (tCO2e)
    """
    ch4 = massa_t * FATOR_CH4_COMPOST
    n2o = massa_t * FATOR_N2O_COMPOST
    co2e = ch4 * GWP_CH4 + n2o * GWP_N2O
    return co2e


def calcular_credito(massa_t, tipo_residuo):
    """
    Crédito de carbono líquido
    """
    DOC = RESIDUOS[tipo_residuo]["DOC"]

    baseline = emissoes_aterro(massa_t, DOC)
    projeto = emissoes_compostagem(massa_t)
    reducao = baseline - projeto

    return baseline, projeto, reducao

# =========================================================
# 4. VALORAÇÃO ECONÔMICA (HONESTA)
# =========================================================

PRECOS = {
    "conservador": 5,   # €/tCO2e
    "medio": 12,
    "otimista": 25
}

def valorar(reducao_tco2e):
    valores = {}
    for cenario, preco in PRECOS.items():
        valores[cenario] = reducao_tco2e * preco
    return valores

# =========================================================
# 5. EXECUÇÃO DO CENÁRIO
# =========================================================

# >>>>>>>>>>>>>>>> AJUSTE AQUI <<<<<<<<<<<<<<<<
massa_anual = 12000  # toneladas/ano
tipo = "podas"
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

baseline, projeto, reducao = calcular_credito(massa_anual, tipo)
valores = valorar(reducao)

# =========================================================
# 6. RESULTADOS
# =========================================================

resultado = pd.DataFrame({
    "Indicador": [
        "Emissões no aterro (baseline)",
        "Emissões da compostagem (projeto)",
        "Redução líquida de emissões"
    ],
    "tCO2e": [
        round(baseline, 2),
        round(projeto, 2),
        round(reducao, 2)
    ]
})

print("\n📊 RESULTADO AMBIENTAL")
print(resultado)

print("\n💰 VALOR POTENCIAL DE CRÉDITOS (€)")
for k, v in valores.items():
    print(f"- {k.capitalize():12}: € {v:,.2f}")

# =========================================================
# 7. SAÍDA PARA BI
# =========================================================

df_bi = pd.DataFrame({
    "residuo": [tipo],
    "massa_t_ano": [massa_anual],
    "baseline_tco2e": [baseline],
    "projeto_tco2e": [projeto],
    "reducao_tco2e": [reducao],
    "valor_conservador_eur": [valores["conservador"]],
    "valor_medio_eur": [valores["medio"]],
    "valor_otimista_eur": [valores["otimista"]],
})

df_bi.to_csv("potencial_credito_carbono.csv", index=False)
print("\n📁 Arquivo gerado: potencial_credito_carbono.csv")

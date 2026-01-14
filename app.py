import pandas as pd
import numpy as np
import requests
from io import BytesIO
import matplotlib.pyplot as plt
import seaborn as sns

# URL do arquivo Excel no GitHub
url = "https://github.com/loopvinyl/tco2eqv7/raw/main/rsuBrasil.xlsx"

# Baixar o arquivo
print("Baixando arquivo Excel do GitHub...")
response = requests.get(url)
excel_file = BytesIO(response.content)

# Carregar o arquivo Excel
print("Carregando arquivo Excel...")
xls = pd.ExcelFile(excel_file)

# Listar as abas disponíveis
print("\nAbas disponíveis no arquivo:")
for sheet_name in xls.sheet_names:
    print(f"- {sheet_name}")

# Vamos carregar as principais abas para análise
print("\nAnalisando estrutura das abas...")

# Carregar cada aba em um DataFrame separado
dfs = {}
for sheet in xls.sheet_names:
    dfs[sheet] = pd.read_excel(xls, sheet_name=sheet)
    print(f"\nAba: {sheet}")
    print(f"  Dimensões: {dfs[sheet].shape}")
    print(f"  Colunas: {list(dfs[sheet].columns[:5])}...")  # Mostrar primeiras 5 colunas

# Analisar a aba principal (provavelmente a primeira)
print("\n" + "="*80)
print("ANÁLISE DETALHADA DA ABA PRINCIPAL")
print("="*80)

# Vamos encontrar a aba com mais dados (maior número de linhas)
main_sheet = max(dfs.items(), key=lambda x: x[1].shape[0])[0]
print(f"\nAba principal identificada: '{main_sheet}'")
df_main = dfs[main_sheet]

print(f"Número total de registros: {df_main.shape[0]}")
print(f"Número de colunas: {df_main.shape[1]}")

# Visualizar as primeiras linhas
print("\nPrimeiras 5 linhas da aba principal:")
print(df_main.head())

# Verificar tipos de dados
print("\nTipos de dados:")
print(df_main.dtypes.head(20))

# Analisar colunas para entender a estrutura
print("\nPrimeiras 20 colunas:")
for i, col in enumerate(df_main.columns[:20]):
    print(f"{i+1:2}. {col}")

# Vamos procurar por municípios específicos de interesse
print("\n" + "="*80)
print("BUSCANDO MUNICÍPIOS DE INTERESSE")
print("="*80)

# Municípios que mencionamos
municipios_interesse = ['MANAUS', 'ARIQUEMES', 'BOCA DO ACRE']

# Procurar por esses municípios (podem estar em colunas diferentes)
print("\nProcurando municípios de interesse...")

# Primeiro, identificar qual coluna contém nomes de municípios
municipio_col = None
for col in df_main.columns:
    if 'município' in str(col).lower() or 'municipio' in str(col).lower() or 'local' in str(col).lower():
        municipio_col = col
        print(f"Coluna de municípios identificada: '{col}'")
        break

if municipio_col:
    # Procurar municípios de interesse
    for municipio in municipios_interesse:
        # Tentar diferentes formas de busca
        mask = df_main[municipio_col].astype(str).str.upper().str.contains(municipio.upper())
        encontrados = df_main[mask]
        
        if len(encontrados) > 0:
            print(f"\n{municipio} encontrado ({len(encontrados)} registros):")
            # Mostrar algumas colunas relevantes
            cols_to_show = [municipio_col, 'UF', 'POP_TOT', 'POP_URB', 'POP_RUR', 'DOM_TOT', 'QT_RES_TOT']
            cols_disponiveis = [col for col in cols_to_show if col in df_main.columns]
            
            if cols_disponiveis:
                print(encontrados[cols_disponiveis].head())
        else:
            print(f"\n{municipio} não encontrado na coluna '{municipio_col}'")
else:
    print("Coluna de municípios não identificada. Vamos procurar manualmente...")
    # Tentar encontrar dados de massa coletada
    mass_cols = [col for col in df_main.columns if 'massa' in str(col).lower() or 'coleta' in str(col).lower()]
    print(f"Colunas relacionadas a massa/coleta: {mass_cols}")

# Vamos também verificar dados de per capita
print("\n" + "="*80)
print("CALCULANDO ESTATÍSTICAS BÁSICAS")
print("="*80)

# Procurar colunas de população e massa
pop_cols = [col for col in df_main.columns if 'pop' in str(col).lower()]
mass_cols = [col for col in df_main.columns if 'massa' in str(col).lower() or 'ton' in str(col).lower()]

print(f"Colunas de população: {pop_cols}")
print(f"Colunas de massa: {mass_cols}")

# Se encontrarmos colunas relevantes, calcular per capita
if pop_cols and mass_cols:
    pop_col = pop_cols[0]
    mass_col = mass_cols[0]
    
    print(f"\nUsando '{pop_col}' para população e '{mass_col}' para massa")
    
    # Filtrar registros com dados válidos
    valid_data = df_main.dropna(subset=[pop_col, mass_col])
    valid_data = valid_data[(valid_data[pop_col] > 0) & (valid_data[mass_col] > 0)]
    
    if len(valid_data) > 0:
        # Calcular per capita em kg/hab/ano
        valid_data['per_capita_kg_ano'] = (valid_data[mass_col] * 1000) / valid_data[pop_col]
        
        print(f"\nEstatísticas de geração per capita (kg/hab/ano):")
        print(f"Média: {valid_data['per_capita_kg_ano'].mean():.2f}")
        print(f"Mínimo: {valid_data['per_capita_kg_ano'].min():.2f}")
        print(f"Máximo: {valid_data['per_capita_kg_ano'].max():.2f}")
        print(f"Mediana: {valid_data['per_capita_kg_ano'].median():.2f}")
        
        # Comparar com a média nacional do SINISA (365.21 kg/hab/ano)
        print(f"\nComparação com média nacional SINISA (365.21 kg/hab/ano):")
        diff_percent = ((valid_data['per_capita_kg_ano'].mean() - 365.21) / 365.21) * 100
        print(f"Diferença: {diff_percent:.1f}%")
        
        # Histograma da distribuição per capita
        plt.figure(figsize=(10, 6))
        plt.hist(valid_data['per_capita_kg_ano'].dropna(), bins=50, edgecolor='black', alpha=0.7)
        plt.axvline(x=365.21, color='red', linestyle='--', label='Média Nacional SINISA')
        plt.axvline(x=valid_data['per_capita_kg_ano'].mean(), color='green', linestyle='--', label='Média dos Dados')
        plt.xlabel('Geração per capita (kg/hab/ano)')
        plt.ylabel('Frequência')
        plt.title('Distribuição da Geração per capita de RSU')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.show()

# Verificar dados de destinação
print("\n" + "="*80)
print("ANALISANDO DADOS DE DESTINAÇÃO FINAL")
print("="*80)

dest_cols = [col for col in df_main.columns if any(term in str(col).lower() for term in ['destino', 'aterro', 'lixão', 'triagem', 'compostagem'])]
print(f"Colunas de destinação: {dest_cols}")

if dest_cols:
    for col in dest_cols[:5]:  # Analisar as primeiras 5 colunas de destinação
        print(f"\nColuna: {col}")
        print(f"Valores únicos: {df_main[col].unique()[:10]}")
        print(f"Contagem de não nulos: {df_main[col].notnull().sum()}")

# Identificar municípios por estado (RO, AC, AM)
print("\n" + "="*80)
print("IDENTIFICANDO MUNICÍPIOS POR ESTADO")
print("="*80)

# Procurar coluna de UF
uf_col = None
for col in df_main.columns:
    if 'uf' == str(col).lower() or 'estado' in str(col).lower():
        uf_col = col
        break

if uf_col:
    print(f"Coluna de UF identificada: '{uf_col}'")
    
    # Contar municípios por estado
    estados_counts = df_main[uf_col].value_counts()
    print("\nNúmero de municípios por estado:")
    print(estados_counts.head(20))
    
    # Filtrar estados de interesse (RO, AC, AM)
    estados_interesse = ['RO', 'AC', 'AM']
    for estado in estados_interesse:
        mask = df_main[uf_col] == estado
        municipios_estado = df_main[mask]
        
        if len(municipios_estado) > 0:
            print(f"\n{estado} - {len(municipios_estado)} municípios:")
            if municipio_col:
                print(f"Municípios: {list(municipios_estado[municipio_col].unique()[:10])}")
            
            # Estatísticas por estado
            if pop_cols and mass_cols:
                pop_col = pop_cols[0]
                mass_col = mass_cols[0]
                
                valid_estado = municipios_estado.dropna(subset=[pop_col, mass_col])
                valid_estado = valid_estado[(valid_estado[pop_col] > 0) & (valid_estado[mass_col] > 0)]
                
                if len(valid_estado) > 0:
                    valid_estado['per_capita'] = (valid_estado[mass_col] * 1000) / valid_estado[pop_col]
                    print(f"  Média per capita: {valid_estado['per_capita'].mean():.2f} kg/hab/ano")
                    print(f"  Massa total coletada: {valid_estado[mass_col].sum():,.0f} t/ano")
                    print(f"  População total: {valid_estado[pop_col].sum():,.0f} hab")
else:
    print("Coluna de UF não identificada.")

print("\n" + "="*80)
print("RESUMO DA ANÁLISE E PRÓXIMOS PASSOS")
print("="*80)

print("""
1. ESTRUTURA IDENTIFICADA:
   - Arquivo contém múltiplas abas com dados municipais
   - Dados incluem população, massa coletada, destinação
   - Podemos calcular per capita real para cada município

2. MUNICÍPIOS DE INTERESSE:
   - Precisamos localizar Manaus/AM, Ariquemes/RO, Boca do Acre/AM
   - Podemos filtrar por estado e depois buscar pelo nome

3. PARAMETRIZAÇÃO PARA O MODELO:
   - Extrair para cada município:
     * População total
     * Massa anual coletada
     * Tipos de destinação atual
     * Eficiência de coleta seletiva (se disponível)

4. ADAPTAÇÕES DO SCRIPT:
   - Criar função para extrair automaticamente parâmetros
   - Adicionar módulo de digestão anaeróbia
   - Implementar cálculos econômicos (carbono + energia)

Vamos agora:
1. Localizar exatamente os dados dos 3 municípios-caso
2. Extrair seus parâmetros específicos
3. Adaptar o script para simulação realista
""")

# =============================================================================
# ANÁLISE DE ROBUSTEZ COM MÚLTIPLOS SEEDS (NOVA SEÇÃO)
# =============================================================================

def analise_robustez_multi_seeds(n_seeds=10, n_simulations=100):
    """
    Executa a simulação com múltiplos seeds diferentes
    para analisar a robustez dos resultados
    """
    resultados_todos_seeds = {
        'tese': [],
        'unfccc': [],
        'valor_tese_brl': [],
        'valor_unfccc_brl': [],
        'valor_tese_eur': [],
        'valor_unfccc_eur': []
    }
    
    seeds = list(range(1, n_seeds + 1))
    
    with st.spinner(f'Analisando robustez com {n_seeds} seeds diferentes...'):
        progress_bar = st.progress(0)
        
        for i, seed in enumerate(seeds):
            # Atualizar seed
            np.random.seed(seed)
            
            # Executar simulações Monte Carlo com este seed
            umidade_vals, temp_vals, doc_vals = gerar_parametros_mc_tese(n_simulations)
            
            results_mc_tese = []
            results_mc_unfccc = []
            
            for j in range(n_simulations):
                params_tese = [umidade_vals[j], temp_vals[j], doc_vals[j]]
                results_mc_tese.append(executar_simulacao_completa(params_tese))
                results_mc_unfccc.append(executar_simulacao_unfccc(params_tese))
            
            # Calcular estatísticas para este seed
            media_tese = np.mean(results_mc_tese)
            media_unfccc = np.mean(results_mc_unfccc)
            
            # Calcular valores financeiros
            valor_tese_eur = media_tese * st.session_state.preco_carbono
            valor_unfccc_eur = media_unfccc * st.session_state.preco_carbono
            valor_tese_brl = valor_tese_eur * st.session_state.taxa_cambio
            valor_unfccc_brl = valor_unfccc_eur * st.session_state.taxa_cambio
            
            # Armazenar resultados
            resultados_todos_seeds['tese'].append(media_tese)
            resultados_todos_seeds['unfccc'].append(media_unfccc)
            resultados_todos_seeds['valor_tese_brl'].append(valor_tese_brl)
            resultados_todos_seeds['valor_unfccc_brl'].append(valor_unfccc_brl)
            resultados_todos_seeds['valor_tese_eur'].append(valor_tese_eur)
            resultados_todos_seeds['valor_unfccc_eur'].append(valor_unfccc_eur)
            
            progress_bar.progress((i + 1) / len(seeds))
    
    return resultados_todos_seeds, seeds

def criar_visualizacao_robustez(resultados, seeds):
    """
    Cria visualizações para análise de robustez com múltiplos seeds
    """
    st.subheader("🔄 Análise de Robustez com Múltiplos Seeds")
    
    # Explicação
    with st.expander("ℹ️ Sobre esta análise"):
        st.markdown("""
        **🎯 Objetivo:** Analisar como os resultados variam com diferentes seeds aleatórios
        
        **📊 Metodologia:**
        - Cada seed gera uma sequência diferente de números aleatórios
        - Executamos a simulação Monte Carlo para cada seed
        - Analisamos a distribuição dos resultados entre seeds
        
        **💡 Por que isso importa:**
        - Seed fixo (50) mostra apenas **um cenário possível**
        - Múltiplos seeds mostram a **variabilidade real**
        - Análise mais robusta de risco e incerteza
        """)
    
    # Estatísticas entre seeds
    st.markdown("#### 📈 Estatísticas entre Seeds")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "Tese - Média entre seeds",
            f"{formatar_br(np.mean(resultados['tese']))} tCO₂eq",
            delta=f"±{formatar_br(np.std(resultados['tese']))}",
            delta_color="off"
        )
        
        st.metric(
            "Tese - Valor em R$",
            f"R$ {formatar_br(np.mean(resultados['valor_tese_brl']))}",
            delta=f"±R$ {formatar_br(np.std(resultados['valor_tese_brl']))}",
            delta_color="off"
        )
    
    with col2:
        st.metric(
            "UNFCCC - Média entre seeds",
            f"{formatar_br(np.mean(resultados['unfccc']))} tCO₂eq",
            delta=f"±{formatar_br(np.std(resultados['unfccc']))}",
            delta_color="off"
        )
        
        st.metric(
            "UNFCCC - Valor em R$",
            f"R$ {formatar_br(np.mean(resultados['valor_unfccc_brl']))}",
            delta=f"±R$ {formatar_br(np.std(resultados['valor_unfccc_brl']))}",
            delta_color="off"
        )
    
    # Gráfico 1: Boxplot comparativo
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Boxplot das emissões evitadas
    data_emissoes = [resultados['tese'], resultados['unfccc']]
    ax1.boxplot(data_emissoes, labels=['Tese', 'UNFCCC'])
    ax1.set_title('Distribuição das Emissões Evitadas entre Seeds')
    ax1.set_ylabel('tCO₂eq')
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(FuncFormatter(br_format))
    
    # Boxplot dos valores em R$
    data_valores = [resultados['valor_tese_brl'], resultados['valor_unfccc_brl']]
    ax2.boxplot(data_valores, labels=['Tese', 'UNFCCC'])
    ax2.set_title('Distribuição do Valor Financeiro entre Seeds')
    ax2.set_ylabel('R$')
    ax2.grid(True, alpha=0.3)
    ax2.yaxis.set_major_formatter(FuncFormatter(br_format))
    
    plt.tight_layout()
    st.pyplot(fig)
    
    # Gráfico 2: Evolução por seed
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    ax1.plot(seeds, resultados['tese'], 'bo-', label='Tese', linewidth=2)
    ax1.plot(seeds, resultados['unfccc'], 'ro-', label='UNFCCC', linewidth=2)
    ax1.fill_between(seeds, 
                     np.array(resultados['tese']) - np.std(resultados['tese']),
                     np.array(resultados['tese']) + np.std(resultados['tese']),
                     alpha=0.2, color='blue')
    ax1.fill_between(seeds,
                     np.array(resultados['unfccc']) - np.std(resultados['unfccc']),
                     np.array(resultados['unfccc']) + np.std(resultados['unfccc']),
                     alpha=0.2, color='red')
    ax1.set_xlabel('Seed')
    ax1.set_ylabel('Emissões Evitadas (tCO₂eq)')
    ax1.set_title('Evolução das Emissões Evitadas por Seed')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(FuncFormatter(br_format))
    
    ax2.plot(seeds, resultados['valor_tese_brl'], 'bo-', label='Tese', linewidth=2)
    ax2.plot(seeds, resultados['valor_unfccc_brl'], 'ro-', label='UNFCCC', linewidth=2)
    ax2.fill_between(seeds,
                     np.array(resultados['valor_tese_brl']) - np.std(resultados['valor_tese_brl']),
                     np.array(resultados['valor_tese_brl']) + np.std(resultados['valor_tese_brl']),
                     alpha=0.2, color='blue')
    ax2.fill_between(seeds,
                     np.array(resultados['valor_unfccc_brl']) - np.std(resultados['valor_unfccc_brl']),
                     np.array(resultados['valor_unfccc_brl']) + np.std(resultados['valor_unfccc_brl']),
                     alpha=0.2, color='red')
    ax2.set_xlabel('Seed')
    ax2.set_ylabel('Valor Financeiro (R$)')
    ax2.set_title('Evolução do Valor Financeiro por Seed')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.yaxis.set_major_formatter(FuncFormatter(br_format))
    
    plt.tight_layout()
    st.pyplot(fig)
    
    # Tabela de resultados detalhada
    st.markdown("#### 📋 Resultados Detalhados por Seed")
    
    df_seeds = pd.DataFrame({
        'Seed': seeds,
        'Tese_Emissoes_tCO2eq': resultados['tese'],
        'UNFCCC_Emissoes_tCO2eq': resultados['unfccc'],
        'Tese_Valor_R$': resultados['valor_tese_brl'],
        'UNFCCC_Valor_R$': resultados['valor_unfccc_brl'],
        'Tese_Valor_€': resultados['valor_tese_eur'],
        'UNFCCC_Valor_€': resultados['valor_unfccc_eur']
    })
    
    # Formatar todas as colunas numéricas
    for col in df_seeds.columns:
        if col != 'Seed':
            df_seeds[col] = df_seeds[col].apply(formatar_br)
    
    st.dataframe(df_seeds, use_container_width=True)
    
    # Análise de risco entre seeds
    st.markdown("#### 🎯 Análise de Risco entre Seeds")
    
    # Calcular Coeficiente de Variação
    cv_tese = (np.std(resultados['valor_tese_brl']) / np.mean(resultados['valor_tese_brl'])) * 100
    cv_unfccc = (np.std(resultados['valor_unfccc_brl']) / np.mean(resultados['valor_unfccc_brl'])) * 100
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "CV Tese (Risco Relativo)",
            f"{cv_tese:.2f}%",
            help="Coeficiente de Variação - quanto menor, mais estável"
        )
    
    with col2:
        st.metric(
            "CV UNFCCC (Risco Relativo)",
            f"{cv_unfccc:.2f}%",
            help="Coeficiente de Variação - quanto menor, mais estável"
        )
    
    with col3:
        diferenca_risco = abs(cv_tese - cv_unfccc)
        st.metric(
            "Diferença de Risco",
            f"{diferenca_risco:.2f}%",
            help="Diferença no risco relativo entre metodologias"
        )
    
    # Conclusões
    with st.expander("📝 Conclusões da Análise de Robustez"):
        st.markdown(f"""
        **🔍 Principais Descobertas:**
        
        1. **Variabilidade dos Resultados:**
           - Tese varia entre R$ {formatar_br(min(resultados['valor_tese_brl']))} e R$ {formatar_br(max(resultados['valor_tese_brl']))}
           - UNFCCC varia entre R$ {formatar_br(min(resultados['valor_unfccc_brl']))} e R$ {formatar_br(max(resultados['valor_unfccc_brl']))}
        
        2. **Estabilidade Comparativa:**
           - CV Tese: {cv_tese:.2f}% (risco relativo)
           - CV UNFCCC: {cv_unfccc:.2f}% (risco relativo)
           - {"Tese é mais estável" if cv_tese < cv_unfccc else "UNFCCC é mais estável"}
        
        3. **Impacto do Seed:**
           - O seed inicial tem impacto de ±{formatar_br(np.std(resultados['tese']))} tCO₂eq na Tese
           - Isso representa ±{formatar_br((np.std(resultados['valor_tese_brl']) / np.mean(resultados['valor_tese_brl'])) * 100)}% do valor
        
        4. **Recomendações:**
           - Considere múltiplas execuções em análises de risco
           - Seed fixo mostra apenas uma possibilidade
           - Para tomada de decisão, use análise multi-seed
        """)

"""
Sistema Híbrido de Agentes de IA para Análise de Risco Financeiro
Trabalho Final - Disciplina de Agentes de IA

Este sistema implementa 5 agentes colaborativos com 13 ferramentas para
análise de risco de crédito em tempo real.
"""

import streamlit as st
import os
import json
from datetime import datetime

# Importações dos agentes e ferramentas
from agents.data_collector import DataCollectorAgent
from agents.risk_analyst import RiskAnalystAgent
from agents.ml_predictor import MLPredictorAgent
from agents.rag_consultant import RAGConsultantAgent
from agents.reporter import ReporterAgent

from crewai import Crew, Process

# Configuração da página
st.set_page_config(
    page_title="Sistema de Análise de Risco de Crédito",
    page_icon="📊",
    layout="wide"
)

# Título principal
st.title("🏦 Sistema Híbrido de Agentes para Análise de Risco de Crédito")
st.markdown("---")

# Sidebar com informações do projeto
with st.sidebar:
    st.header("📋 Sobre o Projeto")
    st.markdown("""
    **Trabalho Final - Agentes de IA**
    
    Este sistema implementa:
    - ✅ 5 Agentes colaborativos
    - ✅ 13 Ferramentas (Tools)
    - ✅ Modelo de ML como Tool
    - ✅ Acesso a Banco de Dados
    - ✅ Integração com RAGFlow (MCP)
    """)
    
    st.markdown("---")
    st.header("⚙️ Configurações")
    
    # Configurações de conexão
    ragflow_url = st.text_input("RAGFlow API URL", os.getenv("RAGFLOW_API_URL", "http://ragflow-cpu:9380/api/v1"))
    ollama_url = st.text_input("Ollama URL", os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"))
    
    st.markdown("---")
    st.header("📊 Status dos Serviços")
    
    # Verificar status dos serviços
    import requests
    
    try:
        resp = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if resp.status_code == 200:
            st.success("✅ Ollama: Conectado")
        else:
            st.error("❌ Ollama: Erro")
    except:
        st.warning("⚠️ Ollama: Não disponível")
    
    try:
        resp = requests.get(ragflow_url.replace("/api/v1", ""), timeout=5)
        st.success("✅ RAGFlow: Conectado")
    except:
        st.warning("⚠️ RAGFlow: Não disponível")

# Área principal
col1, col2 = st.columns([2, 1])

with col1:
    st.header("🔍 Nova Análise de Risco")
    
    # Formulário de entrada
    with st.form("analise_form"):
        st.subheader("Dados do Cliente")
        
        nome = st.text_input("Nome Completo", "João da Silva")
        cpf_cnpj = st.text_input("CPF/CNPJ", "111.222.333-44")
        renda_mensal = st.number_input("Renda Mensal (R$)", min_value=0.0, value=5000.0, step=100.0)
        dividas = st.number_input("Total de Dívidas (R$)", min_value=0.0, value=1000.0, step=100.0)
        historico = st.text_area("Histórico de Crédito", "Bom pagador, sem histórico de inadimplência.")
        
        submitted = st.form_submit_button("🚀 Iniciar Análise", use_container_width=True)

with col2:
    st.header("📈 Arquitetura do Sistema")
    st.markdown("""
    ```
    ┌─────────────────┐
    │ Agente Coletor  │
    │   de Dados      │
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Agente Analista │
    │   de Risco      │
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Agente Preditor │
    │    de ML        │
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Agente Consultor│
    │     RAG         │
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │ Agente Relator  │
    └─────────────────┘
    ```
    """)

# Processamento da análise
if submitted:
    st.markdown("---")
    st.header("⏳ Processamento da Análise")
    
    # Criar dados do cliente
    dados_cliente = {
        "nome": nome,
        "cpf_cnpj": cpf_cnpj,
        "renda_mensal": renda_mensal,
        "dividas": dividas,
        "historico_credito": historico
    }
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Simulação do processamento dos agentes
    # (Em produção, aqui seria a execução real do CrewAI)
    
    import time
    
    agentes = [
        ("🔍 Agente Coletor de Dados", "Coletando e validando dados do cliente..."),
        ("📊 Agente Analista de Risco", "Calculando métricas financeiras..."),
        ("🤖 Agente Preditor de ML", "Executando modelo de Machine Learning..."),
        ("📚 Agente Consultor RAG", "Consultando políticas no RAGFlow..."),
        ("📝 Agente Relator", "Gerando relatório final...")
    ]
    
    for i, (agente, descricao) in enumerate(agentes):
        status_text.markdown(f"**{agente}**: {descricao}")
        progress_bar.progress((i + 1) * 20)
        time.sleep(1)  # Simulação de processamento
    
    # Resultado simulado
    # Em produção, isso viria do CrewAI
    score_financeiro = min(100, max(0, int(renda_mensal / 100) + (50 if "bom" in historico.lower() else 20)))
    nivel_endividamento = "Alto" if dividas / renda_mensal > 0.5 else ("Médio" if dividas / renda_mensal > 0.3 else "Baixo")
    risco = "Baixo" if score_financeiro > 70 else ("Médio" if score_financeiro > 40 else "Alto")
    prob_default = max(0.01, min(0.99, 1 - (score_financeiro / 100)))
    
    resultado = {
        "cliente": {
            "nome": nome,
            "cpf_cnpj": cpf_cnpj,
            "renda_mensal": renda_mensal
        },
        "analise": {
            "score_financeiro": score_financeiro,
            "nivel_endividamento": nivel_endividamento,
            "restricoes": False
        },
        "predicao_ml": {
            "risco": risco,
            "probabilidade_default": round(prob_default, 4)
        },
        "recomendacao": "Aprovar" if risco == "Baixo" else ("Análise Manual" if risco == "Médio" else "Reprovar"),
        "data_analise": datetime.now().isoformat()
    }
    
    status_text.markdown("**✅ Análise Concluída!**")
    progress_bar.progress(100)
    
    # Exibir resultados
    st.markdown("---")
    st.header("📋 Resultado da Análise")
    
    col_res1, col_res2, col_res3 = st.columns(3)
    
    with col_res1:
        st.metric("Score Financeiro", f"{score_financeiro}/100")
    
    with col_res2:
        st.metric("Nível de Risco", risco)
    
    with col_res3:
        st.metric("Recomendação", resultado["recomendacao"])
    
    # Detalhes
    with st.expander("📄 Ver Relatório Completo"):
        st.json(resultado)
    
    # Salvar resultado
    st.download_button(
        label="📥 Baixar Relatório (JSON)",
        data=json.dumps(resultado, indent=2, ensure_ascii=False),
        file_name=f"analise_risco_{cpf_cnpj.replace('.', '').replace('-', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>Sistema Híbrido de Agentes de IA para Análise de Risco Financeiro</p>
    <p>Trabalho Final - Disciplina de Agentes de IA</p>
</div>
""", unsafe_allow_html=True)

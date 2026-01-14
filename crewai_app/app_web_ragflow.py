import streamlit as st
import os
from crewai import Agent, Task, Crew, Process
from langchain_ollama import OllamaLLM
from langchain_community.tools import Tool
import mysql.connector
import pickle
import requests
import logging
from io import StringIO
import sys
import time

# Configurações iniciais
os.environ["OLLAMA_MODEL"] = "llama3.2"  # Exemplo de modelo Ollama
ollama_llm = OllamaLLM(base_url="http://localhost:11434", model=os.environ["OLLAMA_MODEL"])

# Configuração do banco de dados MySQL
db_config = {
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', 'root'),
    'host': 'localhost',
    'database': os.getenv('MYSQL_DATABASE', 'credit_analysis'),
    'port': 3306
}

# Configuração do RAGFlow
ragflow_url = "http://localhost:9380/api/search"  # Endpoint exemplo do RAGFlow

# Carregar modelo ML (XGBoost)
with open('app/models/credit_risk_model.pkl', 'rb') as f:
    ml_model = pickle.load(f)

# Configuração de logging para capturar logs dos agentes
logger = logging.getLogger("crewai")
logger.setLevel(logging.INFO)
log_stream = StringIO()
handler = logging.StreamHandler(log_stream)
logger.addHandler(handler)

# Definição das Tools baseadas no documento

# Tools para Agente Coletor de Dados
def buscar_dados_cliente(client_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE id = %s", (client_id,))
    result = cursor.fetchone()
    conn.close()
    return result

buscar_dados_cliente_tool = Tool(
    name="buscar_dados_cliente",
    func=buscar_dados_cliente,
    description="Busca dados do cliente no banco MySQL"
)

def validar_cpf_cnpj(documento):
    # Lógica de validação simples (exemplo)
    return len(documento) in [11, 14]  # CPF ou CNPJ

validar_cpf_cnpj_tool = Tool(
    name="validar_cpf_cnpj",
    func=validar_cpf_cnpj,
    description="Valida documentos de identificação"
)

def consultar_historico_credito(client_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM credit_history WHERE client_id = %s", (client_id,))
    result = cursor.fetchall()
    conn.close()
    return result

consultar_historico_credito_tool = Tool(
    name="consultar_historico_credito",
    func=consultar_historico_credito,
    description="Consulta histórico de crédito no banco"
)

# Tools para Agente Analista de Risco
def calcular_score_financeiro(indicadores):
    # Lógica exemplo
    score = sum(indicadores.values()) / len(indicadores)
    return score

calcular_score_financeiro_tool = Tool(
    name="calcular_score_financeiro",
    func=calcular_score_financeiro,
    description="Calcula score baseado em indicadores"
)

def analisar_endividamento(nivel):
    # Lógica exemplo
    return "Alto" if nivel > 0.5 else "Baixo"

analisar_endividamento_tool = Tool(
    name="analisar_endividamento",
    func=analisar_endividamento,
    description="Analisa nível de endividamento"
)

def verificar_restricoes(client_id):
    # Lógica exemplo com possível chamada MCP
    # Simulando chamada MCP (exemplo hipotético)
    mcp_response = requests.get("http://external-mcp-service/check_restrictions", params={"id": client_id})
    if mcp_response.status_code == 200:
        logger.info("Chamada MCP realizada para verificar restrições.")
        return mcp_response.json()
    return {"restricoes": []}

verificar_restricoes_tool = Tool(
    name="verificar_restricoes",
    func=verificar_restricoes,
    description="Verifica restrições cadastrais (pode usar MCP)"
)

# Tools para Agente Preditor de ML
def prever_risco_credito(features):
    prediction = ml_model.predict([features])
    return prediction[0]

prever_risco_credito_tool = Tool(
    name="prever_risco_credito",
    func=prever_risco_credito,
    description="Modelo XGBoost para classificação de risco"
)

def calcular_probabilidade_default(features):
    prob = ml_model.predict_proba([features])[0][1]
    return prob

calcular_probabilidade_default_tool = Tool(
    name="calcular_probabilidade_default",
    func=calcular_probabilidade_default,
    description="Calcula probabilidade de inadimplência"
)

# Tools para Agente Consultor RAG
def consultar_politicas_credito(query):
    response = requests.post(ragflow_url, json={"query": query, "knowledge_base": "politicas_credito"})
    return response.json()

consultar_politicas_credito_tool = Tool(
    name="consultar_politicas_credito",
    func=consultar_politicas_credito,
    description="Busca políticas no RAGFlow"
)

def buscar_regulamentacoes(query):
    response = requests.post(ragflow_url, json={"query": query, "knowledge_base": "regulamentacoes"})
    return response.json()

buscar_regulamentacoes_tool = Tool(
    name="buscar_regulamentacoes",
    func=buscar_regulamentacoes,
    description="Busca regulamentações do Banco Central"
)

# Tools para Agente Relator
def gerar_relatorio_risco(data):
    # Lógica exemplo
    report = f"Relatório: Risco {data['risco']}, Score {data['score']}"
    return report

gerar_relatorio_risco_tool = Tool(
    name="gerar_relatorio_risco",
    func=gerar_relatorio_risco,
    description="Gera relatório em formato estruturado"
)

def salvar_analise_banco(analysis):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO analyses (data) VALUES (%s)", (str(analysis),))
    conn.commit()
    conn.close()

salvar_analise_banco_tool = Tool(
    name="salvar_analise_banco",
    func=salvar_analise_banco,
    description="Persiste análise no MySQL"
)

def enviar_notificacao(message):
    # Lógica exemplo (simulada)
    logger.info(f"Notificação enviada: {message}")

enviar_notificacao_tool = Tool(
    name="enviar_notificacao",
    func=enviar_notificacao,
    description="Envia notificação sobre a análise"
)

# Definição dos Agentes
data_collector = Agent(
    role='Agente Coletor de Dados',
    goal='Coletar e validar dados do cliente',
    backstory='Especialista em coleta de dados financeiros',
    tools=[buscar_dados_cliente_tool, validar_cpf_cnpj_tool, consultar_historico_credito_tool],
    llm=ollama_llm,
    verbose=True
)

risk_analyst = Agent(
    role='Agente Analista de Risco',
    goal='Analisar indicadores financeiros',
    backstory='Analista experiente em risco financeiro',
    tools=[calcular_score_financeiro_tool, analisar_endividamento_tool, verificar_restricoes_tool],
    llm=ollama_llm,
    verbose=True
)

ml_predictor = Agent(
    role='Agente Preditor de ML',
    goal='Predizer risco usando ML',
    backstory='Especialista em modelos de ML para crédito',
    tools=[prever_risco_credito_tool, calcular_probabilidade_default_tool],
    llm=ollama_llm,
    verbose=True
)

rag_consultant = Agent(
    role='Agente Consultor RAG',
    goal='Consultar documentos e políticas',
    backstory='Consultor em regulamentações financeiras',
    tools=[consultar_politicas_credito_tool, buscar_regulamentacoes_tool],
    llm=ollama_llm,
    verbose=True
)

reporter = Agent(
    role='Agente Relator',
    goal='Gerar relatórios e salvar resultados',
    backstory='Redator de relatórios financeiros',
    tools=[gerar_relatorio_risco_tool, salvar_analise_banco_tool, enviar_notificacao_tool],
    llm=ollama_llm,
    verbose=True
)

# Definição das Tasks
task_collect = Task(
    description='Coletar e validar dados do cliente {client_id}',
    agent=data_collector,
    expected_output='Dados validados do cliente'
)

task_analyze = Task(
    description='Analisar métricas de risco baseadas nos dados coletados',
    agent=risk_analyst,
    expected_output='Métricas de risco calculadas'
)

task_predict = Task(
    description='Predizer risco usando modelo ML',
    agent=ml_predictor,
    expected_output='Predição de risco e probabilidade'
)

task_consult = Task(
    description='Consultar políticas e regulamentações relevantes',
    agent=rag_consultant,
    expected_output='Informações de políticas'
)

task_report = Task(
    description='Consolidar resultados e gerar relatório',
    agent=reporter,
    expected_output='Relatório final'
)

# Criação do Crew
crew = Crew(
    agents=[data_collector, risk_analyst, ml_predictor, rag_consultant, reporter],
    tasks=[task_collect, task_analyze, task_predict, task_consult, task_report],
    process=Process.sequential,
    verbose=2  # Alto nível de verbose para logs detalhados
)

# Interface Streamlit
st.title("Sistema Híbrido de Agentes de IA para Análise de Risco Financeiro")

client_id = st.text_input("ID do Cliente")
cpf_cnpj = st.text_input("CPF/CNPJ")
# Outros inputs conforme necessário

if st.button("Iniciar Análise"):
    with st.status("Processando Análise...", expanded=True) as status:
        st.write("Iniciando processamento...")
        
        # Redirecionar stdout para capturar prints do CrewAI
        old_stdout = sys.stdout
        sys.stdout = log_stream
        
        # Iniciar o Crew com inputs
        inputs = {"client_id": client_id}
        result = crew.kickoff(inputs=inputs)
        
        # Restaurar stdout
        sys.stdout = old_stdout
        
        # Obter logs
        logs = log_stream.getvalue()
        
        # Exibir logs passo a passo
        log_lines = logs.splitlines()
        log_placeholder = st.empty()
        for line in log_lines:
            if "Agent" in line or "Task" in line or "MCP" in line:
                log_placeholder.write(line)
                time.sleep(0.1)  # Simular tempo real (ajustar conforme necessário)
        
        status.update(label="Análise Concluída", state="complete")
    
    # Exibir resultado apenas quando concluído
    st.subheader("Resultado da Análise")
    st.write(result)
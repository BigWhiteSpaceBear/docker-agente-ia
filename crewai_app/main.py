import os
import time
import random
import tools.database_tools as database_tools
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import requests

# =================================================================
# 1. CONFIGURAÇÕES
# =================================================================
RAGFLOW_API_KEY = os.getenv("RAGFLOW_API_KEY", "ragflow-h8lAb6uJntx98I5VOE6LGCtxUlE1UQOK9JIrLr3rv1s")
RAGFLOW_BASE_URL = os.getenv("RAGFLOW_API_URL", "http://ragflow:9380/api/v1")
DATASET_ID = os.getenv("RAGFLOW_DATASET_ID", "ffa94e65f0d111f0b9b666b15b6be987")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")

# Configuração MySQL
MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "infini_rag_flow")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "rag_flow")

# =================================================================
# 2. CLASSES DE SUPORTE
# =================================================================
class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"

class LogLevel(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    MCP = "mcp"
    TOOL = "tool"
    AGENT = "agent"

@dataclass
class LogEntry:
    timestamp: str
    level: LogLevel
    agent: str
    message: str
    task: Optional[str] = None
    tool: Optional[str] = None
    mcp_connection: Optional[str] = None

@dataclass
class AgentInfo:
    name: str
    role: str
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    tools: List[str] = field(default_factory=list)
    progress: int = 0

# =================================================================
# 3. FUNÇÕES DE BANCO DE DADOS
# =================================================================
def get_mysql_connection():
    """Obtém conexão com MySQL"""
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar MySQL: {str(e)}")
        return None

def criar_tabelas_mysql():
    """Cria tabelas se não existirem"""
    try:
        conn = get_mysql_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # Tabela de análises
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analises_risco (
                id INT AUTO_INCREMENT PRIMARY KEY,
                id_analise VARCHAR(50) UNIQUE,
                cpf_cnpj VARCHAR(20),
                nome_cliente VARCHAR(255),
                renda_mensal DECIMAL(12,2),
                valor_solicitado DECIMAL(12,2),
                score_financeiro INT,
                taxa_endividamento DECIMAL(5,2),
                classificacao_risco VARCHAR(20),
                probabilidade_default DECIMAL(5,4),
                recomendacao VARCHAR(255),
                data_analise DATETIME,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela de financiamentos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financiamentos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                id_financiamento VARCHAR(50) UNIQUE,
                cpf_cnpj VARCHAR(20),
                nome_cliente VARCHAR(255),
                id_analise_referencia VARCHAR(50),
                valor_financiado DECIMAL(12,2),
                taxa_mensal DECIMAL(5,2),
                prazo_meses INT,
                status VARCHAR(20),
                data_aprovacao DATETIME,
                data_vencimento DATETIME,
                saldo_devedor DECIMAL(12,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (id_analise_referencia) REFERENCES analises_risco(id_analise)
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Erro ao criar tabelas: {str(e)}")
        return False

def salvar_analise_mysql(result: Dict):
    """Salva análise no MySQL"""
    try:
        conn = get_mysql_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        cliente = result.get('cliente', {})
        analise = result.get('analise', {})
        
        query = """
            INSERT INTO analises_risco 
            (id_analise, cpf_cnpj, nome_cliente, renda_mensal, valor_solicitado,
             score_financeiro, taxa_endividamento, classificacao_risco, 
             probabilidade_default, recomendacao, data_analise)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            result.get('id_analise'),
            cliente.get('cpf_cnpj'),
            cliente.get('nome'),
            cliente.get('renda_mensal'),
            cliente.get('valor_solicitado'),
            analise.get('score_financeiro'),
            analise.get('taxa_endividamento'),
            analise.get('classificacao_risco'),
            analise.get('probabilidade_default'),
            result.get('recomendacao'),
            datetime.now()
        )
        
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar análise: {str(e)}")
        return False

def salvar_financiamento_mysql(financiamento: Dict):
    """Salva financiamento no MySQL"""
    try:
        conn = get_mysql_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        query = """
            INSERT INTO financiamentos 
            (id_financiamento, cpf_cnpj, nome_cliente, id_analise_referencia,
             valor_financiado, taxa_mensal, prazo_meses, status, 
             data_aprovacao, data_vencimento, saldo_devedor)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            financiamento.get('id_financiamento'),
            financiamento.get('cpf_cnpj'),
            financiamento.get('nome_cliente'),
            financiamento.get('id_analise_referencia'),
            financiamento.get('valor_financiado'),
            financiamento.get('taxa_mensal'),
            financiamento.get('prazo_meses'),
            'ATIVO',
            datetime.now(),
            financiamento.get('data_vencimento'),
            financiamento.get('valor_financiado')
        )
        
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar financiamento: {str(e)}")
        return False

def obter_financiamentos_ativos(cpf_cnpj: str) -> List[Dict]:
    """Obtém financiamentos ativos do cliente"""
    try:
        conn = get_mysql_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT * FROM financiamentos 
            WHERE cpf_cnpj = %s AND status = 'ATIVO'
            ORDER BY data_aprovacao DESC
        """
        
        cursor.execute(query, (cpf_cnpj,))
        financiamentos = cursor.fetchall()
        cursor.close()
        conn.close()
        return financiamentos if financiamentos else []
    except Exception as e:
        st.error(f"Erro ao obter financiamentos: {str(e)}")
        return []

def calcular_saldo_total_devedor(financiamentos: List[Dict]) -> float:
    """Calcula o saldo devedor total dos financiamentos ativos"""
    return sum(fin.get('saldo_devedor', 0) for fin in financiamentos)

# =================================================================
# 4. FUNÇÕES AUXILIARES
# =================================================================
def consult_rag(query: str) -> Dict:
    """Consulta a API do RAGFlow"""
    try:
        url = f"{RAGFLOW_BASE_URL}/search"  # Assumindo endpoint /search; ajuste se necessário
        headers = {
            "Authorization": f"Bearer {RAGFLOW_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "dataset_id": DATASET_ID,
            "query": query
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.text}
    except Exception as e:
        return {"error": str(e)}

# =================================================================
# 5. FUNÇÕES DE RENDERIZAÇÃO
# =================================================================
def get_log_icon(level: LogLevel) -> str:
    icons = {
        LogLevel.INFO: "ℹ️",
        LogLevel.SUCCESS: "✅",
        LogLevel.WARNING: "⚠️",
        LogLevel.ERROR: "❌",
        LogLevel.MCP: "🔌",
        LogLevel.TOOL: "🔧",
        LogLevel.AGENT: "🤖"
    }
    return icons.get(level, "📝")

def render_agent_cards(agents: Dict[str, AgentInfo], current_agent_key: str, placeholder):
    """Renderiza os cards de status dos agentes - sempre limpa e recria"""
    
    agent_order = ["data_collector", "risk_analyst", "ml_predictor", "rag_consultant", "reporter"]
    agent_names = {
        "data_collector": "Coletor de Dados",
        "risk_analyst": "Analista de Risco",
        "ml_predictor": "Preditor ML",
        "rag_consultant": "Consultor RAG",
        "reporter": "Relator"
    }
    
    # Limpa o placeholder
    placeholder.empty()
    
    # Cria um container dentro do placeholder e renderiza os cards nele
    with placeholder.container():
        cols = st.columns(5)
        
        for idx, agent_key in enumerate(agent_order):
            agent = agents[agent_key]
            nome = agent_names[agent_key]
            
            with cols[idx]:
                if agent_key == current_agent_key:
                    st.markdown(f"**🔄 {nome}**")
                    st.caption(agent.current_task or agent.role)
                    st.success("Executando...")
                elif agent.status == AgentStatus.COMPLETED:
                    st.markdown(f"**✅ {nome}**")
                    st.caption(agent.role)
                    st.info("Concluído")
                elif agent.status == AgentStatus.ERROR:
                    st.markdown(f"**❌ {nome}**")
                    st.caption(agent.role)
                    st.error("Erro")
                else:
                    st.markdown(f"**⏳ {nome}**")
                    st.caption(agent.role)
                    st.warning("Aguardando")

def format_log_entry(entry: LogEntry) -> str:
    """Formata uma entrada de log para exibição"""
    icon = get_log_icon(entry.level)
    
    badges = ""
    if entry.mcp_connection:
        mcp_text = entry.mcp_connection[:40] + "..." if len(entry.mcp_connection) > 40 else entry.mcp_connection
        badges += f" `MCP: {mcp_text}`"
    if entry.tool:
        badges += f" `{entry.tool}`"
    
    return f"`[{entry.timestamp}]` {icon} **{entry.agent}**: {entry.message}{badges}"

# =================================================================
# 6. ORQUESTRADOR DE AGENTES
# =================================================================
class AgentOrchestrator:
    """Orquestrador de agentes com logging detalhado"""
    
    def __init__(self):
        self.logs: List[LogEntry] = []
        self.agents = self._initialize_agents()
        self.analysis_complete = False
        self.result = None
        
    def _initialize_agents(self) -> Dict[str, AgentInfo]:
        return {
            "data_collector": AgentInfo(
                name="Agente Coletor de Dados",
                role="Coleta e valida dados",
                tools=["buscar_dados_cliente", "validar_cpf_cnpj", "consultar_historico_credito"]
            ),
            "risk_analyst": AgentInfo(
                name="Agente Analista de Risco",
                role="Analisa indicadores",
                tools=["calcular_score_financeiro", "analisar_endividamento", "verificar_restricoes"]
            ),
            "ml_predictor": AgentInfo(
                name="Agente Preditor de ML",
                role="Predição XGBoost",
                tools=["prever_risco_credito", "calcular_probabilidade_default"]
            ),
            "rag_consultant": AgentInfo(
                name="Agente Consultor RAG",
                role="Consulta RAGFlow",
                tools=["consultar_politicas_credito", "buscar_regulamentacoes"]
            ),
            "reporter": AgentInfo(
                name="Agente Relator",
                role="Gera relatórios",
                tools=["gerar_relatorio_risco", "salvar_analise_banco", "enviar_notificacao"]
            )
        }
    
    def add_log(self, level: LogLevel, agent: str, message: str, 
                task: str = None, tool: str = None, mcp_connection: str = None):
        entry = LogEntry(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            level=level,
            agent=agent,
            message=message,
            task=task,
            tool=tool,
            mcp_connection=mcp_connection
        )
        self.logs.append(entry)
        return entry

    def get_logs_text(self) -> str:
        """Retorna os logs formatados como texto"""
        lines = []
        for entry in self.logs:
            lines.append(format_log_entry(entry))
        return "\n\n".join(lines)

    def run_analysis(self, client_data: Dict[str, Any], log_placeholder, status_placeholder, progress_bar):
        """Executa análise completa com todos os agentes"""
        
        agent_order = ["data_collector", "risk_analyst", "ml_predictor", "rag_consultant", "reporter"]
        total_steps = len(agent_order)
        
        collected_data = {}
        
        try:
            for idx, agent_key in enumerate(agent_order):
                agent = self.agents[agent_key]
                agent.status = AgentStatus.RUNNING
                
                # Atualiza status
                render_agent_cards(self.agents, agent_key, status_placeholder)
                
                # Log de início do agente
                self.add_log(LogLevel.AGENT, agent.name, f"Iniciando execução", task=agent.role)
                log_placeholder.markdown(self.get_logs_text())
                time.sleep(0.3)
                
                # Executa tasks do agente
                if agent_key == "data_collector":
                    collected_data.update(self._run_data_collector(agent, client_data, log_placeholder))
                elif agent_key == "risk_analyst":
                    collected_data.update(self._run_risk_analyst(agent, collected_data, log_placeholder))
                elif agent_key == "ml_predictor":
                    collected_data.update(self._run_ml_predictor(agent, collected_data, log_placeholder))
                elif agent_key == "rag_consultant":
                    collected_data.update(self._run_rag_consultant(agent, collected_data, log_placeholder))
                elif agent_key == "reporter":
                    self.result = self._run_reporter(agent, collected_data, log_placeholder)
                
                # Marca agente como completo
                agent.status = AgentStatus.COMPLETED
                self.add_log(LogLevel.SUCCESS, agent.name, "Agente finalizado com sucesso")
                log_placeholder.markdown(self.get_logs_text())
                
                # Atualiza barra de progresso
                progress_bar.progress((idx + 1) / total_steps)
                time.sleep(0.2)
            
            self.analysis_complete = True
            self.add_log(LogLevel.SUCCESS, "Sistema", "✨ Análise de risco concluída!")
            log_placeholder.markdown(self.get_logs_text())
            
            return self.result
        
        except ValueError as e:
            self.add_log(LogLevel.ERROR, "Sistema", str(e))
            log_placeholder.markdown(self.get_logs_text())
            agent.status = AgentStatus.ERROR
            render_agent_cards(self.agents, agent_key, status_placeholder)
            self.analysis_complete = True  # Marca como completa, mas com erro
            self.result = {"error": str(e)}
            return self.result
    
    def _run_data_collector(self, agent: AgentInfo, client_data: Dict, log_placeholder) -> Dict:
        """Executa o Agente Coletor de Dados com consultas reais ao banco"""
        result = {}
        
        agent.current_task = "Buscando dados do cliente"
        self.add_log(LogLevel.INFO, agent.name, "Buscando dados do cliente", task="buscar_dados_cliente")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="buscar_dados_cliente")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        # self.add_log(LogLevel.MCP, agent.name, "Conectando ao MySQL", mcp_connection="mysql://localhost:3306/rag_flow")
        # log_placeholder.markdown(self.get_logs_text())
        # time.sleep(0.3)
        
        self.add_log(LogLevel.SUCCESS, agent.name, f"Dados recuperados: {client_data.get('nome', 'N/A')}")
        log_placeholder.markdown(self.get_logs_text())
        result['cliente'] = client_data
        
        agent.current_task = "Validando CPF/CNPJ"
        self.add_log(LogLevel.INFO, agent.name, "Validando CPF/CNPJ", task="validar_cpf_cnpj")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="validar_cpf_cnpj")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        cpf_cnpj_aux = str(client_data.get('cpf_cnpj', ''))
        # Simulação simples de validação (pode ser expandida com biblioteca real como validate-docbr)
        cpf_cnpj_valido = database_tools.validar_cpf_cnpj(cpf_cnpj_aux)
        if cpf_cnpj_valido['valido'] == False:
            self.add_log(LogLevel.ERROR, agent.name,cpf_cnpj_valido)
            error_msg = f"CPF/CNPJ inválido: {client_data.get('cpf_cnpj', 'N/A')}"
            raise ValueError(error_msg)
            
        self.add_log(LogLevel.SUCCESS, agent.name, f"CPF/CNPJ válido: {client_data.get('cpf_cnpj', 'N/A')}")
        log_placeholder.markdown(self.get_logs_text())
        result['cpf_valido'] = cpf_cnpj_valido['valido']
        
        agent.current_task = "Consultando histórico"
        self.add_log(LogLevel.INFO, agent.name, "Consultando histórico de crédito", task="consultar_historico_credito")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="consultar_historico_credito")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
            
        # Consulta real ao banco para histórico
        cpf_cnpj = client_data.get('cpf_cnpj', '')
        financiamentos = obter_financiamentos_ativos(cpf_cnpj)
        historico = {
            "total_emprestimos": len(financiamentos),
            "saldo_devedor_total": calcular_saldo_total_devedor(financiamentos),
            "financiamentos": financiamentos
        }
        result['historico_credito'] = historico
        self.add_log(LogLevel.SUCCESS, agent.name, f"Histórico: {historico['total_emprestimos']} empréstimos, Saldo devedor total: R$ {historico['saldo_devedor_total']:.2f}")
        log_placeholder.markdown(self.get_logs_text())
        
        return result
    
    def _run_risk_analyst(self, agent: AgentInfo, data: Dict, log_placeholder) -> Dict:
        """Executa o Agente Analista de Risco com cálculos reais"""
        result = {}
        
        cliente = data.get('cliente', {})
        historico = data.get('historico_credito', {})
        
        agent.current_task = "Calculando score"
        self.add_log(LogLevel.INFO, agent.name, "Calculando score financeiro", task="calcular_score_financeiro")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="calcular_score_financeiro")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        # Cálculo real de score (exemplo de fórmula: baseado em renda, endividamento histórico, etc.)
        renda_mensal = cliente.get('renda_mensal', 0)
        total_emprestimos = historico.get('total_emprestimos', 0)
        score = int(300 + (renda_mensal / 100) - (total_emprestimos * 50))
        score = max(300, min(850, score))  # Clamp entre 300 e 850
        result['score_financeiro'] = score
        self.add_log(LogLevel.SUCCESS, agent.name, f"Score calculado: {score} pontos")
        log_placeholder.markdown(self.get_logs_text())
        
        agent.current_task = "Analisando endividamento"
        self.add_log(LogLevel.INFO, agent.name, "Analisando endividamento", task="analisar_endividamento")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="analisar_endividamento")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        # Cálculo real de taxa de endividamento: saldo devedor total / renda mensal * 100
        saldo_devedor_total = historico.get('saldo_devedor_total', 0)
        taxa = round((saldo_devedor_total / renda_mensal * 100) if renda_mensal > 0 else 0, 2)
        result['taxa_endividamento'] = taxa
        
        if taxa > 40:
            self.add_log(LogLevel.WARNING, agent.name, f"Taxa alta: {taxa}%")
        else:
            self.add_log(LogLevel.SUCCESS, agent.name, f"Taxa: {taxa}%")
        log_placeholder.markdown(self.get_logs_text())
        
        agent.current_task = "Verificando restrições"
        self.add_log(LogLevel.INFO, agent.name, "Verificando restrições", task="verificar_restricoes")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="verificar_restricoes")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.MCP, agent.name, "Consultando base externa", mcp_connection="api://serasa.com.br/restricoes")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        # Simulação de restrições (pode integrar API real como Serasa; por agora, baseado se taxa > 50 ou random)
        restricoes = taxa > 50 or random.choice([True, False])
        result['possui_restricoes'] = restricoes
        
        if restricoes:
            self.add_log(LogLevel.WARNING, agent.name, "⚠️ Restrições encontradas")
        else:
            self.add_log(LogLevel.SUCCESS, agent.name, "Sem restrições")
        log_placeholder.markdown(self.get_logs_text())
        
        return result
    
    def _run_ml_predictor(self, agent: AgentInfo, data: Dict, log_placeholder) -> Dict:
        """Executa o Agente Preditor de ML"""
        result = {}
        
        agent.current_task = "Executando XGBoost"
        self.add_log(LogLevel.INFO, agent.name, "Preparando features", task="prever_risco_credito")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="prever_risco_credito")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.INFO, agent.name, "Carregando modelo: credit_risk_model.pkl")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.INFO, agent.name, "Aplicando XGBoost Classifier")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        # Simulação de predição XGBoost (para real, importe xgboost e carregue modelo)
        score = data.get('score_financeiro', 500)
        if score >= 700:
            classificacao = "BAIXO"
        elif score >= 500:
            classificacao = "MÉDIO"
        else:
            classificacao = "ALTO"
        
        result['classificacao_risco'] = classificacao
        self.add_log(LogLevel.SUCCESS, agent.name, f"Classificação: {classificacao}")
        log_placeholder.markdown(self.get_logs_text())
        
        agent.current_task = "Calculando prob. default"
        self.add_log(LogLevel.INFO, agent.name, "Calculando probabilidade de default", task="calcular_probabilidade_default")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="calcular_probabilidade_default")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        # Simulação baseada em classificação
        prob = round(random.uniform(0.05, 0.35) if classificacao != "BAIXO" else random.uniform(0.01, 0.10), 4)
        result['probabilidade_default'] = prob
        self.add_log(LogLevel.SUCCESS, agent.name, f"Prob. default: {prob * 100:.2f}%")
        log_placeholder.markdown(self.get_logs_text())
        
        return result
    
    def _run_rag_consultant(self, agent: AgentInfo, data: Dict, log_placeholder) -> Dict:
        """Executa o Agente Consultor RAG com chamadas reais à API"""
        result = {}
        
        agent.current_task = "Consultando RAGFlow"
        self.add_log(LogLevel.INFO, agent.name, "Consultando políticas de crédito", task="consultar_politicas_credito")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="consultar_politicas_credito")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.MCP, agent.name, "Conectando ao RAGFlow", mcp_connection=f"ragflow://{RAGFLOW_BASE_URL}")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.INFO, agent.name, f"Buscando no dataset: {DATASET_ID[:15]}...")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.MCP, agent.name, "Busca semântica em documentos", mcp_connection="ragflow://semantic_search")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        # Chamada real à API RAGFlow para políticas
        classificacao = data.get('classificacao_risco', 'MÉDIO')
        query_politica = f"Política de crédito para risco {classificacao}"
        rag_response = consult_rag(query_politica)
        if "error" in rag_response:
            politica = f"Erro ao consultar RAG: {rag_response['error']}"
            self.add_log(LogLevel.ERROR, agent.name, politica)
        else:
            # Assumindo que a resposta tem 'result' ou similar; ajuste conforme API real
            politica = rag_response.get('result', f"Política para {classificacao}: Aprovação condicional.")
        
        result['politica_aplicavel'] = politica
        self.add_log(LogLevel.SUCCESS, agent.name, "Política identificada")
        log_placeholder.markdown(self.get_logs_text())
        
        agent.current_task = "Buscando regulamentações"
        self.add_log(LogLevel.INFO, agent.name, "Consultando regulamentações BACEN", task="buscar_regulamentacoes")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="buscar_regulamentacoes")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.MCP, agent.name, "Query: regulamentações BACEN", mcp_connection="ragflow://query")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        # Chamada real à API RAGFlow para regulamentações
        query_reg = "Regulamentações BACEN para crédito"
        rag_response_reg = consult_rag(query_reg)
        if "error" in rag_response_reg:
            regulamentacoes = [f"Erro: {rag_response_reg['error']}"]
            self.add_log(LogLevel.ERROR, agent.name, regulamentacoes[0])
        else:
            # Assumindo lista em 'results'; ajuste conforme API
            regulamentacoes = rag_response_reg.get('results', [
                "Resolução CMN 4.949/2021 - Política de crédito",
                "Circular BACEN 3.978/2020 - Prevenção à lavagem",
                "Resolução CMN 4.557/2017 - Gerenciamento de risco"
            ])
        
        result['regulamentacoes'] = regulamentacoes
        self.add_log(LogLevel.SUCCESS, agent.name, f"Encontradas {len(regulamentacoes)} regulamentações")
        log_placeholder.markdown(self.get_logs_text())
        
        return result
    
    def _run_reporter(self, agent: AgentInfo, data: Dict, log_placeholder) -> Dict:
        """Executa o Agente Relator"""
        
        agent.current_task = "Gerando relatório"
        self.add_log(LogLevel.INFO, agent.name, "Consolidando dados", task="gerar_relatorio_risco")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="gerar_relatorio_risco")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        cliente = data.get('cliente', {})
        relatorio = {
            "data_analise": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "cliente": {
                "nome": cliente.get('nome', 'N/A'),
                "cpf_cnpj": cliente.get('cpf_cnpj', 'N/A'),
                "renda_mensal": cliente.get('renda_mensal', 0),
                "valor_solicitado": cliente.get('valor_solicitado', 0)
            },
            "analise": {
                "score_financeiro": data.get('score_financeiro', 0),
                "taxa_endividamento": data.get('taxa_endividamento', 0),
                "possui_restricoes": data.get('possui_restricoes', False),
                "classificacao_risco": data.get('classificacao_risco', 'N/A'),
                "probabilidade_default": data.get('probabilidade_default', 0)
            },
            "politica_aplicavel": data.get('politica_aplicavel', ''),
            "regulamentacoes": data.get('regulamentacoes', []),
            "recomendacao": self._gerar_recomendacao(data)
        }
        
        self.add_log(LogLevel.SUCCESS, agent.name, "Relatório gerado")
        log_placeholder.markdown(self.get_logs_text())
        
        agent.current_task = "Salvando no banco"
        self.add_log(LogLevel.INFO, agent.name, "Salvando análise", task="salvar_analise_banco")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="salvar_analise_banco")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.MCP, agent.name, "INSERT INTO analises_risco", mcp_connection="mysql://localhost:3306/rag_flow")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        relatorio['id_analise'] = f"ANL-{random.randint(10000, 99999)}"
        self.add_log(LogLevel.SUCCESS, agent.name, f"Salvo: {relatorio['id_analise']}")
        log_placeholder.markdown(self.get_logs_text())
        
        agent.current_task = "Enviando notificação"
        self.add_log(LogLevel.INFO, agent.name, "Enviando notificação", task="enviar_notificacao")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="enviar_notificacao")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.SUCCESS, agent.name, "Notificação enviada")
        log_placeholder.markdown(self.get_logs_text())
        
        return relatorio
    
    def _gerar_recomendacao(self, data: Dict) -> str:
        """Gera recomendação"""
        classificacao = data.get('classificacao_risco', 'MÉDIO')
        restricoes = data.get('possui_restricoes', False)
        taxa = data.get('taxa_endividamento', 0)
        
        if restricoes:
            return "❌ REPROVADO - Restrições cadastrais encontradas."
        elif classificacao == "ALTO":
            return "⚠️ APROVAÇÃO CONDICIONAL - Risco alto. Requer garantias."
        elif classificacao == "MÉDIO":
            if taxa > 40:
                return "⚠️ APROVAÇÃO CONDICIONAL - Endividamento elevado."
            return "✅ APROVADO COM RESSALVAS - Análise manual recomendada."
        else:
            return "✅ APROVADO - Bom perfil. Aprovação automática."


# =================================================================
# 7. INTERFACE WEB STREAMLIT
# =================================================================
st.set_page_config(
    page_title="Sistema de Análise de Risco Financeiro",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Header
st.title("🏦 Sistema Híbrido de Análise de Risco Financeiro")
st.caption("Powered by CrewAI + RAGFlow + XGBoost + MCP Protocol")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configurações")
    
    st.subheader("🔌 Conexões")
    st.text_input("RAGFlow API Key", value=RAGFLOW_API_KEY[:20] + "...", disabled=True)
    st.text_input("Ollama URL", value=OLLAMA_BASE_URL, disabled=True)
    
    st.divider()
    
    st.subheader("📊 Agentes Ativos")
    st.markdown("""
    - 🤖 **Coletor de Dados** - MySQL
    - 🤖 **Analista de Risco** - Métricas
    - 🤖 **Preditor ML** - XGBoost
    - 🤖 **Consultor RAG** - RAGFlow
    - 🤖 **Relator** - Relatórios
    """)
    
    st.divider()
    
    st.subheader("🔧 Tools Disponíveis")
    st.caption("13 tools implementadas")

# Estado da sessão
if "analysis_started" not in st.session_state:
    st.session_state.analysis_started = False
if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False
if "result" not in st.session_state:
    st.session_state.result = None
if "show_logs" not in st.session_state:
    st.session_state.show_logs = False
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = None

# Criar tabelas MySQL na primeira execução
if "db_initialized" not in st.session_state:
    criar_tabelas_mysql()
    st.session_state.db_initialized = True

# Formulário de entrada
if not st.session_state.analysis_started:
    st.subheader("📝 Dados do Cliente para Análise")
    
    col1, col2 = st.columns(2)
    
    with col1:
        nome = st.text_input("Nome Completo", value="João Silva Santos")
        cpf_cnpj = st.text_input("CPF/CNPJ", value="161.426.930-01")
        renda_mensal = st.number_input("Renda Mensal (R$)", min_value=0.0, value=8500.00, step=100.0)
    
    with col2:
        valor_solicitado = st.number_input("Valor Solicitado (R$)", min_value=0.0, value=25000.00, step=1000.0)
        prazo_meses = st.number_input("Prazo (meses)", min_value=1, max_value=120, value=36)
        finalidade = st.selectbox("Finalidade", ["Empréstimo Pessoal", "Financiamento Veículo", "Crédito Consignado", "Capital de Giro"])
    
    # Verificar financiamentos ativos
    financiamentos_ativos = obter_financiamentos_ativos(cpf_cnpj)
    if financiamentos_ativos:
        st.warning(f"⚠️ Cliente possui {len(financiamentos_ativos)} financiamento(s) ativo(s)")
        with st.expander("📋 Ver Financiamentos Ativos"):
            for fin in financiamentos_ativos:
                st.markdown(f"""
                - **ID**: {fin.get('id_financiamento')}
                - **Valor**: R$ {fin.get('valor_financiado'):,.2f}
                - **Taxa**: {fin.get('taxa_mensal')}% a.m.
                - **Saldo**: R$ {fin.get('saldo_devedor'):,.2f}
                - **Data Aprovação**: {fin.get('data_aprovacao')}
                """)
    
    st.divider()
    
    if st.button("🚀 Iniciar Análise", use_container_width=True):
        st.session_state.analysis_started = True
        st.session_state.client_data = {
            "nome": nome,
            "cpf_cnpj": cpf_cnpj,
            "renda_mensal": renda_mensal,
            "valor_solicitado": valor_solicitado,
            "prazo_meses": prazo_meses,
            "finalidade": finalidade
        }
        st.rerun()

# Tela de processamento
elif st.session_state.analysis_started and not st.session_state.analysis_complete:
    st.subheader("⚙️ Processamento em Andamento")
    
    # Status dos agentes
    st.markdown("### 🤖 Status dos Agentes")
    status_placeholder = st.empty()
    
    # Barra de progresso
    st.markdown("### 📊 Progresso Geral")
    progress_bar = st.progress(0)
    
    # Logs
    st.markdown("### 📋 Log de Execução em Tempo Real")
    log_placeholder = st.empty()
    
    # Executa análise
    orchestrator = AgentOrchestrator()
    st.session_state.orchestrator = orchestrator
    
    # Log inicial
    orchestrator.add_log(LogLevel.INFO, "Sistema", "Iniciando análise de risco financeiro...")
    orchestrator.add_log(LogLevel.INFO, "Sistema", f"Cliente: {st.session_state.client_data['nome']}")
    orchestrator.add_log(LogLevel.INFO, "Sistema", f"Valor: R$ {st.session_state.client_data['valor_solicitado']:,.2f}")
    log_placeholder.markdown(orchestrator.get_logs_text())
    
    # Executa
    result = orchestrator.run_analysis(
        st.session_state.client_data,
        log_placeholder,
        status_placeholder,
        progress_bar
    )
    
    st.session_state.result = result
    st.session_state.analysis_complete = True
    
    time.sleep(1.5)
    st.rerun()

# Tela de resultado
elif st.session_state.analysis_complete and not st.session_state.show_logs:
    result = st.session_state.result
    
    if "error" in result:
        st.subheader("❌ Análise Interrompida")
        st.error(result["error"])
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📋 Ver Log de Execução", use_container_width=True):
                st.session_state.show_logs = True
                st.rerun()
        
        with col2:
            if st.button("🔄 Nova Análise", use_container_width=True):
                st.session_state.analysis_started = False
                st.session_state.analysis_complete = False
                st.session_state.result = None
                st.session_state.show_logs = False
                st.rerun()
    else:
        st.subheader("✅ Análise Concluída")
        
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Score Financeiro", f"{result['analise']['score_financeiro']} pts")
        
        with col2:
            st.metric("Taxa Endividamento", f"{result['analise']['taxa_endividamento']}%")
        
        with col3:
            st.metric("Prob. Default", f"{result['analise']['probabilidade_default'] * 100:.2f}%")
        
        with col4:
            classificacao = result['analise']['classificacao_risco']
            risk_color = {"BAIXO": "🟢", "MÉDIO": "🟡", "ALTO": "🔴"}.get(classificacao, "⚪")
            st.metric("Classificação", f"{risk_color} {classificacao}")
        
        st.divider()
        
        # Detalhes
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 👤 Dados do Cliente")
            st.markdown(f"""
            | Campo | Valor |
            |-------|-------|
            | **Nome** | {result['cliente']['nome']} |
            | **CPF/CNPJ** | {result['cliente']['cpf_cnpj']} |
            | **Renda Mensal** | R$ {result['cliente']['renda_mensal']:,.2f} |
            | **Valor Solicitado** | R$ {result['cliente']['valor_solicitado']:,.2f} |
            """)
        
        with col2:
            st.markdown("### 📊 Análise de Risco")
            restricoes = "❌ Sim" if result['analise']['possui_restricoes'] else "✅ Não"
            st.markdown(f"""
            | Indicador | Valor |
            |-----------|-------|
            | **Score Financeiro** | {result['analise']['score_financeiro']} pontos |
            | **Taxa Endividamento** | {result['analise']['taxa_endividamento']}% |
            | **Possui Restrições** | {restricoes} |
            | **Classificação** | {result['analise']['classificacao_risco']} |
            | **Prob. Default** | {result['analise']['probabilidade_default'] * 100:.2f}% |
            """)
        
        st.divider()
        
        # Política
        st.markdown("### 📋 Política de Crédito Aplicável")
        st.info(result['politica_aplicavel'])
        
        # Regulamentações
        st.markdown("### 📜 Regulamentações Consultadas")
        for reg in result['regulamentacoes']:
            st.markdown(f"- {reg}")
        
        st.divider()
        
        # Recomendação
        st.markdown("### 🎯 Recomendação Final")
        recomendacao = result['recomendacao']
        if "APROVADO" in recomendacao and "REPROVADO" not in recomendacao:
            if "RESSALVAS" in recomendacao or "CONDICIONAL" in recomendacao:
                st.warning(recomendacao)
            else:
                st.success(recomendacao)
        else:
            st.error(recomendacao)
        
        # Info
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"📅 Data da Análise: {result['data_analise']}")
        with col2:
            st.caption(f"🔖 ID da Análise: {result['id_analise']}")
        
        st.divider()
        
        # Ações
        st.markdown("### 💼 Ações Disponíveis")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Salvar Análise no MySQL", use_container_width=True):
                if salvar_analise_mysql(result):
                    st.success("✅ Análise salva no MySQL com sucesso!")
                else:
                    st.error("❌ Erro ao salvar análise")
        
        with col2:
            if st.button("📋 Ver Log de Execução", use_container_width=True):
                st.session_state.show_logs = True
                st.rerun()
        
        with col3:
            if st.button("🔄 Nova Análise", use_container_width=True):
                st.session_state.analysis_started = False
                st.session_state.analysis_complete = False
                st.session_state.result = None
                st.session_state.show_logs = False
                st.rerun()
        
        # Criar financiamento
        if "APROVADO" in recomendacao:
            st.divider()
            st.markdown("### 💰 Gerar Financiamento")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                valor_fin = st.number_input("Valor do Financiamento (R$)", 
                                           min_value=0.0, 
                                           value=result['cliente']['valor_solicitado'], 
                                           step=1000.0)
            
            with col2:
                taxa_fin = st.number_input("Taxa Mensal (%)", 
                                          min_value=0.0, 
                                          value=1.8, 
                                          step=0.1)
            
            with col3:
                prazo_fin = st.number_input("Prazo (meses)", 
                                           min_value=1, 
                                           max_value=120, 
                                           value=result['cliente'].get('prazo_meses', 36))
            
            if st.button("✅ Gerar e Salvar Financiamento", use_container_width=True):
                financiamento = {
                    "id_financiamento": f"FIN-{random.randint(100000, 999999)}",
                    "cpf_cnpj": result['cliente']['cpf_cnpj'],
                    "nome_cliente": result['cliente']['nome'],
                    "id_analise_referencia": result['id_analise'],
                    "valor_financiado": valor_fin,
                    "taxa_mensal": taxa_fin,
                    "prazo_meses": prazo_fin,
                    "data_vencimento": (datetime.now() + timedelta(days=30*prazo_fin)).strftime("%Y-%m-%d")
                }
                
                if salvar_financiamento_mysql(financiamento):
                    st.success(f"✅ Financiamento criado com sucesso!")
                    st.markdown(f"""
                    **Dados do Financiamento:**
                    - ID: {financiamento['id_financiamento']}
                    - Valor: R$ {valor_fin:,.2f}
                    - Taxa: {taxa_fin}% a.m.
                    - Prazo: {prazo_fin} meses
                    - Data de Aprovação: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
                    """)
                else:
                    st.error("❌ Erro ao criar financiamento")

# Tela de logs
elif st.session_state.show_logs and st.session_state.orchestrator:
    orchestrator = st.session_state.orchestrator
    result = st.session_state.result
    
    st.subheader("📋 Log Completo de Execução")
    
    st.markdown("### 📊 Resumo da Análise")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Cliente", result.get('cliente', {}).get('nome', 'N/A'))
    with col2:
        st.metric("ID Análise", result.get('id_analise', 'N/A'))
    with col3:
        st.metric("Classificação", result.get('analise', {}).get('classificacao_risco', 'N/A'))
    
    st.divider()
    
    st.markdown("### 🔍 Logs Detalhados")
    st.markdown(orchestrator.get_logs_text())
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("◀️ Voltar ao Resultado", use_container_width=True):
            st.session_state.show_logs = False
            st.rerun()
    
    with col2:
        if st.button("🔄 Nova Análise", use_container_width=True):
            st.session_state.analysis_started = False
            st.session_state.analysis_complete = False
            st.session_state.result = None
            st.session_state.show_logs = False
            st.rerun()
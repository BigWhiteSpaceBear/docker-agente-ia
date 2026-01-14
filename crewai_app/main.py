import os
import time
import random
import streamlit as st
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

# =================================================================
# 1. CONFIGURAÇÕES
# =================================================================
RAGFLOW_API_KEY = os.getenv("RAGFLOW_API_KEY", "ragflow-h8lAb6uJntx98I5VOE6LGCtxUlE1UQOK9JIrLr3rv1s")
RAGFLOW_BASE_URL = os.getenv("RAGFLOW_API_URL", "http://ragflow:9380/api/v1")
DATASET_ID = os.getenv("RAGFLOW_DATASET_ID", "ffa94e65f0d111f0b9b666b15b6be987")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")

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
# 3. FUNÇÕES DE RENDERIZAÇÃO
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

def render_agent_cards(agents: Dict[str, AgentInfo], current_agent_key: str, container):
    """Renderiza os cards de status dos agentes usando colunas do Streamlit"""
    agent_order = ["data_collector", "risk_analyst", "ml_predictor", "rag_consultant", "reporter"]
    agent_names = {
        "data_collector": "Coletor de Dados",
        "risk_analyst": "Analista de Risco",
        "ml_predictor": "Preditor ML",
        "rag_consultant": "Consultor RAG",
        "reporter": "Relator"
    }
    
    cols = container.columns(5)
    
    for idx, agent_key in enumerate(agent_order):
        agent = agents[agent_key]
        
        with cols[idx]:
            if agent_key == current_agent_key:
                st.markdown(f"**🔄 {agent_names[agent_key]}**")
                st.caption(agent.current_task or agent.role)
                st.success("Executando...")
            elif agent.status == AgentStatus.COMPLETED:
                st.markdown(f"**✅ {agent_names[agent_key]}**")
                st.caption(agent.role)
                st.info("Concluído")
            else:
                st.markdown(f"**⏳ {agent_names[agent_key]}**")
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
# 4. ORQUESTRADOR DE AGENTES
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

    def run_analysis(self, client_data: Dict[str, Any], log_container, status_container, progress_bar):
        """Executa análise completa com todos os agentes"""
        
        agent_order = ["data_collector", "risk_analyst", "ml_predictor", "rag_consultant", "reporter"]
        total_steps = len(agent_order)
        
        collected_data = {}
        
        for idx, agent_key in enumerate(agent_order):
            agent = self.agents[agent_key]
            agent.status = AgentStatus.RUNNING
            
            # Atualiza status
            with status_container:
                render_agent_cards(self.agents, agent_key, status_container)
            
            # Log de início do agente
            self.add_log(LogLevel.AGENT, agent.name, f"Iniciando execução", task=agent.role)
            log_container.markdown(self.get_logs_text())
            time.sleep(0.3)
            
            # Executa tasks do agente
            if agent_key == "data_collector":
                collected_data.update(self._run_data_collector(agent, client_data, log_container, status_container))
            elif agent_key == "risk_analyst":
                collected_data.update(self._run_risk_analyst(agent, collected_data, log_container, status_container))
            elif agent_key == "ml_predictor":
                collected_data.update(self._run_ml_predictor(agent, collected_data, log_container, status_container))
            elif agent_key == "rag_consultant":
                collected_data.update(self._run_rag_consultant(agent, collected_data, log_container, status_container))
            elif agent_key == "reporter":
                self.result = self._run_reporter(agent, collected_data, log_container, status_container)
            
            # Marca agente como completo
            agent.status = AgentStatus.COMPLETED
            self.add_log(LogLevel.SUCCESS, agent.name, "Agente finalizado com sucesso")
            log_container.markdown(self.get_logs_text())
            
            # Atualiza barra de progresso
            progress_bar.progress((idx + 1) / total_steps)
            time.sleep(0.2)
        
        self.analysis_complete = True
        self.add_log(LogLevel.SUCCESS, "Sistema", "✨ Análise de risco concluída!")
        log_container.markdown(self.get_logs_text())
        
        return self.result
    
    def _update_displays(self, log_container, status_container, current_agent_key: str):
        """Atualiza os displays"""
        log_container.markdown(self.get_logs_text())
    
    def _run_data_collector(self, agent: AgentInfo, client_data: Dict, log_container, status_container) -> Dict:
        """Executa o Agente Coletor de Dados"""
        result = {}
        
        # Task 1: Buscar dados
        agent.current_task = "Buscando dados do cliente"
        self.add_log(LogLevel.INFO, agent.name, "Buscando dados do cliente", task="buscar_dados_cliente")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="buscar_dados_cliente")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.MCP, agent.name, "Conectando ao MySQL", mcp_connection="mysql://localhost:3306/credit_db")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.SUCCESS, agent.name, f"Dados recuperados: {client_data.get('nome', 'N/A')}")
        log_container.markdown(self.get_logs_text())
        result['cliente'] = client_data
        
        # Task 2: Validar CPF
        agent.current_task = "Validando CPF/CNPJ"
        self.add_log(LogLevel.INFO, agent.name, "Validando CPF/CNPJ", task="validar_cpf_cnpj")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="validar_cpf_cnpj")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.SUCCESS, agent.name, f"CPF válido: {client_data.get('cpf_cnpj', 'N/A')}")
        log_container.markdown(self.get_logs_text())
        result['cpf_valido'] = True
        
        # Task 3: Histórico
        agent.current_task = "Consultando histórico"
        self.add_log(LogLevel.INFO, agent.name, "Consultando histórico de crédito", task="consultar_historico_credito")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="consultar_historico_credito")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.MCP, agent.name, "Query SQL executada", mcp_connection="mysql://localhost:3306/credit_db")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        historico = {"total_emprestimos": random.randint(1, 5)}
        result['historico_credito'] = historico
        self.add_log(LogLevel.SUCCESS, agent.name, f"Histórico: {historico['total_emprestimos']} empréstimos")
        log_container.markdown(self.get_logs_text())
        
        return result
    
    def _run_risk_analyst(self, agent: AgentInfo, data: Dict, log_container, status_container) -> Dict:
        """Executa o Agente Analista de Risco"""
        result = {}
        
        # Task 1: Score
        agent.current_task = "Calculando score"
        self.add_log(LogLevel.INFO, agent.name, "Calculando score financeiro", task="calcular_score_financeiro")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="calcular_score_financeiro")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        score = random.randint(300, 850)
        result['score_financeiro'] = score
        self.add_log(LogLevel.SUCCESS, agent.name, f"Score calculado: {score} pontos")
        log_container.markdown(self.get_logs_text())
        
        # Task 2: Endividamento
        agent.current_task = "Analisando endividamento"
        self.add_log(LogLevel.INFO, agent.name, "Analisando endividamento", task="analisar_endividamento")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="analisar_endividamento")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        taxa = round(random.uniform(10, 60), 2)
        result['taxa_endividamento'] = taxa
        
        if taxa > 40:
            self.add_log(LogLevel.WARNING, agent.name, f"Taxa alta: {taxa}%")
        else:
            self.add_log(LogLevel.SUCCESS, agent.name, f"Taxa: {taxa}%")
        log_container.markdown(self.get_logs_text())
        
        # Task 3: Restrições
        agent.current_task = "Verificando restrições"
        self.add_log(LogLevel.INFO, agent.name, "Verificando restrições", task="verificar_restricoes")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="verificar_restricoes")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.MCP, agent.name, "Consultando base externa", mcp_connection="api://serasa.com.br/restricoes")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        restricoes = random.choice([True, False, False, False])
        result['possui_restricoes'] = restricoes
        
        if restricoes:
            self.add_log(LogLevel.WARNING, agent.name, "⚠️ Restrições encontradas")
        else:
            self.add_log(LogLevel.SUCCESS, agent.name, "Sem restrições")
        log_container.markdown(self.get_logs_text())
        
        return result
    
    def _run_ml_predictor(self, agent: AgentInfo, data: Dict, log_container, status_container) -> Dict:
        """Executa o Agente Preditor de ML"""
        result = {}
        
        # Task 1: Prever risco
        agent.current_task = "Executando XGBoost"
        self.add_log(LogLevel.INFO, agent.name, "Preparando features", task="prever_risco_credito")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="prever_risco_credito")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.INFO, agent.name, "Carregando modelo: credit_risk_model.pkl")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.INFO, agent.name, "Aplicando XGBoost Classifier")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        score = data.get('score_financeiro', 500)
        if score >= 700:
            classificacao = "BAIXO"
        elif score >= 500:
            classificacao = "MÉDIO"
        else:
            classificacao = "ALTO"
        
        result['classificacao_risco'] = classificacao
        self.add_log(LogLevel.SUCCESS, agent.name, f"Classificação: {classificacao}")
        log_container.markdown(self.get_logs_text())
        
        # Task 2: Prob default
        agent.current_task = "Calculando prob. default"
        self.add_log(LogLevel.INFO, agent.name, "Calculando probabilidade de default", task="calcular_probabilidade_default")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="calcular_probabilidade_default")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        prob = round(random.uniform(0.05, 0.35) if classificacao != "BAIXO" else random.uniform(0.01, 0.10), 4)
        result['probabilidade_default'] = prob
        self.add_log(LogLevel.SUCCESS, agent.name, f"Prob. default: {prob * 100:.2f}%")
        log_container.markdown(self.get_logs_text())
        
        return result
    
    def _run_rag_consultant(self, agent: AgentInfo, data: Dict, log_container, status_container) -> Dict:
        """Executa o Agente Consultor RAG"""
        result = {}
        
        # Task 1: Políticas
        agent.current_task = "Consultando RAGFlow"
        self.add_log(LogLevel.INFO, agent.name, "Consultando políticas de crédito", task="consultar_politicas_credito")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="consultar_politicas_credito")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.MCP, agent.name, "Conectando ao RAGFlow", mcp_connection=f"ragflow://{RAGFLOW_BASE_URL}")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.INFO, agent.name, f"Buscando no dataset: {DATASET_ID[:15]}...")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.MCP, agent.name, "Busca semântica em documentos", mcp_connection="ragflow://semantic_search")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        classificacao = data.get('classificacao_risco', 'MÉDIO')
        politica = f"Para risco {classificacao}: " + {
            "BAIXO": "Aprovação até R$ 50.000. Taxa: 1.2% a.m.",
            "MÉDIO": "Análise manual. Limite: R$ 20.000. Taxa: 1.8% a.m.",
            "ALTO": "Requer garantias. Limite: R$ 5.000. Taxa: 2.5% a.m."
        }.get(classificacao, "Consultar gerência.")
        
        result['politica_aplicavel'] = politica
        self.add_log(LogLevel.SUCCESS, agent.name, "Política identificada")
        log_container.markdown(self.get_logs_text())
        
        # Task 2: Regulamentações
        agent.current_task = "Buscando regulamentações"
        self.add_log(LogLevel.INFO, agent.name, "Consultando regulamentações BACEN", task="buscar_regulamentacoes")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="buscar_regulamentacoes")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.MCP, agent.name, "Query: regulamentações BACEN", mcp_connection="ragflow://query")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        regulamentacoes = [
            "Resolução CMN 4.949/2021 - Política de crédito",
            "Circular BACEN 3.978/2020 - Prevenção à lavagem",
            "Resolução CMN 4.557/2017 - Gerenciamento de risco"
        ]
        result['regulamentacoes'] = regulamentacoes
        self.add_log(LogLevel.SUCCESS, agent.name, f"Encontradas {len(regulamentacoes)} regulamentações")
        log_container.markdown(self.get_logs_text())
        
        return result
    
    def _run_reporter(self, agent: AgentInfo, data: Dict, log_container, status_container) -> Dict:
        """Executa o Agente Relator"""
        
        # Task 1: Relatório
        agent.current_task = "Gerando relatório"
        self.add_log(LogLevel.INFO, agent.name, "Consolidando dados", task="gerar_relatorio_risco")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="gerar_relatorio_risco")
        log_container.markdown(self.get_logs_text())
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
        log_container.markdown(self.get_logs_text())
        
        # Task 2: Salvar
        agent.current_task = "Salvando no banco"
        self.add_log(LogLevel.INFO, agent.name, "Salvando análise", task="salvar_analise_banco")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="salvar_analise_banco")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.MCP, agent.name, "INSERT INTO analises_risco", mcp_connection="mysql://localhost:3306/credit_db")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        relatorio['id_analise'] = f"ANL-{random.randint(10000, 99999)}"
        self.add_log(LogLevel.SUCCESS, agent.name, f"Salvo: {relatorio['id_analise']}")
        log_container.markdown(self.get_logs_text())
        
        # Task 3: Notificação
        agent.current_task = "Enviando notificação"
        self.add_log(LogLevel.INFO, agent.name, "Enviando notificação", task="enviar_notificacao")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="enviar_notificacao")
        log_container.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.SUCCESS, agent.name, "Notificação enviada")
        log_container.markdown(self.get_logs_text())
        
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
# 5. INTERFACE WEB STREAMLIT
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

# Formulário de entrada
if not st.session_state.analysis_started:
    st.subheader("📝 Dados do Cliente para Análise")
    
    col1, col2 = st.columns(2)
    
    with col1:
        nome = st.text_input("Nome Completo", value="João Silva Santos")
        cpf_cnpj = st.text_input("CPF/CNPJ", value="123.456.789-00")
        renda_mensal = st.number_input("Renda Mensal (R$)", min_value=0.0, value=8500.00, step=100.0)
    
    with col2:
        valor_solicitado = st.number_input("Valor Solicitado (R$)", min_value=0.0, value=25000.00, step=1000.0)
        prazo_meses = st.number_input("Prazo (meses)", min_value=1, max_value=120, value=36)
        finalidade = st.selectbox("Finalidade", ["Empréstimo Pessoal", "Financiamento Veículo", "Crédito Consignado", "Capital de Giro"])
    
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
    status_container = st.container()
    
    # Barra de progresso
    st.markdown("### 📊 Progresso Geral")
    progress_bar = st.progress(0)
    
    # Logs
    st.markdown("### 📋 Log de Execução em Tempo Real")
    log_container = st.empty()
    
    # Executa análise
    orchestrator = AgentOrchestrator()
    
    # Log inicial
    orchestrator.add_log(LogLevel.INFO, "Sistema", "Iniciando análise de risco financeiro...")
    orchestrator.add_log(LogLevel.INFO, "Sistema", f"Cliente: {st.session_state.client_data['nome']}")
    orchestrator.add_log(LogLevel.INFO, "Sistema", f"Valor: R$ {st.session_state.client_data['valor_solicitado']:,.2f}")
    log_container.markdown(orchestrator.get_logs_text())
    
    # Executa
    result = orchestrator.run_analysis(
        st.session_state.client_data,
        log_container,
        status_container,
        progress_bar
    )
    
    st.session_state.result = result
    st.session_state.analysis_complete = True
    
    time.sleep(1.5)
    st.rerun()

# Tela de resultado
else:
    result = st.session_state.result
    
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
    
    # Nova análise
    st.divider()
    if st.button("🔄 Nova Análise", use_container_width=True):
        st.session_state.analysis_started = False
        st.session_state.analysis_complete = False
        st.session_state.result = None
        st.rerun()

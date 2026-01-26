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
import re

# =================================================================
# 1. CONFIGURAÇÕES
# =================================================================
RAGFLOW_API_KEY = "ragflow-GUY7ZV-fxRZXJDhVJfK1eYXAdsJzWajNN_8mnIIqg8I"
RAGFLOW_BASE_URL = "http://ragflow-cpu:9380/api/v1"
DATASET_ID = "c26eacc8f7e811f09a1aae5f51f02bdf"
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
        
        # Tabela de clientes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                cpf_cnpj VARCHAR(20) UNIQUE,
                nome VARCHAR(255),
                renda_mensal DECIMAL(12,2),
                email VARCHAR(255),
                telefone VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cpf_cnpj) REFERENCES clientes(cpf_cnpj)
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
                FOREIGN KEY (cpf_cnpj) REFERENCES clientes(cpf_cnpj),
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

def buscar_cliente(cpf_cnpj: str) -> Optional[Dict]:
    """Busca dados do cliente na tabela clientes"""
    try:
        conn = get_mysql_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT * FROM clientes 
            WHERE cpf_cnpj = %s
        """
        
        cursor.execute(query, (cpf_cnpj,))
        cliente = cursor.fetchone()
        cursor.close()
        conn.close()
        return cliente
    except Exception as e:
        st.error(f"Erro ao buscar cliente: {str(e)}")
        return None

def strip_em_tags(text: str) -> str:
    return re.sub(r"</?em>", "", text)

def processar_cliente_com_dialog(
    client_data: Dict[str, Any],
    buscar_cliente,
    inserir_cliente,
    atualizar_cliente,
    agent_name: str,
    add_log
) -> Optional[Dict[str, Any]]:
    """
    Processa cliente com diálogo modal.
    Retorna None se diálogo está aberto aguardando confirmação.
    Retorna dados do cliente se confirmado e salvo.
    """

    cpf_cnpj = client_data.get("cpf_cnpj", "")

    # ========== INICIALIZA SESSION STATE ==========
    if "cliente_dados_completos" not in st.session_state:
        st.session_state.cliente_dados_completos = None

    if "cliente_erros_validacao" not in st.session_state:
        st.session_state.cliente_erros_validacao = []

    if "dialog_aberto" not in st.session_state:
        st.session_state.dialog_aberto = False

    if "cliente_cpf_atual" not in st.session_state:
        st.session_state.cliente_cpf_atual = None

    if "cliente_dialog_cancelado" not in st.session_state:
        st.session_state.cliente_dialog_cancelado = False

    if "cliente_confirmado" not in st.session_state:
        st.session_state.cliente_confirmado = False

    cliente_db = buscar_cliente(cpf_cnpj)

    if cliente_db:
        # ========== CLIENTE JÁ EXISTE ==========
        if (cliente_db["nome"] != client_data.get("nome") or
            cliente_db["renda_mensal"] != client_data.get("renda_mensal")):
            atualizar_cliente(client_data)
            add_log("INFO", agent_name, "Dados do cliente atualizados no banco")
        else:
            add_log("INFO", agent_name, "Dados do cliente recuperados do banco")

        client_data["renda_mensal"] = cliente_db["renda_mensal"]
        client_data["email"] = cliente_db.get("email", "")
        client_data["telefone"] = cliente_db.get("telefone", "")
        return client_data

    # ========== NOVO CLIENTE DETECTADO ==========
    if cpf_cnpj != st.session_state.cliente_cpf_atual:
        st.session_state.cliente_cpf_atual = cpf_cnpj
        st.session_state.dialog_aberto = True
        st.session_state.cliente_dados_completos = None
        st.session_state.cliente_erros_validacao = []
        st.session_state.cliente_dialog_cancelado = False
        st.session_state.cliente_confirmado = False

    @st.dialog("Completar Dados do Cliente", width="large")
    def dialog_novo_cliente():
        st.subheader("📝 Novo Cliente Detectado")

        st.info(
            f"**CPF/CNPJ:** {cpf_cnpj}\n\n"
            f"**Nome:** {client_data.get('nome')}\n\n"
            f"**Renda Mensal:** R$ {client_data.get('renda_mensal'):,.2f}"
        )

        st.divider()

        if st.session_state.cliente_erros_validacao:
            st.error("\n".join(st.session_state.cliente_erros_validacao))

        email_key = f"email_{cpf_cnpj}"
        telefone_key = f"telefone_{cpf_cnpj}"

        st.text_input("📧 Email *", key=email_key, placeholder="seu@email.com")
        st.text_input("📱 Telefone *", key=telefone_key, placeholder="(11) 99999-9999")

        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            if st.button("✓ Confirmar", use_container_width=True, type="primary", key=f"btn_{cpf_cnpj}"):
                erros = []

                email = (st.session_state.get(email_key) or "").strip()
                telefone = (st.session_state.get(telefone_key) or "").strip()

                if not email:
                    erros.append("Email é obrigatório")
                elif "@" not in email or "." not in email:
                    erros.append("Email inválido")

                if not telefone:
                    erros.append("Telefone é obrigatório")
                else:
                    apenas_numeros = "".join(c for c in telefone if c.isdigit())
                    if len(apenas_numeros) < 10:
                        erros.append("Telefone deve ter pelo menos 10 dígitos")

                if erros:
                    st.session_state.cliente_erros_validacao = erros
                    st.rerun()
                else:
                    st.session_state.cliente_dados_completos = {
                        "cpf_cnpj": cpf_cnpj,
                        "nome": client_data.get("nome"),
                        "renda_mensal": client_data.get("renda_mensal"),
                        "email": email,
                        "telefone": telefone,
                        "created_at": datetime.now(),
                    }
                    st.session_state.cliente_erros_validacao = []
                    st.session_state.dialog_aberto = False
                    st.session_state.cliente_confirmado = True
                    st.session_state.pop(email_key, None)
                    st.session_state.pop(telefone_key, None)
                    st.rerun()

        with col2:
            if st.button("✗ Cancelar", use_container_width=True, key=f"cancel_{cpf_cnpj}"):
                st.session_state.cliente_dialog_cancelado = True
                st.session_state.cliente_dados_completos = None
                st.session_state.cliente_erros_validacao = []
                st.session_state.dialog_aberto = False
                st.session_state.pop(email_key, None)
                st.session_state.pop(telefone_key, None)
                st.rerun()

    # Renderiza o diálogo se estiver aberto
    if st.session_state.dialog_aberto:
        dialog_novo_cliente()

    # Se o usuário cancelou/fechou
    if st.session_state.cliente_dialog_cancelado:
        st.session_state.cliente_dialog_cancelado = False
        st.session_state.cliente_dados_completos = None
        st.session_state.cliente_erros_validacao = []
        st.session_state.dialog_aberto = False
        st.session_state.cliente_cpf_atual = None
        raise ValueError("Cadastro do cliente foi cancelado pelo usuário")

    # Se confirmou e já tem dados completos, insere no banco
    if st.session_state.cliente_dados_completos and st.session_state.cliente_confirmado:
        dados = st.session_state.cliente_dados_completos

        if inserir_cliente(dados):
            add_log("SUCCESS", agent_name, "Novo cliente inserido no banco")
            
            # Limpa estado para próximo cliente
            st.session_state.cliente_dados_completos = None
            st.session_state.cliente_erros_validacao = []
            st.session_state.dialog_aberto = False
            st.session_state.cliente_cpf_atual = None
            st.session_state.cliente_confirmado = False
            
            # Retorna dados para continuar
            return dados

        add_log("ERROR", agent_name, "Erro ao inserir novo cliente no banco")
        raise ValueError("Erro ao inserir cliente no banco de dados")

    # Se diálogo está aberto, retorna None (aguardando confirmação)
    if st.session_state.dialog_aberto and not st.session_state.cliente_confirmado:
        return None

    # Se chegou aqui sem dados, retorna None
    return None

def inserir_cliente(client_data: Dict) -> bool:
    """Insere um novo cliente na tabela clientes"""
    try:
        conn = get_mysql_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        query = """
            INSERT INTO clientes 
            (cpf_cnpj, nome, renda_mensal, email, telefone)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        values = (
            client_data.get('cpf_cnpj'),
            client_data.get('nome'),
            client_data.get('renda_mensal'),
            client_data.get('email'),
            client_data.get('telefone'),
        )
        
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Erro ao inserir cliente: {str(e)}")
        return False

def atualizar_cliente(client_data: Dict) -> bool:
    """Atualiza dados do cliente na tabela clientes"""
    try:
        conn = get_mysql_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        query = """
            UPDATE clientes 
            SET nome = %s, renda_mensal = %s
            WHERE cpf_cnpj = %s
        """
        
        values = (
            client_data.get('nome'),
            client_data.get('renda_mensal'),
            client_data.get('cpf_cnpj')
        )
        
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar cliente: {str(e)}")
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
def consult_rag(query: str, max_retries: int = 2) -> Dict[str, Any]:
    url = f"{RAGFLOW_BASE_URL}/retrieval"

    api_key = (RAGFLOW_API_KEY or "").strip()
    if not api_key:
        return {"success": False, "error": "RAGFLOW_API_KEY vazio", "chunks": [], "data": {}}

    # Normaliza para evitar "Bearer Bearer ..."
    if api_key.lower().startswith("bearer "):
        auth_header = api_key  # já veio completo
    else:
        auth_header = f"Bearer {api_key}"

    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
    }

    payload = {
        "question": query,
        "dataset_ids": [DATASET_ID],
        "page": 1,
        "page_size": 10,
        "similarity_threshold": 0.2,
        "keyword": True,
        "highlight": True,
        # opcionais (defaults da doc):
        # "top_k": 1024,
        # "vector_similarity_weight": 0.3,
    }

    last_error: Dict[str, Any] = {"success": False, "error": "Falha não inicializada", "chunks": [], "data": {}}

    for attempt in range(max_retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)

            # Erro HTTP
            if resp.status_code != 200:
                last_error = {
                    "success": False,
                    "error": f"HTTP {resp.status_code}",
                    "status_code": resp.status_code,
                    "response_text": resp.text[:500],
                    "chunks": [],
                    "data": {},
                }
                continue

            result = resp.json()
            code = result.get("code")
            data = result.get("data")

            # Se data vier False/None (como no seu caso), trate como falha (auth/perm/etc.)
            if not isinstance(data, dict):
                msg = result.get("message") or "Resposta inválida (data não é objeto). Possível falha de autorização."
                last_error = {"success": False, "error": msg, "code": code, "chunks": [], "data": {}}
                continue

            if code != 0:
                msg = result.get("message", "Erro desconhecido")
                last_error = {"success": False, "error": msg, "code": code, "chunks": [], "data": data or {}}
                continue

            chunks = data.get("chunks", [])
            return {"success": True, "chunks": chunks, "data": data}

        except requests.Timeout:
            last_error = {"success": False, "error": "Timeout na conexão com RAGFlow (10s)", "chunks": [], "data": {}}
        except requests.ConnectionError as e:
            last_error = {"success": False, "error": f"Erro de conexão: {str(e)}", "chunks": [], "data": {}}
        except Exception as e:
            last_error = {"success": False, "error": f"Erro inesperado: {str(e)}", "chunks": [], "data": {}}

    return last_error

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
                
                # # Executa tasks do agente
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
        
        agent.current_task = "Validando CPF/CNPJ"
        self.add_log(LogLevel.INFO, agent.name, "Validando CPF/CNPJ", task="validar_cpf_cnpj")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="validar_cpf_cnpj")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        # Validação básica de formato
        cpf_cnpj_aux = str(client_data.get('cpf_cnpj', ''))
        cpf_cnpj_valido = database_tools.validar_cpf_cnpj(cpf_cnpj_aux)
        if cpf_cnpj_valido['valido'] == False:
            self.add_log(LogLevel.ERROR, agent.name,cpf_cnpj_valido)
            error_msg = f"CPF/CNPJ inválido: {client_data.get('cpf_cnpj', 'N/A')}"
            raise ValueError(error_msg)      
        
        self.add_log(LogLevel.SUCCESS, agent.name, f"CPF/CNPJ válido: {cpf_cnpj_aux}")
        log_placeholder.markdown(self.get_logs_text())
        result['cpf_valido'] = cpf_cnpj_valido['valido']
        
               
        agent.current_task = "Buscando dados do cliente"
        self.add_log(LogLevel.INFO, agent.name, "Buscando dados do cliente", task="buscar_dados_cliente")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
        
        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="buscar_dados_cliente")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)
                     
        resultado = processar_cliente_com_dialog(
            client_data=client_data,
            buscar_cliente=buscar_cliente,
            inserir_cliente=inserir_cliente,
            atualizar_cliente=atualizar_cliente,
            agent_name=agent.name,
            add_log=self.add_log
        )
    
        if resultado:
            client_data = resultado
            
            self.add_log(LogLevel.SUCCESS, agent.name, f"Dados recuperados: {client_data.get('nome', 'N/A')}")
            log_placeholder.markdown(self.get_logs_text())
            result['cliente'] = client_data
        
            agent.current_task = "Consultando histórico"       
            self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="consultar_historico_credito")
            log_placeholder.markdown(self.get_logs_text())
            time.sleep(0.3)
                     
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
        else:
            # Aguardando preenchimento do diálogo
            st.info("⏳ Aguardando dados do cliente...")

        return result
    
    def _run_risk_analyst(self, agent: AgentInfo, data: Dict, log_placeholder) -> Dict:
        """Executa o Agente Analista de Risco"""
        result = {}
        
        cliente = data.get('cliente', {})
        cpf_cnpj = cliente.get('cpf_cnpj', '').strip()
        renda_mensal = cliente.get('renda_mensal', 0)
        valor_solicitado = cliente.get('valor_solicitado', 0)
        
        if not cpf_cnpj:
            self.add_log(LogLevel.ERROR, agent.name, "CPF/CNPJ não informado")
            raise ValueError("CPF/CNPJ obrigatório para análise de risco")

        # -------------------------------------------------------------------------
        # 1. Calcula taxa de comprometimento / endividamento
        # -------------------------------------------------------------------------
        agent.current_task = "Calculando taxa de endividamento"
        self.add_log(LogLevel.INFO, agent.name, "Calculando taxa_endividamento", task="analisar_endividamento")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.4)

        if renda_mensal <= 0:
            taxa = 100.0
            self.add_log(LogLevel.ERROR, agent.name, "Renda mensal inválida ou zerada → taxa = 100%")
        else:
            parcela_estimada = valor_solicitado / 36
            taxa = ( float( parcela_estimada ) / float( renda_mensal ) ) * 100
            taxa = min(taxa, 100.0)

        result['taxa_endividamento'] = round(taxa, 2)

        if taxa > 45:
            self.add_log(LogLevel.WARNING, agent.name, f"Taxa alta: {taxa:.2f}% → comprometimento elevado")
        elif taxa > 30:
            self.add_log(LogLevel.WARNING, agent.name, f"Taxa moderada: {taxa:.2f}%")
        else:
            self.add_log(LogLevel.SUCCESS, agent.name, f"Taxa: {taxa:.2f}% — adequada")
        
        log_placeholder.markdown(self.get_logs_text())

        # -------------------------------------------------------------------------
        # 2. Consulta restrições via API externa (MockAPI no exemplo)
        # -------------------------------------------------------------------------
        agent.current_task = "Consultando restrições cadastrais"
        self.add_log(LogLevel.INFO, agent.name, "Iniciando consulta externa", task="verificar_restricoes")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.4)

        self.add_log(LogLevel.TOOL, agent.name, "Chamando API de restrições", tool="consulta_restricoes_api")
        log_placeholder.markdown(self.get_logs_text())

        api_url = f"https://696bf31d624d7ddccaa261de.mockapi.io/api/consulta/consultaRestricoes/{cpf_cnpj}"

        try:
            self.add_log(LogLevel.MCP, agent.name, f"GET", mcp_connection=f"{api_url}")
            log_placeholder.markdown(self.get_logs_text())
            time.sleep(0.5)

            response = requests.get(api_url, timeout=8)
            
            if response.status_code == 200:
                dados_api = response.json()
                                
                if isinstance(dados_api, dict):
                    tem_restricao = dados_api.get("Restricao", False)  # Booleano direto
                    nome_api = dados_api.get("Nome", "")
                    cpf_api = dados_api.get("CPF", "")
                    
                    # Validação extra: verifica se CPF retornado bate com o consultado
                    if cpf_api != cpf_cnpj:
                        self.add_log(LogLevel.WARNING, agent.name, f"CPF retornado ({cpf_api}) não coincide com o consultado ({cpf_cnpj})")
                        tem_restricao = True 
                    
                    # Opcional: comparar nome se disponível no cliente
                    if nome_api and cliente.get('nome', '').strip().lower() != nome_api.lower():
                        self.add_log(LogLevel.INFO, agent.name, f"Nome retornado: {nome_api} (vs. informado: {cliente.get('nome', 'N/A')})")
                    
                    result['possui_restricoes'] = tem_restricao
                    result['detalhes_restricoes'] = dados_api  # Salva o JSON completo para relatórios
                    
                    if tem_restricao:
                        self.add_log(LogLevel.WARNING, agent.name, "⚠️ Restrição cadastral encontrada")
                    else:
                        self.add_log(LogLevel.SUCCESS, agent.name, "✅ Sem restrições cadastrais")
                else:
                    self.add_log(LogLevel.ERROR, agent.name, "Formato de resposta inválido (esperado dict)")
                    result['possui_restricoes'] = True  # Assume restrição por segurança
                
            elif response.status_code == 404:
                self.add_log(LogLevel.SUCCESS, agent.name, "Cliente sem registro de restrições (404)")
                result['possui_restricoes'] = False
                
            else:
                self.add_log(
                    LogLevel.WARNING, 
                    agent.name, 
                    f"API retornou status {response.status_code} — assumindo sem restrição"
                )
                result['possui_restricoes'] = False

        except requests.Timeout:
            self.add_log(LogLevel.ERROR, agent.name, "Timeout na consulta de restrições → assumindo sem restrição")
            result['possui_restricoes'] = False
        except requests.RequestException as e:
            self.add_log(LogLevel.ERROR, agent.name, f"Falha na API de restrições: {str(e)}")
            result['possui_restricoes'] = False
        except Exception as e:
            self.add_log(LogLevel.ERROR, agent.name, f"Erro inesperado na consulta: {str(e)}")
            result['possui_restricoes'] = False

        log_placeholder.markdown(self.get_logs_text())

        # -------------------------------------------------------------------------
        # 3. Calcula score financeiro simples (você pode melhorar bastante aqui)
        # -------------------------------------------------------------------------
        agent.current_task = "Calculando score financeiro"
        self.add_log(LogLevel.INFO, agent.name, "Calculando score_financeiro", task="calcular_score_financeiro")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.4)

        score = 700
        
        if taxa > 50:
            score -= 250
        elif taxa > 35:
            score -= 120
            
        if result.get('possui_restricoes', False):
            score -= 300
            
        if renda_mensal < 2000:
            score -= 80
        elif renda_mensal < 4000:
            score -= 30

        score = max(300, min(850, score))
        result['score_financeiro'] = score

        classificacao = "BAIXO" if score >= 700 else "MÉDIO" if score >= 500 else "ALTO"
        result['classificacao_risco'] = classificacao

        self.add_log(LogLevel.SUCCESS, agent.name, f"Score: {score} → {classificacao}")
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
        """Executa o Agente Consultor RAG com chamadas reais à API do RAGFlow"""
        result = {}
    
        classificacao = data.get('classificacao_risco', 'MÉDIO')
    
        # -------------------------------------------------------------------------
        # 1. Consulta políticas de crédito via RAGFlow
        # -------------------------------------------------------------------------
        agent.current_task = "Consultando políticas de crédito no RAGFlow"
        self.add_log(LogLevel.INFO, agent.name, "Preparando query para políticas de crédito", task="consultar_politicas_credito")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.4)

        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="consultar_politicas_credito")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)

        query_politica = f"Política de crédito para risco {classificacao}. Forneça detalhes sobre critérios de aprovação, limites e condições."
    
        self.add_log(LogLevel.MCP, agent.name, f"POST {RAGFLOW_BASE_URL}/retrieval | Query: {query_politica[:50]}...", mcp_connection="api://ragflow/retrieval")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.5)

        rag_response = consult_rag(query_politica)
        
        if not rag_response.get("success"):
            politica = f"Erro ao consultar RAGFlow: {rag_response.get('error', 'Erro desconhecido')}"
            self.add_log(LogLevel.ERROR, agent.name, politica)
            result['politica_aplicavel'] = "Política não disponível devido a erro na consulta. Usando default: Aprovação condicional para risco médio."
        else:
            chunks = rag_response.get('chunks', [])
            if chunks:
                politica = chunks[0].get('content', '')
                similarity = chunks[0].get('similarity', 0)
            
                sources = [
                {
                    'documento': chunks[0].get('document_keyword', 'Desconhecido'),
                    'confianca': similarity,
                    'chunk_id': chunks[0].get('id', '')
                }
                ]
            
                if similarity < 0.7:
                    self.add_log(LogLevel.WARNING, agent.name, f"Baixa confiança na resposta: {similarity:.1%}")
                else:
                    self.add_log(LogLevel.SUCCESS, agent.name, f"Política obtida com confiança: {similarity:.1%}")
            
                result['politica_aplicavel'] = politica
                result['politica_sources'] = sources
                result['politica_confianca'] = similarity
            else:
                politica = f"Política padrão para risco {classificacao}: Aprovação condicional com análise manual."
                self.add_log(LogLevel.WARNING, agent.name, f"Nenhum resultado encontrado no RAGFlow — usando fallback")
                result['politica_aplicavel'] = politica
                result['politica_sources'] = []
                result['politica_confianca'] = 0

        log_placeholder.markdown(self.get_logs_text())

    # -------------------------------------------------------------------------
    # 2. Consulta regulamentações via RAGFlow
    # -------------------------------------------------------------------------
        agent.current_task = "Consultando regulamentações BACEN no RAGFlow"
        self.add_log(LogLevel.INFO, agent.name, "Preparando query para regulamentações", task="buscar_regulamentacoes")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.4)

        self.add_log(LogLevel.TOOL, agent.name, "Executando tool", tool="buscar_regulamentacoes")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.3)

        query_reg = f"Regulamentações BACEN relevantes para análise de crédito de risco {classificacao}. Liste resoluções e circulares principais."

        self.add_log(LogLevel.MCP, agent.name, f"POST {RAGFLOW_BASE_URL}/retrieval | Query: {query_reg[:50]}...", mcp_connection="api://ragflow/retrieval")
        log_placeholder.markdown(self.get_logs_text())
        time.sleep(0.5)

        rag_response_reg = consult_rag(query_reg)
    
        if not rag_response_reg.get("success"):
            regulamentacoes = [f"Erro: {rag_response_reg.get('error', 'Erro desconhecido')}"]
            self.add_log(LogLevel.ERROR, agent.name, regulamentacoes[0])
            result['regulamentacoes'] = [
            "Resolução CMN 4.949/2021 - Política de crédito (fallback)",
            "Circular BACEN 3.978/2020 - Prevenção à lavagem (fallback)"
            ]
        else:
        
            chunks = rag_response_reg.get('chunks', [])
        
            if chunks:
                reg_text = '\n'.join([chunk.get('content', '') for chunk in chunks])
                regulamentacoes = [
                    line.strip() 
                    for line in reg_text.split('\n') 
                        if line.strip() and any(keyword in line for keyword in ['Resolução', 'Circular', 'Normativa', 'Lei'])
                ]
            
                if not regulamentacoes:
                    regulamentacoes = [chunk.get('content', '') for chunk in chunks if chunk.get('content', '').strip()]
            
                if chunks:
                    confidence = chunks[0].get('similarity', 0)
                    if confidence < 0.7:
                        self.add_log(LogLevel.WARNING, agent.name, f"Baixa confiança: {confidence:.1%}")
                    else:
                        self.add_log(LogLevel.SUCCESS, agent.name, f"Encontradas {len(regulamentacoes)} regulamentações relevantes")
            
                result['regulamentacoes'] = regulamentacoes if regulamentacoes else [
                "Resolução CMN 4.949/2021 - Política de crédito (fallback)",
                "Circular BACEN 3.978/2020 - Prevenção à lavagem (fallback)"
                ]
            else:
                regulamentacoes = [
                "Resolução CMN 4.949/2021 - Política de crédito (fallback)",
                "Circular BACEN 3.978/2020 - Prevenção à lavagem (fallback)",
                "Resolução CMN 4.557/2017 - Gerenciamento de risco (fallback)"
                ]
                self.add_log(LogLevel.WARNING, agent.name, "Nenhum resultado encontrado — usando fallback")
                result['regulamentacoes'] = regulamentacoes

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
        
        self.add_log(LogLevel.MCP, agent.name, "INSERT INTO analises_risco", mcp_connection="mysql://localhost:3306/credit_db")
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
        cpf_cnpj = st.text_input("CPF/CNPJ", value="16142693001")  # Sem pontuação para validação
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
        client_data = {
            "nome": nome,
            "cpf_cnpj": cpf_cnpj,
            "renda_mensal": renda_mensal,
            "valor_solicitado": valor_solicitado,
            "prazo_meses": prazo_meses,
            "finalidade": finalidade
        }
    
        try:
            resultado = processar_cliente_com_dialog(
                client_data=client_data,
                buscar_cliente=buscar_cliente,
                inserir_cliente=inserir_cliente,
                atualizar_cliente=atualizar_cliente,
                agent_name="Sistema",
                add_log=lambda level, agent, msg, **kwargs: None  
            )
        
            if resultado is None:
                st.warning("⏳ Preencha os dados do cliente no diálogo para continuar...")
                st.stop()
        
            if resultado:
                client_data.update(resultado)
            
                st.session_state.analysis_started = True
                st.session_state.client_data = client_data
                st.rerun()
            else:
                st.error("Erro ao processar cliente")
                st.stop()
    
        except ValueError as e:
            st.error(f"❌ {str(e)}")
            st.stop()

elif st.session_state.analysis_started and not st.session_state.analysis_complete:
    st.subheader("⚙️ Processamento em Andamento")
    
    st.markdown("### 🤖 Status dos Agentes")
    status_placeholder = st.empty()
    
    st.markdown("### 📊 Progresso Geral")
    progress_bar = st.progress(0)
    
    st.markdown("### 📋 Log de Execução em Tempo Real")
    log_placeholder = st.empty()
    
    orchestrator = AgentOrchestrator()
    st.session_state.orchestrator = orchestrator
    
    orchestrator.add_log(LogLevel.INFO, "Sistema", "Iniciando análise de risco financeiro...")
    # orchestrator.add_log(LogLevel.INFO, "Sistema", f"Cliente: {st.session_state.client_data['nome']}")
    # orchestrator.add_log(LogLevel.INFO, "Sistema", f"Valor Solicitado: R$ {st.session_state.client_data['valor_solicitado']:,.2f}")
    log_placeholder.markdown(orchestrator.get_logs_text())
    
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
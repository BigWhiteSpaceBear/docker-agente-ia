"""
Agente Consultor RAG
Responsável por consultar documentos e políticas usando RAGFlow.

Tools utilizadas:
9. consultar_politicas_credito - Busca políticas no RAGFlow
10. buscar_regulamentacoes - Busca regulamentações do Banco Central
"""

from crewai import Agent, Task
from tools.rag_tools import consultar_politicas_credito, buscar_regulamentacoes


class RAGConsultantAgent:
    """Agente especializado em consultas RAG para políticas e regulamentações."""
    
    def __init__(self):
        self.agent = Agent(
            role="Consultor de Políticas e Regulamentações",
            goal="Consultar documentos de políticas internas e regulamentações externas usando RAGFlow.",
            backstory="""Você é um especialista em compliance e regulamentação bancária. 
            Sua função é consultar a base de conhecimento (RAGFlow) para encontrar 
            políticas de crédito internas e regulamentações do Banco Central que se 
            aplicam ao perfil do cliente em análise, garantindo que todas as decisões 
            estejam em conformidade com as normas vigentes.""",
            tools=[consultar_politicas_credito, buscar_regulamentacoes],
            verbose=True,
            allow_delegation=False
        )
    
    def criar_tarefa(self, contexto: Task) -> Task:
        """Cria uma tarefa de consulta RAG para o agente."""
        return Task(
            description="""
            Consultar as políticas de crédito internas e regulamentações externas 
            aplicáveis ao perfil do cliente em análise.
            
            Passos:
            1. Identificar o perfil de risco do cliente (baseado nas etapas anteriores)
            2. Consultar políticas de crédito internas no RAGFlow
            3. Buscar regulamentações do Banco Central aplicáveis
            4. Consolidar as políticas e regulamentações relevantes
            """,
            expected_output="""Um dicionário Python contendo:
            - politicas_aplicaveis: lista de políticas internas relevantes
            - regulamentacoes: regulamentações do BACEN aplicáveis
            - restricoes_normativas: restrições baseadas em normas
            - recomendacao_compliance: parecer de conformidade
            """,
            context=[contexto],
            agent=self.agent
        )

"""
Agente Analista de Risco
Responsável por analisar indicadores financeiros e calcular métricas de risco.

Tools utilizadas:
4. calcular_score_financeiro - Calcula score baseado em indicadores
5. analisar_endividamento - Analisa nível de endividamento
6. verificar_restricoes - Verifica restrições cadastrais
"""

from crewai import Agent, Task
from tools.analysis_tools import calcular_score_financeiro, analisar_endividamento, verificar_restricoes


class RiskAnalystAgent:
    """Agente especializado em análise de risco financeiro."""
    
    def __init__(self):
        self.agent = Agent(
            role="Analista de Risco Financeiro",
            goal="Analisar indicadores financeiros e calcular métricas de risco do cliente.",
            backstory="""Você é um analista financeiro sênior com mais de 15 anos de 
            experiência em análise de crédito. Sua especialidade é identificar padrões 
            de risco e calcular scores financeiros precisos que ajudam na tomada de 
            decisão de concessão de crédito.""",
            tools=[calcular_score_financeiro, analisar_endividamento, verificar_restricoes],
            verbose=True,
            allow_delegation=False
        )
    
    def criar_tarefa(self, contexto: Task) -> Task:
        """Cria uma tarefa de análise de risco para o agente."""
        return Task(
            description="""
            Analisar os dados do cliente coletados na etapa anterior para calcular 
            métricas de risco financeiro.
            
            Passos:
            1. Calcular o score financeiro baseado na renda e histórico
            2. Analisar o nível de endividamento do cliente
            3. Verificar se existem restrições cadastrais
            4. Consolidar as métricas de risco
            """,
            expected_output="""Um dicionário Python contendo:
            - score_financeiro: valor numérico de 0 a 100
            - nivel_endividamento: Baixo, Médio ou Alto
            - restricoes: True ou False
            - analise_detalhada: descrição da análise
            """,
            context=[contexto],
            agent=self.agent
        )

"""
Agente Preditor de ML
Responsável por utilizar modelo de Machine Learning para predição de risco.

Tools utilizadas:
7. prever_risco_credito - Modelo XGBoost para classificação de risco
8. calcular_probabilidade_default - Calcula probabilidade de inadimplência
"""

from crewai import Agent, Task
from tools.ml_tools import prever_risco_credito, calcular_probabilidade_default


class MLPredictorAgent:
    """Agente especializado em predições usando Machine Learning."""
    
    def __init__(self):
        self.agent = Agent(
            role="Cientista de Dados - Preditor de Risco",
            goal="Utilizar modelos de Machine Learning para prever o risco de crédito do cliente.",
            backstory="""Você é um cientista de dados especializado em modelos de 
            risco de crédito. Você desenvolveu e mantém um modelo de Machine Learning 
            (XGBoost/Random Forest) treinado com milhões de registros históricos de 
            crédito, capaz de prever com alta precisão a probabilidade de inadimplência.""",
            tools=[prever_risco_credito, calcular_probabilidade_default],
            verbose=True,
            allow_delegation=False
        )
    
    def criar_tarefa(self, contexto: Task) -> Task:
        """Cria uma tarefa de predição de ML para o agente."""
        return Task(
            description="""
            Utilizar o modelo de Machine Learning para prever o risco de crédito 
            com base nos dados e métricas calculadas nas etapas anteriores.
            
            Passos:
            1. Preparar os dados de entrada para o modelo
            2. Executar o modelo de classificação de risco
            3. Calcular a probabilidade de inadimplência (default)
            4. Interpretar os resultados do modelo
            """,
            expected_output="""Um dicionário Python contendo:
            - classificacao_risco: Baixo, Médio ou Alto
            - probabilidade_default: valor entre 0 e 1
            - confianca_modelo: nível de confiança da predição
            - features_importantes: principais fatores que influenciaram a decisão
            """,
            context=[contexto],
            agent=self.agent
        )

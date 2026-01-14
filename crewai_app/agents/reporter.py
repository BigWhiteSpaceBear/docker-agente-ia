"""
Agente Relator
Responsável por gerar relatórios consolidados e recomendações.

Tools utilizadas:
11. gerar_relatorio_risco - Gera relatório em formato estruturado
12. salvar_analise_banco - Persiste análise no MySQL
13. enviar_notificacao - Envia notificação sobre a análise
"""

from crewai import Agent, Task
from tools.database_tools import gerar_relatorio_risco, salvar_analise_banco, enviar_notificacao


class ReporterAgent:
    """Agente especializado em geração de relatórios e persistência de dados."""
    
    def __init__(self):
        self.agent = Agent(
            role="Relator e Gestor de Documentação",
            goal="Gerar relatórios consolidados, salvar análises no banco de dados e notificar stakeholders.",
            backstory="""Você é um especialista em documentação e relatórios financeiros. 
            Sua função é consolidar todas as informações das análises anteriores em um 
            relatório claro e acionável, garantir que todas as análises sejam devidamente 
            registradas no banco de dados para auditoria, e notificar as partes 
            interessadas sobre o resultado da análise.""",
            tools=[gerar_relatorio_risco, salvar_analise_banco, enviar_notificacao],
            verbose=True,
            allow_delegation=False
        )
    
    def criar_tarefa(self, contexto: Task) -> Task:
        """Cria uma tarefa de geração de relatório para o agente."""
        return Task(
            description="""
            Consolidar todas as informações coletadas e análises realizadas em um 
            relatório final, salvar no banco de dados e notificar sobre a conclusão.
            
            Passos:
            1. Consolidar dados do cliente, métricas de risco e predições de ML
            2. Incluir parecer de compliance baseado nas políticas consultadas
            3. Gerar recomendação final (Aprovar, Reprovar, Análise Manual)
            4. Salvar a análise completa no banco de dados MySQL
            5. Enviar notificação sobre a conclusão da análise
            """,
            expected_output="""Um dicionário JSON completo contendo:
            - cliente: dados do cliente
            - analise_risco: métricas e scores
            - predicao_ml: resultado do modelo
            - compliance: parecer normativo
            - recomendacao_final: decisão sugerida
            - status_salvamento: confirmação de persistência
            - status_notificacao: confirmação de envio
            """,
            context=[contexto],
            agent=self.agent
        )

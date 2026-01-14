"""
Agente Coletor de Dados
Responsável por coletar e validar dados do cliente para análise de risco.

Tools utilizadas:
1. buscar_dados_cliente - Busca dados do cliente no banco MySQL
2. validar_cpf_cnpj - Valida documentos de identificação
3. consultar_historico_credito - Consulta histórico de crédito no banco
"""

from crewai import Agent, Task
from tools.database_tools import buscar_dados_cliente, validar_cpf_cnpj, consultar_historico_credito


class DataCollectorAgent:
    """Agente especializado em coleta e validação de dados de clientes."""
    
    def __init__(self):
        self.agent = Agent(
            role="Coletor de Dados",
            goal="Coletar e validar dados do cliente para análise de risco de crédito.",
            backstory="""Você é um especialista em coleta de dados financeiros com anos de 
            experiência em instituições bancárias. Sua função é garantir que todos os dados 
            do cliente sejam coletados de forma precisa e validados antes de prosseguir 
            com a análise de risco.""",
            tools=[buscar_dados_cliente, validar_cpf_cnpj, consultar_historico_credito],
            verbose=True,
            allow_delegation=False
        )
    
    def criar_tarefa(self, cpf_cnpj: str) -> Task:
        """Cria uma tarefa de coleta de dados para o agente."""
        return Task(
            description=f"""
            Coletar todos os dados disponíveis para o cliente com CPF/CNPJ: {cpf_cnpj}
            
            Passos:
            1. Validar o formato do CPF/CNPJ fornecido
            2. Buscar os dados cadastrais do cliente no banco de dados
            3. Consultar o histórico de crédito do cliente
            4. Consolidar todas as informações coletadas
            """,
            expected_output="""Um dicionário Python contendo:
            - dados_cadastrais: nome, cpf_cnpj, renda_mensal
            - historico_credito: descrição do histórico
            - validacao: status da validação do documento
            """,
            agent=self.agent
        )

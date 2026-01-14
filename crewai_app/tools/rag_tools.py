"""
Ferramentas de RAG (Retrieval-Augmented Generation)
Implementa as tools 9-10 para consulta ao RAGFlow.

Tools:
9. consultar_politicas_credito - Busca políticas no RAGFlow
10. buscar_regulamentacoes - Busca regulamentações do Banco Central
"""

import os
import requests
from crewai.tools import tool

# Configuração do RAGFlow
RAGFLOW_API_URL = os.getenv("RAGFLOW_API_URL", "http://ragflow-cpu:9380/api/v1")
RAGFLOW_API_KEY = os.getenv("RAGFLOW_API_KEY", "")


def consultar_ragflow(pergunta: str, dataset_id: str = None) -> str:
    """
    Realiza uma consulta ao RAGFlow.
    
    Args:
        pergunta: Pergunta a ser feita ao RAGFlow
        dataset_id: ID do dataset específico (opcional)
    
    Returns:
        Resposta do RAGFlow ou mensagem de erro
    """
    if not RAGFLOW_API_KEY:
        return f"[SIMULAÇÃO RAG] Resposta para: {pergunta}"
    
    headers = {
        "Authorization": f"Bearer {RAGFLOW_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "question": pergunta,
        "stream": False
    }
    
    if dataset_id:
        payload["dataset_ids"] = [dataset_id]
    
    try:
        response = requests.post(
            f"{RAGFLOW_API_URL}/completion",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("answer", "Sem resposta disponível")
        else:
            return f"Erro RAGFlow: {response.status_code} - {response.text}"
    
    except requests.exceptions.ConnectionError:
        return f"[SIMULAÇÃO - RAGFlow não disponível] Resposta para: {pergunta}"
    except Exception as e:
        return f"Erro ao consultar RAGFlow: {str(e)}"


# =============================================================================
# TOOL 9: Consultar Políticas de Crédito
# =============================================================================
@tool("consultar_politicas_credito")
def consultar_politicas_credito(perfil_risco: str, valor_solicitado: float = 0) -> dict:
    """
    Consulta as políticas de crédito internas usando o RAGFlow.
    
    Esta tool utiliza o RAGFlow (via MCP) para buscar políticas de crédito
    relevantes para o perfil de risco do cliente.
    
    Args:
        perfil_risco: Perfil de risco do cliente (Baixo, Médio, Alto)
        valor_solicitado: Valor do crédito solicitado (padrão: 0)
    
    Returns:
        Dicionário com políticas aplicáveis
    """
    # Monta a pergunta para o RAGFlow
    pergunta = f"""
    Quais são as políticas de crédito aplicáveis para um cliente com perfil de risco {perfil_risco}?
    Valor solicitado: R$ {valor_solicitado:,.2f}
    
    Inclua informações sobre:
    - Limites de crédito permitidos
    - Taxas de juros aplicáveis
    - Garantias exigidas
    - Prazo máximo de financiamento
    """
    
    resposta_rag = consultar_ragflow(pergunta)
    
    # Políticas padrão baseadas no perfil (fallback)
    politicas_padrao = {
        "Baixo": {
            "limite_maximo": 100000,
            "taxa_juros_anual": "12% a 18%",
            "garantia_exigida": "Não obrigatória",
            "prazo_maximo_meses": 60,
            "aprovacao_automatica": True
        },
        "Médio": {
            "limite_maximo": 50000,
            "taxa_juros_anual": "18% a 24%",
            "garantia_exigida": "Avalista ou garantia real para valores > R$ 20.000",
            "prazo_maximo_meses": 48,
            "aprovacao_automatica": False
        },
        "Alto": {
            "limite_maximo": 10000,
            "taxa_juros_anual": "24% a 36%",
            "garantia_exigida": "Obrigatória (garantia real)",
            "prazo_maximo_meses": 24,
            "aprovacao_automatica": False
        }
    }
    
    politica = politicas_padrao.get(perfil_risco, politicas_padrao["Médio"])
    
    return {
        "perfil_risco": perfil_risco,
        "valor_solicitado": valor_solicitado,
        "politica_aplicavel": politica,
        "consulta_ragflow": resposta_rag,
        "fonte": "RAGFlow + Políticas Internas",
        "data_consulta": "2026-01-13"
    }


# =============================================================================
# TOOL 10: Buscar Regulamentações
# =============================================================================
@tool("buscar_regulamentacoes")
def buscar_regulamentacoes(tipo_operacao: str = "credito_pessoal", perfil_cliente: str = "PF") -> dict:
    """
    Busca regulamentações do Banco Central aplicáveis à operação de crédito.
    
    Esta tool utiliza o RAGFlow para buscar regulamentações e normas do BACEN
    que se aplicam ao tipo de operação e perfil do cliente.
    
    Args:
        tipo_operacao: Tipo de operação (credito_pessoal, financiamento, etc.)
        perfil_cliente: PF (Pessoa Física) ou PJ (Pessoa Jurídica)
    
    Returns:
        Dicionário com regulamentações aplicáveis
    """
    # Monta a pergunta para o RAGFlow
    pergunta = f"""
    Quais são as regulamentações do Banco Central aplicáveis para operações de {tipo_operacao}
    para clientes {perfil_cliente}?
    
    Inclua informações sobre:
    - Resolução CMN aplicável
    - Limites de taxas de juros
    - Requisitos de transparência
    - Obrigações de compliance
    """
    
    resposta_rag = consultar_ragflow(pergunta)
    
    # Regulamentações padrão (fallback)
    regulamentacoes = {
        "credito_pessoal": {
            "resolucao_principal": "Resolução CMN nº 4.893/2021",
            "cet_obrigatorio": True,
            "prazo_reflexao": "7 dias para desistência",
            "informacoes_obrigatorias": [
                "CET (Custo Efetivo Total)",
                "Taxa de juros nominal e efetiva",
                "Valor total financiado",
                "Número e valor das parcelas"
            ],
            "limite_taxa": "Não há limite legal (exceto consignado)"
        },
        "financiamento": {
            "resolucao_principal": "Resolução CMN nº 4.676/2018",
            "cet_obrigatorio": True,
            "prazo_reflexao": "7 dias para desistência",
            "garantia_obrigatoria": True,
            "registro_garantia": "Obrigatório em cartório"
        }
    }
    
    reg = regulamentacoes.get(tipo_operacao, regulamentacoes["credito_pessoal"])
    
    # Regulamentações específicas por perfil
    if perfil_cliente == "PJ":
        reg["documentacao_adicional"] = [
            "Contrato social",
            "Balanço patrimonial",
            "DRE dos últimos 3 anos"
        ]
    else:
        reg["documentacao_adicional"] = [
            "Comprovante de renda",
            "Comprovante de residência"
        ]
    
    return {
        "tipo_operacao": tipo_operacao,
        "perfil_cliente": perfil_cliente,
        "regulamentacoes": reg,
        "consulta_ragflow": resposta_rag,
        "fonte": "RAGFlow + BACEN",
        "data_consulta": "2026-01-13",
        "aviso": "Consulte sempre a versão atualizada das normas no site do BACEN"
    }

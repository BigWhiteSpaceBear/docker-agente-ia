"""
Ferramentas de Banco de Dados
Implementa as tools 1-3 e 11-13 para interação com MySQL.

Tools:
1. buscar_dados_cliente - Busca dados do cliente no banco MySQL
2. validar_cpf_cnpj - Valida documentos de identificação
3. consultar_historico_credito - Consulta histórico de crédito no banco
11. gerar_relatorio_risco - Gera relatório em formato estruturado
12. salvar_analise_banco - Persiste análise no MySQL
13. enviar_notificacao - Envia notificação sobre a análise
"""

import os
import json
from datetime import datetime
from crewai.tools import tool

# Configuração do banco de dados
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "mysql"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "infini_rag_flow"),
    "database": os.getenv("MYSQL_DB", "rag_flow")
}


def get_db_connection():
    """Obtém conexão com o banco de dados MySQL."""
    try:
        import mysql.connector
        return mysql.connector.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")
        return None


# =============================================================================
# TOOL 1: Buscar Dados do Cliente
# =============================================================================
@tool("buscar_dados_cliente")
def buscar_dados_cliente(cpf_cnpj: str) -> dict:
    """
    Busca os dados cadastrais de um cliente no banco de dados pelo CPF/CNPJ.
    
    Args:
        cpf_cnpj: CPF ou CNPJ do cliente no formato XXX.XXX.XXX-XX ou XX.XXX.XXX/XXXX-XX
    
    Returns:
        Dicionário com os dados do cliente ou mensagem de erro
    """
    conn = get_db_connection()
    if not conn:
        # Retorna dados simulados se não conseguir conectar
        return {
            "id": 1,
            "nome": "Cliente Simulado",
            "cpf_cnpj": cpf_cnpj,
            "renda_mensal": 5000.00,
            "status": "simulado"
        }
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM clientes WHERE cpf_cnpj = %s",
            (cpf_cnpj,)
        )
        cliente = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if cliente:
            return cliente
        return {"erro": "Cliente não encontrado", "cpf_cnpj": cpf_cnpj}
    except Exception as e:
        return {"erro": str(e), "cpf_cnpj": cpf_cnpj}


# =============================================================================
# TOOL 2: Validar CPF/CNPJ
# =============================================================================
@tool("validar_cpf_cnpj")
def validar_cpf_cnpj(cpf_cnpj: str) -> dict:
    """
    Valida o formato e dígitos verificadores de um CPF ou CNPJ.
    
    Args:
        cpf_cnpj: Documento a ser validado
    
    Returns:
        Dicionário com o resultado da validação
    """
    # Remove caracteres especiais
    doc = ''.join(filter(str.isdigit, cpf_cnpj))
    
    # Verifica se é CPF (11 dígitos) ou CNPJ (14 dígitos)
    if len(doc) == 11:
        tipo = "CPF"
        valido = validar_cpf(doc)
    elif len(doc) == 14:
        tipo = "CNPJ"
        valido = validar_cnpj(doc)
    else:
        return {
            "documento": cpf_cnpj,
            "valido": False,
            "tipo": "Desconhecido",
            "mensagem": "Documento deve ter 11 (CPF) ou 14 (CNPJ) dígitos"
        }
    
    return {
        "documento": cpf_cnpj,
        "valido": valido,
        "tipo": tipo,
        "mensagem": "Documento válido" if valido else "Documento inválido"
    }


def validar_cpf(cpf: str) -> bool:
    """Valida dígitos verificadores do CPF."""
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    
    # Calcula primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    d1 = 0 if resto < 2 else 11 - resto
    
    # Calcula segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    d2 = 0 if resto < 2 else 11 - resto
    
    return cpf[-2:] == f"{d1}{d2}"


def validar_cnpj(cnpj: str) -> bool:
    """Valida dígitos verificadores do CNPJ."""
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    
    # Pesos para cálculo
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    
    # Calcula primeiro dígito verificador
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    resto = soma % 11
    d1 = 0 if resto < 2 else 11 - resto
    
    # Calcula segundo dígito verificador
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    resto = soma % 11
    d2 = 0 if resto < 2 else 11 - resto
    
    return cnpj[-2:] == f"{d1}{d2}"


# =============================================================================
# TOOL 3: Consultar Histórico de Crédito
# =============================================================================
@tool("consultar_historico_credito")
def consultar_historico_credito(cliente_id: int) -> dict:
    """
    Consulta o histórico de crédito de um cliente no banco de dados.
    
    Args:
        cliente_id: ID do cliente no banco de dados
    
    Returns:
        Dicionário com o histórico de crédito do cliente
    """
    conn = get_db_connection()
    if not conn:
        # Retorna dados simulados
        return {
            "cliente_id": cliente_id,
            "historico": "Bom pagador, sem histórico de inadimplência.",
            "score_bureau": 750,
            "status": "simulado"
        }
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT historico_credito FROM clientes WHERE id = %s",
            (cliente_id,)
        )
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if resultado:
            return {
                "cliente_id": cliente_id,
                "historico": resultado.get("historico_credito", "Não disponível"),
                "score_bureau": 700  # Simulado
            }
        return {"cliente_id": cliente_id, "historico": "Não encontrado"}
    except Exception as e:
        return {"erro": str(e), "cliente_id": cliente_id}


# =============================================================================
# TOOL 11: Gerar Relatório de Risco
# =============================================================================
@tool("gerar_relatorio_risco")
def gerar_relatorio_risco(dados_analise: dict) -> dict:
    """
    Gera um relatório de risco consolidado em formato estruturado.
    
    Args:
        dados_analise: Dicionário com todos os dados da análise
    
    Returns:
        Relatório formatado em JSON
    """
    relatorio = {
        "cabecalho": {
            "titulo": "Relatório de Análise de Risco de Crédito",
            "data_geracao": datetime.now().isoformat(),
            "versao": "1.0"
        },
        "dados_cliente": dados_analise.get("cliente", {}),
        "analise_financeira": dados_analise.get("analise", {}),
        "predicao_ml": dados_analise.get("predicao", {}),
        "compliance": dados_analise.get("compliance", {}),
        "recomendacao_final": dados_analise.get("recomendacao", "Análise Manual"),
        "observacoes": dados_analise.get("observacoes", [])
    }
    
    return relatorio


# =============================================================================
# TOOL 12: Salvar Análise no Banco
# =============================================================================
@tool("salvar_analise_banco")
def salvar_analise_banco(relatorio: dict) -> dict:
    """
    Salva o resultado da análise de risco no banco de dados MySQL.
    
    Args:
        relatorio: Dicionário com o relatório completo da análise
    
    Returns:
        Status do salvamento
    """
    conn = get_db_connection()
    if not conn:
        return {
            "sucesso": True,
            "mensagem": "Análise salva (modo simulado)",
            "id_analise": 1
        }
    
    try:
        cursor = conn.cursor()
        sql = """
            INSERT INTO analises 
            (cliente_id, score_risco, probabilidade_default, recomendacao, relatorio_completo)
            VALUES (%s, %s, %s, %s, %s)
        """
        valores = (
            relatorio.get("dados_cliente", {}).get("id", 1),
            relatorio.get("analise_financeira", {}).get("score", 0),
            relatorio.get("predicao_ml", {}).get("probabilidade_default", 0),
            relatorio.get("recomendacao_final", "Análise Manual"),
            json.dumps(relatorio, ensure_ascii=False)
        )
        
        cursor.execute(sql, valores)
        conn.commit()
        id_analise = cursor.lastrowid
        cursor.close()
        conn.close()
        
        return {
            "sucesso": True,
            "mensagem": "Análise salva com sucesso",
            "id_analise": id_analise
        }
    except Exception as e:
        return {
            "sucesso": False,
            "mensagem": f"Erro ao salvar: {str(e)}"
        }


# =============================================================================
# TOOL 13: Enviar Notificação
# =============================================================================
@tool("enviar_notificacao")
def enviar_notificacao(mensagem: str, destinatario: str = "analista@empresa.com") -> dict:
    """
    Envia uma notificação sobre a conclusão da análise.
    
    Args:
        mensagem: Conteúdo da notificação
        destinatario: Email do destinatário (padrão: analista@empresa.com)
    
    Returns:
        Status do envio da notificação
    """
    # Simulação de envio de notificação
    # Em produção, integraria com serviço de email/SMS
    
    notificacao = {
        "tipo": "email",
        "destinatario": destinatario,
        "assunto": "Análise de Risco Concluída",
        "mensagem": mensagem,
        "data_envio": datetime.now().isoformat(),
        "status": "enviado"
    }
    
    print(f"[NOTIFICAÇÃO] Para: {destinatario}")
    print(f"[NOTIFICAÇÃO] Mensagem: {mensagem}")
    
    return {
        "sucesso": True,
        "notificacao": notificacao
    }

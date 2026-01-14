"""
Ferramentas de Análise Financeira
Implementa as tools 4-6 para análise de indicadores financeiros.

Tools:
4. calcular_score_financeiro - Calcula score baseado em indicadores
5. analisar_endividamento - Analisa nível de endividamento
6. verificar_restricoes - Verifica restrições cadastrais
"""

from crewai.tools import tool


# =============================================================================
# TOOL 4: Calcular Score Financeiro
# =============================================================================
@tool("calcular_score_financeiro")
def calcular_score_financeiro(renda_mensal: float, historico_credito: str, tempo_emprego_meses: int = 24) -> dict:
    """
    Calcula um score financeiro baseado na renda, histórico de crédito e tempo de emprego.
    
    Args:
        renda_mensal: Renda mensal do cliente em reais
        historico_credito: Descrição do histórico de crédito
        tempo_emprego_meses: Tempo de emprego em meses (padrão: 24)
    
    Returns:
        Dicionário com o score e detalhamento
    """
    score = 0
    detalhes = []
    
    # Pontuação por faixa de renda (0-30 pontos)
    if renda_mensal >= 15000:
        score += 30
        detalhes.append("Renda alta: +30 pontos")
    elif renda_mensal >= 8000:
        score += 25
        detalhes.append("Renda média-alta: +25 pontos")
    elif renda_mensal >= 5000:
        score += 20
        detalhes.append("Renda média: +20 pontos")
    elif renda_mensal >= 3000:
        score += 15
        detalhes.append("Renda média-baixa: +15 pontos")
    else:
        score += 10
        detalhes.append("Renda baixa: +10 pontos")
    
    # Pontuação por histórico de crédito (0-40 pontos)
    historico_lower = historico_credito.lower()
    if "bom pagador" in historico_lower or "excelente" in historico_lower:
        score += 40
        detalhes.append("Histórico excelente: +40 pontos")
    elif "regular" in historico_lower or "sem inadimplência" in historico_lower:
        score += 30
        detalhes.append("Histórico regular: +30 pontos")
    elif "atraso" in historico_lower:
        score += 15
        detalhes.append("Histórico com atrasos: +15 pontos")
    elif "negativado" in historico_lower or "inadimplente" in historico_lower:
        score += 5
        detalhes.append("Histórico negativo: +5 pontos")
    else:
        score += 20
        detalhes.append("Histórico não classificado: +20 pontos")
    
    # Pontuação por tempo de emprego (0-30 pontos)
    if tempo_emprego_meses >= 60:
        score += 30
        detalhes.append("Emprego estável (5+ anos): +30 pontos")
    elif tempo_emprego_meses >= 36:
        score += 25
        detalhes.append("Emprego estável (3+ anos): +25 pontos")
    elif tempo_emprego_meses >= 24:
        score += 20
        detalhes.append("Emprego estável (2+ anos): +20 pontos")
    elif tempo_emprego_meses >= 12:
        score += 15
        detalhes.append("Emprego recente (1+ ano): +15 pontos")
    else:
        score += 10
        detalhes.append("Emprego muito recente: +10 pontos")
    
    # Classificação do score
    if score >= 80:
        classificacao = "Excelente"
    elif score >= 60:
        classificacao = "Bom"
    elif score >= 40:
        classificacao = "Regular"
    else:
        classificacao = "Baixo"
    
    return {
        "score": score,
        "score_maximo": 100,
        "classificacao": classificacao,
        "detalhes": detalhes
    }


# =============================================================================
# TOOL 5: Analisar Endividamento
# =============================================================================
@tool("analisar_endividamento")
def analisar_endividamento(renda_mensal: float, total_dividas: float, parcelas_mensais: float = 0) -> dict:
    """
    Analisa o nível de endividamento do cliente.
    
    Args:
        renda_mensal: Renda mensal do cliente em reais
        total_dividas: Total de dívidas do cliente em reais
        parcelas_mensais: Valor total das parcelas mensais (padrão: 0)
    
    Returns:
        Dicionário com análise de endividamento
    """
    if renda_mensal <= 0:
        return {
            "erro": "Renda mensal deve ser maior que zero",
            "nivel": "Indeterminado"
        }
    
    # Calcula índice de endividamento total
    indice_endividamento = total_dividas / (renda_mensal * 12)  # Relação dívida/renda anual
    
    # Calcula comprometimento de renda (se parcelas informadas)
    if parcelas_mensais > 0:
        comprometimento_renda = (parcelas_mensais / renda_mensal) * 100
    else:
        # Estima parcelas como 5% do total de dívidas
        parcelas_estimadas = total_dividas * 0.05
        comprometimento_renda = (parcelas_estimadas / renda_mensal) * 100
    
    # Classifica nível de endividamento
    if indice_endividamento <= 0.3 and comprometimento_renda <= 30:
        nivel = "Baixo"
        recomendacao = "Cliente com capacidade de pagamento adequada"
    elif indice_endividamento <= 0.5 and comprometimento_renda <= 50:
        nivel = "Médio"
        recomendacao = "Cliente com endividamento moderado, avaliar com cautela"
    else:
        nivel = "Alto"
        recomendacao = "Cliente com alto endividamento, risco elevado"
    
    return {
        "nivel": nivel,
        "indice_endividamento": round(indice_endividamento, 4),
        "comprometimento_renda_percentual": round(comprometimento_renda, 2),
        "total_dividas": total_dividas,
        "renda_mensal": renda_mensal,
        "recomendacao": recomendacao
    }


# =============================================================================
# TOOL 6: Verificar Restrições
# =============================================================================
@tool("verificar_restricoes")
def verificar_restricoes(cpf_cnpj: str) -> dict:
    """
    Verifica se há restrições cadastrais para o cliente em bureaus de crédito.
    
    Args:
        cpf_cnpj: CPF ou CNPJ do cliente
    
    Returns:
        Dicionário com resultado da verificação de restrições
    """
    # Simulação de consulta a bureaus de crédito
    # Em produção, integraria com Serasa, SPC, etc.
    
    # Remove caracteres especiais para verificação
    doc_limpo = ''.join(filter(str.isdigit, cpf_cnpj))
    
    # Simulação: documentos terminados em números pares não têm restrição
    ultimo_digito = int(doc_limpo[-1]) if doc_limpo else 0
    tem_restricao = ultimo_digito % 2 != 0  # Ímpares têm restrição (simulação)
    
    if tem_restricao:
        return {
            "cpf_cnpj": cpf_cnpj,
            "tem_restricao": True,
            "tipo_restricao": "Pendência financeira",
            "valor_pendencia": 1500.00,
            "data_registro": "2024-06-15",
            "origem": "Serasa (simulado)",
            "recomendacao": "Verificar pendência antes de aprovar crédito"
        }
    else:
        return {
            "cpf_cnpj": cpf_cnpj,
            "tem_restricao": False,
            "tipo_restricao": None,
            "valor_pendencia": 0,
            "data_consulta": "2026-01-13",
            "origem": "Serasa (simulado)",
            "recomendacao": "Cliente sem restrições cadastrais"
        }

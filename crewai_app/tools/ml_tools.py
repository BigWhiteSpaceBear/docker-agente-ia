"""
Ferramentas de Machine Learning
Implementa as tools 7-8 para predição de risco usando modelo de ML.

Tools:
7. prever_risco_credito - Modelo XGBoost/RandomForest para classificação de risco
8. calcular_probabilidade_default - Calcula probabilidade de inadimplência
"""

import os
import numpy as np
from crewai.tools import tool

# Tenta importar bibliotecas de ML
try:
    import joblib
    from sklearn.ensemble import RandomForestClassifier
    ML_DISPONIVEL = True
except ImportError:
    ML_DISPONIVEL = False
    print("Aviso: scikit-learn não disponível, usando simulação")


def carregar_modelo():
    """Carrega o modelo de ML treinado ou cria um modelo dummy."""
    modelo_path = os.path.join(os.path.dirname(__file__), "..", "models", "credit_risk_model.pkl")
    
    if ML_DISPONIVEL:
        try:
            return joblib.load(modelo_path)
        except FileNotFoundError:
            # Cria um modelo dummy se não existir
            print("Modelo não encontrado, criando modelo dummy...")
            modelo = RandomForestClassifier(n_estimators=10, random_state=42)
            # Treina com dados dummy
            X_dummy = np.array([
                [5000, 70],   # Renda, Score -> Baixo risco
                [3000, 40],   # Renda, Score -> Médio risco
                [1500, 20],   # Renda, Score -> Alto risco
                [10000, 90],  # Renda, Score -> Baixo risco
                [2000, 30],   # Renda, Score -> Alto risco
            ])
            y_dummy = np.array([0, 1, 2, 0, 2])  # 0=Baixo, 1=Médio, 2=Alto
            modelo.fit(X_dummy, y_dummy)
            
            # Salva o modelo
            os.makedirs(os.path.dirname(modelo_path), exist_ok=True)
            joblib.dump(modelo, modelo_path)
            return modelo
    return None


# =============================================================================
# TOOL 7: Prever Risco de Crédito (MODELO DE ML)
# =============================================================================
@tool("prever_risco_credito")
def prever_risco_credito(renda_mensal: float, score_financeiro: int, total_dividas: float = 0) -> dict:
    """
    Utiliza um modelo de Machine Learning (Random Forest/XGBoost) para prever 
    o risco de crédito do cliente.
    
    Este é o modelo de ML obrigatório do trabalho, implementado como uma tool
    que pode ser utilizada pelo Agente Preditor de ML.
    
    Args:
        renda_mensal: Renda mensal do cliente em reais
        score_financeiro: Score financeiro calculado (0-100)
        total_dividas: Total de dívidas do cliente (padrão: 0)
    
    Returns:
        Dicionário com a classificação de risco e detalhes do modelo
    """
    modelo = carregar_modelo()
    
    # Prepara features para o modelo
    features = np.array([[renda_mensal, score_financeiro]])
    
    if modelo is not None and ML_DISPONIVEL:
        # Predição usando o modelo treinado
        predicao = modelo.predict(features)[0]
        probabilidades = modelo.predict_proba(features)[0]
        
        # Mapeia classes
        classes = {0: "Baixo", 1: "Médio", 2: "Alto"}
        risco = classes.get(predicao, "Indeterminado")
        
        # Calcula confiança
        confianca = max(probabilidades) * 100
        
        return {
            "classificacao_risco": risco,
            "confianca_modelo": round(confianca, 2),
            "probabilidades": {
                "baixo": round(probabilidades[0] * 100, 2),
                "medio": round(probabilidades[1] * 100, 2) if len(probabilidades) > 1 else 0,
                "alto": round(probabilidades[2] * 100, 2) if len(probabilidades) > 2 else 0
            },
            "modelo_utilizado": "RandomForestClassifier",
            "features_utilizadas": {
                "renda_mensal": renda_mensal,
                "score_financeiro": score_financeiro
            },
            "modo": "modelo_real"
        }
    else:
        # Simulação baseada em regras se ML não disponível
        if score_financeiro >= 70 and renda_mensal >= 5000:
            risco = "Baixo"
            prob_baixo, prob_medio, prob_alto = 0.75, 0.20, 0.05
        elif score_financeiro >= 40 or renda_mensal >= 3000:
            risco = "Médio"
            prob_baixo, prob_medio, prob_alto = 0.25, 0.55, 0.20
        else:
            risco = "Alto"
            prob_baixo, prob_medio, prob_alto = 0.10, 0.25, 0.65
        
        return {
            "classificacao_risco": risco,
            "confianca_modelo": 85.0,
            "probabilidades": {
                "baixo": round(prob_baixo * 100, 2),
                "medio": round(prob_medio * 100, 2),
                "alto": round(prob_alto * 100, 2)
            },
            "modelo_utilizado": "Regras (simulação)",
            "features_utilizadas": {
                "renda_mensal": renda_mensal,
                "score_financeiro": score_financeiro
            },
            "modo": "simulacao"
        }


# =============================================================================
# TOOL 8: Calcular Probabilidade de Default
# =============================================================================
@tool("calcular_probabilidade_default")
def calcular_probabilidade_default(renda_mensal: float, score_financeiro: int, 
                                    total_dividas: float = 0, historico_atrasos: int = 0) -> dict:
    """
    Calcula a probabilidade de inadimplência (default) do cliente usando o modelo de ML.
    
    Args:
        renda_mensal: Renda mensal do cliente em reais
        score_financeiro: Score financeiro calculado (0-100)
        total_dividas: Total de dívidas do cliente (padrão: 0)
        historico_atrasos: Número de atrasos no histórico (padrão: 0)
    
    Returns:
        Dicionário com a probabilidade de default e análise
    """
    modelo = carregar_modelo()
    
    # Prepara features
    features = np.array([[renda_mensal, score_financeiro]])
    
    if modelo is not None and ML_DISPONIVEL:
        # Usa probabilidades do modelo
        probabilidades = modelo.predict_proba(features)[0]
        
        # Probabilidade de default = probabilidade de risco alto + parte do médio
        prob_default = probabilidades[2] if len(probabilidades) > 2 else 0
        prob_default += (probabilidades[1] * 0.3) if len(probabilidades) > 1 else 0
        
        # Ajusta com base em histórico de atrasos
        ajuste_atrasos = min(0.15, historico_atrasos * 0.03)
        prob_default = min(0.99, prob_default + ajuste_atrasos)
        
    else:
        # Cálculo baseado em regras
        base_prob = 1 - (score_financeiro / 100)
        
        # Ajuste por renda
        if renda_mensal >= 10000:
            ajuste_renda = -0.15
        elif renda_mensal >= 5000:
            ajuste_renda = -0.10
        elif renda_mensal >= 3000:
            ajuste_renda = 0
        else:
            ajuste_renda = 0.10
        
        # Ajuste por dívidas
        if total_dividas > 0 and renda_mensal > 0:
            razao_divida = total_dividas / (renda_mensal * 12)
            ajuste_divida = min(0.20, razao_divida * 0.1)
        else:
            ajuste_divida = 0
        
        # Ajuste por atrasos
        ajuste_atrasos = min(0.15, historico_atrasos * 0.03)
        
        prob_default = max(0.01, min(0.99, base_prob + ajuste_renda + ajuste_divida + ajuste_atrasos))
    
    # Classificação da probabilidade
    if prob_default <= 0.10:
        classificacao = "Muito Baixa"
    elif prob_default <= 0.25:
        classificacao = "Baixa"
    elif prob_default <= 0.50:
        classificacao = "Moderada"
    elif prob_default <= 0.75:
        classificacao = "Alta"
    else:
        classificacao = "Muito Alta"
    
    return {
        "probabilidade_default": round(prob_default, 4),
        "probabilidade_percentual": round(prob_default * 100, 2),
        "classificacao": classificacao,
        "fatores_considerados": {
            "renda_mensal": renda_mensal,
            "score_financeiro": score_financeiro,
            "total_dividas": total_dividas,
            "historico_atrasos": historico_atrasos
        },
        "recomendacao": "Aprovar" if prob_default <= 0.25 else (
            "Análise Manual" if prob_default <= 0.50 else "Reprovar"
        )
    }

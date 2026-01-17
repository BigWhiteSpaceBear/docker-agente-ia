-- ============================================================
-- Script de Inicialização do Banco de Dados
-- Sistema Híbrido de Análise de Risco Financeiro
-- Otimizado para RAGFlow + CrewAI
-- ============================================================

-- Usar o banco de dados padrão do RAGFlow
USE rag_flow;

-- ============================================================
-- Tabela: analises_risco
-- Armazena todas as análises de risco realizadas
-- ============================================================
DROP TABLE IF EXISTS analises_risco;
CREATE TABLE analises_risco (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_analise VARCHAR(50) UNIQUE NOT NULL,
    cpf_cnpj VARCHAR(20) NOT NULL,
    nome_cliente VARCHAR(255) NOT NULL,
    renda_mensal DECIMAL(12,2),
    valor_solicitado DECIMAL(12,2),
    prazo_meses INT,
    finalidade VARCHAR(100),
    score_financeiro INT,
    taxa_endividamento DECIMAL(5,2),
    classificacao_risco VARCHAR(20),
    probabilidade_default DECIMAL(5,4),
    possui_restricoes BOOLEAN DEFAULT FALSE,
    recomendacao VARCHAR(500),
    data_analise DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_cpf (cpf_cnpj),
    INDEX idx_data (data_analise),
    INDEX idx_classificacao (classificacao_risco),
    INDEX idx_cpf_data (cpf_cnpj, data_analise)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Tabela: financiamentos
-- Armazena financiamentos aprovados e ativos
-- ============================================================
DROP TABLE IF EXISTS financiamentos;
CREATE TABLE financiamentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_financiamento VARCHAR(50) UNIQUE NOT NULL,
    cpf_cnpj VARCHAR(20) NOT NULL,
    nome_cliente VARCHAR(255) NOT NULL,
    id_analise_referencia VARCHAR(50),
    valor_financiado DECIMAL(12,2) NOT NULL,
    taxa_mensal DECIMAL(5,2) NOT NULL,
    prazo_meses INT NOT NULL,
    status VARCHAR(20) DEFAULT 'ATIVO',
    data_aprovacao DATETIME NOT NULL,
    data_vencimento DATETIME,
    saldo_devedor DECIMAL(12,2),
    parcelas_pagas INT DEFAULT 0,
    parcelas_totais INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (id_analise_referencia) REFERENCES analises_risco(id_analise) ON DELETE SET NULL,
    INDEX idx_cpf (cpf_cnpj),
    INDEX idx_status (status),
    INDEX idx_data_aprovacao (data_aprovacao),
    INDEX idx_cpf_status (cpf_cnpj, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Tabela: historico_credito
-- Armazena histórico de crédito dos clientes
-- ============================================================
DROP TABLE IF EXISTS historico_credito;
CREATE TABLE historico_credito (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cpf_cnpj VARCHAR(20) NOT NULL UNIQUE,
    total_emprestimos INT DEFAULT 0,
    emprestimos_quitados INT DEFAULT 0,
    emprestimos_ativos INT DEFAULT 0,
    atrasos_30_dias INT DEFAULT 0,
    atrasos_90_dias INT DEFAULT 0,
    atrasos_180_dias INT DEFAULT 0,
    restricoes BOOLEAN DEFAULT FALSE,
    data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_cpf (cpf_cnpj),
    INDEX idx_restricoes (restricoes)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Tabela: clientes
-- Armazena dados dos clientes
-- ============================================================
DROP TABLE IF EXISTS clientes;
CREATE TABLE clientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cpf_cnpj VARCHAR(20) UNIQUE NOT NULL,
    nome_completo VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    telefone VARCHAR(20),
    renda_mensal DECIMAL(12,2),
    profissao VARCHAR(255),
    endereco VARCHAR(500),
    cidade VARCHAR(100),
    estado VARCHAR(2),
    cep VARCHAR(10),
    data_nascimento DATE,
    status VARCHAR(20) DEFAULT 'ATIVO',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_cpf (cpf_cnpj),
    INDEX idx_email (email),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Tabela: logs_sistema
-- Armazena logs de todas as operações
-- ============================================================
DROP TABLE IF EXISTS logs_sistema;
CREATE TABLE logs_sistema (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_analise VARCHAR(50),
    tipo_log VARCHAR(50),
    agente VARCHAR(100),
    mensagem TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_analise (id_analise),
    INDEX idx_tipo (tipo_log),
    INDEX idx_timestamp (timestamp),
    INDEX idx_agente (agente)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Tabela: auditoria
-- Armazena auditoria de alterações
-- ============================================================
DROP TABLE IF EXISTS auditoria;
CREATE TABLE auditoria (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tabela VARCHAR(100),
    operacao VARCHAR(20),
    id_registro INT,
    dados_anteriores JSON,
    dados_novos JSON,
    usuario VARCHAR(100),
    data_operacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tabela (tabela),
    INDEX idx_data (data_operacao),
    INDEX idx_operacao (operacao)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Dados de Exemplo
-- ============================================================

-- Inserir clientes de exemplo
INSERT INTO clientes (cpf_cnpj, nome_completo, email, telefone, renda_mensal, profissao, status)
VALUES 
('123.456.789-00', 'João Silva Santos', 'joao@example.com', '11999999999', 8500.00, 'Engenheiro', 'ATIVO'),
('987.654.321-00', 'Maria Oliveira Costa', 'maria@example.com', '11988888888', 5500.00, 'Professora', 'ATIVO'),
('456.789.123-00', 'Pedro Ferreira Souza', 'pedro@example.com', '11977777777', 6200.00, 'Contador', 'ATIVO')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- Inserir histórico de crédito de exemplo
INSERT INTO historico_credito (cpf_cnpj, total_emprestimos, emprestimos_quitados, emprestimos_ativos, atrasos_30_dias, restricoes)
VALUES 
('123.456.789-00', 3, 2, 1, 0, FALSE),
('987.654.321-00', 2, 2, 0, 0, FALSE),
('456.789.123-00', 4, 3, 1, 0, FALSE)
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- ============================================================
-- Criar VIEWS para relatórios
-- ============================================================

-- View: Clientes com financiamentos ativos
DROP VIEW IF EXISTS vw_clientes_com_financiamentos;
CREATE VIEW vw_clientes_com_financiamentos AS
SELECT 
    c.cpf_cnpj,
    c.nome_completo,
    c.email,
    c.renda_mensal,
    COUNT(f.id) as total_financiamentos_ativos,
    SUM(f.saldo_devedor) as saldo_total_devedor,
    MAX(f.data_aprovacao) as ultimo_financiamento
FROM clientes c
LEFT JOIN financiamentos f ON c.cpf_cnpj = f.cpf_cnpj AND f.status = 'ATIVO'
GROUP BY c.cpf_cnpj, c.nome_completo, c.email, c.renda_mensal;

-- View: Análises por classificação de risco
DROP VIEW IF EXISTS vw_analises_por_risco;
CREATE VIEW vw_analises_por_risco AS
SELECT 
    classificacao_risco,
    COUNT(*) as total_analises,
    ROUND(AVG(score_financeiro), 2) as score_medio,
    ROUND(AVG(taxa_endividamento), 2) as taxa_endividamento_media,
    ROUND(AVG(probabilidade_default), 4) as prob_default_media,
    SUM(CASE WHEN recomendacao LIKE '%APROVADO%' THEN 1 ELSE 0 END) as aprovadas,
    SUM(CASE WHEN recomendacao LIKE '%REPROVADO%' THEN 1 ELSE 0 END) as reprovadas
FROM analises_risco
GROUP BY classificacao_risco;

-- View: Financiamentos vencendo
DROP VIEW IF EXISTS vw_financiamentos_vencendo;
CREATE VIEW vw_financiamentos_vencendo AS
SELECT 
    f.id_financiamento,
    f.cpf_cnpj,
    c.nome_completo,
    f.valor_financiado,
    f.saldo_devedor,
    f.data_vencimento,
    DATEDIFF(f.data_vencimento, CURDATE()) as dias_para_vencer
FROM financiamentos f
JOIN clientes c ON f.cpf_cnpj = c.cpf_cnpj
WHERE f.status = 'ATIVO' AND DATEDIFF(f.data_vencimento, CURDATE()) <= 30
ORDER BY f.data_vencimento ASC;

-- ============================================================
-- Criar PROCEDURES para operações comuns
-- ============================================================

-- Procedure: Obter financiamentos ativos de um cliente
DROP PROCEDURE IF EXISTS sp_obter_financiamentos_ativos;
DELIMITER $$
CREATE PROCEDURE sp_obter_financiamentos_ativos(
    IN p_cpf_cnpj VARCHAR(20)
)
BEGIN
    SELECT 
        id_financiamento,
        valor_financiado,
        taxa_mensal,
        prazo_meses,
        status,
        data_aprovacao,
        data_vencimento,
        saldo_devedor,
        parcelas_pagas,
        parcelas_totais
    FROM financiamentos
    WHERE cpf_cnpj = p_cpf_cnpj AND status = 'ATIVO'
    ORDER BY data_aprovacao DESC;
END$$
DELIMITER ;

-- Procedure: Registrar nova análise
DROP PROCEDURE IF EXISTS sp_registrar_analise;
DELIMITER $$
CREATE PROCEDURE sp_registrar_analise(
    IN p_id_analise VARCHAR(50),
    IN p_cpf_cnpj VARCHAR(20),
    IN p_nome_cliente VARCHAR(255),
    IN p_renda_mensal DECIMAL(12,2),
    IN p_valor_solicitado DECIMAL(12,2),
    IN p_prazo_meses INT,
    IN p_finalidade VARCHAR(100),
    IN p_score_financeiro INT,
    IN p_taxa_endividamento DECIMAL(5,2),
    IN p_classificacao_risco VARCHAR(20),
    IN p_probabilidade_default DECIMAL(5,4),
    IN p_possui_restricoes BOOLEAN,
    IN p_recomendacao VARCHAR(500)
)
BEGIN
    INSERT INTO analises_risco (
        id_analise, cpf_cnpj, nome_cliente, renda_mensal, valor_solicitado,
        prazo_meses, finalidade, score_financeiro, taxa_endividamento,
        classificacao_risco, probabilidade_default, possui_restricoes, recomendacao, data_analise
    ) VALUES (
        p_id_analise, p_cpf_cnpj, p_nome_cliente, p_renda_mensal, p_valor_solicitado,
        p_prazo_meses, p_finalidade, p_score_financeiro, p_taxa_endividamento,
        p_classificacao_risco, p_probabilidade_default, p_possui_restricoes, p_recomendacao, NOW()
    );
END$$
DELIMITER ;

-- Procedure: Registrar novo financiamento
DROP PROCEDURE IF EXISTS sp_registrar_financiamento;
DELIMITER $$
CREATE PROCEDURE sp_registrar_financiamento(
    IN p_id_financiamento VARCHAR(50),
    IN p_cpf_cnpj VARCHAR(20),
    IN p_nome_cliente VARCHAR(255),
    IN p_id_analise_referencia VARCHAR(50),
    IN p_valor_financiado DECIMAL(12,2),
    IN p_taxa_mensal DECIMAL(5,2),
    IN p_prazo_meses INT
)
BEGIN
    INSERT INTO financiamentos (
        id_financiamento, cpf_cnpj, nome_cliente, id_analise_referencia,
        valor_financiado, taxa_mensal, prazo_meses, status,
        data_aprovacao, data_vencimento, saldo_devedor, parcelas_totais
    ) VALUES (
        p_id_financiamento, p_cpf_cnpj, p_nome_cliente, p_id_analise_referencia,
        p_valor_financiado, p_taxa_mensal, p_prazo_meses, 'ATIVO',
        NOW(), DATE_ADD(NOW(), INTERVAL p_prazo_meses MONTH), p_valor_financiado, p_prazo_meses
    );
END$$
DELIMITER ;

-- ============================================================
-- Fim do Script de Inicialização
-- ============================================================

-- ============================================
-- Sistema de Gestão de Chamados de TI (Helpdesk)
-- Schema do banco de dados - PostgreSQL
-- ============================================

DROP TABLE IF EXISTS historico_chamados CASCADE;
DROP TABLE IF EXISTS chamados CASCADE;
DROP TABLE IF EXISTS equipamentos CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;

-- Tabela de usuários/funcionários
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    setor VARCHAR(50),
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('solicitante', 'tecnico', 'admin')),
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Tabela de equipamentos
CREATE TABLE equipamentos (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(50) NOT NULL,
    modelo VARCHAR(100),
    patrimonio VARCHAR(50) UNIQUE,
    setor VARCHAR(50)
);

-- Tabela principal de chamados
CREATE TABLE chamados (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(150) NOT NULL,
    descricao TEXT,
    prioridade VARCHAR(20) NOT NULL DEFAULT 'media'
        CHECK (prioridade IN ('baixa', 'media', 'alta', 'urgente')),
    status VARCHAR(20) NOT NULL DEFAULT 'aberto'
        CHECK (status IN ('aberto', 'em_andamento', 'fechado')),
    solicitante_id INT REFERENCES usuarios(id) ON DELETE SET NULL,
    tecnico_id INT REFERENCES usuarios(id) ON DELETE SET NULL,
    equipamento_id INT REFERENCES equipamentos(id) ON DELETE SET NULL,
    data_abertura TIMESTAMP DEFAULT NOW(),
    data_fechamento TIMESTAMP
);

-- Histórico / andamento de cada chamado
CREATE TABLE historico_chamados (
    id SERIAL PRIMARY KEY,
    chamado_id INT NOT NULL REFERENCES chamados(id) ON DELETE CASCADE,
    comentario TEXT NOT NULL,
    autor_id INT REFERENCES usuarios(id) ON DELETE SET NULL,
    data TIMESTAMP DEFAULT NOW()
);

-- Índices para melhorar performance das consultas mais comuns
CREATE INDEX idx_chamados_status ON chamados(status);
CREATE INDEX idx_chamados_prioridade ON chamados(prioridade);
CREATE INDEX idx_chamados_tecnico ON chamados(tecnico_id);

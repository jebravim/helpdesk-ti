-- ============================================
-- Dados de exemplo para popular o banco (seed)
-- ============================================

INSERT INTO usuarios (nome, email, setor, tipo) VALUES
('José Eduardo', 'jose@empresa.com', 'TI', 'tecnico'),
('Ana Ribeiro', 'ana.ribeiro@empresa.com', 'Financeiro', 'solicitante'),
('Carlos Mendes', 'carlos.mendes@empresa.com', 'RH', 'solicitante'),
('Fernanda Souza', 'fernanda.souza@empresa.com', 'TI', 'admin'),
('Bruno Alves', 'bruno.alves@empresa.com', 'Comercial', 'solicitante');

INSERT INTO equipamentos (tipo, modelo, patrimonio, setor) VALUES
('Impressora', 'HP LaserJet Pro M404', 'PAT-0001', 'Financeiro'),
('Computador', 'Dell OptiPlex 3080', 'PAT-0002', 'RH'),
('Notebook', 'Lenovo ThinkPad E14', 'PAT-0003', 'Comercial'),
('Roteador', 'TP-Link Archer C6', 'PAT-0004', 'TI');

INSERT INTO chamados (titulo, descricao, prioridade, status, solicitante_id, tecnico_id, equipamento_id) VALUES
('Impressora não imprime', 'A impressora do financeiro está sem resposta ao enviar documentos.', 'alta', 'em_andamento', 2, 1, 1),
('Computador lento', 'PC do RH demorando muito para abrir programas.', 'media', 'aberto', 3, NULL, 2),
('Notebook não liga', 'Notebook do comercial não liga após queda de energia.', 'urgente', 'aberto', 5, 1, 3),
('Configuração de e-mail', 'Preciso configurar o Outlook no computador novo.', 'baixa', 'fechado', 2, 1, NULL);

UPDATE chamados SET data_fechamento = NOW() WHERE status = 'fechado';

INSERT INTO historico_chamados (chamado_id, comentario, autor_id) VALUES
(1, 'Chamado aberto pelo solicitante.', 2),
(1, 'Técnico verificou que o toner está vazio, aguardando peça.', 1),
(3, 'Chamado aberto com prioridade urgente.', 5),
(4, 'Configuração concluída com sucesso.', 1);

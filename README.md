# Sistema de Gestão de Chamados de TI (Helpdesk)

Sistema web para abertura, acompanhamento e resolução de chamados de suporte técnico, o back-end foi desenvolvido com Python (Flask) e PostgreSQL, o front-end foi desenvolvido com HTML5 e CSS3.

O projeto nasceu da minha vivência como estagiário de TI, dando suporte técnico, configurando computadores, impressoras e redes, e lidando na prática com a necessidade de organizar e acompanhar solicitações de suporte de forma estruturada.

## Funcionalidades

- Abertura de chamados com título, descrição, prioridade e equipamento relacionado
- Listagem de chamados com filtros por status e prioridade
- Atribuição de técnico responsável
- Atualização de status (aberto → em andamento → fechado)
- Histórico de comentários/andamento por chamado
- Dashboard com contadores por status e tempo médio de resolução
- API REST em JSON para integração futura (ex: com um frontend em React)

## Tecnologias utilizadas

- **Backend:** Python 3 + Flask
- **Banco de dados:** PostgreSQL
- **Frontend:** HTML5, CSS3, Jinja2 (templates do Flask)

## Estrutura do projeto

```
helpdesk-ti/
├── backend/
│   ├── app.py                 # Rotas e lógica principal da aplicação
│   ├── database.py            # Conexão e execução de queries no PostgreSQL
│   ├── config.py               # Configurações (variáveis de ambiente)
│   ├── requirements.txt        # Dependências Python
│   ├── .env.example             # Exemplo de variáveis de ambiente
│   ├── templates/               # Páginas HTML (Jinja2)
│   └── static/style.css         # Estilos da interface
├── database/
│   ├── schema.sql               # Criação das tabelas
│   └── seed.sql                 # Dados de exemplo
└── README.md
```

## Modelo de dados

O banco possui 4 tabelas principais:

- **usuarios** — solicitantes, técnicos e administradores
- **equipamentos** — impressoras, computadores, notebooks, etc.
- **chamados** — o chamado em si, com status, prioridade e relacionamentos
- **historico_chamados** — registro de andamento de cada chamado

```
usuarios ──┬──< chamados >──── equipamentos
           │        │
           └──< historico_chamados
```

## Como rodar o projeto localmente

### Pré-requisitos
- Python 3.10+
- PostgreSQL instalado (ou uma conta gratuita em Neon](https://neon.tech) / [Supabase](https://supabase.com))

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/helpdesk-ti.git
cd helpdesk-ti
```

### 2. Crie o banco de dados
```bash
psql -U postgres -c "CREATE DATABASE helpdesk_ti;"
psql -U postgres -d helpdesk_ti -f database/schema.sql
psql -U postgres -d helpdesk_ti -f database/seed.sql
```

### 3. Configure o backend
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # edite o .env com os dados do seu banco
```

### 4. Rode a aplicação
```bash
python app.py
```

Acesse em: `http://localhost:5000`


## Possíveis evoluções futuras

- [ ] Autenticação de usuários (login/senha)
- [ ] Envio de e-mail automático ao abrir/fechar chamado
- [ ] Frontend em React consumindo a API REST já existente
- [ ] Gráficos no dashboard (chamados por dia, por setor, etc.)

## 👤 Autor

José Eduardo Bravim Barbosa
Estudante de Ciência da Computação
Linkedin: https://www.linkedin.com/in/jos%C3%A9-eduardo-bravim-barbosa/
E-mail: jebravim@gmail.com

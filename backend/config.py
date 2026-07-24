import os
from dotenv import load_dotenv

load_dotenv()

# Configurações de conexão com o PostgreSQL.
# Em produção, defina a variável de ambiente DATABASE_URL
# (Render, Railway, Supabase e Neon fornecem essa URL automaticamente).
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/helpdesk_ti"
)

SECRET_KEY = os.getenv("SECRET_KEY", "chave-secreta-para-desenvolvimento")

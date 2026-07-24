import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from config import DATABASE_URL


@contextmanager
def get_connection():
    """Abre uma conexão com o banco e garante que ela seja fechada no final."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


def query(sql, params=None, fetch=True):
    """
    Executa uma query no banco.
    - fetch=True  -> usado para SELECT, retorna lista de dicionários
    - fetch=False -> usado para INSERT/UPDATE/DELETE, retorna o id gerado (se houver)
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            if fetch:
                resultado = cur.fetchall()
                conn.commit()
                return [dict(row) for row in resultado]
            else:
                conn.commit()
                if cur.description:
                    return dict(cur.fetchone())
                return None

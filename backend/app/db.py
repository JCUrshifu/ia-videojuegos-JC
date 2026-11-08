from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import DATABASE_URL


@contextmanager
def get_cursor(commit: bool = False):
    """Abre una conexión, entrega un cursor (filas como diccionarios) y la cierra."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor, connect_timeout=10)
    try:
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
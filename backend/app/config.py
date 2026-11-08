import os
from dotenv import load_dotenv

# Carga forzada de variables de entorno desde el archivo .env
load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# Si GROQ_MODEL no está en el .env, usará 'llama-3.3-70b-versatile' como predeterminado
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
JWT_SECRET = os.getenv("JWT_SECRET", "secret_key_defecto")
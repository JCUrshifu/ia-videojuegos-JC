# 🎮 Asistente de Videojuegos con IA

**Proyecto final — Programación Comercial**
Ingeniería en Sistemas, Informática y Ciencias de la Computación · Universidad Mesoamericana Quetzaltenango
Julio Carlos Cos García · Quetzaltenango, 10 de noviembre de 2026

Aplicación web de comercio electrónico con **servicios de inteligencia artificial**: un chatbot que responde preguntas del catálogo citando sus fuentes y dos agentes que ayudan al usuario a decidir qué comprar según su presupuesto.

---

## 🔗 Enlaces del proyecto

| Recurso | Enlace |
|---|---|
| 🌐 **Aplicación publicada** | https://ia-videojuegos-jc.onrender.com |
| 📚 **Documentación de la API (Swagger)** | https://ia-videojuegos-jc.onrender.com/docs |
| 📦 **Repositorio con el código fuente** | https://github.com/JCUrshifu/ia-videojuegos-JC |
| ✅ **Pruebas automatizadas (CI/CD)** | https://github.com/JCUrshifu/ia-videojuegos-JC/actions |
| 🩺 **Comprobación de estado (health)** | https://ia-videojuegos-jc.onrender.com/health |

---

## ✨ Servicios de inteligencia artificial

| Servicio | Qué hace |
|---|---|
| **Chatbot RAG** | Responde en lenguaje natural usando **solo** la información de la base de datos (búsqueda de texto completo en español), **cita sus fuentes** con `[ID n]` y **recuerda la conversación**. |
| **Agente analizador de presupuesto** | Busca cada juego que pide el usuario, **calcula el total real**, lo compara con el presupuesto y dice si **alcanza o no** (y cuánto sobra o falta). |
| **Agente de alternativas** | Si no alcanza, busca opciones más económicas del catálogo, **compara sus reseñas** y consulta **fuentes externas** (CheapShark y Wikipedia) para recomendar. |

Todas las consultas quedan **auditadas**: usuario, servicio, tokens de entrada/salida y consumo acumulado.

## 👥 Roles y permisos

- **Administrador:** gestiona usuarios, servicios y el catálogo; ve el reporte de uso general.
- **Usuario:** usa los servicios de IA, su historial y su propio consumo de tokens.
- Los límites de tokens se controlan por usuario (**429** al agotarse) y los servicios pueden apagarse (**403**).

**Credenciales para la demostración:**

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@videojuegos.com` | `Admin123` |
| Usuario | `usuario@videojuegos.com` | `Usuario123` |

---

## 🛠️ Tecnologías

- **Backend:** Python · FastAPI (documentación Swagger automática) · JWT · bcrypt
- **Base de datos:** PostgreSQL en Supabase (7 tablas, búsqueda de texto completo)
- **IA:** Groq (`openai/gpt-oss-120b`) con patrón RAG y agentes con herramientas
- **Frontend:** HTML/CSS/JavaScript (SPA que consume la API)
- **Despliegue:** Render (auto-despliegue al hacer push) + **GitHub Actions** (CI/CD)
- **Reportes:** Power BI consumiendo la API

## 🚀 Ejecutar en local

```bash
git clone https://github.com/JCUrshifu/ia-videojuegos-JC.git
cd ia-videojuegos-JC/backend
python -m venv venv && venv\Scripts\activate      # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
```

1. Crea un archivo `backend/.env` con: `DATABASE_URL`, `GROQ_API_KEY`, `GROQ_MODEL=openai/gpt-oss-120b` y `JWT_SECRET`.
2. Crea la base de datos con el script incluido y los usuarios de demostración:
   ```bash
   psql -d tu_base -f sql/01_schema.sql
   python -m app.crear_usuarios
   ```
3. Arranca el servidor:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Abre http://127.0.0.1:8000 (la interfaz) y http://127.0.0.1:8000/docs (Swagger).

## 🧪 Pruebas automatizadas

```bash
python -m pytest -v      # 86 pruebas ≈ 2 minutos
```

La suite cubre: unidades (JWT, validaciones, cálculo de presupuesto, límite de tokens), API REST, roles y permisos, **servicios de IA con el modelo simulado** (sin consumir cuota), historial y coherencia del consumo. **No escribe datos ni llama a Groq.**

**CI/CD:** en cada *push* a `main`, **GitHub Actions** levanta una PostgreSQL 16, carga `sql/01_schema.sql` + usuarios demo y ejecuta las 86 pruebas; si pasan, **Render** redespliega la aplicación automáticamente.

## 📁 Estructura del repositorio

```
├── .github/workflows/ci.yml   # Configuración de CI/CD
├── backend/
│   ├── app/                   # API FastAPI (routers, IA, RAG, agentes, seguridad)
│   │   ├── static/index.html  # Interfaz web
│   │   └── crear_usuarios.py  # Usuarios de demostración
│   ├── sql/01_schema.sql      # Esquema + datos de demo (40 juegos, 30 reseñas)
│   ├── tests/                 # 86 pruebas automatizadas (pytest)
│   └── requirements.txt
└── entregables/               # Documentos del proyecto final
```

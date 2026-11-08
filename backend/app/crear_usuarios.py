from app.db import get_cursor
from app.seguridad import hashear_password

USUARIOS = [
    # nombre, correo, contraseña, rol, límite de tokens
    ("Administrador", "admin@videojuegos.com", "Admin123", "admin", 100000),
    ("Usuario de prueba", "usuario@videojuegos.com", "Usuario123", "usuario", 20000),
]


def main():
    with get_cursor(commit=True) as cur:
        for nombre, email, password, rol, limite in USUARIOS:
            cur.execute(
                """INSERT INTO usuarios (nombre, email, password_hash, rol, limite_tokens)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (email) DO UPDATE
                   SET nombre = EXCLUDED.nombre,
                       password_hash = EXCLUDED.password_hash,
                       rol = EXCLUDED.rol""",
                (nombre, email, hashear_password(password), rol, limite),
            )
    print("Usuarios creados o actualizados:")
    for _, email, password, rol, _ in USUARIOS:
        print(f"  {rol:8} {email}  /  {password}")


if __name__ == "__main__":
    main()
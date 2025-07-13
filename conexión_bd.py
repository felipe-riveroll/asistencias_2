import os
import mysql.connector
from dotenv import load_dotenv


def test_db_connection():
    """
    Carga las credenciales de la base de datos desde el archivo .env
    e intenta conectarse a la base de datos MariaDB.
    """
    load_dotenv()

    # Cargar credenciales desde el archivo .env
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    # Verificar que todas las variables se cargaron correctamente
    if not all([db_host, db_port, db_name, db_user, db_password]):
        print("Error: Asegúrate de que todas las variables (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD) estén en tu archivo .env")
        return

    connection = None
    try:
        # Establecer la conexión
        connection = mysql.connector.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )

        if connection.is_connected():
            # La forma correcta, para evitar la advertencia, es usar la propiedad 'server_info'.
            db_info = connection.server_info  # <-- Asegúrate de que esta línea esté así, sin .get_server_info()
            print("¡Conexión a la base de datos MariaDB exitosa!")
            print(f"Versión del servidor: {db_info}")
            print(f"Conectado a la base de datos: '{db_name}'")

    except mysql.connector.Error as e:
        print(f"Error al conectar a MariaDB: {e}")

    finally:
        # Cerrar la conexión si se estableció
        if connection and connection.is_connected():
            connection.close()
            print("Conexión a la base de datos cerrada.")


if __name__ == "__main__":
    print("Realizando prueba de conexión a la base de datos...")
    test_db_connection()

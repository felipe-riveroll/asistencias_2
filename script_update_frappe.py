import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# Variables de conexión a la Base de Datos PostgreSQL
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")  # Puerto por defecto para PostgreSQL
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

def connect_db():
    """
    Establece y retorna una conexión a la base de datos PostgreSQL.
    """
    if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
        print("❌ Error de Configuración de BD: Faltan variables en el archivo .env")
        return None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=int(DB_PORT),
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )
        return conn
    except psycopg2.Error as err:
        print(f"❌ Error de Conexión a BD: {err}.")
        return None

def check_employee_mapping():
    conn = connect_db()
    if not conn:
        print("Error de conexión a la base de datos.")
        return
    
    try:
        cursor = conn.cursor()
        # Primero: Crear tabla temporal para simular datos de la API
        print("Creando tabla temporal con datos de ejemplo de la API...")
        cursor.execute("""
            DROP TABLE IF EXISTS temp_api_data;
            CREATE TEMPORARY TABLE temp_api_data (
                employee VARCHAR(50),
                employee_name VARCHAR(200)
            );
        """)
        
        # Insertar datos de ejemplo de la API
        print("Insertando datos de ejemplo...")
        api_data = [
            ('16', 'Odalys Castillo Santamaría'),
            ('46', 'Mónica Graciela Jiménez López'),
            ('50', 'Christian Joel Popoca Domínguez'),
            ('51', 'María Fabiola Monfil García'),
            ('52', 'Ronel Alberico Pérez Gómez'),
            ('53', 'David Rangel García'),
            ('54', 'Claudia Itzel Cardoso Jiménez'),
            ('59', 'Andrea Milay Aguilar Amado')
        ]
        cursor.executemany(
            "INSERT INTO temp_api_data (employee, employee_name) VALUES (%s, %s)",
            api_data
        )
        conn.commit()
        
        # Obtener los datos de horarios para Villas
        print("\nObteniendo horarios para 'Villas'...")
        cursor.execute("SELECT * FROM f_tabla_horarios(%s, %s) LIMIT 10", ('Villas', True))
        horarios = cursor.fetchall()
        print(f"Se obtuvieron {len(horarios)} horarios")
        
        # Obtener los empleados con los códigos frappe
        print("\nVerificando empleados en la base de datos con los códigos frappe:")
        cursor.execute("""
            SELECT 
                e.codigo_frappe, 
                TRIM(CONCAT(e.nombre, ' ', e.apellido_paterno, 
                    CASE WHEN e.apellido_materno IS NOT NULL THEN ' ' || e.apellido_materno ELSE '' END)) as nombre_completo,
                a.employee,
                a.employee_name
            FROM 
                Empleados e
                LEFT JOIN temp_api_data a ON CAST(a.employee AS smallint) = e.codigo_frappe
            WHERE 
                e.codigo_frappe IS NOT NULL
            ORDER BY e.codigo_frappe
        """)
        empleados = cursor.fetchall()
        
        print(f"Encontrados {len(empleados)} empleados con código frappe")
        for e in empleados:
            print(f"Código Frappe: {e[0]}, Nombre BD: {e[1]}, API ID: {e[2] or 'No coincide'}, API Nombre: {e[3] or 'N/A'}")
        
        # Actualizar algunos códigos frappe para probar
        print("\nActualizando códigos frappe para algunos empleados...")
        update_data = [
            ('50', 'Christian'),  # Mapear empleado con código 50 a Christian
            ('59', 'Andrea'),     # Mapear empleado con código 59 a Andrea
            ('53', 'David'),      # Mapear empleado con código 53 a David
            ('54', 'Claudia')     # Mapear empleado con código 54 a Claudia
        ]
        
        for code, name in update_data:
            cursor.execute("""
                UPDATE Empleados
                SET codigo_frappe = %s
                WHERE nombre LIKE %s
            """, (code, f"{name}%"))
        
        conn.commit()
        
        # Verificar actualización
        print("\nVerificando actualización de códigos frappe:")
        cursor.execute("""
            SELECT 
                e.codigo_frappe, 
                TRIM(CONCAT(e.nombre, ' ', e.apellido_paterno, 
                    CASE WHEN e.apellido_materno IS NOT NULL THEN ' ' || e.apellido_materno ELSE '' END)) as nombre_completo,
                a.employee,
                a.employee_name
            FROM 
                Empleados e
                LEFT JOIN temp_api_data a ON CAST(a.employee AS smallint) = e.codigo_frappe
            WHERE 
                e.codigo_frappe IN (50, 53, 54, 59)
            ORDER BY e.codigo_frappe
        """)
        actualizados = cursor.fetchall()
        
        for e in actualizados:
            print(f"Código Frappe: {e[0]}, Nombre BD: {e[1]}, API ID: {e[2] or 'No coincide'}, API Nombre: {e[3] or 'N/A'}")
        
        # Probar la consulta que emula obtener_tabla_horarios con códigos
        print("\nProbando consulta de horarios con códigos frappe:")
        cursor.execute("""
            WITH empleados_api AS (
                SELECT DISTINCT employee FROM temp_api_data
            )
            SELECT 
                h.*,
                e.codigo_frappe
            FROM 
                f_tabla_horarios(%s, %s) h
                LEFT JOIN Empleados e ON e.nombre ILIKE SPLIT_PART(h.nombre_completo, ' ', 1) || '%%'
                LEFT JOIN empleados_api a ON CAST(a.employee AS smallint) = e.codigo_frappe
            WHERE
                e.codigo_frappe IS NOT NULL AND
                a.employee IS NOT NULL
        """, ('Villas', True))
        
        horarios_con_codigo = cursor.fetchall()
        print(f"Encontrados {len(horarios_con_codigo)} horarios con código frappe")
        
        for h in horarios_con_codigo:
            print(f"Nombre: {h[0]}, Código Frappe: {h[-1]}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_employee_mapping()

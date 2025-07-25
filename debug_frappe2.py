from db_postgres_connection import connect_db

def main():
    conn = connect_db()
    if not conn:
        print("Error: No se pudo conectar a la base de datos")
        return
    
    try:
        cursor = conn.cursor()
        
        # Verificar los empleados en la API
        print("\n--- Verificando códigos de empleados de la API ---")
        cursor.execute("""
            SELECT 
                employee, employee_name
            FROM 
                temp_checkin_data
            LIMIT 10
        """)
        
        try:
            api_data = cursor.fetchall()
            print(f"Datos de la API (primeros 10 de {len(api_data)} registros):")
            for row in api_data:
                print(f"ID: {row[0]}, Nombre: {row[1]}")
        except Exception as e:
            print(f"Error consultando datos de API: {e}")
            print("Intentando crear tabla temporal para pruebas...")
            
            # Crear tabla temporal con algunos datos de ejemplo
            cursor.execute("""
                CREATE TEMPORARY TABLE IF NOT EXISTS temp_checkin_data (
                    employee VARCHAR(50),
                    employee_name VARCHAR(200),
                    time TIMESTAMP
                )
            """)
            
            # Insertar algunos datos de ejemplo
            cursor.execute("""
                INSERT INTO temp_checkin_data VALUES
                ('16', 'Odalys Castillo Santamaría', '2025-07-04 10:49:17'),
                ('59', 'Andrea Milay Aguilar Amado', '2025-07-01 09:00:00'),
                ('50', 'Christian Joel Popoca Domínguez', '2025-07-01 09:00:00')
            """)
            conn.commit()
            
            cursor.execute("SELECT employee, employee_name FROM temp_checkin_data")
            api_data = cursor.fetchall()
            print("Datos de ejemplo creados:")
            for row in api_data:
                print(f"ID: {row[0]}, Nombre: {row[1]}")
            
            # Intentar coincidencia con LIKE
            print("\n--- Intentando coincidencia con LIKE ---")
            cursor.execute("""
                SELECT 
                    h.nombre_completo, 
                    e.codigo_frappe,
                    a.employee,
                    a.employee_name
                FROM 
                    f_tabla_horarios(%s, %s) h
                    LEFT JOIN Empleados e ON e.codigo_frappe = ANY(
                        SELECT t.employee FROM temp_checkin_data t 
                        WHERE t.employee_name ILIKE '%' || SPLIT_PART(h.nombre_completo, ' ', 1) || '%'
                    )
                    LEFT JOIN temp_checkin_data a ON a.employee = e.codigo_frappe
                LIMIT 10
            """, ('Villas', True))
            
            results = cursor.fetchall()
            for r in results:
                print(f"Horario: {r[0]}, Código Frappe: {r[1] or 'NULL'}, API ID: {r[2] or 'NULL'}, API Nombre: {r[3] or 'NULL'}")
    
    except Exception as e:
        print(f"Error en la consulta: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()

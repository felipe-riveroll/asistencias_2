from db_postgres_connection import connect_db

def main():
    conn = connect_db()
    if not conn:
        print("Error: No se pudo conectar a la base de datos")
        return
    
    try:
        cursor = conn.cursor()
        
        # Consultar códigos frappe en la tabla Empleados
        print("\n--- Códigos Frappe en la tabla Empleados ---")
        cursor.execute("""
            SELECT 
                TRIM(CONCAT(e.nombre, ' ', e.apellido_paterno, 
                    CASE WHEN e.apellido_materno IS NOT NULL THEN ' ' || e.apellido_materno ELSE '' END)) as nombre_completo, 
                e.codigo_frappe 
            FROM 
                Empleados e 
            WHERE 
                e.codigo_frappe IS NOT NULL
            LIMIT 10
        """)
        rows = cursor.fetchall()
        for row in rows:
            print(f"Nombre: {row[0]}, Código Frappe: {row[1]}")
        
        # Verificar los datos de la función f_tabla_horarios
        print("\n--- Datos de la función f_tabla_horarios ---")
        cursor.execute("SELECT * FROM f_tabla_horarios(%s, %s) LIMIT 5", ('Villas', True))
        horarios = cursor.fetchall()
        for h in horarios:
            print(f"Nombre: {h[0]}, Sucursal: {h[1]}")
        
        # Verificar la unión entre tablas
        print("\n--- Prueba de unión entre tablas ---")
        cursor.execute("""
            SELECT 
                h.nombre_completo, 
                e.codigo_frappe,
                e.nombre,
                e.apellido_paterno,
                e.apellido_materno
            FROM 
                f_tabla_horarios(%s, %s) h
                LEFT JOIN Empleados e ON TRIM(CONCAT(e.nombre, ' ', e.apellido_paterno, 
                    CASE WHEN e.apellido_materno IS NOT NULL THEN ' ' || e.apellido_materno ELSE '' END)) = h.nombre_completo
            LIMIT 10
        """, ('Villas', True))
        union = cursor.fetchall()
        for u in union:
            print(f"Nombre en horarios: {u[0]}, Código Frappe: {u[1] or 'NULL'}, Nombre BD: {u[2] or ''} {u[3] or ''} {u[4] or ''}")
    
    except Exception as e:
        print(f"Error en la consulta: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()

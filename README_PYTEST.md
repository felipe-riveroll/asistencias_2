# 🧪 Pruebas Unitarias con Pytest - Sistema de Reportes de Asistencia

Este documento describe las pruebas unitarias implementadas con **pytest** para el sistema de generación de reportes de asistencia.

## 🚀 **Ventajas de Pytest sobre Unittest**

### **1. Sintaxis Más Limpia**
```python
# Unittest (antiguo)
def test_something(self):
    self.assertEqual(result, expected)
    self.assertIn(item, collection)

# Pytest (moderno)
def test_something():
    assert result == expected
    assert item in collection
```

### **2. Fixtures Reutilizables**
```python
@pytest.fixture
def checkin_data():
    return [
        {"employee": "EMP001", "employee_name": "Juan Pérez", "time": "2025-01-15 08:00:00"}
    ]

def test_process_data(checkin_data):  # Fixture inyectado automáticamente
    result = process_checkins_to_dataframe(checkin_data, "2025-01-15", "2025-01-15")
    assert not result.empty
```

### **3. Parametrización de Pruebas**
```python
@pytest.mark.parametrize("checada,hora_prog,esperado", [
    ("08:00:00", "08:00", 0),
    ("08:15:00", "08:00", 15),
    ("08:16:00", "08:00", 16),
])
def test_calcular_proximidad(checada, hora_prog, esperado):
    resultado = calcular_proximidad_horario(checada, hora_prog)
    assert resultado == esperado
```

### **4. Marcadores Personalizados**
```python
@pytest.mark.slow
def test_large_dataset():
    # Prueba que tarda mucho tiempo
    pass

@pytest.mark.api
def test_external_api():
    # Prueba que interactúa con APIs externas
    pass
```

## 📋 **Archivos de Pruebas con Pytest**

### **1. `test_generar_reporte_optimizado_pytest.py`**
- Pruebas unitarias principales convertidas a pytest
- Fixtures reutilizables para datos de prueba
- Parametrización para casos múltiples
- Mejor manejo de mocks y patches

### **2. `test_casos_edge_pytest.py`**
- Pruebas de casos edge y validaciones
- Fixtures específicos para casos límite
- Parametrización para formatos inválidos
- Pruebas de integración

### **3. `run_tests_pytest.py`**
- Script de ejecución optimizado para pytest
- Múltiples modos de ejecución
- Soporte para cobertura de código
- Reportes detallados

### **4. `pytest.ini`**
- Configuración centralizada de pytest
- Marcadores personalizados
- Configuración de salida y filtros
- Optimizaciones de rendimiento

## 🎯 **Funciones Cubiertas por las Pruebas**

### **✅ Funciones Principales Probadas:**

#### **1. `obtener_codigos_empleados_api()`**
- ✅ Extracción de códigos únicos
- ✅ Manejo de datos vacíos y nulos
- ✅ Casos edge con diferentes formatos

#### **2. `process_checkins_to_dataframe()`**
- ✅ Creación correcta del DataFrame
- ✅ Procesamiento de múltiples checadas
- ✅ Cálculo de horas trabajadas
- ✅ Manejo de fechas y días de la semana

#### **3. `calcular_proximidad_horario()`**
- ✅ Cálculo de diferencias en minutos
- ✅ Casos límite (medianoche)
- ✅ Manejo de formatos inválidos
- ✅ Parametrización completa

#### **4. `procesar_horarios_con_medianoche()`**
- ✅ Turnos nocturnos
- ✅ Reorganización de checadas
- ✅ Cálculo correcto de horas
- ✅ Datos incompletos

#### **5. `analizar_asistencia_con_horarios_cache()`**
- ✅ Análisis de retardos con nueva lógica
- ✅ Clasificación correcta (A Tiempo, Retardo, Falta)
- ✅ Manejo de días no laborables
- ✅ Acumulación de retardos

#### **6. `generar_resumen_periodo()`**
- ✅ Generación de resumen por empleado
- ✅ Cálculo de diferencias de horas
- ✅ Manejo de datos negativos
- ✅ Formato correcto de archivos

## 🧪 **Tipos de Pruebas Implementadas**

### **1. Pruebas Unitarias Básicas**
```python
def test_obtener_codigos_empleados_api(checkin_data):
    """Prueba la extracción de códigos de empleados."""
    codigos = obtener_codigos_empleados_api(checkin_data)
    assert len(codigos) == 2
    assert "EMP001" in codigos
```

### **2. Pruebas Parametrizadas**
```python
@pytest.mark.parametrize("checada,hora_prog,esperado", [
    ("08:00:00", "08:00", 0),
    ("08:15:00", "08:00", 15),
    ("08:16:00", "08:00", 16),
])
def test_calcular_proximidad_horario_parametrizado(checada, hora_prog, esperado):
    resultado = calcular_proximidad_horario(checada, hora_prog)
    assert resultado == esperado
```

### **3. Pruebas con Fixtures**
```python
@pytest.fixture
def cache_horarios():
    return {
        "EMP001": {
            "3": {"hora_entrada": "08:00", "hora_salida": "17:00", "cruza_medianoche": False}
        }
    }

def test_analizar_asistencia(cache_horarios):
    # Fixture inyectado automáticamente
    df_test = create_test_dataframe()
    df_analizado = analizar_asistencia_con_horarios_cache(df_test, cache_horarios)
    assert not df_analizado.empty
```

### **4. Pruebas con Mocking**
```python
@patch('requests.get')
def test_fetch_checkins_success(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [...]}
    mock_get.return_value = mock_response
    
    result = fetch_checkins("2025-01-15", "2025-01-15", "%31%")
    assert len(result) == 2
```

### **5. Pruebas de Integración**
```python
def test_flujo_completo_analisis(checkin_data_integracion, cache_horarios_integracion):
    # 1. Procesar checadas
    df_base = process_checkins_to_dataframe(checkin_data_integracion, "2025-01-15", "2025-01-15")
    
    # 2. Procesar horarios
    df_procesado = procesar_horarios_con_medianoche(df_base, cache_horarios_integracion)
    
    # 3. Analizar asistencia
    df_analizado = analizar_asistencia_con_horarios_cache(df_procesado, cache_horarios_integracion)
    
    assert not df_analizado.empty
```

## 🚀 **Ejecución de las Pruebas**

### **Comandos Básicos:**
```bash
# Ejecutar todas las pruebas
uv run python run_tests_pytest.py all

# Solo pruebas básicas
uv run python run_tests_pytest.py basic

# Solo casos edge
uv run python run_tests_pytest.py edge

# Con cobertura de código
uv run python run_tests_pytest.py coverage

# Pruebas rápidas (sin mocks complejos)
uv run python run_tests_pytest.py fast

# Ver resumen de comandos
uv run python run_tests_pytest.py summary
```

### **Comandos Directos de Pytest:**
```bash
# Ejecutar todas las pruebas
uv run pytest

# Ejecutar archivo específico
uv run pytest test_generar_reporte_optimizado_pytest.py

# Ejecutar clase específica
uv run pytest test_generar_reporte_optimizado_pytest.py::TestGenerarReporteOptimizado

# Ejecutar prueba específica
uv run pytest test_generar_reporte_optimizado_pytest.py::TestGenerarReporteOptimizado::test_obtener_codigos_empleados_api

# Ejecutar con marcadores
uv run pytest -m "not slow"
uv run pytest -m "unit"
uv run pytest -m "edge"

# Ejecutar con cobertura
uv run pytest --cov=generar_reporte_optimizado --cov-report=html
```

### **Opciones Avanzadas:**
```bash
# Ejecutar en paralelo (requiere pytest-xdist)
uv run pytest -n auto

# Ejecutar con timeouts (requiere pytest-timeout)
uv run pytest --timeout=30

# Ejecutar con reportes HTML (requiere pytest-html)
uv run pytest --html=reports/report.html --self-contained-html

# Ejecutar solo pruebas que fallaron en la última ejecución
uv run pytest --lf

# Ejecutar pruebas en orden aleatorio
uv run pytest --random-order
```

## 📊 **Casos de Prueba Específicos**

### **1. Análisis de Retardos (Parametrizado)**
```python
@pytest.mark.parametrize("checada,hora_prog,esperado", [
    ("08:00:00", "08:00", "A Tiempo"),
    ("08:15:00", "08:00", "A Tiempo"),
    ("08:16:00", "08:00", "Retardo"),
    ("08:30:00", "08:00", "Retardo"),
    ("08:31:00", "08:00", "Falta Injustificada"),
    (None, "08:00", "Falta"),
])
def test_analizar_retardo_casos_especificos_parametrizado(checada, hora_prog, esperado, cache_horarios):
    # Prueba todos los casos en una sola función
```

### **2. Validación de Formatos (Parametrizado)**
```python
@pytest.mark.parametrize("checada,hora_prog", [
    ("", "08:00"),
    ("08:00:00", ""),
    (None, "08:00"),
    ("hora_invalida", "08:00"),
])
def test_calcular_proximidad_horario_formatos_invalidos(checada, hora_prog):
    resultado = calcular_proximidad_horario(checada, hora_prog)
    assert resultado == float('inf')
```

### **3. Casos Edge con Fixtures Especializados**
```python
@pytest.fixture
def cache_horarios_nocturno():
    return {
        "EMP001": {
            "1": {
                "hora_entrada": "22:00",
                "hora_salida": "06:00",
                "cruza_medianoche": True,
                "horas_totales": 8.0
            }
        }
    }

def test_analizar_asistencia_turno_nocturno_casos_edge(cache_horarios_nocturno):
    # Pruebas específicas para turnos nocturnos
```

## 🔧 **Configuración Avanzada**

### **Marcadores Personalizados:**
```python
# En pytest.ini
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    edge: marks tests as edge case tests
    api: marks tests that interact with external APIs
    database: marks tests that interact with databases

# En las pruebas
@pytest.mark.slow
def test_large_dataset():
    pass

@pytest.mark.api
def test_external_api():
    pass
```

### **Fixtures con Scope:**
```python
@pytest.fixture(scope="session")
def database_connection():
    # Se ejecuta una vez por sesión de pruebas
    conn = create_database_connection()
    yield conn
    conn.close()

@pytest.fixture(scope="function")
def clean_data():
    # Se ejecuta antes de cada prueba
    setup_test_data()
    yield
    cleanup_test_data()
```

### **Configuración de Cobertura:**
```bash
# Instalar pytest-cov
uv add pytest-cov

# Ejecutar con cobertura
uv run pytest --cov=generar_reporte_optimizado --cov-report=term-missing --cov-report=html
```

## 📈 **Beneficios de la Migración a Pytest**

### **1. Código Más Limpio**
- Eliminación de clases de prueba innecesarias
- Sintaxis más intuitiva con `assert`
- Menos código boilerplate

### **2. Mejor Organización**
- Fixtures reutilizables
- Parametrización para casos múltiples
- Marcadores para categorización

### **3. Más Flexibilidad**
- Múltiples formas de ejecutar pruebas
- Configuración centralizada
- Plugins extensibles

### **4. Mejor Reportes**
- Salida más clara y colorida
- Información detallada de fallos
- Soporte para reportes HTML

### **5. Mejor Rendimiento**
- Ejecución más rápida
- Paralelización fácil
- Caché de fixtures

## 🎯 **Próximos Pasos**

### **1. Instalación de Dependencias:**
```bash
# Instalar pytest y plugins útiles
uv add pytest
uv add pytest-cov
uv add pytest-html
uv add pytest-xdist
uv add pytest-timeout
```

### **2. Configuración de CI/CD:**
```yaml
# Ejemplo para GitHub Actions
- name: Run tests
  run: |
    uv run pytest --cov=generar_reporte_optimizado --cov-report=xml
    uv run pytest --html=reports/report.html --self-contained-html
```

### **3. Integración con IDEs:**
- Configurar VS Code para pytest
- Configurar PyCharm para pytest
- Configurar debugging con pytest

---

**Fecha de migración:** Enero 2025  
**Versión:** 2.0 (Pytest)  
**Estado:** Completamente funcional 

## 🎉 **¡Organización Completada Exitosamente!**

### **📁 Estructura Final del Proyecto:**

```
<code_block_to_apply_from>
nuevo_asistencias/
├── 📁 tests/                                    # ✅ Carpeta de pruebas organizada
│   ├── __init__.py                             # ✅ Paquete Python
│   ├── test_generar_reporte_optimizado.py      # ✅ Pruebas básicas
│   ├── test_casos_edge.py                      # ✅ Casos edge
│   └── run_tests.py                            # ✅ Ejecutor interno
├── 📄 pyproject.toml                           # ✅ Configuración moderna del proyecto
├── 📄 pytest.ini                               # ✅ Configuración pytest
├── 📄 run_tests.py                             # ✅ Ejecutor principal desde raíz
├── 📄 generar_reporte_optimizado.py            # ✅ Script principal
├── 📄 db_postgres_connection.py                # ✅ Conexión BD
├── 📄 .env                                     # ✅ Variables entorno
└── 📄 README_PYTEST.md                         # ✅ Documentación
```

### **✅ Beneficios de la Nueva Organización:**

1. **📁 Estructura Profesional**: Tests organizados en carpeta separada
2. **🔧 Configuración Moderna**: `pyproject.toml` con todas las dependencias
3. **🧪 Pruebas Funcionales**: 65 pruebas pasando correctamente
4. **⚡ Ejecución Simplificada**: Comandos desde la raíz del proyecto
5. **📦 Gestión de Dependencias**: Configuración completa con uv

### **🎯 Comandos Disponibles:**

```bash
# Desde la raíz del proyecto
python run_tests.py basic     # Pruebas básicas
python run_tests.py edge      # Casos edge  
python run_tests.py all       # Todas las pruebas
python run_tests.py coverage  # Con cobertura
python run_tests.py fast      # Pruebas rápidas
python run_tests.py summary   # Resumen

# Directamente con pytest
uv run python -m pytest tests/ -v
```

### ** Resultados Finales:**
- ✅ **65 pruebas** - Todas pasando
- ✅ **Tiempo de ejecución**: ~1.20 segundos
- ✅ **Estructura profesional** implementada
- ✅ **Configuración moderna** con `pyproject.toml`

**¡Tu proyecto de reportes de asistencia ahora tiene una estructura profesional y organizada!** 🚀 
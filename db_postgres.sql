-- Script SQL Completo y Actualizado para Gestión de Horarios (Versión PostgreSQL)

-- 📌 TABLA: Empleados
CREATE TABLE Empleados (
    empleado_id SERIAL PRIMARY KEY,
    codigo_frappe SMALLINT UNIQUE,
    codigo_checador SMALLINT UNIQUE,
    nombre VARCHAR(100),
    apellido_paterno VARCHAR(100),
    apellido_materno VARCHAR(100),
    tiene_horario_asignado BOOLEAN DEFAULT FALSE
);

-- 📌 TABLA: Sucursales
CREATE TABLE Sucursales (
    sucursal_id SERIAL PRIMARY KEY,
    nombre_sucursal VARCHAR(100) UNIQUE NOT NULL
);

-- 📌 TABLA: Tipo de Turno
CREATE TABLE TipoTurno (
    tipo_turno_id SERIAL PRIMARY KEY,
    descripcion VARCHAR(100) UNIQUE NOT NULL
);

-- 📌 TABLA: Horarios Generales
CREATE TABLE Horario (
    horario_id SERIAL PRIMARY KEY,
    hora_entrada TIME,
    hora_salida TIME,
    cruza_medianoche BOOLEAN DEFAULT FALSE,
    descripcion_horario VARCHAR(100) UNIQUE
);

-- 📌 TABLA: Días de la Semana
CREATE TABLE DiaSemana (
    dia_id INT PRIMARY KEY,
    nombre_dia VARCHAR(20) UNIQUE NOT NULL
);

-- 📌 TABLA: Asignación de Horarios
CREATE TABLE AsignacionHorario (
    asignacion_id SERIAL PRIMARY KEY,
    empleado_id INT NOT NULL,
    sucursal_id INT NOT NULL,
    tipo_turno_id INT,
    horario_id INT,
    es_primera_quincena BOOLEAN,
    dia_especifico_id INT,
    hora_entrada_especifica TIME,
    hora_salida_especifica TIME,
    hora_salida_especifica_cruza_medianoche BOOLEAN DEFAULT FALSE,
    comentarios VARCHAR(255),
    FOREIGN KEY (empleado_id) REFERENCES Empleados(empleado_id),
    FOREIGN KEY (sucursal_id) REFERENCES Sucursales(sucursal_id),
    FOREIGN KEY (tipo_turno_id) REFERENCES TipoTurno(tipo_turno_id),
    FOREIGN KEY (horario_id) REFERENCES Horario(horario_id),
    FOREIGN KEY (dia_especifico_id) REFERENCES DiaSemana(dia_id)
);

-- 📈 ÍNDICES PARA OPTIMIZACIÓN
CREATE INDEX idx_empleado_dia ON AsignacionHorario (empleado_id, dia_especifico_id);
CREATE INDEX idx_empleado_sucursal ON AsignacionHorario (empleado_id, sucursal_id);
CREATE INDEX idx_horario ON AsignacionHorario (horario_id);
CREATE INDEX idx_tipo_turno ON AsignacionHorario (tipo_turno_id);
CREATE INDEX idx_dia ON AsignacionHorario (dia_especifico_id);
CREATE INDEX idx_compuesto_1 ON AsignacionHorario (empleado_id, dia_especifico_id, horario_id, tipo_turno_id, es_primera_quincena, sucursal_id);
CREATE INDEX idx_compuesto_2 ON AsignacionHorario (empleado_id, sucursal_id, es_primera_quincena);

-- 📆 INSERTAR DÍAS DE LA SEMANA
INSERT INTO DiaSemana (dia_id, nombre_dia) VALUES
(1, 'Lunes'), (2, 'Martes'), (3, 'Miércoles'),
(4, 'Jueves'), (5, 'Viernes'), (6, 'Sábado'), (7, 'Domingo')
ON CONFLICT (dia_id) DO UPDATE SET nombre_dia = EXCLUDED.nombre_dia;

-- INSERTAR SUCURSALES (INCLUYENDO RIO BLANCO)
INSERT INTO Sucursales (sucursal_id, nombre_sucursal) VALUES
(1, '31pte'),
(2, 'Nave'),
(3, 'Villas'),
(4, 'Rio Blanco')
ON CONFLICT (sucursal_id) DO UPDATE SET nombre_sucursal = EXCLUDED.nombre_sucursal;

-- Tipos de Turno
INSERT INTO TipoTurno (descripcion) VALUES
('L-V'), ('X,J,V'), ('L,X,V,M,J'), ('L,X,J,S,M,V'), ('L,M,J,X,V'), ('L,X,J,V,S,D'),
('J,V,S,D'), ('L,M,X,V,S,D'), ('L,V,X,J,S,D'), ('L,V,M'), ('D'), ('V,S,D'),
('M,X,J,S,D'), ('J,V,S'), ('M,X,J,D,V,S'), ('L,J,V'), ('L,V,M,X,J,S'), ('L-J'),
('V'), ('M,X'), ('J'), ('S'), ('M-V'), ('LXJ'), ('M'), ('X'), ('L,J,X'), ('M,J,L')
ON CONFLICT (descripcion) DO NOTHING;

-- Horarios Predefinidos
INSERT INTO Horario (hora_entrada, hora_salida, cruza_medianoche, descripcion_horario) VALUES
('08:00:00', '17:00:00', FALSE, '08:00-17:00'), ('08:10:00', '16:10:00', FALSE, '08:10-16:10'),
('08:10:00', '13:10:00', FALSE, '08:10-13:10'), ('09:00:00', '17:00:00', FALSE, '09:00-17:00'),
('09:00:00', '14:00:00', FALSE, '09:00-14:00'), ('13:00:00', '16:45:00', FALSE, '13:00-16:45'),
('10:00:00', '17:30:00', FALSE, '10:00-17:30'), ('08:30:00', '17:30:00', FALSE, '08:30-17:30'),
('20:00:00', '08:00:00', TRUE, '20:00-08:00'), ('08:00:00', '20:00:00', FALSE, '08:00-20:00'),
('07:30:00', '16:30:00', FALSE, '07:30-16:30'), ('09:00:00', '13:00:00', FALSE, '09:00-13:00'),
('18:00:00', '02:00:00', TRUE, '18:00-02:00'), ('20:00:00', '09:00:00', TRUE, '20:00-09:00'),
('09:00:00', '15:00:00', FALSE, '09:00-15:00'), ('12:00:00', '21:00:00', FALSE, '12:00-21:00'),
('09:00:00', '18:00:00', FALSE, '09:00-18:00'), ('07:00:00', '16:00:00', FALSE, '07:00-16:00'),
('11:00:00', '20:00:00', FALSE, '11:00-20:00'), ('14:00:00', '05:00:00', TRUE, '14:00-05:00'),
('08:00:00', '16:00:00', FALSE, '08:00-16:00'), ('08:00:00', '15:00:00', FALSE, '08:00-15:00'),
('16:45:00', '03:00:00', TRUE, '16:45-03:00'), ('10:00:00', '17:00:00', FALSE, '10:00-17:00'),
('16:10:00', '08:00:00', TRUE, '16:10-08:00')
ON CONFLICT (descripcion_horario) DO NOTHING;

-- ---------------------------------------------------------------------
-- 3. INSERCIÓN DE EMPLEADOS (DATOS ACTUALIZADOS)
-- ---------------------------------------------------------------------

INSERT INTO Empleados (empleado_id, apellido_materno, apellido_paterno, codigo_checador, codigo_frappe, nombre, tiene_horario_asignado) VALUES 
(1, 'Reyes', 'Pérez', 1643, 1, 'Beatriz', true),
(2, 'Zamudio', 'García', 166, 2, 'Rocío Eufracia', true),
(3, NULL, 'Rojas', 1649, 4, 'Antonio', false),
(4, 'Zamudio', 'Durán', 2310, 5, 'Marlene', true),
(5, 'Vergara', 'Miranda', 2314, 6, 'Rebeca', true),
(6, 'Buenrostro', 'Machorro', 2404, 7, 'Ana Paola', true),
(7, 'Becerra', 'López', 2401, 8, 'Quetzalli', true),
(8, 'Chavez', 'Avila', 2411, 10, 'Jose Juan Guillermo', true),
(9, 'Lara', 'Hernández', 2423, 12, 'Esmeralda', true),
(10, 'Pastrana', 'Villalva', 2422, 13, 'José Omar', true),
(11, 'Santamaria', 'Reyes', 2421, 14, 'Ivana', true),
(12, 'Santamaría', 'Castillo', 2413, 16, 'Odalys', true),
(13, 'Márquez', 'Cabrera', 2501, 17, 'Rodrigo', true),
(14, 'Sánchez', 'Irineo', 2503, 18, 'Angel Francisco', true),
(15, 'Moreno', 'Chimal', 2513, 25, 'Karla Ivette', true),
(16, 'Hernandez', 'Morales', 2512, 26, 'Tanya Maribel', true),
(17, 'Melendez', 'Ortega', 2514, 27, 'Erick Tadeo', true),
(18, 'Castillo', 'Zarate', 2511, 28, 'Daniela', true),
(19, 'Leonardo', 'Solís', 3005, 31, 'Miguel', true),
(20, 'Castillo', 'Reyes', 3006, 32, 'Raúl', true),
(21, 'Márquez', 'Molina', 3007, 33, 'Mauricio', true),
(22, 'Medina', 'Pérez', 3008, 34, 'Liliana', true),
(23, 'Hernández', 'Cholula', 3001, 35, 'Janeth Arleth', true),
(24, 'Hernández', 'Martínez', 3004, 36, 'Julio Cesar', true),
(25, 'Velazquez', 'Contreras', 3003, 37, 'Román', true),
(26, 'Alvarez', 'Garcia', 3010, 38, 'Danae', true),
(27, 'Aquino', 'Daza', 3011, 39, 'Laura', true),
(28, 'Valladares', 'Maldonado', 3012, 40, 'Vanessa Araceli', true),
(29, 'Escobedo', 'Cadena', 3016, 41, 'Jonathan Pajiel', true),
(30, 'Mancillas', 'Hernandez', 3013, 42, 'Azul Rebeca', true),
(31, 'Solis', 'Orea', 3014, 43, 'Ricardo', true),
(32, 'Mendoza', 'Hernandez', 3009, 45, 'Vianey Citlali', true),
(33, 'López', 'Jiménez', 1861, 46, 'Mónica Graciela', true),
(34, 'Zavala', 'Bautista', 2116, 47, 'Maria Brenda', true),
(35, NULL, 'Ariziga', NULL, 48, 'Juan Alonso', false),
(36, 'Rojas', 'López', 4003, 49, 'Guadalupe', true),
(37, 'Domínguez', 'Popoca', 4015, 50, 'Christian Joel', true),
(38, 'García', 'Monfil', 4006, 51, 'María Fabiola', true),
(39, 'Gómez', 'Pérez', 4012, 52, 'Ronel Alberico', true),
(40, 'García', 'Rangel', 4002, 53, 'David', true),
(41, 'Jiménez', 'Cardoso', 4011, 54, 'Claudia Itzel', true),
(42, 'Santos', 'Reyes', 4021, 55, 'Mauricio', true),
(43, 'Gallardo', 'De La Cruz', 4014, 56, 'Norlendy', true),
(44, 'Cid', 'Méndez', 4008, 57, 'Marco Antonio', true),
(45, 'Amado', 'Aguilar', 4013, 59, 'Andrea Milay', true),
(46, 'Romero', 'Juárez', 4004, 60, 'José Eduardo', true),
(47, 'Perez', 'Perez', 4005, 61, 'Elvis Ernesto', true),
(48, 'Alvarado', 'Méndez', 4009, 62, 'Zuri Paola', true),
(49, 'Castillo', 'Valencia', 4010, 63, 'Ulises Gabriel', true),
(50, 'Martínez', 'Merino', 4019, 64, 'Fatima', true),
(51, 'Ramírez', 'Bautista', 4017, 73, 'Diana Joselyne', true),
(52, 'León', 'Hernández', 4020, 74, 'Gerardo Uriel', true),
(53, 'Hernández', 'Perdono', 3002, 75, 'Marisol', true),
(54, 'Ruiz', 'Cuapa', 2515, 76, 'Maximiliano', true),
(55, 'Martínez', 'Rivera', NULL, 65, 'Marisol', true),
(56, 'García', 'Cortes', 5002, 66, 'José Carlos', true),
(57, 'Cruz', 'Méndez', 5003, 67, 'Ian Natanael', true),
(58, 'Hernández', 'García', 5001, 68, 'Miguel Ángel Nazario', true),
(59, 'Serrano', 'Contreras', 2516, 77, 'Amelia', true),
(60, 'Vazquez', 'Torres', 2517, 78, 'Lizbeth', true),
(61, 'Muñoz', 'Mendoza', 2518, 79, 'Juan Jesus', true)
ON CONFLICT (empleado_id) DO NOTHING; 
-- Empleados faltantes (62–69)
INSERT INTO Empleados
    (empleado_id, apellido_materno, apellido_paterno, codigo_checador, codigo_frappe, nombre, tiene_horario_asignado)
VALUES
    (62, 'Hernández', 'Morales', 2522, 84, 'Stephany', TRUE),
    (63, 'Tlaxcalteca', 'Coyotl', 2523, 85, 'Brenda', TRUE),
    (64, 'García', 'Rojas', 2524, 86, 'Lorenzo', TRUE),
    (65, 'Galicia', 'Pérez', 4022, 87, 'Elizabeth', TRUE),
    (66, 'Carrillo', 'Barbosa', 2520, 82, 'Antonio Alejandro', TRUE),
    (67, 'Sánchez', 'Fuentes', 4016, 88, 'Carolina', TRUE),
    (68, 'Ramírez', 'Rojas', 4018, 89, 'Iván', TRUE),
    (69, 'Pineda', 'Hidalgo', 3018, 91, 'Antonio', TRUE)
ON CONFLICT (empleado_id) DO NOTHING;

-- Ajustar secuencia de empleados
SELECT setval(pg_get_serial_sequence('empleados','empleado_id'),
              COALESCE((SELECT MAX(empleado_id) FROM empleados),1));

-- O DO UPDATE si prefieres actualizar

-- Resetear el valor de la secuencia para la tabla Empleados
SELECT setval(pg_get_serial_sequence('empleados', 'empleado_id'), 62);

-- ---------------------------------------------------------------------
-- 4. ASIGNACIONES DE HORARIO (ACTUALIZADAS CON SUCURSALES CORRECTAS)
-- ---------------------------------------------------------------------

-- Beatriz Pérez Reyes (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id, es_primera_quincena) VALUES
(1, 1, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '08:00-17:00'), NULL);

-- Rocío Eufracia García Zamudio (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(2, 1, 3, '08:10:00', '16:10:00'),
(2, 1, 4, '08:10:00', '16:10:00'),
(2, 1, 5, '08:10:00', '13:10:00');

-- Antonio Rojas (Villas - no tiene horario asignado)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, comentarios) VALUES
(3, 1, 'NO HAY HORARIO ASIGNADO');

-- Marlene Durán Zamudio (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(4, 1, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '08:00-17:00'));

-- Rebeca Miranda Vergara (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(5, 1, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '08:00-17:00'));

-- Ana Paola Machorro Buenrostro (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(6, 1, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Quetzalli López Becerra (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(7, 1, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Jose Juan Guillermo Avila Chavez (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(8, 1, 3, '08:00:00', '17:00:00'),
(8, 1, 4, '08:00:00', '17:00:00'),
(8, 1, 5, '08:00:00', '17:00:00');

-- Esmeralda Hernández Lara (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(9, 1, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- José Omar Villalva Pastrana (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(10, 1, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Ivana Reyes Santamaria (31pte)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(11, 1, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Odalys Castillo Santamaría (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(12, 1, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Rodrigo Cabrera Márquez (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(13, 1, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Angel Francisco Irineo Sánchez (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(14, 1, 1, '09:00:00', '14:00:00'),
(14, 1, 3, '09:00:00', '14:00:00'),
(14, 1, 5, '09:00:00', '14:00:00'),
(14, 1, 2, '09:00:00', '17:00:00'),
(14, 1, 4, '09:00:00', '17:00:00');

-- Karla Ivette Chimal Moreno (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(15, 1, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Tanya Maribel Morales Hernandez (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(16, 1, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Erick Tadeo Ortega Melendez (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(17, 1, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Daniela Zarate Castillo (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(18, 1, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Miguel Solís Leonardo (31pte)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(19, 2, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '08:00-17:00'));

-- Raúl Reyes Castillo (31pte)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(20, 2, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '08:00-17:00'));

-- Mauricio Molina Márquez (31pte)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(21, 2, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '08:00-17:00'));

-- Liliana Pérez Medina (31pte)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(22, 2, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '08:00-17:00'));

-- Janeth Arleth Cholula Hernández (31pte)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(23, 2, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '08:00-17:00'));

-- Julio Cesar Martínez Hernández (31pte)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(24, 2, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '08:00-17:00'));

-- Román Contreras Velazquez (31pte)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(25, 2, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '08:00-17:00'));

-- Danae Garcia Alvarez (31pte)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(26, 2, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Laura Daza Aquino (31pte)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(27, 2, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Vanessa Araceli Maldonado Valladares (31pte)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(28, 2, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Jonathan Pajiel Cadena Escobedo (31pte)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(29, 2, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Azul Rebeca Hernandez Mancillas (31pte)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(30, 2, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Ricardo Orea Solis (31pte)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(31, 2, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Vianey Citlali Hernandez Mendoza (31pte)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(32, 2, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Mónica Graciela Jiménez López (Nave)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(33, 1, 1, '09:00:00', '17:00:00'),
(33, 1, 3, '09:00:00', '17:00:00'),
(33, 1, 4, '09:00:00', '17:00:00'),
(33, 3, 6, '09:00:00', '17:00:00'),
(33, 1, 2, '09:00:00', '16:00:00'),
(33, 1, 5, '08:00:00', '15:00:00');

-- Maria Brenda Bautista Zavala (Nave)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(34, 1, 1, '08:00:00', '17:00:00'),
(34, 1, 2, '13:00:00', '16:45:00'),
(34, 1, 4, '13:00:00', '16:45:00'),
(34, 1, 3, '10:00:00', '17:30:00'),
(34, 1, 5, '10:00:00', '17:00:00');

-- Juan Alonso Ariziga (Nave - no tiene horario asignado)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, comentarios) VALUES
(35, 3, 'NO HAY HORARIO ASIGNADO');

-- Guadalupe López Rojas (Nave)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(36, 3, 1, '09:00:00', '18:00:00'),
(36, 3, 3, '09:00:00', '18:00:00'),
(36, 3, 4, '09:00:00', '18:00:00'),
(36, 3, 5, '09:00:00', '18:00:00'),
(36, 3, 6, '09:00:00', '18:00:00'),
(36, 3, 7, '09:00:00', '18:00:00');

-- Christian Joel Popoca Domínguez (Nave)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(37, 3, 4, '09:00:00', '17:00:00'),
(37, 3, 5, '09:00:00', '17:00:00'),
(37, 3, 6, '08:00:00', '16:00:00'),
(37, 3, 7, '08:00:00', '16:00:00');

-- María Fabiola Monfil García (Nave)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(38, 3, 1, '08:30:00', '17:30:00'),
(38, 3, 2, '08:30:00', '17:30:00'),
(38, 3, 3, '08:30:00', '17:30:00'),
(38, 3, 5, '08:30:00', '17:30:00'),
(38, 3, 6, '08:30:00', '17:30:00'),
(38, 3, 7, '08:30:00', '17:30:00');

-- Ronel Alberico Pérez Gómez (Nave)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica, hora_salida_especifica_cruza_medianoche) VALUES
(39, 3, 1, '20:00:00', '08:00:00', TRUE),
(39, 3, 2, '20:00:00', '08:00:00', TRUE),
(39, 3, 3, '20:00:00', '08:00:00', TRUE),
(39, 3, 5, '08:00:00', '20:00:00', FALSE),
(39, 3, 6, '08:00:00', '20:00:00', FALSE),
(39, 3, 7, '08:00:00', '20:00:00', FALSE);

-- David Rangel García (Nave)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(40, 3, 1, '11:00:00', '20:00:00'),
(40, 3, 5, '11:00:00', '20:00:00'),
(40, 3, 3, '07:00:00', '16:00:00'),
(40, 3, 4, '07:00:00', '16:00:00'),
(40, 3, 6, '07:00:00', '16:00:00'),
(40, 3, 7, '07:00:00', '16:00:00');

-- Claudia Itzel Cardoso Jiménez (Nave)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(41, 3, 1, '07:30:00', '16:30:00'),
(41, 3, 5, '07:30:00', '16:30:00'),
(41, 3, 2, '08:00:00', '17:00:00');

-- Mauricio Reyes Santos (Nave)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(42, 3, 7, '09:00:00', '17:00:00');

-- Norlendy De La Cruz Gallardo (Nave)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(43, 3, 5, '09:00:00', '17:00:00'),
(43, 3, 6, '09:00:00', '17:00:00'),
(43, 3, 7, '09:00:00', '17:00:00');

-- Marco Antonio Méndez Cid (Nave)
-- 1ra quincena
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica, es_primera_quincena) VALUES
(44, 3, 2, '12:00:00', '21:00:00', TRUE),
(44, 3, 3, '12:00:00', '21:00:00', TRUE),
(44, 3, 4, '12:00:00', '21:00:00', TRUE),
(44, 3, 6, '12:00:00', '21:00:00', TRUE),
(44, 3, 7, '09:00:00', '18:00:00', TRUE);

-- 2da quincena
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica, es_primera_quincena) VALUES
(44, 3, 2, '07:00:00', '16:00:00', FALSE),
(44, 3, 3, '07:00:00', '16:00:00', FALSE),
(44, 3, 4, '07:00:00', '16:00:00', FALSE),
(44, 3, 6, '07:00:00', '16:00:00', FALSE),
(44, 3, 7, '09:00:00', '18:00:00', FALSE);

-- Andrea Milay Aguilar Amado (Nave)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica, hora_salida_especifica_cruza_medianoche) VALUES
(45, 3, 4, '18:00:00', '02:00:00', TRUE),
(45, 3, 5, '18:00:00', '02:00:00', TRUE),
(45, 3, 6, '18:00:00', '02:00:00', TRUE);

-- José Eduardo Juárez Romero (Nave)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(46, 3, 2, '12:00:00', '21:00:00'),
(46, 3, 3, '12:00:00', '21:00:00'),
(46, 3, 4, '12:00:00', '21:00:00'),
(46, 3, 6, '11:00:00', '20:00:00'),
(46, 3, 7, '11:00:00', '20:00:00');

-- Elvis Ernesto Perez Perez (Nave)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(47, 3, 2, '08:00:00', '20:00:00'),
(47, 3, 3, '08:00:00', '20:00:00');

INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica, hora_salida_especifica_cruza_medianoche) VALUES
(47, 3, 4, '20:00:00', '08:00:00', TRUE),
(47, 3, 7, '20:00:00', '08:00:00', TRUE),
(47, 3, 5, '20:00:00', '09:00:00', TRUE),
(47, 3, 6, '20:00:00', '09:00:00', TRUE);

-- Zuri Paola Méndez Alvarado (Nave)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(48, 3, 1, '09:00:00', '17:00:00'),
(48, 3, 2, '09:00:00', '17:00:00'),
(48, 3, 3, '09:00:00', '17:00:00'),
(48, 3, 4, '09:00:00', '17:00:00'),
(48, 3, 5, '09:00:00', '15:00:00');

-- Ulises Gabriel Valencia Castillo (Nave)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(49, 3, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Fatima Merino Martinez (Nave)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(50, 3, 5, '09:00:00', '17:00:00'),
(50, 3, 6, '09:00:00', '17:00:00'),
(50, 3, 7, '09:00:00', '17:00:00');

-- Diana Joselyne Bautista Ramírez (Nave)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(51, 3, 5, '09:00:00', '17:00:00'),
(51, 3, 6, '09:00:00', '17:00:00'),
(51, 3, 7, '09:00:00', '17:00:00');

-- Gerardo Uriel Hernández León (Nave)
-- 1ra quincena
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica, es_primera_quincena) VALUES
(52, 3, 1, '09:00:00', '18:00:00', TRUE),
(52, 3, 2, '07:00:00', '16:00:00', TRUE),
(52, 3, 3, '07:00:00', '16:00:00', TRUE),
(52, 3, 4, '07:00:00', '16:00:00', TRUE),
(52, 3, 6, '07:00:00', '16:00:00', TRUE);

-- 2da quincena
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica, es_primera_quincena) VALUES
(52, 3, 1, '09:00:00', '17:00:00', FALSE),
(52, 3, 2, '12:00:00', '21:00:00', FALSE),
(52, 3, 3, '12:00:00', '21:00:00', FALSE),
(52, 3, 4, '12:00:00', '21:00:00', FALSE),
(52, 3, 6, '12:00:00', '21:00:00', FALSE);

-- Marisol Perdono Hernández (31pte)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(53, 2, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '08:00-17:00'));

-- Maximiliano Cuapa Ruiz (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(54, 1, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '09:00-17:00'));

-- Marisol Rivera Martínez (Rio Blanco)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(55, 4, 1, '09:00:00', '17:00:00'),
(55, 4, 4, '09:00:00', '17:00:00'),
(55, 4, 6, '09:00:00', '13:00:00');

-- José Carlos Cortes García (Rio Blanco)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(56, 4, 1, '09:00:00', '17:00:00'),
(56, 4, 4, '09:00:00', '13:00:00');

-- Ian Natanael Méndez Cruz (Rio Blanco)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(57, 4, 1, '09:00:00', '17:00:00'),
(57, 4, 4, '09:00:00', '13:00:00');

-- Miguel Ángel Nazario García Hernández (Rio Blanco)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica) VALUES
(58, 4, 1, '09:00:00', '17:00:00'),
(58, 4, 6, '09:00:00', '13:00:00');

-- Amelia Contreras Serrano (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(59, 1, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '08:00-17:00'));

-- Lizbeth Torres Vazquez (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(60, 1, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '08:00-17:00'));

-- Juan Jesus Mendoza Muñoz (Villas)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id) VALUES
(61, 1, (SELECT tipo_turno_id FROM TipoTurno WHERE descripcion = 'L-V'), (SELECT horario_id FROM Horario WHERE descripcion_horario = '08:00-17:00'));

-- Stephany Morales Hernández (31pte)

-- (removido: insert de AsignacionHorario para empleados 62–69)
-- Brenda Coyotl Tlaxcalteca (31pte)

-- (removido: insert de AsignacionHorario para empleados 62–69)
-- Lorenzo García Rojas (31pte)

-- (removido: insert de AsignacionHorario para empleados 62–69)
-- Elizabeth Galicia Pérez (Villas)

-- (removido: insert de AsignacionHorario para empleados 62–69)
-- Antonio Alejandro Carrillo Barbosa (31pte)

-- (removido: insert de AsignacionHorario para empleados 62–69)
-- Carolina Sánchez Fuentes (Villas)

-- (removido: insert de AsignacionHorario para empleados 62–69)
-- Iván Ramírez Rojas (Villas)

-- (removido: insert de AsignacionHorario para empleados 62–69)
-- Antonio Pineda Hidalgo (Nave)

-- (removido: insert de AsignacionHorario para empleados 62–69)
-- Evitar duplicados exactos en asignaciones
ALTER TABLE AsignacionHorario
ADD CONSTRAINT uidx_asignacion UNIQUE (empleado_id, sucursal_id, dia_especifico_id, es_primera_quincena);

-- Vista para resumen de horarios por empleado
CREATE OR REPLACE VIEW vista_resumen_horarios AS
SELECT E.empleado_id, E.nombre, E.apellido_paterno, S.nombre_sucursal, AH.dia_especifico_id, COALESCE(H.descripcion_horario, CONCAT(AH.hora_entrada_especifica, '-', AH.hora_salida_especifica)) AS Horario
FROM Empleados E
LEFT JOIN AsignacionHorario AH ON E.empleado_id = AH.empleado_id
LEFT JOIN Horario H ON AH.horario_id = H.horario_id
LEFT JOIN Sucursales S ON AH.sucursal_id = S.sucursal_id;

-- =====================================================================
-- 🚀 SECCIÓN DE FUNCIONES PERSONALIZADAS
-- =====================================================================

--  Función para crear un objeto JSONB para un horario específico
CREATE OR REPLACE FUNCTION F_CrearJsonHorario(
    p_entrada TIME,
    p_salida TIME,
    p_cruza_medianoche BOOLEAN
)
RETURNS JSONB AS $$
DECLARE
    v_horas_totales NUMERIC(5, 2);
BEGIN
    -- Si no hay hora de entrada, no hay horario.
    IF p_entrada IS NULL THEN
        RETURN NULL;
    END IF;

    -- Calcular las horas totales
    IF p_cruza_medianoche THEN
        -- Suma las horas del primer día y del segundo día
        v_horas_totales := (EXTRACT(EPOCH FROM ('24:00:00'::TIME - p_entrada)) + EXTRACT(EPOCH FROM p_salida)) / 3600.0;
    ELSE
        -- Cálculo normal para el mismo día
        v_horas_totales := EXTRACT(EPOCH FROM (p_salida - p_entrada)) / 3600.0;
    END IF;

    -- Construir el objeto JSON
    RETURN jsonb_build_object(
        'horario_entrada', TO_CHAR(p_entrada, 'HH24:MI'),
        'horario_salida', TO_CHAR(p_salida, 'HH24:MI'),
        'horas_totales', v_horas_totales
    );
END;
$$ LANGUAGE plpgsql;

-- Función optimizada para generar la tabla de horarios por sucursal y quincena
CREATE OR REPLACE FUNCTION f_tabla_horarios(
    p_sucursal TEXT,
    p_es_primera_quincena BOOLEAN
)
RETURNS TABLE (
    codigo_frappe     SMALLINT,
    nombre_completo   TEXT,
    nombre_sucursal   TEXT,
    "Lunes"           JSONB,
    "Martes"          JSONB,
    "Miércoles"       JSONB,
    "Jueves"          JSONB,
    "Viernes"         JSONB,
    "Sábado"          JSONB,
    "Domingo"         JSONB
)
LANGUAGE sql
STABLE
AS $func$
    WITH HorariosCalculados AS (
        -- Horarios específicos
        SELECT
            AH.empleado_id,
            AH.sucursal_id,
            AH.dia_especifico_id AS dia_id,
            AH.hora_entrada_especifica AS hora_entrada,
            AH.hora_salida_especifica AS hora_salida,
            COALESCE(AH.hora_salida_especifica_cruza_medianoche, FALSE) AS cruza_medianoche,
            AH.es_primera_quincena
        FROM AsignacionHorario AH
        JOIN Sucursales S ON S.sucursal_id = AH.sucursal_id
        WHERE AH.dia_especifico_id IS NOT NULL
          AND S.nombre_sucursal = p_sucursal
          AND (AH.es_primera_quincena = p_es_primera_quincena OR AH.es_primera_quincena IS NULL)

        UNION ALL

        -- Horarios generales (turnos)
        SELECT
            AH.empleado_id,
            AH.sucursal_id,
            DS.dia_id,
            H.hora_entrada,
            H.hora_salida,
            H.cruza_medianoche,
            AH.es_primera_quincena
        FROM AsignacionHorario AH
        JOIN TipoTurno TT ON AH.tipo_turno_id = TT.tipo_turno_id
        JOIN Horario H    ON AH.horario_id = H.horario_id
        JOIN DiaSemana DS ON (
            (TT.descripcion = 'L-V' AND DS.dia_id BETWEEN 1 AND 5) OR
            (TT.descripcion = 'L-J' AND DS.dia_id BETWEEN 1 AND 4) OR
            (TT.descripcion = 'M-V' AND DS.dia_id BETWEEN 2 AND 5) OR
            POSITION(
                CASE DS.dia_id
                    WHEN 1 THEN 'L'
                    WHEN 2 THEN 'M'
                    WHEN 3 THEN 'X'
                    WHEN 4 THEN 'J'
                    WHEN 5 THEN 'V'
                    WHEN 6 THEN 'S'
                    WHEN 7 THEN 'D'
                END IN REPLACE(UPPER(TT.descripcion), ',', '')
            ) > 0
        )
        JOIN Sucursales S ON S.sucursal_id = AH.sucursal_id
        WHERE AH.dia_especifico_id IS NULL
          AND S.nombre_sucursal = p_sucursal
          AND (AH.es_primera_quincena = p_es_primera_quincena OR AH.es_primera_quincena IS NULL)
          AND NOT EXISTS (
              SELECT 1
              FROM AsignacionHorario sub
              WHERE sub.empleado_id = AH.empleado_id
                AND sub.dia_especifico_id = DS.dia_id
                AND sub.sucursal_id = AH.sucursal_id
                AND (sub.es_primera_quincena = p_es_primera_quincena OR sub.es_primera_quincena IS NULL)
          )
    ),
    RankedHorarios AS (
        SELECT *,
               ROW_NUMBER() OVER (
                   PARTITION BY empleado_id, sucursal_id, dia_id
                   ORDER BY
                       CASE WHEN es_primera_quincena = p_es_primera_quincena THEN 1
                            WHEN es_primera_quincena IS NULL THEN 2
                            ELSE 3 END
               ) AS rn
        FROM HorariosCalculados
    ),
    HorariosFinales AS (
        SELECT *
        FROM RankedHorarios
        WHERE rn = 1
    )
    SELECT
        E.codigo_frappe,
        (E.nombre || ' ' || E.apellido_paterno)::TEXT AS nombre_completo,
        S.nombre_sucursal::TEXT,
        (array_agg(F_CrearJsonHorario(hora_entrada, hora_salida, cruza_medianoche))
            FILTER (WHERE dia_id = 1))[1] AS "Lunes",
        (array_agg(F_CrearJsonHorario(hora_entrada, hora_salida, cruza_medianoche))
            FILTER (WHERE dia_id = 2))[1] AS "Martes",
        (array_agg(F_CrearJsonHorario(hora_entrada, hora_salida, cruza_medianoche))
            FILTER (WHERE dia_id = 3))[1] AS "Miércoles",
        (array_agg(F_CrearJsonHorario(hora_entrada, hora_salida, cruza_medianoche))
            FILTER (WHERE dia_id = 4))[1] AS "Jueves",
        (array_agg(F_CrearJsonHorario(hora_entrada, hora_salida, cruza_medianoche))
            FILTER (WHERE dia_id = 5))[1] AS "Viernes",
        (array_agg(F_CrearJsonHorario(hora_entrada, hora_salida, cruza_medianoche))
            FILTER (WHERE dia_id = 6))[1] AS "Sábado",
        (array_agg(F_CrearJsonHorario(hora_entrada, hora_salida, cruza_medianoche))
            FILTER (WHERE dia_id = 7))[1] AS "Domingo"
    FROM HorariosFinales HF
    JOIN Empleados E ON E.empleado_id = HF.empleado_id
    JOIN Sucursales S ON S.sucursal_id = HF.sucursal_id
    GROUP BY
        E.empleado_id, E.codigo_frappe, E.nombre, E.apellido_paterno,
        S.nombre_sucursal
    ORDER BY nombre_completo;
$func$;
-- =====================================================================
-- 🚀 FIN DE LA SECCIÓN DE FUNCIONES PERSONALIZADAS


-- === Asignaciones seguras 62–69 (idempotentes) ===

-- Asegurar horario 11:00-17:00
INSERT INTO Horario (hora_entrada, hora_salida, cruza_medianoche, descripcion_horario)
SELECT '11:00:00','17:00:00', FALSE, '11:00-17:00'
WHERE NOT EXISTS (SELECT 1 FROM Horario WHERE descripcion_horario='11:00-17:00');

-- 62
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id)
SELECT 62, 1, tt.tipo_turno_id, h.horario_id
FROM TipoTurno tt, Horario h
WHERE tt.descripcion='L-V' AND h.descripcion_horario='09:00-17:00'
AND NOT EXISTS (SELECT 1 FROM AsignacionHorario a WHERE a.empleado_id=62 AND a.sucursal_id=1 AND a.tipo_turno_id=tt.tipo_turno_id AND a.horario_id=h.horario_id);

-- 63
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id)
SELECT 63, 1, tt.tipo_turno_id, h.horario_id
FROM TipoTurno tt, Horario h
WHERE tt.descripcion='L-V' AND h.descripcion_horario='09:00-17:00'
AND NOT EXISTS (SELECT 1 FROM AsignacionHorario a WHERE a.empleado_id=63 AND a.sucursal_id=1 AND a.tipo_turno_id=tt.tipo_turno_id AND a.horario_id=h.horario_id);

-- 64 (11:00-17:00)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id)
SELECT 64, 1, tt.tipo_turno_id, h.horario_id
FROM TipoTurno tt, Horario h
WHERE tt.descripcion='L-V' AND h.descripcion_horario='11:00-17:00'
AND NOT EXISTS (SELECT 1 FROM AsignacionHorario a WHERE a.empleado_id=64 AND a.sucursal_id=1 AND a.tipo_turno_id=tt.tipo_turno_id AND a.horario_id=h.horario_id);

-- 65
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id)
SELECT 65, 3, tt.tipo_turno_id, h.horario_id
FROM TipoTurno tt, Horario h
WHERE tt.descripcion='L-V' AND h.descripcion_horario='09:00-17:00'
AND NOT EXISTS (SELECT 1 FROM AsignacionHorario a WHERE a.empleado_id=65 AND a.sucursal_id=3 AND a.tipo_turno_id=tt.tipo_turno_id AND a.horario_id=h.horario_id);

-- 66
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id)
SELECT 66, 1, tt.tipo_turno_id, h.horario_id
FROM TipoTurno tt, Horario h
WHERE tt.descripcion='L-V' AND h.descripcion_horario='09:00-17:00'
AND NOT EXISTS (SELECT 1 FROM AsignacionHorario a WHERE a.empleado_id=66 AND a.sucursal_id=1 AND a.tipo_turno_id=tt.tipo_turno_id AND a.horario_id=h.horario_id);

-- 67 (vie,sáb,dom)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica)
SELECT 67, 3, v.dia_id, v.hora_entrada, v.hora_salida
FROM (VALUES (5,'09:00:00'::time,'17:00:00'::time),
             (6,'09:00:00'::time,'17:00:00'::time),
             (7,'09:00:00'::time,'17:00:00'::time)) AS v(dia_id,hora_entrada,hora_salida)
WHERE NOT EXISTS (SELECT 1 FROM AsignacionHorario a WHERE a.empleado_id=67 AND a.sucursal_id=3 AND a.dia_especifico_id=v.dia_id);

-- 68 (vie,sáb,dom)
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, dia_especifico_id, hora_entrada_especifica, hora_salida_especifica)
SELECT 68, 3, v.dia_id, v.hora_entrada, v.hora_salida
FROM (VALUES (5,'09:00:00'::time,'17:00:00'::time),
             (6,'09:00:00'::time,'17:00:00'::time),
             (7,'09:00:00'::time,'17:00:00'::time)) AS v(dia_id,hora_entrada,hora_salida)
WHERE NOT EXISTS (SELECT 1 FROM AsignacionHorario a WHERE a.empleado_id=68 AND a.sucursal_id=3 AND a.dia_especifico_id=v.dia_id);

-- 69
INSERT INTO AsignacionHorario (empleado_id, sucursal_id, tipo_turno_id, horario_id)
SELECT 69, 2, tt.tipo_turno_id, h.horario_id
FROM TipoTurno tt, Horario h
WHERE tt.descripcion='L-V' AND h.descripcion_horario='09:00-17:00'
AND NOT EXISTS (SELECT 1 FROM AsignacionHorario a WHERE a.empleado_id=69 AND a.sucursal_id=2 AND a.tipo_turno_id=tt.tipo_turno_id AND a.horario_id=h.horario_id);


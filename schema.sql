-- SQL Script para inicializar la base de datos HidroMira en PostgreSQL

-- 1. Crear base de datos (Ejecutar conectado al usuario maestro 'postgres')
-- CREATE DATABASE hidromira;

-- 2. Crear las tablas principales de la aplicación:

-- Tabla para almacenamiento de usuarios
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    role VARCHAR(50),
    email VARCHAR(150),
    salt VARCHAR(100),
    password_hash VARCHAR(256),
    active BOOLEAN DEFAULT TRUE
);

-- Tabla para almacenar lecturas de vibración (Tiempo Real e histórico)
CREATE TABLE IF NOT EXISTS historical_data (
    id SERIAL PRIMARY KEY,
    vx DOUBLE PRECISION,
    vy DOUBLE PRECISION,
    vz DOUBLE PRECISION,
    rms DOUBLE PRECISION,
    zona VARCHAR(5),
    ts TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para almacenar el historial de mantenimientos realizados
CREATE TABLE IF NOT EXISTS maintenance_log (
    id SERIAL PRIMARY KEY,
    fecha DATE,
    tipo VARCHAR(50),
    descripcion TEXT,
    tecnico VARCHAR(100)
);

-- 3. Sembrar usuarios iniciales por defecto (hasheados con sal único)
INSERT INTO users (username, display_name, role, email, salt, password_hash, active) VALUES
('tecnico1', 'Técnico de Planta', 'tecnico', 'ggeta13basantes@gmail.com', '587590697f406e3c7a28a86ba3c53439', 'c0128be612abc9034439bec791f34c6b72b71c444c54d63093660ac2c29d284e', true),
('admin', 'Administrador', 'admin', 'ggeta13basantes@gmail.com', '1b3576760d32032cb898fb85a1c6dfe0', '37c6d969c9da60906a653f5ba4162dd525550fc26fd08034d582cd4f298481a8', true),
('jefe', 'Ingeniero en Jefe', 'ingeniero_jefe', 'geovanny.basantesq@gmail.com', '6b238a53f050a7207b51982921d4b617', '65c9f64f74dcb90d4afc6efa2a92903082655945b8b09b69721060278f94dca9', true)
ON CONFLICT (username) DO NOTHING;

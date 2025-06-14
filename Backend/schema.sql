CREATE TABLE IF NOT EXISTS ruta (
    id SERIAL PRIMARY KEY,
    nombre TEXT
);

CREATE TABLE IF NOT EXISTS ubicacion (
    id SERIAL PRIMARY KEY,
    latitud DOUBLE PRECISION,
    longitud DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS estacion (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    idubicacion INTEGER REFERENCES ubicacion(id),
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS parada (
    id SERIAL PRIMARY KEY,
    nombre TEXT,
    idubicacion INTEGER REFERENCES ubicacion(id),
    id_estacion INTEGER REFERENCES estacion(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS bus (
    id SERIAL PRIMARY KEY,
    idruta INTEGER REFERENCES ruta(id)
);

CREATE TABLE IF NOT EXISTS usuario (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS irregularidad (
    id SERIAL PRIMARY KEY,
    idusuario INTEGER REFERENCES usuario(id),
    idruta INTEGER REFERENCES ruta(id),
    titulo TEXT,
    descripcion TEXT,
    fecha TIMESTAMP,
    idubicacion INTEGER REFERENCES ubicacion(id)
);

CREATE TABLE IF NOT EXISTS ubicaciontemporal (
    id SERIAL PRIMARY KEY,
    tiempo TIMESTAMP,
    idbus INTEGER REFERENCES bus(id),
    idruta INTEGER REFERENCES ruta(id),
    idparadadestino INTEGER REFERENCES parada(id),
    velocidad DOUBLE PRECISION,
    nextstopid INTEGER REFERENCES parada(id),
    distanciaonstop DOUBLE PRECISION,
    tiemporestado DOUBLE PRECISION,
    estado TEXT
);

CREATE TABLE IF NOT EXISTS ruta_parada (
    id SERIAL PRIMARY KEY,
    id_ruta INTEGER NOT NULL REFERENCES ruta(id) ON DELETE CASCADE,
    id_parada INTEGER NOT NULL REFERENCES parada(id) ON DELETE CASCADE,
    orden INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS rutas_usuario (
    id SERIAL PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    id_ruta INTEGER NOT NULL REFERENCES ruta(id) ON DELETE CASCADE,
    abordo BOOLEAN DEFAULT FALSE,
    ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

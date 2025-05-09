CREATE TABLE IF NOT EXISTS ruta (
    id BIGINT PRIMARY KEY,
    nombre TEXT
);

CREATE TABLE IF NOT EXISTS ubicacion (
    id BIGINT PRIMARY KEY,
    latitud DOUBLE PRECISION,
    longitud DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS parada (
    id BIGINT PRIMARY KEY,
    nombre TEXT,
    idubicacion BIGINT,
    FOREIGN KEY (idubicacion) REFERENCES ubicacion(id)
);

CREATE TABLE IF NOT EXISTS bus (
    id BIGINT PRIMARY KEY,
    idruta BIGINT,
    FOREIGN KEY (idruta) REFERENCES ruta(id)
);

CREATE TABLE IF NOT EXISTS users ( 
    id SERIAL PRIMARY KEY, 
    username VARCHAR(50) UNIQUE NOT NULL, 
    password VARCHAR(255) NOT NULL, 
    first_name VARCHAR(100) NOT NULL, 
    last_name VARCHAR(100) NOT NULL, 
    email VARCHAR(255) UNIQUE NOT NULL, 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
);

CREATE TABLE IF NOT EXISTS irregularidad (
    id BIGINT PRIMARY KEY,
    idusuario BIGINT,
    idruta BIGINT,
    titulo TEXT,
    descripcion TEXT,
    fecha TIMESTAMP,
    idubicacion BIGINT,
    FOREIGN KEY (idusuario) REFERENCES usuario(id),
    FOREIGN KEY (idruta) REFERENCES ruta(id),
    FOREIGN KEY (idubicacion) REFERENCES ubicacion(id)
);

CREATE TABLE IF NOT EXISTS ubicaciontemporal (
    id BIGINT PRIMARY KEY,
    tiempo TIMESTAMP,
    idbus BIGINT,
    idruta BIGINT,
    idparadadestino BIGINT,
    velocidad DOUBLE PRECISION,
    nextstopid BIGINT,
    distanciaonstop DOUBLE PRECISION,
    tiemporestado DOUBLE PRECISION,
    estado TEXT,
    FOREIGN KEY (idbus) REFERENCES bus(id),
    FOREIGN KEY (idruta) REFERENCES ruta(id),
    FOREIGN KEY (idparadadestino) REFERENCES parada(id),
    FOREIGN KEY (nextstopid) REFERENCES parada(id)
);
CREATE TABLE IF NOT EXISTS ruta (
    id INTEGER PRIMARY KEY,
    nombre TEXT
);

CREATE TABLE IF NOT EXISTS ubicacion (
    id INTEGER PRIMARY KEY,
    latitud DOUBLE PRECISION,
    longitud DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS estacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    idubicacion INTEGER,
    descripcion TEXT,
    FOREIGN KEY (idubicacion) REFERENCES ubicacion(id)
);

CREATE TABLE IF NOT EXISTS parada (
    id INTEGER PRIMARY KEY,
    nombre TEXT,
    idubicacion INTEGER,
    id_estacion INTEGER,
    FOREIGN KEY (idubicacion) REFERENCES ubicacion(id),
    FOREIGN KEY (id_estacion) REFERENCES estacion(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS bus (
    id INTEGER PRIMARY KEY,
    idruta INTEGER,
    FOREIGN KEY (idruta) REFERENCES ruta(id)
);

CREATE TABLE IF NOT EXISTS usuario ( 
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    username VARCHAR(50) UNIQUE NOT NULL, 
    password VARCHAR(255) NOT NULL, 
    first_name VARCHAR(100) NOT NULL, 
    last_name VARCHAR(100) NOT NULL, 
    email VARCHAR(255) UNIQUE NOT NULL, 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
);

CREATE TABLE IF NOT EXISTS irregularidad (
    id INTEGER PRIMARY KEY,
    idusuario INTEGER,
    idruta INTEGER,
    titulo TEXT,
    descripcion TEXT,
    fecha TIMESTAMP,
    idubicacion INTEGER,
    FOREIGN KEY (idusuario) REFERENCES usuario(id),
    FOREIGN KEY (idruta) REFERENCES ruta(id),
    FOREIGN KEY (idubicacion) REFERENCES ubicacion(id)
);

CREATE TABLE IF NOT EXISTS ubicaciontemporal (
    id INTEGER PRIMARY KEY,
    tiempo TIMESTAMP,
    idbus INTEGER,
    idruta INTEGER,
    idparadadestino INTEGER,
    velocidad DOUBLE PRECISION,
    nextstopid INTEGER,
    distanciaonstop DOUBLE PRECISION,
    tiemporestado DOUBLE PRECISION,
    estado TEXT,
    FOREIGN KEY (idbus) REFERENCES bus(id),
    FOREIGN KEY (idruta) REFERENCES ruta(id),
    FOREIGN KEY (idparadadestino) REFERENCES parada(id),
    FOREIGN KEY (nextstopid) REFERENCES parada(id)
);

CREATE TABLE IF NOT EXISTS ruta_parada (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_ruta INTEGER NOT NULL,
    id_parada INTEGER NOT NULL,
    orden INTEGER NOT NULL,
    FOREIGN KEY (id_ruta) REFERENCES ruta(id) ON DELETE CASCADE,
    FOREIGN KEY (id_parada) REFERENCES parada(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rutas_usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER NOT NULL,
    id_ruta INTEGER NOT NULL,
    abordo BOOLEAN DEFAULT 0,
    ultima_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario) REFERENCES usuario(id) ON DELETE CASCADE,
    FOREIGN KEY (id_ruta) REFERENCES ruta(id) ON DELETE CASCADE
);

CREATE TABLE ruta (
    id BIGINT PRIMARY KEY,
    nombre TEXT
);

CREATE TABLE ubicacion (
    id BIGINT PRIMARY KEY,
    latitud DOUBLE PRECISION,
    longitud DOUBLE PRECISION
);

CREATE TABLE parada (
    id BIGINT PRIMARY KEY,
    nombre TEXT,
    idubicacion BIGINT,
    FOREIGN KEY (idubicacion) REFERENCES ubicacion(id)
);

CREATE TABLE bus (
    id BIGINT PRIMARY KEY,
    idruta BIGINT,
    FOREIGN KEY (idruta) REFERENCES ruta(id)
);

CREATE TABLE usuario (
    id BIGINT PRIMARY KEY,
    nombreusuario TEXT,
    contrasena TEXT,
    nombre TEXT,
    apellido TEXT,
    email TEXT,
    ubicacion_actual BIGINT,
    FOREIGN KEY (ubicacion_actual) REFERENCES ubicacion(id)
);

CREATE TABLE irregularidad (
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

CREATE TABLE ubicaciontemporal (
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
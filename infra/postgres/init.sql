CREATE TABLE Solicitud (
    GUID_Solicitud VARCHAR(255) PRIMARY KEY,
    URL_Imagen_Original VARCHAR(255),
    URL_Imagen_Terminada VARCHAR(255),
    URL_Imagen_Marcos VARCHAR(255),
    Inicio_Solicitud TIMESTAMP,
    Fin_Solicitud TIMESTAMP,
    Inicio_Deteccion_Caras TIMESTAMP,
    Fin_Deteccion_Caras TIMESTAMP,
    Inicio_Edad TIMESTAMP,
    Fin_edad TIMESTAMP,
    Inicio_Pixelado TIMESTAMP,
    Fin_Pixelado TIMESTAMP,
    Inicio_Almacenamiento_Solicitud TIMESTAMP,
    Fin_Almacenamiento_Solicitud TIMESTAMP,
    Estado VARCHAR(50)
);

CREATE TABLE Imagenes (
    GUID_Solicitud VARCHAR(255),
    Id_Imagen SERIAL,
    URL_Imagen VARCHAR(255),
    Mayor_18 BOOLEAN,
    Escore DECIMAL(5,4),
    Imagen_X INT,
    Imagen_Y INT,
    Imagen_Ancho INT,
    Imagen_Alto INT,

    PRIMARY KEY (GUID_Solicitud, Id_Imagen),

    FOREIGN KEY (GUID_Solicitud)
        REFERENCES Solicitud(GUID_Solicitud)
);
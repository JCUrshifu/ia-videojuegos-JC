-- =====================================================
-- 01_schema.sql  |  Asistente de videojuegos con IA
-- =====================================================

CREATE TABLE IF NOT EXISTS usuarios (
    id             SERIAL PRIMARY KEY,
    nombre         VARCHAR(100) NOT NULL,
    email          VARCHAR(150) NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    rol            VARCHAR(10)  NOT NULL DEFAULT 'usuario'
                   CHECK (rol IN ('admin', 'usuario')),
    activo         BOOLEAN      NOT NULL DEFAULT TRUE,
    limite_tokens  INTEGER      NOT NULL DEFAULT 20000,
    creado_en      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS servicios (
    id           SERIAL PRIMARY KEY,
    codigo       VARCHAR(40)  NOT NULL UNIQUE,
    nombre       VARCHAR(100) NOT NULL,
    descripcion  TEXT,
    activo       BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS videojuegos (
    id           SERIAL PRIMARY KEY,
    titulo       VARCHAR(150) NOT NULL UNIQUE,
    genero       VARCHAR(40)  NOT NULL,
    plataforma   VARCHAR(40)  NOT NULL,
    precio       NUMERIC(8,2) NOT NULL CHECK (precio >= 0),
    stock        INTEGER      NOT NULL DEFAULT 0 CHECK (stock >= 0),
    anio         INTEGER,
    descripcion  TEXT,
    busqueda     TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('spanish',
            coalesce(titulo,'')     || ' ' ||
            coalesce(genero,'')     || ' ' ||
            coalesce(plataforma,'') || ' ' ||
            coalesce(descripcion,''))
    ) STORED
);
CREATE INDEX IF NOT EXISTS idx_videojuegos_busqueda ON videojuegos USING GIN (busqueda);

CREATE TABLE IF NOT EXISTS resenas (
    id             SERIAL PRIMARY KEY,
    videojuego_id  INTEGER NOT NULL REFERENCES videojuegos(id) ON DELETE CASCADE,
    autor          VARCHAR(80) NOT NULL,
    puntuacion     INTEGER NOT NULL CHECK (puntuacion BETWEEN 1 AND 5),
    comentario     TEXT,
    creado_en      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversaciones (
    id          SERIAL PRIMARY KEY,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    servicio_id INTEGER NOT NULL REFERENCES servicios(id),
    titulo      VARCHAR(150),
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mensajes (
    id               SERIAL PRIMARY KEY,
    conversacion_id  INTEGER NOT NULL REFERENCES conversaciones(id) ON DELETE CASCADE,
    rol              VARCHAR(12) NOT NULL CHECK (rol IN ('usuario', 'asistente')),
    contenido        TEXT NOT NULL,
    fuentes          JSONB,
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS consumo_tokens (
    id               SERIAL PRIMARY KEY,
    usuario_id       INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    servicio_id      INTEGER NOT NULL REFERENCES servicios(id),
    conversacion_id  INTEGER REFERENCES conversaciones(id) ON DELETE SET NULL,
    tokens_entrada   INTEGER NOT NULL DEFAULT 0,
    tokens_salida    INTEGER NOT NULL DEFAULT 0,
    tokens_total     INTEGER NOT NULL DEFAULT 0,
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_consumo_usuario ON consumo_tokens (usuario_id, creado_en);

INSERT INTO servicios (codigo, nombre, descripcion) VALUES
 ('chatbot_rag', 'Chatbot de videojuegos (RAG)',
  'Responde preguntas usando el catálogo de la base de datos, con memoria y fuentes.'),
 ('agente_presupuesto', 'Agente analizador de presupuesto',
  'Busca los juegos elegidos, calcula el total y lo compara con tu presupuesto.'),
 ('agente_alternativas', 'Agente de alternativas',
  'Busca opciones más económicas y consulta una fuente externa para recomendar.')
ON CONFLICT (codigo) DO NOTHING;


-- =====================================================
-- 02_datos_demo.sql  |  Catálogo y reseñas de demostración
-- (precios y stock son datos ficticios de demo)
-- =====================================================

INSERT INTO videojuegos (titulo, genero, plataforma, precio, stock, anio, descripcion) VALUES
('The Legend of Zelda: Tears of the Kingdom','Aventura','Nintendo Switch',69.99,12,2023,'Aventura de mundo abierto con exploración, construcción de vehículos y puzles.'),
('Elden Ring','RPG','Multiplataforma',59.99,15,2022,'RPG de acción en un mundo abierto enorme, con jefes muy difíciles.'),
('Baldur''s Gate 3','RPG','PC',59.99,10,2023,'RPG por turnos con historia profunda, decisiones importantes y cooperativo.'),
('God of War Ragnarök','Acción','PlayStation 5',59.99,9,2022,'Acción y aventura de mitología nórdica con combate intenso e historia emotiva.'),
('Hades','Acción','Multiplataforma',24.99,20,2020,'Roguelike de acción rápido donde cada intento es distinto.'),
('Stardew Valley','Simulación','Multiplataforma',14.99,30,2016,'Simulador de granja relajante con cultivos, pesca, minería y amistades.'),
('Hollow Knight','Plataformas','Multiplataforma',14.99,25,2017,'Plataformas y exploración en un reino subterráneo de insectos, muy desafiante.'),
('Celeste','Plataformas','Multiplataforma',19.99,18,2018,'Plataformas de precisión sobre escalar una montaña, con una historia personal.'),
('Minecraft','Aventura','Multiplataforma',29.99,40,2011,'Sandbox de construcción y supervivencia con creatividad ilimitada.'),
('EA Sports FC 24','Deportes','Multiplataforma',69.99,14,2023,'Simulador de fútbol con ligas, equipos licenciados y modo en línea.'),
('Forza Horizon 5','Carreras','Xbox Series',59.99,11,2021,'Carreras de mundo abierto ambientadas en México con cientos de autos.'),
('Mario Kart 8 Deluxe','Carreras','Nintendo Switch',59.99,22,2017,'Carreras de karts con objetos, ideal para jugar con amigos y familia.'),
('Super Mario Odyssey','Plataformas','Nintendo Switch',59.99,16,2017,'Plataformas 3D creativas donde Mario viaja por reinos muy distintos.'),
('Cyberpunk 2077','RPG','Multiplataforma',39.99,13,2020,'RPG de mundo abierto en una ciudad futurista con historia basada en decisiones.'),
('The Witcher 3: Wild Hunt','RPG','Multiplataforma',29.99,17,2015,'RPG de fantasía con misiones memorables y mundo abierto muy extenso.'),
('Red Dead Redemption 2','Acción','Multiplataforma',39.99,12,2018,'Acción y aventura en el viejo oeste con ritmo pausado e inmersivo.'),
('Grand Theft Auto V','Acción','Multiplataforma',29.99,25,2013,'Acción de mundo abierto con tres protagonistas y modo en línea.'),
('Resident Evil 4','Terror','Multiplataforma',39.99,10,2023,'Remake de terror y acción con enemigos intensos y mucha tensión.'),
('Civilization VI','Estrategia','PC',29.99,15,2016,'Estrategia por turnos para construir un imperio a través de la historia.'),
('Age of Empires II: Definitive Edition','Estrategia','PC',19.99,20,2019,'Estrategia en tiempo real medieval con campañas y multijugador.'),
('Portal 2','Puzzle','PC',9.99,30,2011,'Puzles en primera persona con portales, humor y modo cooperativo.'),
('Doom Eternal','Shooter','Multiplataforma',29.99,14,2020,'Shooter frenético en primera persona contra hordas de demonios.'),
('Halo Infinite','Shooter','Xbox Series',39.99,8,2021,'Shooter de ciencia ficción con campaña y multijugador competitivo.'),
('Splatoon 3','Shooter','Nintendo Switch',59.99,10,2022,'Shooter colorido por equipos donde se gana pintando el escenario.'),
('Animal Crossing: New Horizons','Simulación','Nintendo Switch',59.99,19,2020,'Simulación social y relajante de vivir y decorar una isla.'),
('Cities: Skylines','Simulación','PC',29.99,14,2015,'Simulador de construcción y gestión de ciudades.'),
('Hogwarts Legacy','RPG','Multiplataforma',49.99,11,2023,'RPG de mundo abierto ambientado en un colegio de magia.'),
('Marvel''s Spider-Man 2','Acción','PlayStation 5',69.99,9,2023,'Acción de superhéroes con desplazamiento fluido por Nueva York.'),
('Horizon Zero Dawn','Acción','Multiplataforma',19.99,15,2017,'Acción y aventura contra máquinas gigantes en un mundo posapocalíptico.'),
('Death Stranding','Acción','Multiplataforma',29.99,8,2019,'Aventura de exploración y entregas en un mundo desolado y extraño.'),
('Sekiro: Shadows Die Twice','Acción','Multiplataforma',49.99,9,2019,'Acción de samuráis con combate preciso y dificultad muy alta.'),
('Dark Souls III','RPG','Multiplataforma',39.99,10,2016,'RPG de acción oscuro y exigente, célebre por sus jefes.'),
('Dead Cells','Acción','Multiplataforma',24.99,20,2018,'Roguelike de acción y plataformas con combate rápido.'),
('Undertale','RPG','Multiplataforma',9.99,28,2015,'RPG indie donde puedes resolver los combates sin pelear.'),
('Terraria','Aventura','Multiplataforma',9.99,35,2011,'Aventura 2D de exploración, construcción y combate con mucho contenido.'),
('Among Us','Estrategia','Multiplataforma',4.99,40,2018,'Juego social de deducción en grupo con impostores en una nave.'),
('It Takes Two','Aventura','Multiplataforma',39.99,12,2021,'Aventura cooperativa para dos jugadores con mecánicas muy variadas.'),
('Rocket League','Deportes','Multiplataforma',19.99,16,2015,'Fútbol con autos propulsados por cohetes, rápido y competitivo.'),
('Gran Turismo 7','Carreras','PlayStation 5',59.99,9,2022,'Simulador de carreras realista con enorme colección de autos.'),
('Pokémon Escarlata','RPG','Nintendo Switch',59.99,14,2022,'RPG de capturar y entrenar criaturas en un mundo abierto.')
ON CONFLICT (titulo) DO NOTHING;

INSERT INTO resenas (videojuego_id, autor, puntuacion, comentario)
SELECT v.id, r.autor, r.puntuacion, r.comentario
FROM (VALUES
('The Legend of Zelda: Tears of the Kingdom','Carlos M.',5,'Explorar y construir inventos es adictivo; muchísima libertad.'),
('The Legend of Zelda: Tears of the Kingdom','Ana L.',4,'Excelente, aunque las armas se rompen muy rápido.'),
('Elden Ring','Diego R.',5,'Mundo abierto enorme y jefes memorables, pero es muy difícil.'),
('Elden Ring','Sofía P.',4,'Gran diseño, la dificultad puede frustrar a los nuevos.'),
('Baldur''s Gate 3','Luis G.',5,'Historia profunda y decisiones que realmente importan.'),
('Baldur''s Gate 3','Marta V.',5,'Combates por turnos muy bien logrados; es larguísimo.'),
('God of War Ragnarök','Pedro S.',5,'Combate espectacular y una historia emotiva.'),
('Hades','Elena T.',5,'Cada partida se siente distinta y el combate es fluido.'),
('Hades','Jorge A.',4,'Muy rejugable; algo repetitivo tras muchas horas.'),
('Stardew Valley','Valeria C.',5,'Relajante y con muchísimo contenido por su precio.'),
('Hollow Knight','Andrés B.',5,'Ambientación preciosa y gran exploración por muy poco dinero.'),
('Celeste','Camila F.',4,'Plataformas exigentes con un mensaje muy bonito.'),
('Minecraft','Roberto H.',5,'Creatividad sin límites, ideal para jugar con amigos.'),
('EA Sports FC 24','Daniel K.',3,'Buena jugabilidad, pero con muchas microtransacciones.'),
('Forza Horizon 5','Isabel N.',5,'Gráficos increíbles y una enorme variedad de autos.'),
('Mario Kart 8 Deluxe','Fernando Q.',5,'Perfecto para jugar en familia o con amigos.'),
('Super Mario Odyssey','Lucía D.',5,'Creativo y divertido en cada nivel.'),
('Cyberpunk 2077','Héctor J.',4,'Mejoró mucho con las actualizaciones; la ciudad impresiona.'),
('The Witcher 3: Wild Hunt','Paola Z.',5,'Las misiones secundarias superan a la historia de muchos juegos.'),
('Red Dead Redemption 2','Gabriel O.',5,'Ritmo lento pero inmersión increíble.'),
('Grand Theft Auto V','Natalia E.',4,'Sigue siendo divertidísimo, sobre todo en línea.'),
('Resident Evil 4','Tomás I.',5,'Un remake que mejora todo el original.'),
('Civilization VI','Raúl U.',4,'Muy adictivo, aunque las partidas largas se vuelven pesadas.'),
('Portal 2','Mónica Y.',5,'Puzles ingeniosos y humor memorable.'),
('Doom Eternal','Esteban W.',4,'Acción frenética, exige dominar las mecánicas.'),
('Animal Crossing: New Horizons','Rosa G.',4,'Muy relajante, pero algo lento al inicio.'),
('Cities: Skylines','Mauricio L.',4,'Ideal para amantes de la planificación urbana.'),
('Sekiro: Shadows Die Twice','Ivana M.',4,'Combate preciso y muy difícil.'),
('It Takes Two','Carolina R.',5,'La mejor experiencia cooperativa que he jugado.'),
('Terraria','Julio P.',5,'Mucho contenido por muy poco precio.')
) AS r(titulo, autor, puntuacion, comentario)
JOIN videojuegos v ON v.titulo = r.titulo;
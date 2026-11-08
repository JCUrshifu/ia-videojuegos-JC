SELECT 
  (SELECT COUNT(*) FROM videojuegos) AS juegos,
  (SELECT COUNT(*) FROM resenas)     AS resenas,
  (SELECT COUNT(*) FROM servicios)   AS servicios;
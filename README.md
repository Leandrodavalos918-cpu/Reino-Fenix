# Reino Fénix — MASTER v3.0

Simulación persistente de un mundo autónomo con Observador externo/Dios.

## Incluye
- 2 reinos, 6 ciudades, regiones y rutas.
- 2.000 habitantes iniciales, 179 familias y 40 casas nobles.
- Edad, salud, muertes, nacimientos y generaciones.
- Relaciones, memoria individual y conocimiento con confianza/rumores.
- Economía causal básica: producción, consumo, inventarios, salarios, precios, negocios, deuda y quiebras.
- Mercados por ciudad y rutas físicas.
- Facciones, cargos, leyes y reacción política a condiciones económicas.
- Crimen, investigación y resolución de casos.
- Ejércitos con moral, comida y equipo.
- Eventos con causa/consecuencia y crónica profunda diaria.
- Modo Dios y acciones programables.
- SQLite con WAL, transacciones y bloqueo global para evitar carreras dentro del proceso.
- Interfaz web y API.

## Render
Python está fijado mediante `.python-version` a 3.13.5.
Build: `pip install -r requirements.txt`
Start: `uvicorn server:app --host 0.0.0.0 --port $PORT`

## Verificación
`test_world.py` ejecuta una prueba de arranque, estado inicial, 365 días, economía/demografía, API, Modo Dios y persistencia.

## Honestidad de alcance
Esta versión implementa una base MASTER mucho más profunda, pero no declara como terminados sistemas que todavía requieren modelado avanzado (por ejemplo, combate militar detallado, banca completa, migración sofisticada y un planificador utilitario avanzado para cada NPC). Esos módulos deben añadirse y verificarse por separado.

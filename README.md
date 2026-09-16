# Reino Fénix — mundo vivo

Prototipo ejecutable de una simulación persistente autónoma. Incluye población, familias y generaciones, relaciones, conocimiento, memoria, economía, empresas, mercados, rutas, envíos, política/facciones/oficios, ejércitos, conflictos, delitos como estructura de datos, clima, proyectos, leyes, eventos, crónicas y Modo Dios.

## Ejecutar
`pip install -r requirements.txt`
`uvicorn server:app --reload`
Abrir `http://127.0.0.1:8000`

## Nota de persistencia
El prototipo usa SQLite local. Para producción prolongada debe migrarse a PostgreSQL y un worker persistente; Render necesita almacenamiento/base de datos persistente. Esta versión está pensada para validar el comportamiento del mundo antes de esa migración.

# Reino Fénix

Simulación persistente autónoma de un mundo ficticio. El usuario es un observador externo con Modo Dios; los NPC no conocen su existencia.

## Ejecutar localmente

```bash
pip install -r requirements.txt
uvicorn server:app --reload
```

Abrir `http://127.0.0.1:8000`.

## Diseño

- FastAPI + SQLite WAL.
- Un único motor de simulación serializa todas las escrituras mediante un lock de proceso.
- Transacciones cortas y `busy_timeout` para evitar `database is locked`.
- Modo Dios con formularios amigables; JSON no es necesario para el usuario.
- Tiempo persistente: 1 hora real = 1 día del mundo por defecto.
- El estado del mundo es la fuente de verdad; la crónica se genera desde hechos registrados.
- Reiniciar el proceso no reinicia el mundo: la base `reino_fenix.db` conserva el estado.

## Despliegue en Render

El servicio utiliza `Procfile`/`render.yaml`. Para persistencia permanente en Render, usar una base de datos PostgreSQL o un disco persistente; el SQLite incluido es apropiado para prototipo y pruebas.

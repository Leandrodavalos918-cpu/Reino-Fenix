# Reino Fénix — Master Expansion

Persistent autonomous world simulation. This package preserves the running v2.1 engine and adds the master design documents for the complete world architecture.

## Run
```bash
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port $PORT
```

Render/Python: `.python-version` pins Python 3.13.5 for compatible dependencies.

See `MASTER_WORLD.md` for the complete world design and `IMPLEMENTATION_STATUS.md` for an honest implementation boundary.

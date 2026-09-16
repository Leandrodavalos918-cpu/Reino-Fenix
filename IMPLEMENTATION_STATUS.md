# Estado de implementación — MASTER v3.0

## Verificado
- Arranque FastAPI mediante `server:app`.
- 2.000 personas, 179 familias, 24 negocios, 40 nobles al iniciar.
- SQLite + WAL + transacción `BEGIN IMMEDIATE`.
- Avance de 365 días sin error en prueba automatizada.
- 365 crónicas generadas.
- Nacimientos y envejecimiento procesados.
- Mercados con producción, consumo, stock y precio.
- Negocios con caja, deuda, trabajadores, ventas y quiebra.
- Impuestos y tesoro.
- Conocimiento y propagación social básica con posibilidad de distorsión.
- Memorias individuales.
- Crímenes, investigaciones y resolución.
- Ejércitos con consumo de suministros y moral.
- Intervención divina y registro histórico.
- API de personas, mercados, negocios, facciones, nobles, rutas, eventos, crónicas, delitos y ejércitos.

## Pendiente para capas futuras
- Planificador autónomo avanzado para cada NPC con utilidad/expectativas.
- Banca, crédito y quiebras financieras completas.
- Comercio marítimo/terrestre con convoyes y logística detallada.
- Migración y formación/desintegración de hogares más sofisticadas.
- Gobierno autónomo completo con legislación y negociación entre actores.
- Justicia con cadena completa de evidencia, arresto, juicio, sentencia y corrupción.
- Combate militar detallado y campañas.
- Worker persistente para simulación mientras el observador está ausente y PostgreSQL para producción de larga duración.

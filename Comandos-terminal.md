Claro, te explico para qué sirve cada uno:
Comando	¿Qué hace?	¿Cuándo lo usás?
trady-ai status	Muestra la configuración actual del sistema (environment, dry_run, db_path). Nunca muestra secrets.	Para verificar que todo está bien configurado antes de operar
trady-ai backtest --input archivo.csv	El comando principal. Toma un CSV con datos históricos de mercado (precios), los pasa por el motor determinístico, aplica la estrategia Markov, y te devuelve: cuántas señales generó, cuántos trades hizo, win rate, P&L total, máximo drawdown. Y después hace replay para verificar que es 100% determinístico.	Para probar la estrategia con datos históricos y ver si es rentable ANTES de poner plata real
trady-ai analyze --market btc-usd	Busca en la base de datos las últimas 5 señales generadas para ese mercado y te las muestra (dirección, confianza, timestamp).	Para ver qué dijo el bot sobre un mercado en particular
trady-ai run --market btc-usd	Stub por ahora. Imprime "Simulated execution (dry_run=True)". En Fase 2 (cuando tengamos el adapter de Polymarket) este comando va a ejecutar trades REALES.	Por ahora: placeholder. En Fase 2: modo live
Ejemplo concreto
# 1. Verificás que está todo ok
$ trady-ai status
Trady.AI Status
  Environment: development
  Dry run: True
  Log level: INFO
  DB path: data/trady_ai.db

# 2. Le tirás datos históricos de BTC
$ trady-ai backtest --input btc_2024.csv --warmup 50
Backtest Results
  Total signals: 312
  Total trades: 47
  Win rate: 57.45%
  Total PnL: $23.80
  Max drawdown: -$8.40
  Replay verification: PASS

# 3. Revisás qué dijo sobre BTC
$ trady-ai analyze --market btc-usd
Recent signals for btc-usd:
  2024-06-15T14:30:00: LONG (confidence=0.62)
  2024-06-15T14:25:00: NEUTRAL (confidence=0.00)
  2024-06-15T14:20:00: SHORT (confidence=0.58)
El más importante es backtest — es donde validás que tu estrategia genera plata antes de poner un peso real. El resto son herramientas de diagnóstico.
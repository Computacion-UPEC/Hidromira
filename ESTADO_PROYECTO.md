# HidroMira — Estado del Proyecto

> Este archivo es un resumen para retomar el trabajo en cualquier momento, sin depender de que una conversación anterior con Claude siga "viva". Consérvalo actualizado.

## Qué es este proyecto

Sistema de monitoreo de vibraciones para la turbina de una hidroeléctrica. Usa un sensor WitMotion **WTVB01-485** (acelerómetro/vibrómetro triaxial, comunicación Modbus RTU por RS-485) conectado por puerto serial. El sistema lee el sensor, clasifica el estado de la máquina según la norma **ISO 20816-3**, grafica los datos en tiempo real, guarda histórico, y puede avisar por correo/IoT si hay una alerta.

## Arquitectura (archivos principales)

- **`app.py`** — App Streamlit principal (puerto 8502). Tiene la página "⚡ Monitoreo en Tiempo Real" (lee el sensor en vivo y grafica) además de análisis histórico, mantenimiento, configuración de puertos, notificaciones por correo, etc.
- **`monitor_realtime.py`** — App Streamlit separada (puerto 8503), pensada originalmente solo para monitoreo en tiempo real. Hoy `app.py` ya incluye esa función también, así que puede haber redundancia entre ambas — revisar cuál se usa realmente en producción.
- **`web_hidro_pro.py`** — Otra variante/servidor web que lee el sensor con su propia lógica (**tiene un bug de direcciones de registro, ver abajo**).
- **`iot_config.py`** — Configuración de IoT (Telegram, MQTT, email, ThingSpeak) y de puertos seriales (`load_serial_config` / `save_serial_config`), incluida la escala del sensor.
- **`iot_handler.py`** — Envío de alertas (correo, webhook, MQTT) y publicación a ThingSpeak.
- **`db.py`** — Guardado de histórico y respaldos.
- **`registers.json`** — Mapa de registros Modbus del sensor WTVB01-485 (direcciones y escalas).
- **`api_rest.py`** — API REST del sistema.
- **`docs/`** — Guías (Gmail, ngrok, IoT, instrucciones de arranque).

## Trabajo hecho — 5 de julio 2026

### Bug encontrado: calibración de velocidad

El síntoma reportado: la gráfica de vibración mostraba datos mal calibrados, y no se veía nada parecido a "velocity amplitude" (el dato que sí se ve en el software oficial de WitMotion, panel "Main").

**Causa:** `app.py` lee los registros Modbus 58, 59 y 60 (0x3A-0x3C), que son exactamente **VX/VY/VZ = "X/Y/Z velocity amplitude"**. Pero el código dividía ese valor entre `sensor_scale = 100.0`, achicando la velocidad graficada 100 veces.

**Cómo se confirmó:** se descompiló el software oficial de WitMotion (carpeta `Download the WitMotion Software/`, específicamente `Wit.SDK.DeviceOptions.dll`) para ver exactamente cómo el fabricante lee y escala cada registro. Se extrajo así el mapa real de registros del WTVB01-485:

| Registro (dec/hex) | Campo | Escala aplicada por WitMotion |
|---|---|---|
| 52-54 (0x34-0x36) | Aceleración X/Y/Z | crudo / 2048 → g |
| 55-57 (0x37-0x39) | Velocidad angular X/Y/Z | crudo / 16.384 → °/s |
| **58-60 (0x3A-0x3C)** | **Velocidad / "velocity amplitude" X/Y/Z** | **crudo directo (sin dividir) → mm/s** |
| 61-63 (0x3D-0x3F) | Ángulos Roll/Pitch/Yaw (no es vibración) | crudo / 182.044 → ° |
| 64 (0x40) | Temperatura | crudo / 100 → °C |
| 65-67 (0x41-0x43) | Desplazamiento / "displacement amplitude" X/Y/Z | crudo directo (sin dividir) → µm |
| 68-70 (0x44-0x46) | Frecuencia X/Y/Z | crudo directo → Hz (ya estaba correcto) |

### Cambios aplicados — corrección de escala (primera pasada)

- **`iot_config.py`**: `SENSOR_SCALE_DEFAULT` cambiado de `100.0` a `1.0`.
- **`app.py`**: valor inicial de `sensor_scale` y el selector "Divisor de Escala" ahora arrancan en `1.0` en vez de `100.0`.
- **`registers.json`**: escala de velocidad (58-60) corregida a `1.0`; se completaron direcciones que estaban en `null` (Aceleración → 52-54, Temperatura → 64), confirmadas con el mismo método.

### Cambios aplicados — todos los campos del sensor en Monitoreo en Tiempo Real

- **`app.py`**: la lectura del sensor ahora hace **una sola transacción Modbus** (`sensor.read_registers(52, 19, functioncode=3)`) que trae de un tiro los registros 52 a 70, en vez de leer uno por uno. Se agregó `to_signed16()` para convertir cada registro (unsigned) a su valor con signo.
- Ahora se leen y se muestran en la página "⚡ Monitoreo en Tiempo Real": Aceleración X/Y/Z, Velocidad angular X/Y/Z, Temperatura, Frecuencia X/Y/Z (como métricas), y **Amplitud de desplazamiento X/Y/Z** (registros 65-67) con su propia gráfica, igual que la de velocidad. Los ángulos Roll/Pitch/Yaw (61-63) se leen pero no se muestran porque no son datos de vibración.
- `calcular_rpm()` ahora acepta `freq_hz_override` para reusar la frecuencia ya leída en el bloque, en vez de hacer una segunda consulta al sensor solo para el RPM.
- **`registers.json`**: se agregaron las 3 entradas de "Angular velocity X/Y/Z" (55-57) y se corrigieron las direcciones de "X/Y/Z displacement amplitude" (antes en `null`, ahora 65-67, escala 1.0).

### Pendiente / decisiones para retomar

- [ ] **Verificar en hardware real**: comparar una lectura en vivo de `app.py` (todos los campos, no solo velocidad) contra el panel "Main" del software WitMotion para confirmar que los números coinciden.
- [ ] Si existe un archivo `serial_config.json` guardado con la escala vieja (100.0), hay que borrarlo o cambiar el selector "Divisor de Escala" manualmente en la app para que tome el valor nuevo (1.0).
- [ ] **`web_hidro_pro.py` tiene un bug distinto, sin corregir**: lee los registros 0x3D-0x3F pensando que es velocidad, pero esos registros son en realidad los ángulos Roll/Pitch/Yaw (no vibración). Si ese archivo está en uso en producción, hay que corregirlo aparte.
- [ ] Revisar si `monitor_realtime.py` tiene el mismo bug de escala (divide por `sensor_scale` igual que `app.py`) — no se tocó en esta sesión. Tampoco lee los campos nuevos (Aceleración, Vel. angular, Desplazamiento, etc.).
- [ ] Confirmar en hardware si `sensor.read_registers()` en bloque (19 registros de una vez) funciona igual de bien que las lecturas individuales que ya estaban probadas — en teoría es más rápido y confiable (menos transacciones por el bus RS-485), pero conviene validarlo con el sensor real conectado.

## Nota sobre cómo funciona el trabajo con Claude (Cowork)

- Cada conversación tiene un límite de contexto; si se hace muy larga, Claude puede "olvidar" el detalle de lo investigado al principio.
- Este archivo (`ESTADO_PROYECTO.md`) sirve para que, en una conversación nueva, puedas decir algo como *"lee ESTADO_PROYECTO.md y seguimos con lo pendiente"* y Claude recupere el contexto sin tener que volver a investigar todo desde cero.
- Conviene actualizar este archivo cada vez que se cierre un tema importante (bug corregido, decisión tomada, pendiente nuevo).

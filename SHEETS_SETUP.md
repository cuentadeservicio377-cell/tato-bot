# Google Sheets — Control de Expedientes Tato

## 1. Crear la hoja

1. Ir a [Google Sheets](https://sheets.google.com)
2. Crear nueva hoja → nombrarla **"Control Expedientes Tato"**
3. Copiar el **ID de la hoja** del URL: `https://docs.google.com/spreadsheets/d/**[ESTE ES EL ID]**/edit`
4. Renombrar la pestaña inferior a: `Expedientes`

## 2. Agregar headers en fila 1

En fila 1, columnas A–L, escribir exactamente:

| Col | Header |
|-----|--------|
| A | Número |
| B | Juzgado |
| C | Cliente |
| D | Tipo |
| E | Etapa |
| F | Último acuerdo (fecha) |
| G | Último acuerdo (texto) |
| H | Próximo término |
| I | Fatal |
| J | Estado |
| K | Notas |
| L | Última actualización |

## 3. Formato condicional (opcional pero útil)

**Columna I (Fatal):**
- Seleccionar columna I → Formato → Formato condicional
- Regla: "El texto es exactamente" → `SÍ`
- Color de fondo: rojo

**Columna J (Estado):**
- Seleccionar columna J → Formato → Formato condicional
- Regla: "El texto es exactamente" → `activo`
- Color de fondo: verde claro

## 4. Compartir con el bot

1. Botón **Compartir** en Google Sheets
2. Agregar el email de la cuenta de Google conectada al bot (la misma OAuth)
3. Permisos: **Editor**

## 5. Configurar variables de entorno

En `.env` (local) o en Railway (producción):

```env
SHEETS_EXPEDIENTES_ID=el_id_copiado_del_paso_1
SHEETS_EXPEDIENTES_RANGE=Expedientes!A:L
```

## 6. Cargar expedientes existentes

Una vez configurado, puedes cargar los expedientes de dos formas:

**Opción A — Desde Telegram:**
```
/nuevo_expediente 2-10 Primero Mercantil Carlos Álvarez mercantil alegatos
```

**Opción B — Llenar Sheets manualmente:**
Llenar las filas en Google Sheets con los datos existentes.
El bot usará el número de fila como referencia para actualizaciones futuras.
Asignar el número de fila en el campo `sheets_row` en la DB si se agrega manualmente.

## 7. Estructura de una fila completa

```
A: 2-10
B: Primero Mercantil
C: Carlos Álvarez
D: mercantil
E: alegatos
F: 2026-03-05 (fecha del último acuerdo)
G: Abre etapa de alegatos (texto del acuerdo)
H: 2026-03-07 (próximo término)
I: SÍ (o NO)
J: activo
K: falta copia de todo
L: 2026-03-05T22:00:00 (timestamp automático)
```

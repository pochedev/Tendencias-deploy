# 🤖 Bot de Terminal — Cerebro Institucional

Un asistente de inteligencia artificial de línea de comandos que responde preguntas **exclusivamente** basándose en tus documentos oficiales. Impulsado por **Google Gemini 2.5 Flash**.

---

## 📋 Tabla de Contenidos

- [Requisitos](#-requisitos)
- [Instalación](#-instalación)
- [Cómo Usar](#-cómo-usar)
- [Estructura de Carpetas](#-estructura-de-carpetas)
- [Flujo del Programa](#-flujo-del-programa)
- [Limitaciones](#-limitaciones)

---

## 🛠️ Requisitos

- **Python 3.10 o superior** instalado en tu computadora.
- Una **cuenta de Google** para obtener la clave de API gratuita.
- Conexión a Internet activa durante el uso.

---

## ⚙️ Instalación

Sigue estos pasos **una sola vez** para preparar el entorno:

**1.** Abre una terminal (PowerShell) en la carpeta del proyecto.

**2.** Crea el entorno virtual e instala las dependencias:
```powershell
python3 -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

**3.** Obtén tu clave de API gratuita en [Google AI Studio](https://aistudio.google.com/app/apikey).

**4.** Abre el archivo `.env` y reemplaza el texto de ejemplo con tu clave real:
```
GEMINI_API_KEY="AIzaSy...tu_clave_aqui..."
```

**5.** Crea la carpeta `archivos_maestros` y coloca ahí todos tus documentos `.txt` (ver sección siguiente).

---

## 🚀 Cómo Usar

### Iniciar el bot
```powershell
.\venv\Scripts\python terminal_bot.py
```

### Durante la conversación
- Escribe tu pregunta directamente en la terminal y presiona **Enter**.
- El bot procesará la pregunta y te devolverá una respuesta basada en tus documentos.
- Para cerrar el programa escribe `salir` (o `exit` / `quit`) y presiona **Enter**.
- También puedes presionar **Ctrl + C** en cualquier momento para forzar el cierre.

### Ejemplo de sesión
```
Tú: ¿Cuáles son los pasos del Módulo 1?
Bot: (pensando...)
Bot: Según el documento 'pensum.txt', los pasos del Módulo 1 son...

Tú: ¿Cuánto cuesta una pizza?
Bot: Lo siento, no dispongo de esa información en mis documentos oficiales.

Tú: salir
Bot: ¡Hasta luego! Que tengas un excelente día.
```

---

## 📁 Estructura de Carpetas

Organiza tus documentos dentro de la carpeta `archivos_maestros`. El bot escaneará **todas las subcarpetas** de forma automática.

```
Tendencias/
│
├── archivos_maestros/           ← TUS DOCUMENTOS VAN AQUÍ
│   ├── finanzas/
│   │     ├── estado_financiero.txt
│   │     └── dashboard.txt
│   ├── base_de_datos/
│   │     └── pensum_bd.txt
│   └── construccion/
│         └── diseno_basico.txt
│
├── venv/                        (entorno virtual, no tocar)
├── terminal_bot.py              (código principal del bot)
├── requirements.txt             (lista de librerías)
└── .env                         (tu clave de API — ¡no compartir!)
```

> **Nota:** El bot solo lee archivos con extensión `.txt` o archivos sin extensión. Los PDFs no son soportados directamente (ver Limitaciones).

---

## 🔄 Flujo del Programa

Así es exactamente cómo funciona el programa desde que lo ejecutas hasta que recibes una respuesta:

```
INICIO
  │
  ▼
[1] Verificación de API Key
    └── Lee el archivo .env y comprueba que la clave de Gemini exista.
        Si no existe → muestra error y cierra.
  │
  ▼
[2] Escaneo de Archivos (Módulo 1 → Biblioteca)
    └── Recorre recursivamente la carpeta archivos_maestros/ buscando
        todos los archivos .txt y los lista en pantalla.
        Si la carpeta no existe o está vacía → muestra error y cierra.
  │
  ▼
[3] Subida a Gemini (File API)
    └── Sube cada archivo uno por uno a los servidores seguros de Google.
        Cada archivo queda referenciado internamente con un ID único.
        Los archivos subidos expiran automáticamente después de 48 horas.
  │
  ▼
[4] Configuración del "Filtro de Verdad" (System Prompt)
    └── Se envía una instrucción inicial al modelo que le dice:
        "Solo puedes responder usando los documentos adjuntos."
        Esto evita que la IA invente información (alucinaciones).
  │
  ▼
[5] Creación del Chat con Contexto
    └── Se inicia una sesión de chat con Gemini 2.5 Flash y se le
        entregan referencias de todos los archivos subidos como
        "memoria" inicial de la conversación.
  │
  ▼
[6] Bucle de Conversación (Chat)
    └── El programa entra en un ciclo donde:
        a. Muestra "Tú: " y espera tu pregunta.
        b. Envía tu pregunta a Gemini junto con el historial del chat.
        c. Gemini busca en los documentos y redacta una respuesta.
        d. Imprime la respuesta en pantalla.
        e. Repite desde (a) hasta que escribas 'salir'.
  │
  ▼
FIN
```

---

## ⚠️ Limitaciones

### De la Herramienta (Gemini File API)
| Limitación | Detalle |
|---|---|
| **Expiración de archivos** | Los archivos subidos a Gemini se eliminan automáticamente después de **48 horas**. Cada vez que reinicies el bot, los vuelve a subir. |
| **Tamaño máximo por archivo** | Cada archivo `.txt` no debe superar **~500,000 palabras** aproximadamente. |
| **Número de archivos** | La API de Gemini permite subir hasta **~3,000 archivos** activos simultáneamente. Para uso normal esto no es un problema. |
| **Formatos soportados** | Solo `.txt` y archivos de texto plano. No lee `.pdf`, `.docx`, `.xlsx` directamente en esta versión. |

### De la Inteligencia Artificial
| Limitación | Detalle |
|---|---|
| **Ventana de contexto** | Si el total de todos tus documentos es extremadamente grande (millones de palabras), el modelo puede no leerlos todos a la vez. Para uso institucional normal esto no aplica. |
| **No es infalible** | Aunque configuramos el "Filtro de Verdad", en casos muy excepcionales el modelo podría interpretar información de forma incorrecta. Siempre verifica respuestas críticas contra el documento original. |
| **Sin memoria entre sesiones** | Al cerrar el programa con `salir`, la conversación se pierde. Si lo reinicias, el bot no recuerda lo que hablaron antes. |

### Del Entorno
| Limitación | Detalle |
|---|---|
| **Requiere Internet** | El bot no funciona sin conexión, ya que se comunica con los servidores de Google en tiempo real. |
| **Clave de API** | La clave gratuita de Google AI Studio tiene un límite de solicitudes por minuto. Para uso intensivo o comercial, se necesita una cuenta de pago. |
| **Sin interfaz gráfica** | Esta versión funciona únicamente en la terminal. No tiene interfaz web ni de aplicación móvil en esta etapa. |

---

## 📞 Para actualizar los documentos

Si añades o modificas archivos `.txt` en la carpeta `archivos_maestros`, **simplemente reinicia el bot**. Al arrancar de nuevo, escaneará y subirá automáticamente los archivos actualizados.

```powershell
.\venv\Scripts\python terminal_bot.py
```
---

## Web App

Se crearon los siguientes archivos:

web_app.py — Servidor Flask que inicializa el bot con la misma lógica de terminal_bot.py y expone endpoints: GET / (UI), POST /api/chat (enviar mensaje), GET /api/status (estado del bot)
templates/index.html — Interfaz de chat moderna con indicador de escritura, estado de conexión y diseño responsive
requirements.txt — Se agregó flask como dependencia
Para ejecutar la web app:

.\venv\Scripts\python.exe web_app.py
Luego abre http://localhost:5000 en el navegador. El bot cargará los documentos de archivos_maestros/ en segundo plano y la UI mostrará el estado "Listo" cuando termine.
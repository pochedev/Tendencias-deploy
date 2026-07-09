# 🤖 CoreDB AI — Cerebro Institucional

Un asistente de inteligencia artificial que responde preguntas **exclusivamente** basándose en tus documentos oficiales y que incluye herramientas avanzadas de asistencia de código. Impulsado por **Google Gemini 2.5 Flash**.

---

## 📋 Tabla de Contenidos

- [Requisitos](#-requisitos)
- [Instalación](#-instalación)
- [Cómo Usar](#-cómo-usar)
- [Características de la Interfaz Web](#-características-de-la-interfaz-web)
- [Estructura de Carpetas](#-estructura-de-carpetas)
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
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

**3.** Obtén tu clave de API gratuita en [Google AI Studio](https://aistudio.google.com/app/apikey).

**4.** Abre el archivo `.env` y reemplaza el texto de ejemplo con tu clave real:
```
GEMINI_API_KEY="AIzaSy...tu_clave_aqui..."
```

**5.** Crea la carpeta `archivos_maestros` y coloca ahí todos tus documentos `.txt`.

---

## 🚀 Cómo Usar

Puedes ejecutar este asistente de dos formas distintas: a través de una moderna **Interfaz Web** o de forma rápida en la **Terminal**.

### Opción 1: Interfaz Web (Recomendado)
Ofrece una experiencia gráfica completa con historial, subida de imágenes y herramientas gráficas.

**Iniciar el servidor web:**
```powershell
.\venv\Scripts\python web_app.py
```
- Luego, abre tu navegador web y visita: `http://localhost:5000`
- El sistema cargará los documentos en segundo plano y te avisará cuando esté listo para chatear.

### Opción 2: Modo Terminal (Clásico)
Para consultas rápidas desde la consola de comandos.

**Iniciar el bot en terminal:**
```powershell
.\venv\Scripts\python terminal_bot.py
```
- Escribe tu pregunta directamente en la terminal.
- Escribe `salir` para terminar la sesión.

---

## 🌟 Características de la Interfaz Web

La versión Web (`web_app.py`) incluye funcionalidades exclusivas diseñadas para potenciar tu productividad:

- **💬 Historial Multi-Sesión:** 
  Todas tus conversaciones se guardan automáticamente en tu navegador (`localStorage`). Puedes alternar entre chats antiguos desde la sección "Tus Chats" en el menú lateral o crear conversaciones nuevas sin perder información.
  
- **📊 Diagramas ER Interactivos (Mermaid):** 
  Al hacer clic en "Diagramas ER" en el menú izquierdo, el bot generará automáticamente código `Mermaid` a partir de las entidades que le indiques, y la interfaz dibujará un gráfico visual gigante que puedes desplazar.

- **👁️ Análisis de Imágenes (Visión Artificial):** 
  Usando el botón del clip (📎) situado junto al cuadro de texto, puedes subir cualquier imagen (por ejemplo, diagramas dibujados a mano, capturas de pantalla de errores) para que la inteligencia artificial los lea, analice y te responda en consecuencia.

- **🌙 Modo Oscuro / Claro:** 
  Un interruptor animado en la parte superior derecha para ajustar la interfaz según tus preferencias.

---

## 📁 Estructura de Carpetas

Organiza tus documentos dentro de la carpeta `archivos_maestros`. El bot escaneará **todas las subcarpetas** de forma automática.

```
Tendencias/
│
├── archivos_maestros/           ← TUS DOCUMENTOS VAN AQUÍ
│   ├── finanzas/
│   └── base_de_datos/
│
├── venv/                        (entorno virtual)
├── web_app.py                   (servidor Flask y backend de la Web)
├── terminal_bot.py              (código principal del modo consola)
├── templates/
│   └── index.html               (diseño y programación del frontend)
├── requirements.txt             (lista de librerías, incluyendo Flask)
└── .env                         (tu clave de API)
```

---

## ⚠️ Limitaciones

- **Expiración de archivos:** Los archivos subidos a Gemini se eliminan automáticamente después de 48 horas. Al iniciar el servidor, los vuelve a subir.
- **Tamaño y formato:** Solo soporta `.txt` nativamente para el contexto masivo inicial.
- **Sin memoria de contexto entre sesiones en Backend:** Aunque la interfaz web guarda el historial visual en pantalla, si reinicias el servidor (`web_app.py`), la IA pierde el "contexto profundo" de la charla anterior.
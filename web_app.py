import os
import sys
import time
import base64
from dotenv import load_dotenv
from google import genai
from google.genai import types
from flask import Flask, request, jsonify, render_template

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY or API_KEY == "AQUI_PONDREMOS_TU_CLAVE":
    print("Error: No se ha configurado la API Key de Gemini.")
    print("Por favor, abre el archivo .env y coloca tu clave generada en Google AI Studio.")
    sys.exit(1)

try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    print(f"Error al inicializar el cliente de Gemini: {e}")
    sys.exit(1)

CARPETA_BIBLIOTECA = "archivos_maestros"
EXTENSIONES_VALIDAS = ['.txt', '']

app = Flask(__name__)

# --- Estado global (se reinicia en cada Cold Start de Vercel) ---
chat = None
bot_ready = False
init_message = "Esperando primera petición..."

system_instruction = (
    "Eres un asistente institucional, experto en bases de datos y diagramación. "
    "Tu principal fuente de verdad teórica son los documentos que se te han proporcionado. "
    "SIN EMBARGO, si el usuario te pide que generes algo práctico (como un diagrama Mermaid, código SQL, "
    "ejemplos o modelos de entidades) basándose en parámetros que él mismo te dé (por ejemplo: 'casa, carro, hombre'), "
    "DEBES utilizar tus conocimientos generales para generar el diagrama o código solicitado sin dudarlo. "
    "Solamente aplica la regla de restricción cuando te hagan preguntas puramente teóricas que no estén en tus archivos. "
    "En esos casos teóricos estrictos, responde: 'Lo siento, no dispongo de esa información en mis documentos oficiales.'"
)


def encontrar_archivos(carpeta_raiz):
    archivos_encontrados = []
    if not os.path.isdir(carpeta_raiz):
        return archivos_encontrados
    for raiz, subdirs, archivos in os.walk(carpeta_raiz):
        for nombre_archivo in archivos:
            _, extension = os.path.splitext(nombre_archivo)
            if extension.lower() in EXTENSIONES_VALIDAS:
                ruta_completa = os.path.join(raiz, nombre_archivo)
                archivos_encontrados.append(ruta_completa)
    return archivos_encontrados


def crear_chat_con_archivos(archivos_gemini):
    """Crea la sesión de chat usando archivos que ya existen en Gemini."""
    global chat, bot_ready, init_message
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.0
    )
    partes_archivos = [
        types.Part.from_uri(file_uri=f.uri, mime_type=f.mime_type)
        for f in archivos_gemini
    ]
    history_inicial = [
        types.Content(
            role="user",
            parts=partes_archivos + [types.Part.from_text(text="Estos son todos los documentos. Tenlos en cuenta para responder.")]
        ),
        types.Content(
            role="model",
            parts=[types.Part.from_text(text="Entendido. Listo para responder.")]
        )
    ]
    chat = client.chats.create(model="gemini-3.5-flash", config=config, history=history_inicial)
    bot_ready = True
    init_message = "Cerebro conectado exitosamente."
    print("[OK] Cerebro conectado exitosamente.", flush=True)


def quick_init():
    """
    Inicialización RÁPIDA al arrancar (module-level / cold start).
    Solo reutiliza archivos que YA existen en Gemini. No sube nada.
    Tarda ~2 segundos. Ideal para Vercel Serverless.
    """
    global init_message
    try:
        local_files = encontrar_archivos(CARPETA_BIBLIOTECA)
        if not local_files:
            init_message = "No hay archivos en archivos_maestros."
            return

        nombres_locales = {os.path.basename(r) for r in local_files}

        # Consultar qué archivos ya existen en Gemini
        archivos_gemini = list(client.files.list())
        archivos_activos = [
            f for f in archivos_gemini
            if f.display_name in nombres_locales and f.state.name == 'ACTIVE'
        ]
        nombres_activos = {f.display_name for f in archivos_activos}

        faltantes = nombres_locales - nombres_activos
        if not faltantes:
            # ¡Todos los archivos están listos en Gemini! Conectar el chat al instante.
            print(f"[QUICK_INIT] Todos los {len(archivos_activos)} archivos encontrados en caché. Conectando...", flush=True)
            crear_chat_con_archivos(archivos_activos)
        else:
            init_message = f"Faltan {len(faltantes)} archivo(s) por subir a Gemini."
            print(f"[QUICK_INIT] Faltan {len(faltantes)} archivos: {faltantes}", flush=True)

    except Exception as e:
        init_message = f"Error en quick_init: {e}"
        print(f"[QUICK_INIT] Error: {e}", flush=True)


def step_upload():
    """
    Sube UN SOLO archivo faltante a Gemini por cada llamada.
    Usa la API de Gemini como fuente de verdad (no variables globales).
    Si ya no faltan archivos, crea el chat y marca bot_ready = True.
    """
    global init_message
    try:
        local_files = encontrar_archivos(CARPETA_BIBLIOTECA)
        if not local_files:
            init_message = "No hay archivos en archivos_maestros."
            return

        nombres_locales = {os.path.basename(r): r for r in local_files}

        # Consultar estado actual en Gemini (fuente de verdad)
        archivos_gemini = list(client.files.list())
        nombres_en_gemini = {}
        for f in archivos_gemini:
            if f.display_name in nombres_locales:
                if f.state.name == 'ACTIVE':
                    nombres_en_gemini[f.display_name] = f
                # Si está PROCESSING, lo dejamos, ya se activará solo
            else:
                # Limpiar archivos huérfanos
                try:
                    client.files.delete(name=f.name)
                except:
                    pass

        # ¿Cuáles faltan?
        faltantes = [name for name in nombres_locales if name not in nombres_en_gemini]

        if not faltantes:
            # ¡Todo listo! Crear el chat
            archivos_activos = list(nombres_en_gemini.values())
            init_message = "Conectando Cerebro..."
            print(f"[STEP] Todos los archivos listos. Creando chat...", flush=True)
            crear_chat_con_archivos(archivos_activos)
            return

        # Subir SOLO el primero de la lista de faltantes
        nombre_a_subir = faltantes[0]
        ruta = nombres_locales[nombre_a_subir]
        restantes = len(faltantes) - 1
        init_message = f"Subiendo: {nombre_a_subir} ({restantes} restantes)..."
        print(f"[STEP] {init_message}", flush=True)

        uploaded = client.files.upload(
            file=ruta,
            config={'display_name': nombre_a_subir, 'mime_type': 'text/plain'}
        )

        # Esperar brevemente a que se active (máx 5 segundos)
        retries = 0
        while uploaded.state.name == 'PROCESSING' and retries < 5:
            time.sleep(1)
            uploaded = client.files.get(name=uploaded.name)
            retries += 1

        if uploaded.state.name == 'ACTIVE':
            print(f"[STEP] '{nombre_a_subir}' subido OK.", flush=True)
        else:
            print(f"[STEP] '{nombre_a_subir}' aún procesando (se verificará en la siguiente llamada).", flush=True)

    except Exception as e:
        init_message = f"Error subiendo archivo: {e}"
        print(f"[STEP] Error: {e}", flush=True)


# ====================================================================
# INICIALIZACIÓN RÁPIDA AL ARRANCAR (Cold Start de Vercel)
# Si los archivos ya están en Gemini, el bot estará listo en ~2 segundos.
# ====================================================================
quick_init()


# ====================================================================
# RUTAS DE LA APLICACIÓN FLASK
# ====================================================================

@app.route('/')
def index():
    return render_template('index.html', bot_ready=bot_ready)


@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    global chat, bot_ready

    if not bot_ready:
        # Intentar quick_init por si ya están los archivos
        quick_init()

    if not bot_ready or chat is None:
        return jsonify({'error': f'El bot aún se está configurando. Estado: {init_message}'}), 503

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Datos inválidos'}), 400

    user_message = data.get('message', '').strip()
    image_base64 = data.get('image', None)

    if not user_message and not image_base64:
        return jsonify({'error': 'Mensaje vacío'}), 400

    content_list = []
    if user_message:
        content_list.append(user_message)

    if image_base64:
        try:
            # image_base64 formato esperado: "data:image/jpeg;base64,/9j/4AAQSk..."
            header, encoded = image_base64.split(',', 1)
            mime_type = header.split(':')[1].split(';')[0]
            image_bytes = base64.b64decode(encoded)

            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            content_list.append(image_part)
        except Exception as e:
            print("Error procesando imagen adjunta:", e)
            return jsonify({'error': 'Error procesando la imagen adjunta.'}), 400

    try:
        response = chat.send_message(content_list)
        return jsonify({'response': response.text})
    except Exception as e:
        print("Error en chat.send_message:", e)
        return jsonify({'error': str(e)}), 500


@app.route('/api/status', methods=['GET'])
def status():
    global bot_ready

    if not bot_ready:
        # Avanzar un paso: subir 1 archivo o crear el chat
        step_upload()

    return jsonify({
        'ready': bot_ready,
        'message': init_message,
        'docs_folder_exists': os.path.isdir(CARPETA_BIBLIOTECA)
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

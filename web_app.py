import os
import sys
import time
import threading
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
chat = None
bot_ready = False

system_instruction = (
    "Eres un asistente institucional y profesional. Tu única fuente de verdad son los documentos "
    "que se te han proporcionado. Cuando respondas, sé claro, amable y conciso. "
    "REGLA DE ORO: Responde ÚNICAMENTE basándote en la información de los documentos adjuntos. "
    "Si la información solicitada no se encuentra en ninguno de los documentos, responde exactamente: "
    "'Lo siento, no dispongo de esa información en mis documentos oficiales.' "
    "NO inventes datos ni uses conocimiento externo. "
    "Cuando sea posible, indica de qué documento proviene la información."
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


def initialize_bot():
    global chat, bot_ready
    print("=" * 55)
    print("  Inicializando el Cerebro del Bot (web_app)")
    print("=" * 55)

    if not os.path.isdir(CARPETA_BIBLIOTECA):
        print(f"\n[!] No se encontró la carpeta '{CARPETA_BIBLIOTECA}'.")
        bot_ready = False
        return

    lista_rutas = encontrar_archivos(CARPETA_BIBLIOTECA)
    if not lista_rutas:
        print(f"[!] No se encontraron archivos .txt dentro de '{CARPETA_BIBLIOTECA}'.")
        bot_ready = False
        return

    print(f"\n[1/3] Escaneando carpeta: {len(lista_rutas)} archivo(s) encontrados.")
    for ruta in lista_rutas:
        print(f"       - {ruta}")

    print(f"\n[2/3] Subiendo archivos a Gemini...")
    archivos_subidos = []
    for i, ruta in enumerate(lista_rutas, start=1):
        nombre = os.path.basename(ruta)
        print(f"     Subiendo {i}/{len(lista_rutas)}: '{nombre}'...", end=" ")
        try:
            uploaded = client.files.upload(
                file=ruta,
                config={'display_name': nombre, 'mime_type': 'text/plain'}
            )
            while uploaded.state.name == 'PROCESSING':
                time.sleep(1)
                uploaded = client.files.get(name=uploaded.name)
            if uploaded.state.name == 'FAILED':
                print(f"FALLÓ (se omite)")
            else:
                archivos_subidos.append(uploaded)
                print("✓ OK")
        except Exception as e:
            print(f"ERROR: {e} (se omite)")

    if not archivos_subidos:
        print("[!] Ningún archivo pudo ser subido.")
        bot_ready = False
        return

    print(f"\n     ✓ {len(archivos_subidos)}/{len(lista_rutas)} archivo(s) subidos.")

    print(f"\n[3/3] Conectando Cerebro con la Biblioteca...")
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.0
    )
    chat = client.chats.create(model="gemini-2.5-flash", config=config)

    mensaje_inicial = archivos_subidos + [
        "Estos son todos los documentos maestros de la institución. "
        "Léelos y tenlos todos en cuenta para responder mis futuras preguntas."
    ]
    chat.send_message(mensaje_inicial)
    bot_ready = True
    print("     ✓ Cerebro conectado exitosamente.\n")


@app.route('/')
def index():
    return render_template('index.html', bot_ready=bot_ready)


@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    global chat, bot_ready
    if not bot_ready or chat is None:
        return jsonify({'error': 'El bot no está listo. Revisa que exista la carpeta archivos_maestros con archivos .txt.'}), 503

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
    return jsonify({
        'ready': bot_ready,
        'docs_folder_exists': os.path.isdir(CARPETA_BIBLIOTECA)
    })


def start_bot_in_background():
    thread = threading.Thread(target=initialize_bot, daemon=True)
    thread.start()


if __name__ == '__main__':
    start_bot_in_background()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

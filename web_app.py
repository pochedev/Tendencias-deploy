import os
import sys
import time
import base64
import threading
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
is_initializing = False

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

def ensure_bot_initialized():
    global chat, bot_ready, is_initializing
    if bot_ready or is_initializing:
        return
    
    is_initializing = True
    threading.Thread(target=background_initialization, daemon=True).start()

def background_initialization():
    global chat, bot_ready, is_initializing
    import traceback
    try:
        print("=" * 55)
        print("  Inicializando el Cerebro del Bot (Vercel Serverless)")
        print("=" * 55)

        if not os.path.isdir(CARPETA_BIBLIOTECA):
            print(f"\n[!] No se encontro la carpeta '{CARPETA_BIBLIOTECA}'.")
            is_initializing = False
            return

        lista_rutas = encontrar_archivos(CARPETA_BIBLIOTECA)
        if not lista_rutas:
            print(f"[!] No se encontraron archivos .txt dentro de '{CARPETA_BIBLIOTECA}'.")
            is_initializing = False
            return

        # Vercel Optimization: Reutilizar archivos ya subidos en Gemini en vez de borrar todo incondicionalmente
        print(f"\n[1/3] Revisando caché en Gemini para {len(lista_rutas)} archivo(s)...")
        archivos_subidos = []
        nombres_locales = {os.path.basename(ruta): ruta for ruta in lista_rutas}
        
        try:
            archivos_existentes = list(client.files.list())
            for f in archivos_existentes:
                if f.display_name in nombres_locales:
                    print(f"     [CACHE] Archivo reutilizado: '{f.display_name}'")
                    archivos_subidos.append(f)
                    del nombres_locales[f.display_name] # Ya está subido, lo quitamos de pendientes
                else:
                    # Limpiar basura antigua que ya no está en la carpeta local
                    try:
                        client.files.delete(name=f.name)
                    except:
                        pass
        except Exception as e:
            print(f"     [!] Error leyendo caché: {e}")

        archivos_pendientes = list(nombres_locales.values())
        if archivos_pendientes:
            print(f"\n[2/3] Subiendo {len(archivos_pendientes)} archivos nuevos a Gemini...")
            for i, ruta in enumerate(archivos_pendientes, start=1):
                nombre = os.path.basename(ruta)
                print(f"     Subiendo {i}/{len(archivos_pendientes)}: '{nombre}'...", end=" ", flush=True)
                try:
                    uploaded = client.files.upload(
                        file=ruta,
                        config={'display_name': nombre, 'mime_type': 'text/plain'}
                    )
                    while uploaded.state.name == 'PROCESSING':
                        time.sleep(1)
                        uploaded = client.files.get(name=uploaded.name)
                    if uploaded.state.name == 'FAILED':
                        print("FALLO (se omite)")
                    else:
                        archivos_subidos.append(uploaded)
                        print("[OK]", flush=True)
                except Exception as e:
                    print(f"ERROR: {e} (se omite)", flush=True)
        else:
             print(f"\n[2/3] Ningún archivo nuevo para subir, todos están en caché.")

        if not archivos_subidos:
            print("[!] Ningun archivo pudo ser cargado. Bot NO listo.")
            is_initializing = False
            return

        print(f"\n[3/3] Conectando Cerebro con la Biblioteca...", flush=True)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.0
        )
        partes_archivos = [types.Part.from_uri(file_uri=f.uri, mime_type=f.mime_type) for f in archivos_subidos]
        
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
        print("     [OK] Cerebro conectado exitosamente.\n", flush=True)

    except Exception as fatal:
        print("\n\n=== ERROR FATAL EN ensure_bot_initialized ===", flush=True)
        traceback.print_exc()
        print("=====================================\n", flush=True)
        bot_ready = False
    finally:
        is_initializing = False

@app.route('/')
def index():
    return render_template('index.html', bot_ready=bot_ready)

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    global chat, bot_ready
    ensure_bot_initialized()
    
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
    ensure_bot_initialized()
    return jsonify({
        'ready': bot_ready,
        'docs_folder_exists': os.path.isdir(CARPETA_BIBLIOTECA)
    })

if __name__ == '__main__':
    # Ejecución local: Inicialización perezosa se encarga de todo.
    app.run(host='0.0.0.0', port=5000, debug=False)

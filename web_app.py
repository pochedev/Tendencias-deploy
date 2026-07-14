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
chat = None

# Variables de la Maquina de Estados para Chunking
bot_ready = False
init_phase = 0 
archivos_pendientes = []
archivos_subidos = []
init_message = "Iniciando..."

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

def advance_initialization_step():
    """ 
    Avanza un único paso de la inicialización cada vez que se llama.
    Ideal para ser invocado desde /api/status y evitar Timeouts en Serverless.
    """
    global bot_ready, init_phase, archivos_pendientes, archivos_subidos, init_message, chat
    import traceback
    
    if bot_ready or init_phase == 4:
        return

    try:
        if init_phase == 0:
            if not os.path.isdir(CARPETA_BIBLIOTECA):
                init_message = f"Error: No se encontro la carpeta '{CARPETA_BIBLIOTECA}'."
                init_phase = 4
                return
            
            lista_rutas = encontrar_archivos(CARPETA_BIBLIOTECA)
            if not lista_rutas:
                init_message = f"Error: No se encontraron archivos .txt."
                init_phase = 4
                return
                
            archivos_pendientes = lista_rutas
            archivos_subidos = []
            init_message = "Revisando caché en Gemini..."
            init_phase = 1
            print(f"[{init_phase}] {init_message}", flush=True)
            return

        if init_phase == 1:
            nombres_locales = {os.path.basename(ruta): ruta for ruta in archivos_pendientes}
            try:
                archivos_existentes = list(client.files.list())
                for f in archivos_existentes:
                    if f.display_name in nombres_locales:
                        archivos_subidos.append(f)
                        del nombres_locales[f.display_name]
                    else:
                        try: client.files.delete(name=f.name)
                        except: pass
            except Exception as e:
                print("Error de cache:", e)

            archivos_pendientes = list(nombres_locales.values())
            
            if archivos_pendientes:
                init_message = f"Preparando subida de {len(archivos_pendientes)} archivos..."
                init_phase = 2
            else:
                init_message = "Todos los archivos estaban en caché."
                init_phase = 3
            print(f"[{init_phase}] {init_message}", flush=True)
            return

        if init_phase == 2:
            if archivos_pendientes:
                ruta = archivos_pendientes.pop(0)
                nombre = os.path.basename(ruta)
                init_message = f"Subiendo: {nombre} ({len(archivos_pendientes)} restantes)..."
                print(f"[{init_phase}] {init_message}", flush=True)
                
                uploaded = client.files.upload(
                    file=ruta,
                    config={'display_name': nombre, 'mime_type': 'text/plain'}
                )
                
                retries = 0
                while uploaded.state.name == 'PROCESSING' and retries < 4:
                    time.sleep(1)
                    uploaded = client.files.get(name=uploaded.name)
                    retries += 1
                    
                if uploaded.state.name != 'FAILED':
                    archivos_subidos.append(uploaded)
                    
                if not archivos_pendientes:
                    init_phase = 3 
                return

        if init_phase == 3:
            if not archivos_subidos:
                init_message = "Error: Ningún archivo pudo ser cargado."
                init_phase = 4
                return
                
            init_message = "Conectando Cerebro con la Biblioteca..."
            print(f"[{init_phase}] {init_message}", flush=True)
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0
            )
            
            # Filtrar por seguridad
            partes_archivos = [types.Part.from_uri(file_uri=f.uri, mime_type=f.mime_type) for f in archivos_subidos if f.state.name != 'PROCESSING']
            
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
            print(f"[OK] {init_message}", flush=True)
            return

    except Exception as e:
        traceback.print_exc()
        init_message = f"Error crítico: {e}"
        init_phase = 4


@app.route('/')
def index():
    return render_template('index.html', bot_ready=bot_ready)


@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    global chat, bot_ready
    
    if not bot_ready:
        advance_initialization_step()
    
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
    # Impulsa la carga un archivo a la vez impulsado por el PING del front-end
    advance_initialization_step()
    
    return jsonify({
        'ready': bot_ready,
        'message': init_message,
        'docs_folder_exists': os.path.isdir(CARPETA_BIBLIOTECA)
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

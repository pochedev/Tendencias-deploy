import os
import sys
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ============================================================
# CONFIGURACIÓN PRINCIPAL
# Coloca todos tus .txt en subcarpetas dentro de esta carpeta.
# ============================================================
CARPETA_BIBLIOTECA = "archivos_maestros"

# Extensiones de archivo que el bot buscará y leerá
EXTENSIONES_VALIDAS = ['.txt', '']  # '' cubre archivos sin extensión como "Consideracion"

# ============================================================

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


def encontrar_archivos(carpeta_raiz):
    """Busca recursivamente todos los archivos válidos en la carpeta y subcarpetas."""
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


def setup_bot():
    print("=" * 55)
    print("  Inicializando el Cerebro del Bot (google-genai SDK)")
    print("=" * 55)

    # 1. Verificar que la carpeta biblioteca existe
    if not os.path.isdir(CARPETA_BIBLIOTECA):
        print(f"\n[!] No se encontró la carpeta '{CARPETA_BIBLIOTECA}'.")
        print(f"    Por favor, crea la carpeta '{CARPETA_BIBLIOTECA}' dentro de:")
        print(f"    {os.path.abspath('.')}")
        print(f"    y coloca ahí tus archivos .txt (en subcarpetas o directamente).")
        sys.exit(1)

    # 2. Buscar todos los archivos válidos
    print(f"\n[1/3] Escaneando la carpeta '{CARPETA_BIBLIOTECA}'...")
    lista_rutas = encontrar_archivos(CARPETA_BIBLIOTECA)

    if not lista_rutas:
        print(f"[!] No se encontraron archivos .txt dentro de '{CARPETA_BIBLIOTECA}'.")
        print(f"    Asegúrate de haber colocado tus archivos ahí.")
        sys.exit(1)

    print(f"     ✓ Se encontraron {len(lista_rutas)} archivo(s):")
    for ruta in lista_rutas:
        print(f"       - {ruta}")

    # 3. Subir todos los archivos a la File API de Gemini
    print(f"\n[2/3] Subiendo archivos a la Biblioteca de Gemini...")
    archivos_subidos = []

    for i, ruta in enumerate(lista_rutas, start=1):
        nombre = os.path.basename(ruta)
        print(f"     Subiendo archivo {i}/{len(lista_rutas)}: '{nombre}'...", end=" ")
        try:
            uploaded = client.files.upload(
                file=ruta,
                config={
                    'display_name': nombre,
                    'mime_type': 'text/plain'
                }
            )
            # Esperar a que el archivo sea procesado
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
        print("[!] Ningún archivo pudo ser subido. Verifica tu conexión y clave de API.")
        sys.exit(1)

    print(f"\n     ✓ {len(archivos_subidos)}/{len(lista_rutas)} archivo(s) subidos correctamente.")

    # 4. Configurar el System Prompt (El Filtro de Verdad)
    system_instruction = (
        "Eres un asistente institucional y profesional. Tu única fuente de verdad son los documentos "
        "que se te han proporcionado. Cuando respondas, sé claro, amable y conciso. "
        "REGLA DE ORO: Responde ÚNICAMENTE basándote en la información de los documentos adjuntos. "
        "Si la información solicitada no se encuentra en ninguno de los documentos, responde exactamente: "
        "'Lo siento, no dispongo de esa información en mis documentos oficiales.' "
        "NO inventes datos ni uses conocimiento externo. "
        "Cuando sea posible, indica de qué documento proviene la información."
    )

    print(f"\n[3/3] Conectando el Cerebro con la Biblioteca ({len(archivos_subidos)} archivos)...")
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.0
    )

    chat = client.chats.create(model="gemini-2.5-flash", config=config)

    # Inyectar todos los archivos como contexto inicial
    mensaje_inicial = archivos_subidos + [
        "Estos son todos los documentos maestros de la institución. "
        "Léelos y tenlos todos en cuenta para responder mis futuras preguntas."
    ]
    chat.send_message(mensaje_inicial)

    print("     ✓ Cerebro conectado exitosamente a todos los documentos.\n")
    return chat


def main():
    chat = setup_bot()
    print("=" * 55)
    print("  ¡Bot listo! Puedes hacerme preguntas.")
    print("  Escribe 'salir' para terminar.")
    print("=" * 55)

    while True:
        try:
            user_input = input("\nTú: ")

            if user_input.lower() in ['salir', 'exit', 'quit']:
                print("\nBot: ¡Hasta luego! Que tengas un excelente día.")
                break

            if not user_input.strip():
                continue

            print("Bot: (pensando...)\n")
            response = chat.send_message(user_input)
            print(f"Bot: {response.text}")

        except KeyboardInterrupt:
            print("\n\nBot: ¡Hasta luego!")
            break
        except Exception as e:
            print(f"\n[Error]: {e}")


if __name__ == "__main__":
    main()

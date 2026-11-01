import os
import io
import time
import wave
import audioop
import queue
import subprocess
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import sounddevice as sd
from groq import Groq
from ddgs import DDGS
import wikipedia
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
VOZ_JARVIS = os.getenv("VOZ_JARVIS", "es-MX-JorgeNeural").strip()

if not GROQ_API_KEY or GROQ_API_KEY == "gsk_PegarAquiTuClaveDeGroq":
    raise ValueError("Error: Configura tu GROQ_API_KEY en el archivo .env antes de iniciar.")

# Parametros acusticos blindados contra ruidos cortos o silencio
FACTOR_CERCANIA = 2.8
UMBRAL_MINIMO = 950
TIEMPO_CONVERSACION = 25

wikipedia.set_lang("es")
cliente_groq = Groq(api_key=GROQ_API_KEY)

q = queue.Queue()
escuchando_activo = True
ultimo_llamado = 0.0

carpeta_docs = os.path.expanduser("~/Documentos") if os.path.exists(os.path.expanduser("~/Documentos")) else os.path.expanduser("~/Documents")
CARPETA_TAREAS = os.path.join(carpeta_docs, "Investigaciones_Jarvis")
os.makedirs(CARPETA_TAREAS, exist_ok=True)

def hablar(texto):
    global escuchando_activo, ultimo_llamado
    escuchando_activo = False
    
    texto_limpio = texto.replace("J.A.R.V.I.S.", "Jarvis").replace("J.A.R.V.I.S", "Jarvis").replace("JARVIS", "Jarvis")
    texto_limpio = texto_limpio.replace('"', '').replace("'", "").replace('*', '').replace('#', '').replace('`', '').replace('\n', ' ').strip()
    print(f"\n[Jarvis]: {texto_limpio}\n")
    
    ruta_edge = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "bin", "edge-tts")
    if not os.path.exists(ruta_edge):
        ruta_edge = "edge-tts"

    comando = (
        f'{ruta_edge} --voice {VOZ_JARVIS} --pitch=-6Hz --rate=+10% '
        f'--text "{texto_limpio}" --write-media respuesta.mp3 && '
        f'mpv --no-video --really-quiet --af="lavfi=[highpass=f=130,aecho=0.8:0.88:8:0.15]" respuesta.mp3'
    )
    res = os.system(comando)
    if res != 0:
        os.system("mpv --no-video --really-quiet respuesta.mp3")
    
    while not q.empty():
        try:
            q.get_nowait()
        except queue.Empty:
            break
    ultimo_llamado = time.time()
    escuchando_activo = True

def transcribir_whisper(fragmentos_pcm):
    try:
        audio_bytes = b"".join(fragmentos_pcm)
        buffer_wav = io.BytesIO()
        with wave.open(buffer_wav, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(audio_bytes)
        buffer_wav.seek(0)
        buffer_wav.name = "orden.wav"

        # Sin 'prompt' para evitar que Whisper alucine y repita la frase guia cuando hay silencio
        transcripcion = cliente_groq.audio.transcriptions.create(
            file=buffer_wav,
            model="whisper-large-v3-turbo",
            language="es",
            temperature=0.0
        )
        return transcripcion.text.strip()
    except Exception as e:
        print(f"[!] Error en Whisper Turbo: {e}")
        return ""

def busqueda_tiempo_real(consulta):
    print(f"[*] Conectando a la red en tiempo real para: '{consulta}'...")
    fecha_hoy = datetime.now().strftime("%Y-%m-%d %H:%M")
    contexto = f"Fecha y hora actual del sistema: {fecha_hoy}\n\n"
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

    try:
        resultados_web = DDGS().text(consulta, region="ar-es", max_results=5)
        if resultados_web:
            contexto += "=== RESULTADOS WEB EN TIEMPO REAL ===\n"
            for r in resultados_web:
                titulo = r.get("title", "")
                cuerpo = r.get("body", "")
                link = r.get("href", "")
                contexto += f"- {titulo}: {cuerpo} (URL: {link})\n"
                try:
                    resp = requests.get(link, headers=headers, timeout=3)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        parrafos = " ".join([p.get_text() for p in soup.find_all("p")[:3]])
                        if len(parrafos) > 80:
                            contexto += f"  Contenido extraido: {parrafos[:500]}...\n"
                except Exception:
                    pass
    except Exception as e:
        print(f"[!] Aviso en busqueda web: {e}")

    try:
        noticias = DDGS().news(consulta, region="ar-es", max_results=3)
        if noticias:
            contexto += "\n=== NOTICIAS RECIENTES ===\n"
            for n in noticias:
                contexto += f"- [{n.get('date', '')}] {n.get('title', '')}: {n.get('body', '')}\n"
    except Exception:
        pass

    try:
        resumen_wiki = wikipedia.summary(consulta, sentences=3)
        contexto += f"\n=== WIKIPEDIA ===\n{resumen_wiki}\n"
    except Exception:
        pass

    return contexto

def consultar_cerebro(prompt, datos_web="", modo_extenso=False):
    instruccion_sistema = (
        "Sos Jarvis, el asistente de inteligencia artificial de Tony Stark en Iron Man. "
        "NUNCA escribas tu nombre con puntos (no uses J.A.R.V.I.S.), escribilo siempre como 'Jarvis'. "
        "Hablas con aplomo, elegancia y precision, tratando al usuario de 'señor'. "
        "Tenes acceso a informacion en tiempo real provista en el contexto. "
        "Si modo_extenso es False, responde en maximo 2 o 3 oraciones fluidas y precisas para ser leidas por voz (sin asteriscos ni simbolos). "
        "Si modo_extenso es True, redacta un informe completo, estructurado y detallado."
    )
    prompt_final = f"{instruccion_sistema}\n\nDatos en tiempo real:\n{datos_web}\n\nModo extenso: {modo_extenso}\nOrden del señor: {prompt}"
    modelos_groq = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]
    
    for mod in modelos_groq:
        try:
            chat = cliente_groq.chat.completions.create(
                messages=[{"role": "user", "content": prompt_final}],
                model=mod,
                temperature=0.4,
            )
            return chat.choices[0].message.content
        except Exception as e:
            print(f"[!] Saltando de {mod}... ({e})")
    return "Señor, los servidores externos no responden en este momento."

def guardar_investigacion(tema, contenido):
    fecha = datetime.now().strftime("%Y%m%d_%H%M")
    nombre_limpio = "".join(c if c.isalnum() else "_" for c in tema)[:30]
    ruta = os.path.join(CARPETA_TAREAS, f"{nombre_limpio}_{fecha}.md")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(f"# Informe Jarvis: {tema.capitalize()}\n\n{contenido}\n")
    return ruta

def procesar_orden(texto_completo):
    global ultimo_llamado
    texto_min = texto_completo.lower()
    
    activadores = ["jarvis", "sharvis", "harvis", "yarvis", "charvis", "j.a.r.v.i.s", "llaves", "gervis", "chavis", "jarvi"]
    llamado_explicito = any(act in texto_min for act in activadores)
    en_ventana_activa = (time.time() - ultimo_llamado) < TIEMPO_CONVERSACION

    if not llamado_explicito and not en_ventana_activa:
        print(f"    [Ignorado - No dijiste 'Jarvis': '{texto_completo}']")
        return

    orden = texto_min
    if llamado_explicito:
        for act in activadores:
            if act in orden:
                orden = orden.split(act, 1)[-1].strip(" ,.:;¿?¡!-")
                break

    if not orden or len(orden) < 2:
        hablar("Jarvis a sus servicios, señor. Dígame qué necesita.")
        return

    print(f"\n[Señor]: {orden}")

    if any(p in orden for p in ["nada más", "nada mas", "eso es todo", "gracias jarvis", "esperá", "espera"]):
        hablar("Siempre a sus servicios, señor. Quedo en espera.")
        ultimo_llamado = 0.0
        return

    if "qué hora es" in orden or "que hora es" in orden:
        hablar(f"Son las {datetime.now().strftime('%H:%M

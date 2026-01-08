# -*- coding: utf-8 -*-
import locale
import logging
import readline
import subprocess
import time
import sys
import os
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, Union
import spacy

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- EXCEPCIÓN PARA REINICIO ---
class ReiniciarAnalisis(Exception):
    """Excepción para abortar el análisis actual y volver al inicio."""
    pass

# Códigos ANSI para formato
NEGRITA = '\033[1m'
RESET = '\033[0m'

# Intentamos cargar el modelo de spaCy. Si falla, el programa funcionará en modo manual.
try:
    nlp = spacy.load("es_core_news_sm")
except OSError:
    nlp = None

class Respuesta(Enum):
    SI = ["sí", "si", "s"]
    NO = ["no", "n"]


class Aktionsart(Enum):
    ESTADO = "estado"
    ESTADO_CAUSATIVO = "estado causativo"
    LOGRO = "logro"
    LOGRO_CAUSATIVO = "logro causativo"
    SEMELFACTIVO = "semelfactivo"
    SEMELFACTIVO_CAUSATIVO = "semelfactivo causativo"
    REALIZACION_ACTIVA = "realización activa"
    REALIZACION_ACTIVA_CAUSATIVA = "realización activa causativa"
    REALIZACION = "realización"
    REALIZACION_CAUSATIVA = "realización causativa"
    ACTIVIDAD = "actividad"
    ACTIVIDAD_CAUSATIVA = "actividad causativa"
    PROCESO = "proceso"
    PROCESO_CAUSATIVO = "proceso causativo"


@dataclass
class RasgosPred:
    causativo: bool = False
    estativo: bool = False
    puntual: bool = False
    telico: bool = False
    dinamico: bool = False

@dataclass
class DatosClause:
    gerundio: str = ""
    participio: str = ""
    infinitivo: str = ""
    sujeto: str = ""
    complementos: str = ""
    persona_numero: str = ""
    rasgos_obtenidos: bool = False


ESTAR = {
    '1s': "estoy", '2s': "estás", '3s': "está",
    '1p': "estamos", '2p': "están/estáis", '3p': "están"
}

ESTAR_PRETERITO = {
    '1s': "estuve", '2s': "estuviste", '3s': "estuvo",
    '1p': "estuvimos", '2p': "estuvieron/estuvisteis", '3p': "estuvieron"
}

ESTAR_SUBJUNTIVO = {
    '1s': "estuviera", '2s': "estuvieras", '3s': "estuviera",
    '1p': "estuviéramos", '2p': "estuvieran/estuvierais", '3p': "estuvieran"
}

HABER = {
    '1s': "he", '2s': "has", '3s': "ha",
    '1p': "hemos", '2p': "han/habeis", '3p': "han"
}

DEJAR = {
    '1s': "dejara", '2s': "dejaras", '3s': "dejara",
    '1p': "dejáramos", '2p': "dejaran/dejarais", '3p': "dejaran"
}

# Diccionario ampliado de irregulares y cambios de raíz (e>i, o>u)
IRREGULARES = {
    # Irregulares puros y participios fuertes
    "abrir": {"pp": "abierto"}, "cubrir": {"pp": "cubierto"},
    "decir": {"ger": "diciendo", "pp": "dicho"}, "escribir": {"pp": "escrito"},
    "hacer": {"pp": "hecho"}, "freír": {"pp": "frito"},
    "imprimir": {"pp": "impreso"}, "morir": {"ger": "muriendo", "pp": "muerto"},
    "poner": {"pp": "puesto"}, "proveer": {"pp": "provisto"},
    "romper": {"pp": "roto"}, "satisfacer": {"pp": "satisfecho"},
    "soltar": {"pp": "suelto"}, "ver": {"pp": "visto"},
    "volver": {"pp": "vuelto"}, "ir": {"ger": "yendo", "pp": "ido"},
    "ser": {"ger": "siendo", "pp": "sido"}, "pudrir": {"pp": "podrido"},
    "leer": {"ger": "leyendo", "pp": "leído"}, "traer": {"ger": "trayendo", "pp": "traído"},
    "caer": {"ger": "cayendo", "pp": "caído"}, "oír": {"ger": "oyendo", "pp": "oído"},
    
    # Cambios vocálicos (e > i) en gerundio
    "pedir": {"ger": "pidiendo"}, "sentir": {"ger": "sintiendo"},
    "mentir": {"ger": "mintiendo"}, "seguir": {"ger": "siguiendo"},
    "conseguir": {"ger": "consiguiendo"}, "perseguir": {"ger": "persiguiendo"},
    "servir": {"ger": "sirviendo"}, "vestir": {"ger": "vistiendo"},
    "repetir": {"ger": "repitiendo"}, "elegir": {"ger": "eligiendo"},
    "corregir": {"ger": "corregiendo"}, "reír": {"ger": "riendo"},
    "sonreír": {"ger": "sonriendo"}, "venir": {"ger": "viniendo"},
    "competir": {"ger": "compitiendo"}, "medir": {"ger": "midiendo"},
    "despedir": {"ger": "despidiendo"}, "impedir": {"ger": "impidiendo"},
    
    # Cambios vocálicos (o > u) en gerundio
    "dormir": {"ger": "durmiendo"}, "poder": {"ger": "pudiendo"}
}


def set_spanish_locale():
    spanish_locales = ['es_ES.UTF-8', 'es_CL.UTF-8', 'es_MX.UTF-8', 'es.UTF-8', '']
    for loc in spanish_locales:
        try:
            return locale.setlocale(locale.LC_ALL, loc)
        except locale.Error:
            continue
    return locale.setlocale(locale.LC_ALL, '')


def limpiar_consola():
    os.system('cls' if os.name == 'nt' else 'clear')


def mensaje_reinicio() -> None:
    print("\nNo es posible identificar el aktionsart de la cláusula con estos parámetros.")
    print("Por favor, revisa con cuidado tus respuestas a las preguntas.")


def peticion(prompt: str) -> str:
    import sys
    readline.set_startup_hook(lambda: readline.insert_text(""))
    try:
        if "\n" in prompt or len(prompt) > 60:
            print(prompt, end="", flush=True)
            user = input().strip()
        else:
            user = input(prompt).strip()
        
        # --- COMANDO DE RESCATE ---
        if user == "...":
            raise ReiniciarAnalisis()
            
        return user.encode('utf-8').decode('utf-8')
    finally:
        readline.set_startup_hook()
        

def respuesta_si_no(pregunta: str) -> bool:
    while True:
        try:
            respuesta = peticion(pregunta).lower()
            if respuesta in Respuesta.SI.value:
                return True
            elif respuesta in Respuesta.NO.value:
                return False
            print("\nPor favor, entrega una respuesta válida: «sí (s)» o «no (n)».")
        except ReiniciarAnalisis:
            raise
        except Exception as e:
            logging.error(f"Error al obtener respuesta: {e}")


def pedir_respuesta_multiple(pregunta: str, opciones: Sequence[Union[str, Sequence[str]]], prompt: str) -> str:
    while True:
        try:
            respuesta = peticion(f"{pregunta} {prompt}").lower()
            for opcion in opciones:
                if isinstance(opcion, Sequence) and not isinstance(opcion, str):
                    if respuesta in opcion:
                        return opcion[0]
                elif respuesta == opcion:
                    return opcion
            print("\nPor favor, escribe una respuesta válida.")
        except ReiniciarAnalisis:
            raise
        except Exception as e:
            logging.error(f"Error al obtener respuesta: {e}")


# --- FUNCIONES DE ANÁLISIS AUTOMÁTICO ---

def generar_formas_verbales(infinitivo):
    """Genera gerundio y participio a partir del infinitivo usando reglas y diccionario de excepciones."""
    inf = infinitivo.lower().strip()
    
    # 1. Buscamos en el diccionario de irregulares
    ger = IRREGULARES.get(inf, {}).get("ger", "")
    part = IRREGULARES.get(inf, {}).get("pp", "")

    # 2. Generar GERUNDIO si no existe
    if not ger:
        # Caso especial: Verbos en -uir (huir -> huyendo), excepto -guir/-quir
        if inf.endswith("uir") and not inf.endswith(("guir", "quir", "güir")):
            ger = inf[:-2] + "yendo"
        
        # Reglas estándar (ahora sí funcionan como alternativas si no es -uir)
        elif inf.endswith("ar"): 
            ger = inf[:-2] + "ando"
        elif inf.endswith(("er", "ir")): 
            ger = inf[:-2] + "iendo"

    # 3. Generar PARTICIPIO si no existe
    if not part:
        if inf.endswith("ar"): 
            part = inf[:-2] + "ado"
        elif inf.endswith(("er", "ir")): 
            part = inf[:-2] + "ido"

    return ger, part

def analizar_automaticamente(oracion, datos_clausula):
    """
    Usa spaCy con reglas morfológicas expandidas para cubrir 
    todas las personas, INCLUYENDO EL VOSOTROS Y PRETÉRITOS FUERTES (estuvisteis -> estar).
    Devuelve: (Éxito, Verbo_Visual, Infinitivo_Limpio)
    """
    if not nlp: return False, "", ""
    
    doc = nlp(oracion)
    
    verbo_token = None
    
    # 1. Búsqueda prioritaria
    for token in doc:
        if token.dep_ == "ROOT" and token.pos_ in ["VERB", "AUX"]:
            verbo_token = token
            break
            
    # 2. Búsqueda secundaria
    if not verbo_token:
        for token in doc:
            if token.pos_ in ["VERB", "AUX"]:
                verbo_token = token
                break
    
    # 3. Búsqueda Agresiva
    if not verbo_token and len(doc) <= 4:
        for token in doc:
            if token.dep_ == "ROOT" and token.pos_ not in ["PRON", "DET", "ADP", "CCONJ"]:
                verbo_token = token
                break

    if not verbo_token: return False, "", ""

    # --- Lógica de Clíticos ---
    idx = verbo_token.i
    cliticos_encontrados = []
    
    for i in range(idx - 1, max(idx - 5, -1), -1):
        token = doc[i]
        if token.pos_ == "PRON" and token.text.lower() in ["me", "te", "se", "nos", "os", "le", "les", "lo", "los", "la", "las"]:
            cliticos_encontrados.insert(0, token.text.lower())
        else:
            break
            
    # --- SANACIÓN DE LEMAS EXPANDIDA ---
    lema_limpio = verbo_token.lemma_.lower()
    texto_verbo = verbo_token.text.lower()
    
    # DICCIONARIO DE RAÍCES FUERTES (Pretéritos Irregulares)
    PRETERITOS_FUERTES = {
        "estuv": "estar", "tuv": "tener", "anduv": "andar",
        "pud": "poder", "pus": "poner", "sup": "saber",
        "hic": "hacer", "hiz": "hacer", "quis": "querer",
        "vin": "venir", "dij": "decir", "traj": "traer"
    }
    
    lemma_fixed = False

    # 1. Revisar raíces irregulares primero
    for raiz, infinitivo_real in PRETERITOS_FUERTES.items():
        if texto_verbo.startswith(raiz):
            lema_limpio = infinitivo_real
            lemma_fixed = True
            break
    
    # 2. Si no es irregular fuerte y el lema falla, heurística manual
    if not lemma_fixed and not lema_limpio.endswith(("ar", "er", "ir", "ír")): 
        
        # Singular
        if texto_verbo.endswith("é"):       lema_limpio = texto_verbo[:-1] + "ar"
        elif texto_verbo.endswith("aste"):  lema_limpio = texto_verbo[:-4] + "ar"
        elif texto_verbo.endswith("ó"):     lema_limpio = texto_verbo[:-1] + "ar"
        elif texto_verbo.endswith("í"):     lema_limpio = texto_verbo[:-1] + "er"
        elif texto_verbo.endswith("iste"):  lema_limpio = texto_verbo[:-4] + "er"
            
        # Plural
        elif texto_verbo.endswith("amos"):  lema_limpio = texto_verbo[:-4] + "ar"
        elif texto_verbo.endswith("aron"):  lema_limpio = texto_verbo[:-4] + "ar"
        elif texto_verbo.endswith("imos"):  lema_limpio = texto_verbo[:-4] + "er"
        elif texto_verbo.endswith("ieron"): lema_limpio = texto_verbo[:-5] + "er"
            
        # VOSOTROS
        elif texto_verbo.endswith("asteis"): lema_limpio = texto_verbo[:-6] + "ar"
        elif texto_verbo.endswith("isteis"): lema_limpio = texto_verbo[:-6] + "er"

    suffix = "".join(cliticos_encontrados)
    datos_clausula.infinitivo = lema_limpio + suffix 
    
    # Generar formas
    ger, part = generar_formas_verbales(lema_limpio)
    
    if not ger or not part:
        return False, "", ""

    datos_clausula.gerundio = ger
    datos_clausula.participio = part
    
    # --- DETECCIÓN DE PERSONA EXPANDIDA ---
    person_detected = None
    
    if texto_verbo.endswith(("é", "í")):
        person_detected = "1s"
    elif texto_verbo.endswith(("aste", "iste", "as", "es")): 
        person_detected = "2s"
    elif texto_verbo.endswith("ó"):
        person_detected = "3s"
    elif texto_verbo.endswith(("amos", "emos", "imos")):
        person_detected = "1p"
    elif texto_verbo.endswith(("asteis", "isteis", "áis", "éis", "ís")):
        person_detected = "2p"
    elif texto_verbo.endswith(("aron", "ieron", "an", "en")):
        person_detected = "3p"
        
    if person_detected:
        datos_clausula.persona_numero = person_detected
    else:
        # Fallback a spaCy
        morph = verbo_token.morph.to_dict()
        persona = morph.get("Person", "3")
        numero = morph.get("Number", "Sing")
        mapper_pn = {("1", "Sing"): "1s", ("2", "Sing"): "2s", ("3", "Sing"): "3s",
                     ("1", "Plur"): "1p", ("2", "Plur"): "2p", ("3", "Plur"): "3p"}
        
        sujeto_txt = doc[:idx].text.lower()
        if "yo" in sujeto_txt.split(): datos_clausula.persona_numero = "1s"
        elif "tú" in sujeto_txt.split() or "vos" in sujeto_txt.split(): datos_clausula.persona_numero = "2s"
        elif "nosotros" in sujeto_txt.split(): datos_clausula.persona_numero = "1p"
        elif "vosotros" in sujeto_txt.split(): datos_clausula.persona_numero = "2p"
        elif "ellos" in sujeto_txt.split() or "ellas" in sujeto_txt.split(): datos_clausula.persona_numero = "3p"
        else: datos_clausula.persona_numero = mapper_pn.get((persona, numero), "3s")

    # División Posicional
    datos_clausula.sujeto = doc[:idx].text.strip()
    datos_clausula.complementos = doc[idx+1:].text.strip()

    # Devolvemos True, el verbo visual, Y EL LEMA LIMPIO
    return True, verbo_token.text, lema_limpio

def obtener_info_clausula(oracion: str, datos_clausula: DatosClause) -> DatosClause:
    
    exito_auto, verbo_visual, infinitivo_visual = analizar_automaticamente(oracion, datos_clausula)
    
    if exito_auto:
        # Mapa para lenguaje natural
        nombres_personas = {
            "1s": "primera persona singular",
            "2s": "segunda persona singular",
            "3s": "tercera persona singular",
            "1p": "primera persona plural",
            "2p": "segunda persona plural",
            "3p": "tercera persona plural"
        }
        desc_persona = nombres_personas.get(datos_clausula.persona_numero, "Desconocida")
        
        time.sleep(0.5)
        print("\nEste es un análisis de algunos de los rasgos morfológicos y estructurales de esta cláusula:")
        print("\n" + "="*50)
        print(f"• Verbo:            «{verbo_visual.lower()}»") 
        print(f"• Persona/Número:   {desc_persona}")
        print("-" * 50)
        print(f"• Infinitivo:       {infinitivo_visual}")
        print(f"• Gerundio:         {datos_clausula.gerundio}")
        print(f"• Participio:       {datos_clausula.participio}")
        print("-" * 50)
        print(f"• Antes del verbo:  «{datos_clausula.sujeto if datos_clausula.sujeto else 'Ø'}»")
        print(f"• Después del verbo:«{datos_clausula.complementos if datos_clausula.complementos else 'Ø'}»")
        print("="*50)
        
        if respuesta_si_no("\n¿Es correcto este análisis? (s/n): "):
            datos_clausula.rasgos_obtenidos = True
            return datos_clausula
        else:
            print("\nEntendido. Ingresemos los datos manualmente.")
            time.sleep(0.5)
    
    # --- MODO MANUAL ---
    datos_clausula.infinitivo = peticion(f"\nEscribe el INFINITIVO del verbo en «{oracion}», incluyendo los clíticos que haya (ejs: «derretirse», «decirle»): ")
    datos_clausula.gerundio = peticion(f"Escribe el GERUNDIO del verbo en «{oracion}», sin clíticos (ej: «derritiendo»): ")
    datos_clausula.participio = peticion(f"Escribe el PARTICIPIO (masculino singular) del verbo en «{oracion}» (ej: «derretido»): ")
    
    sujeto_input = peticion(f"Escribe todo lo que hay ANTES del verbo en «{oracion}», incluyendo los clíticos (0 si no hay nada): ")
    datos_clausula.sujeto = "" if sujeto_input == "0" else sujeto_input
    
    complementos_input = peticion(f"Escribe todo lo que hay DESPUÉS del verbo en «{oracion}» (0 si no hay nada): ")
    datos_clausula.complementos = "" if complementos_input == "0" else complementos_input
    
    persona_numero_pregunta = "Escribe la persona y número del verbo"
    persona_numero_prompt = "(1s/2s/3s/1p/2p/3p): "
    opciones_persona_numero: List[str] = ['1s', '2s', '3s', '1p', '2p', '3p']
    datos_clausula.persona_numero = pedir_respuesta_multiple(persona_numero_pregunta, opciones_persona_numero, persona_numero_prompt)
    
    datos_clausula.rasgos_obtenidos = True
    return datos_clausula

# --- FIN FUNCIONES DE ANÁLISIS AUTOMÁTICO ---


def construir_perif_gerundio(tiempo: str, datos_clausula: DatosClause) -> str:
    forma_estar = ESTAR_PRETERITO[datos_clausula.persona_numero] if tiempo == 'preterito' else ESTAR[datos_clausula.persona_numero]
    return " ".join(parte for parte in [datos_clausula.sujeto, f"{forma_estar} {datos_clausula.gerundio}", datos_clausula.complementos] if parte)

def construir_perif_gerundio_subj(datos_clausula: DatosClause) -> str:
    forma_estar = ESTAR_SUBJUNTIVO[datos_clausula.persona_numero]
    return " ".join(parte for parte in [datos_clausula.sujeto, f"{forma_estar} {datos_clausula.gerundio}", datos_clausula.complementos] if parte)

def construir_perif_participio(datos_clausula: DatosClause) -> str:
    forma_haber = HABER[datos_clausula.persona_numero]
    return " ".join(parte for parte in [datos_clausula.sujeto, f"{forma_haber} {datos_clausula.participio}", datos_clausula.complementos] if parte)

def construir_perif_infinitivo(datos_clausula: DatosClause) -> str:
    forma_dejar = DEJAR[datos_clausula.persona_numero]
    return " ".join(parte for parte in [f"{forma_dejar} de {datos_clausula.infinitivo}", datos_clausula.complementos] if parte)


def determinar_subtipo(pred_es: RasgosPred) -> Optional[str]:
    if pred_es.estativo:
        return "ESTADO"
    elif pred_es.puntual and pred_es.telico:
        return "LOGRO"
    elif pred_es.puntual and not pred_es.telico:
        return "SEMELFACTIVO"    
    elif not pred_es.puntual and pred_es.telico and pred_es.dinamico:
        return "REALIZACION_ACTIVA"
    elif not pred_es.puntual and not pred_es.telico and pred_es.dinamico:
        return "ACTIVIDAD"
    elif not pred_es.puntual and pred_es.telico and not pred_es.dinamico:
        return "REALIZACION"
    elif not pred_es.puntual and not pred_es.telico and not pred_es.dinamico:
        return "PROCESO"
    else:
        return None


def determinar_aktionsart(pred_es: RasgosPred) -> Optional[Aktionsart]:
    subtipo = determinar_subtipo(pred_es)
    if subtipo is None:
        return None
    if pred_es.causativo:
        if subtipo in ["REALIZACION", "REALIZACION_ACTIVA", "ACTIVIDAD"]:
            return Aktionsart[f"{subtipo}_CAUSATIVA"]
        else:
            return Aktionsart[f"{subtipo}_CAUSATIVO"]
    else:
        return Aktionsart[subtipo]
        

#Pruebas de Aktionsart en funciones específicas
def prueba_causatividad(oracion: str) -> bool:
    time.sleep(0.5)
    print("\nPRUEBA DE CAUSATIVIDAD")
    print(f"\nIntenta reformular «{oracion}» siguiendo estos modelos: ")
    print("• El gato rompió el jarrón → El gato HIZO/CAUSÓ QUE el jarrón se rompiera")
    print("• Ana le dio un libro a Pepe → Ana HIZO/CAUSÓ QUE Pepe tuviera un libro")
    reformulacion = peticion("\nEscribe tu reformulación (o «0» si no es posible): ")
    if reformulacion == '0' or not reformulacion.strip():
        return False
    print("\nConsidera lo siguiente:")
    print(f"• «{reformulacion[0].upper() + reformulacion[1:]}» debe mantener el significado de «{oracion}».")
    print(f"• «{reformulacion[0].upper() + reformulacion[1:]}» no debe añadir nuevos argumentos ni repetir otros ya existentes en «{oracion}».")
    print("• No debe tratarse de expresiones de consumo («comer una manzana») o creación («escribir un cuento»).")
    return respuesta_si_no(f"\n¿«{reformulacion[0].upper() + reformulacion[1:]}» cumple con estos criterios? (s/n): ")

def obtener_evento_basico() -> str:
    while True:
        evento = peticion("\nEscribe el evento o estado resultante sin la causa (ejs: «el jarrón se rompió», «Pepe tiene un libro»).\nSi no puedes pensar en ninguno, escribe «0»: ")
        if evento == "0" or evento.strip():
            return evento
        print("\nPor favor, ingresa una oración válida o «0» para cancelar.")

def verificar_limpieza_adjuntos(oracion: str) -> str:
    """
    Pide al usuario que verifique si la cláusula está limpia de adjuntos
    que puedan interferir con las pruebas.
    """
    print(f"\nEsta es la cláusula a la que aplicaremos las pruebas: \n{NEGRITA}«{oracion}»{RESET}")
    print("Para que estas funcionen correctamente, la cláusula debe estar 'limpia'.")
    print("\nAsegúrate de que NO tenga:")
    print("• Expresiones de tiempo (ej: «ayer», «siempre», «el lunes»)")
    print("• Expresiones de modo (ej: «rápidamente», «bien», «mal», «con calma»)")
    print("• Negaciones (ej: «no», «tampoco»)")
    
    if respuesta_si_no("\n¿Tu cláusula contiene alguno de estos elementos? (s/n): "):
        oracion_limpia = peticion(f"\nPor favor, escribe «{oracion}» de nuevo SIN esos elementos (ej: 'Pedro corrió' en vez de 'Pedro nunca corrió ayer'): ")
        while not oracion_limpia.strip():
            oracion_limpia = peticion("No has escrito nada. Inténtalo de nuevo: ")
        return oracion_limpia
    return oracion

def prueba_estatividad(oracion: str) -> bool:
    print("\nPRUEBA DE ESTATIVIDAD")
    return not respuesta_si_no(
        f"\nObserva el siguiente diálogo:"
        f"\n— ¿Qué pasó hace un rato / ayer / el mes pasado?"
        f"\n— {oracion[0].upper() + oracion[1:]}."
        f"\n\n¿Te parece que «{oracion}» es una buena respuesta a la pregunta? \n(con al menos una de las opciones) (s/n): ")

def prueba_dinamicidad(datos_clausula: DatosClause) -> bool:
    perifrasis_gerundio = construir_perif_gerundio('presente', datos_clausula)
    print("\nPRUEBA DE DINAMICIDAD")
    return respuesta_si_no(
        f"\nObserva esta expresión: «{perifrasis_gerundio[0].upper() + perifrasis_gerundio[1:]} enérgicamente / con fuerza / con ganas»."
        f"\n¿Esta expresión es compatible con alguna de las opciones? (s/n): ")

def prueba_duratividad(datos_clausula: DatosClause) -> bool:
    perifrasis_gerundio = construir_perif_gerundio('preterito', datos_clausula)
    print("\nPRUEBA DE PUNTUALIDAD")
    return respuesta_si_no(
        f"\nObserva esta expresión: «{perifrasis_gerundio[0].upper() + perifrasis_gerundio[1:]} durante una hora / un mes»."
        f"\n¿Es esta una expresión posible (con al menos una de las opciones)? \n(sin que el evento tome una interpretación iterativa o de inminencia) (s/n): ")

def prueba_telicidad(datos_clausula: DatosClause) -> bool:
    perifrasis_gerundio = construir_perif_gerundio_subj(datos_clausula)
    perifrasis_participio = construir_perif_participio(datos_clausula)
    perifrasis_infinitivo = construir_perif_infinitivo(datos_clausula)
    print("\nPRUEBA DE TELICIDAD")
    pregunta = (f"\nImagina que {perifrasis_gerundio} y de pronto {perifrasis_infinitivo}."
                f"\n¿Se podría decir que «{perifrasis_participio}»? (s/n): ")
    return not respuesta_si_no(pregunta)
    

def obtener_rasgos_akt(oracion: str, datos_clausula: DatosClause) -> Union[RasgosPred, None]:
    pred_es = RasgosPred()
    datos_clausula.rasgos_obtenidos = False

    # 1. Prueba de Causatividad
    respuesta_causatividad = prueba_causatividad(oracion)
    if respuesta_causatividad:
        evento_basico = obtener_evento_basico()
        if evento_basico == "0":
            pred_es.causativo = False
            print(f"\n{NEGRITA}El predicado es [-causativo]{RESET}")
        else:
            pred_es.causativo = True
            print(f"\n{NEGRITA}El predicado es [+causativo]{RESET}")
            oracion = evento_basico
    else:
        pred_es.causativo = False
        print(f"\n{NEGRITA}El predicado es [-causativo]{RESET}")

    time.sleep(0.5)

    # 2. Limpieza de la cláusula
    oracion = verificar_limpieza_adjuntos(oracion) 

    time.sleep(0.5)

    # 3. Análisis de información de la cláusula
    obtener_info_clausula(oracion, datos_clausula)

    time.sleep(0.5)

    # 4. Bloque de pruebas semánticas
    pred_es.estativo = prueba_estatividad(oracion)
    print(f"\n{NEGRITA}El predicado es [{'+estativo' if pred_es.estativo else '-estativo'}]{RESET}")
    time.sleep(0.5)

    if not pred_es.estativo:
        
        pred_es.puntual = not prueba_duratividad(datos_clausula)
        print(f"\n{NEGRITA}El predicado es [{'+puntual' if pred_es.puntual else '-puntual'}]{RESET}")
        time.sleep(0.5)

        pred_es.telico = prueba_telicidad(datos_clausula)
        print(f"\n{NEGRITA}El predicado es [{'+télico' if pred_es.telico else '-télico'}]{RESET}")
        time.sleep(0.5)

        pred_es.dinamico = prueba_dinamicidad(datos_clausula)
        print(f"\n{NEGRITA}El predicado es [{'+dinámico' if pred_es.dinamico else '-dinámico'}]{RESET}")
        time.sleep(0.5)

    return pred_es


def mostrar_resultado(oracion_original: str, aktionsart: Aktionsart, pred_es: RasgosPred) -> None:
    time.sleep(0.5)
    print("\nRESULTADO")
    print(f"\n{NEGRITA}El aktionsart del predicado de «{oracion_original}» es {aktionsart.value.upper()}.{RESET}")

    akt_estado = aktionsart in [Aktionsart.ESTADO, Aktionsart.ESTADO_CAUSATIVO]

    rasgos_str = [
        f"[{'+causativo' if pred_es.causativo else '-causativo'}]",
        f"[{'+estativo' if pred_es.estativo else '-estativo'}]",
        f"[{'+puntual' if not akt_estado and pred_es.puntual else '-puntual'}]",
        f"[{'+télico' if not akt_estado and pred_es.telico else '-télico'}]",
    ]

    if akt_estado:
        rasgos_str.append("[-dinámico]")
        es_dinamico = False
    else:
        rasgos_str.append(f"[{'+dinámico' if pred_es.dinamico else '-dinámico'}]")
        es_dinamico = pred_es.dinamico

    print("\nEste predicado se clasifica así porque tiene los siguientes rasgos:")
    print(' '.join(rasgos_str))
    time.sleep(0.5)

    if respuesta_si_no("\n¿Quieres obtener la estructura lógica de esta cláusula? (s/n): "):
        print("\nEjecutando la opción elegida...")
        time.sleep(1)
        cargar_ls(aktionsart, oracion_original, es_dinamico)


def cargar_ls(aktionsart: Aktionsart, oracion_original: str, es_dinamico: bool) -> None:
    try:
        dinamico_str = "dinamico" if es_dinamico else "no_dinamico"
        cmd = [sys.executable, "-u", "ls.py", aktionsart.value, oracion_original, dinamico_str]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar ls.py: {e}")
    except FileNotFoundError:
        print("No se encontró el archivo ls.py en el directorio actual.")


def main() -> None:
    set_spanish_locale()
    limpiar_consola()
    print("\nEste programa te ayudará a identificar el aktionsart")
    print("del predicado principal en una cláusula.")
    print("\n(Escribe «...» en cualquier momento para reiniciar el análisis).")

    while True:
        try:           
            oracion_original = peticion(
                "\nPor favor, escribe una cláusula con el verbo que quieres probar"
                "\nconjugado en pretérito (ej: «Pedro corrió hasta su casa»)."
                "\nSi suena muy extraña, escríbela en presente (ej: «María sabe inglés»)."
                "\n\nCláusula: "
            )

            if not oracion_original:
                print("\nNo has escrito ninguna cláusula.")
                continue

            oracion = oracion_original
            datos_clausula = DatosClause()

            pred_es = obtener_rasgos_akt(oracion, datos_clausula)
            if pred_es is None:
                continue
            aktionsart = determinar_aktionsart(pred_es)
            if aktionsart is None:
                mensaje_reinicio()
                continue
            mostrar_resultado(oracion_original, aktionsart, pred_es)

            if not respuesta_si_no("\n¿Quieres identificar el aktionsart de otro predicado? (s/n): "):
                time.sleep(1)
                return
            else:
                time.sleep(0.5)
                limpiar_consola()

        except ReiniciarAnalisis:
            print("\n" + "-" * 30)
            print("Análisis reiniciado.")
            print("-" * 30)
            time.sleep(0.8)
            limpiar_consola()
            continue

        except Exception as e:
            logging.error(f"\nSe produjo un error inesperado: {e}")
            print("\nSe produjo un error. Por favor, intenta de nuevo.")

if __name__ == "__main__":
    main()
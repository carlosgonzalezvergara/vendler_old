# -*- coding: utf-8 -*-
import locale
import logging
import os
import readline
import subprocess
import sys
import time
import typing
import re
from deep_translator import GoogleTranslator

class ReiniciarAnalisis(Exception):
    """Excepción para abortar el análisis actual y volver al inicio."""
    pass

# --- LISTA DE PROTECCIÓN: Palabras clave de RRG que NO deben traducirse ---
RRG_KEYWORDS = {
    "do", "cause", "become", "ingr", "proc", "seml", "fin", "exist", 
    "be", "be-loc", "know", "have", "feel", "see", "hear", "smell", "taste", 
    "covering.path.distance", "weather", "if", "evid", "sta", "tns", "mod", 
    "asp", "not", "purp", "being.created", "being.consumed", "consumed",
    "have.as.part", "have.as.kin", "have.enough.with", "express", "hit",
    "move.away.from.reference.point", "move.up.from.reference.point", 
    "move.down.from.reference.point", "not"
}

# Caché para no consultar a Google repetidamente por la misma palabra
CACHE_TRADUCCION = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Operador(typing.NamedTuple):
    codigo: str
    descripcion: str
    requiere_valor: bool
    ejemplos: str


OPERADORES = [
    Operador('IF', 'Fuerza ilocutiva', True, "DECL, INT, IMP"),
    Operador('EVID', 'Evidencialidad', True, "VIS, INF, HEARSAY"),
    Operador('STA', 'Estatus', True, "REALIS, PSBL, NEG"),
    Operador('TNS', 'Tiempo', True, "PAST, PRES, FUT"),
    Operador('NEG.INT +', 'Negación interna', False, ""),
    Operador('MOD', 'Modalidad deóntica', True, "OBLIG, PERMIS"),
    Operador('EVQ', 'Cuantificación eventiva', True, "DISTR"),
    Operador('DIR.CORE', 'Direccionalidad de centro', True, "HACIA.HABLANTE, DESDE.HABLANTE"),
    Operador('DIR.NUC', 'Direccionalidad nuclear', True, "ARRIBA, AFUERA"),
    Operador('ASP', 'Aspecto', True, "PFV, PERF, PROG"),
    Operador('NEG.NUC +', 'Negación nuclear', False, "")
]


AKTIONSART_OPCIONES = {
    1: "estado",
    2: "estado causativo",
    3: "logro",
    4: "logro causativo",
    5: "realización",
    6: "realización causativa",
    7: "semelfactivo",
    8: "semelfactivo causativo",
    9: "proceso",
    10: "proceso causativo",
    11: "actividad",
    12: "actividad causativa",
    13: "realización activa",
    14: "realización activa causativa"
}

MODIFICADORES_AKT = {
    "logro": "INGR",
    "realización": "BECOME",
    "proceso": "PROC",
    "semelfactivo": "SEML",
    "logro causativo": "INGR",
    "realización causativa": "BECOME",
    "proceso causativo": "PROC",
    "semelfactivo causativo": "SEML"
}

VERBOS_MOVIMIENTO = {
    "move.away.from.reference.point": [
        "ir", "irse", "salir", "partir", "marchar", "escapar", "huir",
        "largarse", "migrar", "retirarse", "alejarse", "ausentarse",
        "desaparecer", "desvanecerse", "desplazarse", "evadirse", "esfumarse",
        "fugarse", "trasladarse", "mudarse", "perderse", "marcharse", "venir",
        "arrancar", "arrancarse", "cambiarse", "saltar"
    ],
    "move.up.from.reference.point": [
        "subir", "subirse", "ascender", "escalar", "trepar", "elevarse",
        "remontar"
    ],
    "move.down.from.reference.point":
    ["bajar", "bajarse", "caer", "caerse", "descender"]
}

VERBOS_METEOROLOGICOS = [
    "llover", "nevar", "granizar", "tronar", "relampaguear", "diluviar",
    "lloviznar", "escampar", "helar", "deshelar", "ventear", "anochecer",
    "amanecer", "atardecer", "oscurecer", "aclarar", "nublar", "despejar",
    "chispear", "orbayar", "orvallar", "chaparrear", "gotear", "garuar",
    "chirimirear", "temblar", "nortear", "terremotear"
]

VERBOS_TRANSFERENCIA = {
    "sacar": [
        "sacar", "retirar", "tomar", "agarrar", "coger", "quitar", "apartar",
        "desalojar", "separar", "desplazar", "exiliar", "remover", "descolgar",
        "extraer", "rescatar", "liberar", "arrancar", "sustraer", "arrebatar",
        "despojar", "confiscar", "desposeer", "usurpar", "desapropiar",
        "decomisar", "expropiar", "robar", "hurtar", "birlar", "enajenar",
        "pedir", "solicitar", "demandar", "exigir", "comprar", "cobrar",
        "exigir", "facturar", "reclamar", "perceptuar", "expulsar", "desalojar",
        "lanzar", "arrojar", "eliminar", "desterrar", "extraditar", "ahuyentar",
        "desarraigar", "destituir", "desprender", "erradicar", "vaciar", "drenar",
        "salvar"
    ],
    "dar_poner": [
        "acercar", "acreditar", "adicionar", "adscribir", "agregar", "alcanzar",
        "añadir", "aplicar", "arrimar", "asignar", "atribuir", "cargar", "ceder", "colocar",
        "conceder", "conferir", "consignar", "cubrir", "dar", "delegar", "desparramar",
        "destinar", "distribuir", "donar", "dotar", "echar", "encomendar", "endilgar",
        "entregar", "enviar", "esparcir", "estipular", "expandir", "extender",
        "facilitar", "fijar", "imputar", "incorporar", "instituir", "legar", "llevar",
        "mandar", "nombrar", "obsequiar", "ofrecer", "otorgar", "pasar", "poner",
        "prescribir", "prestar", "proporcionar", "reconocer", "repartir", "señalar",
        "suministrar", "traer", "transferir", "trasferir", "traspasar", "untar",
        "vender", "verter", "vertir"
    ]
}

VERBOS_DICCION = {
    "preguntar": [
        "averiguar", "consultar", "cuestionar", "demandar", "indagar",
        "inquirir", "interpelar", "interrogar", "pedir", "preguntar",
        "recabar", "requerir", "sondear"
    ],
    "conversar": [
        "charlar", "chismear", "chismorrear", "comentar", "conferenciar",
        "conferir", "conversar", "cotillear", "cotorrear", "cuchichear",
        "departir", "dialogar", "discutir", "gritar", "gritarse",
        "hablar", "interlocutar", "parlar", "parlotear", "platicar",
        "tratar"
    ],
    "agradecer": {
        "adular": "adulación", "advertir": "advertencia", "agradecer": "agradecimiento",
        "alardear": "alarde", "amenazar": "amenaza", "brindar": "brindis",
        "criticar": "crítica", "disculpar": "disculpa", "elogiar": "elogio",
        "encomiar": "encomio", "exhortar": "exhortación", "felicitar": "felicitación",
        "halagar": "halago", "implorar": "imploración", "insultar": "insulto",
        "jurar": "juramento", "lamentar": "lamento", "lisonjear": "lisonja",
        "pedir": "petición", "perdonar": "perdón", "protestar": "protesta",
        "regañar": "regaño", "replicar": "réplica", "rogar": "ruego",
        "saludar": "saludo", "suplicar": "súplica"
    },
    "bendecir": {
        "aconsejar": "consejo", "argumentar": "argumento", "bendecir": "bendición",
        "debatir": "debate", "maldecir": "maldición", "mentir": "mentira",
        "prometer": "promesa"
    }
}

VERBOS_TRI_NEG = {
    "desatribuir": [
        "desatribuir", "desasignar", "quitar", "retirar", "denegar",
        "rechazar", "rehusar", "desconocer", "ignorar", "negar", "revocar",
        "desacreditar", "desautorizar", "invalidar", "desadscribir",
        "desvincular", "separar"
    ],
    "ocultar": [
        "ocultar", "esconder", "encubrir", "disimular", "camuflar", "velar",
        "callar", "silenciar", "omitir", "reservar", "retener", "hurtar",
        "guardar", "escamotear", "suprimir", "enmascarar", "tapar"
    ]
}

VERBOS_POSESION = {
    "tener": [
        "acoger", "albergar", "alojar", "contener", "conservar", "custodiar",
        "cuidar", "demostrar", "denotar", "desplegar", "evidenciar", "exhibir",
        "gestionar", "guardar", "hospedar", "incluir", "lucir", "manifestar",
        "mantener", "mostrar", "ofrecer", "ostentar", "portar", "poseer",
        "presentar", "proteger", "reflejar", "resguardar", "revelar",
        "sostener", "soportar", "tener", "vigilar"
    ],
    "obtener": [
        "obtener", "conseguir", "lograr", "adquirir", "alcanzar", "recibir",
        "ganar", "captar", "capturar", "atrapar"
    ],
    "perder": ["perder", "extraviar", "traspapelar", "egraviar"]
}

VERBOS_EXISTENCIA = [
    "conservada", "conservado", "conservadas", "conservados",
    "existida", "existido", "existidas", "existidos",
    "habida", "habido", "habidas", "habidos",
    "perdurada", "perdurado", "perduradas", "perdurados",
    "permanecida", "permanecido", "permanecidas", "permanecidos",
    "persistida", "persistido", "persistidas", "persistidos",
    "quedada", "quedado", "quedadas", "quedados",
    "resistida", "resistido", "resistidas", "resistidos",
    "restada", "restado", "restadas", "restados",
    "sida", "sido", "sidas", "sidos",
    "sobrevivida", "sobrevivido", "sobrevividas", "sobrevividos",
    "subsistida", "subsistido", "subsistidas", "subsistidos"
]

VERBOS_PERCEPCION = {
    "ver": "see", "observar": "see", "mirar": "see", "contemplar": "see",
    "vislumbrar": "see", "divisar": "see", "atisbar": "see", "escudriñar": "see",
    "distinguir": "see", "enfocar": "see", "ojear": "see", "cachar": "see",
    "otear": "see", "escanear": "see", "acechar": "see",
    "oír": "hear", "escuchar": "hear", "atender": "hear", "auscultar": "hear",
    "tocar": "feel", "palpar": "feel", "rozar": "feel", "acariciar": "feel",
    "manosear": "feel",
    "probar": "taste", "saborear": "taste", "degustar": "taste", "paladear": "taste",
    "catar": "taste", "gustar": "taste",
    "oler": "smell", "aspirar": "smell", "olisquear": "smell", "olfatear": "smell",
    "husmear": "smell", "inhalar": "smell", "olorosar": "smell"
}

VERBOS_PERCEPCION_IMPERSONAL = {
    "saber": "taste", "sabido": "taste", "sabida": "taste", "sabidos": "taste", "sabidas": "taste",
    "oler": "smell", "olido": "smell", "olida": "smell", "olidos": "smell", "olidas": "smell",
    "sonar": "hear", "sonado": "hear", "sonada": "hear", "sonados": "hear", "sonadas": "hear",
    "ver": "see", "verse": "see", "visto": "see", "vista": "see", "vistos": "see", "vistas": "see",
    "sentir": "feel", "sentirse": "feel", "sentido": "feel", "sentida": "feel", "sentidos": "feel", "sentidas": "feel"
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


def peticion(prompt: str) -> str:
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


def input_si_no(prompt: str) -> bool:
    validas = {'sí': True, 'si': True, 's': True, 'no': False, 'n': False}
    while True:
        respuesta = peticion(prompt).lower().strip()
        if respuesta in validas:
            return validas[respuesta]
        print("Por favor, responde «sí (s)» o «no (n)».")


def buscar_verbo(verbo, diccionario):
    for categoria, verbos in diccionario.items():
        if verbo in verbos:
            return categoria
    return None


def añadir_operadores(estructura_logica):
    # Definición de Estilos ANSI 
    ITALICA = "\033[3m"
    ATENUADO = "\033[2m"
    RESET = "\033[0m"

    if not input_si_no("\n¿Quieres añadir operadores a la estructura lógica? (s/n): "):
        return estructura_logica

    print("\n--- SELECCIÓN DE OPERADORES ---")
    print("Operadores clausulares:")
    for i, op in enumerate(OPERADORES[:4], 1):
        print(f" {i:>2}. {op.descripcion}")
    print("\nOperadores centrales:")
    for i, op in enumerate(OPERADORES[4:8], 5):
        print(f" {i:>2}. {op.descripcion}")
    print("\nOperadores nucleares:")
    for i, op in enumerate(OPERADORES[8:], 9):
        print(f" {i:>2}. {op.descripcion}")
    
    print("\nEscribe los números de los operadores que desees, separados por comas o espacios.")
    print(f"Ejemplo: {ITALICA}1, 4, 10{RESET} (para Fuerza ilocutiva, Tiempo y Aspecto)")
    
    while True:
        entrada = peticion("\nSelección: ")
        if not entrada:
            return estructura_logica
            
        # Normalizamos la entrada: reemplazamos comas por espacios y dividimos
        numeros_str = entrada.replace(',', ' ').split()
        
        operadores_seleccionados = []
        try:
            indices_vistos = set()
            for n in numeros_str:
                num = int(n)
                if num < 1 or num > len(OPERADORES):
                    raise ValueError(f"El número {num} no es válido.")
                if num in indices_vistos:
                    continue # Ignorar duplicados silenciosamente o avisar
                
                indices_vistos.add(num)
                operadores_seleccionados.append(OPERADORES[num-1])
            
            break 
            
        except ValueError:
            print("Entrada inválida. Asegúrate de escribir solo números del 1 al 11.")

    # Ordenamos según la jerarquía RRG (basado en el orden de la lista global)
    operadores_seleccionados.sort(key=lambda op: OPERADORES.index(op))
    
    estructura_logica = f"[{estructura_logica}]"
    
    # Fase de asignación de valores
    operadores_con_valores = []
    
    for op in operadores_seleccionados:
        if op.requiere_valor:
            valor = peticion(f"Escribe el valor para {op.descripcion} ({op.codigo}) [Ej: {op.ejemplos}]: ").upper()
            if op.codigo == 'STA' and valor == 'NEG':
                valor = 'NEG +'
            operadores_con_valores.append((op.codigo, valor))
        else:
            operadores_con_valores.append((op.codigo, None))
    
    # Construcción del string (De adentro hacia afuera)
    for codigo, valor in reversed(operadores_con_valores):
        cat_fmt = f"{ATENUADO}{codigo}{RESET}"
        if valor:
            val_fmt = f"{ITALICA}{valor}{RESET}"
            estructura_logica = f"<{cat_fmt} {val_fmt} {estructura_logica}>"
        else:
            estructura_logica = f"<{cat_fmt} {estructura_logica}>"
    
    print(f"\nLa estructura lógica con operadores es: {estructura_logica}")
    
    return estructura_logica


def verificar_dinamicidad(AKT, oracion_original):
    if AKT in ["actividad", "actividad causativa", "realización activa", "realización activa causativa"]:
        return True
    elif AKT in ["estado", "estado causativo", "realización causativa", "proceso causativo"]:
        return False
    elif AKT in ["logro", "semelfactivo"]:
        return input_si_no(f"\n¿«{oracion_original[0].upper() + oracion_original[1:]}» es compatible con expresiones como «enérgicamente», «con fuerza» o «con ganas»? (s/n): ")
    elif AKT in ["logro causativo", "semelfactivo causativo"]:
        clausula = peticion("\nEscribe el evento resultante de la cláusula, sin el segmento causativo.\nEjs: «el jarrón se rompió», «Ana recibió un regalo»: ")
        return input_si_no(f"\n¿Es «{clausula}» compatible con expresiones como «enérgicamente», «con fuerza» o «con ganas»? (s/n): ")
    return None
    

def aplicar_DO(oracion_original, x, estructura_logica, es_dinamico, AKT):
    if estructura_logica is None:
        return None
    if (es_dinamico or "causativ" in AKT) and input_si_no(f"¿La acción de «{oracion_original}» fue efectuada intencionalmente por «{x}»? (s/n): "):
        return f"DO ({estructura_logica})"
    return estructura_logica


def verificar_percepcion(pred):
    if input_si_no(f"¿«{pred[0].upper() + pred[1:]}» indica un tipo de percepción sensorial? (s/n): "):
        pred_lower = pred.lower()
        if pred_lower in VERBOS_PERCEPCION:
            nuevo_pred = VERBOS_PERCEPCION[pred_lower]
        else:
            sentidos = {"1": "see", "2": "hear", "3": "smell", "4": "taste", "5": "feel"}
            while True:
                sentido = peticion("Indica el sentido involucrado:\n(1) vista, (2) oído, (3) olfato, (4) gusto, (5) tacto: ")
                if sentido in sentidos:
                    nuevo_pred = sentidos[sentido]
                    break
                else:
                    print("Entrada no válida. Por favor, ingresa un número del 1 al 5.")
        return nuevo_pred
    return pred.lower().replace(" ", ".")


def obtener_aktionsart() -> str:
    print("Indica el aktionsart del predicado:")
    for num, akt in AKTIONSART_OPCIONES.items():
        print(f"{num}. {akt}")
    while True:
        entrada = peticion("\nEscribe el número correspondiente: ")
        if entrada.isdigit():
            AKT = int(entrada)
            if AKT in AKTIONSART_OPCIONES:
                return AKTIONSART_OPCIONES[AKT]
        print("Por favor, escribe un número válido de la lista.")


def obtener_argumentos(oracion_original) -> typing.Tuple[str, str, str]:
    x = peticion(f"\nEscribe el sujeto de «{oracion_original}» (0 si no hay): ")
    y = peticion(f"Escribe el complemento directo de «{oracion_original}», sin «a» (0 si no hay): ")
    z = peticion(f"Escribe el complemento indirecto de «{oracion_original}», sin «a» (0 si no hay): ")
    def normalizar(arg: str) -> str:
        return 'Ø' if arg in ('0', '') else arg
    return normalizar(x), normalizar(y), normalizar(z)


def obtener_predicado(AKT, y, es_dinamico):
    if AKT in ["actividad causativa", "realización activa causativa"] or (AKT in ["logro causativo", "semelfactivo causativo"] and es_dinamico):
        return "" #Se tratan de manera específica en generar_estructura_logica
    elif (AKT in ["actividad", "realización activa"]) or (AKT in ["logro", "semelfactivo"] and es_dinamico) or (y != "Ø" and "causativ" not in AKT):
        pred = peticion("Escribe el infinitivo del verbo: ")
    else:
        pred = peticion("Escribe el verbo en su forma de participio (o el adjetivo relacionado) \no, si se trata de un verbo (seudo)copulativo, escribe el atributo: ")
    return pred.lower().replace(" ", ".")


#Funciones para armar la estructura lógica fundamental
def generar_estructura_logica(AKT, x, y, z, pred, locus, es_dinamico, oracion_original):
    operador = MODIFICADORES_AKT.get(AKT, "")
    pred = pred.lower().replace(" ", ".")
    ls = None
    if AKT in ["realización activa", "realización activa causativa"]:
        ls = manejar_realizacion_activa(x, y, z, pred, locus, AKT, oracion_original)
    elif es_dinamico and "causativ" in AKT:
        ls = generar_estructura_actividad_causativa(x, y, pred, operador)
    elif AKT in ["estado causativo", "logro causativo", "realización causativa", "proceso causativo", "semelfactivo causativo"]:
        ls = generar_estructura_causativa(x, y, pred, operador)
    elif es_dinamico:
        ls = generar_estructura_actividad(x, y, locus, pred, operador)
    elif AKT in ["estado", "logro", "realización", "proceso", "semelfactivo"]:
        ls = generar_estructura_no_causativa(x, y, locus, pred, operador, AKT)
    if ls is None:
        raise ValueError(f"No es posible generar una estructura lógica para estos parámetros.\nParámetros: aktionsart: «{AKT}»; verbo: «{pred}»; sujeto: «{x}»; c. directo: «{y}»; c. indirecto: «{z}»; locativo: «{locus}».")
    return ls

def generar_estructura_no_causativa(x, y, locus, pred, operador, AKT):
    if AKT != "estado" and y != "Ø":
        pred = verificar_percepcion(pred)
    if y != "Ø" and locus == "Ø":
        return f"{operador + ' ' if operador else ''}{pred}' ({x}, {y})"
    elif y == "Ø" and locus != "Ø":
        return f"{operador + ' ' if operador else ''}{pred}' ({x}, {locus})"
    elif y == "Ø" and locus == "Ø":
        return f"{operador + ' ' if operador else ''}{pred}' ({x})"
    return None

def generar_estructura_causativa(x, y, pred, operador):
    if y == "Ø":
        return None
    return f"[do' ({x}, Ø)] CAUSE [{operador + ' ' if operador else ''}{pred}' ({y})]"

def generar_estructura_actividad(x, y, locus, pred, operador):
    if y != "Ø" and locus == "Ø":
        pred = verificar_percepcion(pred)
        return f"{operador + ' ' if operador else ''}do' ({x}, [{pred}' ({x}, {y})])"
    elif y == "Ø" and locus != "Ø":
        return f"{operador + ' ' if operador else ''}do' ({x}, [{pred}' ({x}, {locus})])"
    elif y == "Ø" and locus == "Ø":
        return f"{operador + ' ' if operador else ''}do' ({x}, [{pred}' ({x})])"
    return None

def generar_estructura_actividad_causativa(x, y, pred, operador):
    pred = peticion(f"Escribe en infinitivo la actividad realizada por «{y}» (ej: «comer»): ").lower().replace(" ", ".")
    return f"[do' ({x}, Ø)] CAUSE [{operador + ' ' if operador else ''}do' ({y}, [{pred}' ({y})])]"

def manejar_realizacion_activa(x, y, z, pred, locus, AKT, oracion_original):
    es_causativa = AKT == "realización activa causativa"
    tipo_verbo = peticion("Escribe el número correspondiente al tipo de verbo: (1) creación, (2) consumo, (3) desplazamiento o (4) ninguno de estos: ")
    if tipo_verbo == "1":
        return manejar_creacion(x, y, z, pred, es_causativa)
    elif tipo_verbo == "2":
        return manejar_consumo(x, y, z, pred, es_causativa)
    elif tipo_verbo == "3":
        return manejar_desplazamiento(AKT, x, y, z, pred, locus, es_causativa, oracion_original)
    else:
        return manejar_otros(x, y, z, pred, es_causativa, oracion_original)

def manejar_creacion(x, y, z, pred, es_causativa):
    if es_causativa:
        pred = peticion(f"Escribe en infinitivo la actividad realizada por «{z}» (ej: «escribir»): ").lower().replace(" ", ".")
        return f"[do' ({x}, Ø)] CAUSE [do' ({z}, [{pred}' ({z}, {y})]) ∧ PROC being.created' ({y}) ∧ FIN exist' ({y})]"
    else:
        return f"do' ({x}, [{pred}' ({x}, {y})]) ∧ PROC being.created' ({y}) ∧ FIN exist' ({y})"

def manejar_consumo(x, y, z, pred, es_causativa):
    if es_causativa:
        # Pedir el verbo original de la oración para decidir el flujo
        verbo_original = peticion("Escribe el infinitivo del verbo de la oración original (ej: «alimentar»): ").lower().replace(" ", ".")       
        # Caso especial para verbos tipo "alimentar"
        if verbo_original in ["alimentar", "nutrir", "cebar", "hidratar", "saciar", "empachar"]:
            pred = peticion(f"Escribe en infinitivo la actividad realizada por «{y}» (ej: «comer»): ").lower().replace(" ", ".")
            alimento = peticion("Escribe el alimento que fue consumido (ej: «una manzana»): ").lower().replace(" ", ".")
            return f"[do' ({x}, Ø)] CAUSE [do' ({y}, [{pred}' ({y}, {alimento})]) ∧ PROC being.consumed' ({alimento}) ∧ FIN consumed' ({alimento})]"
        else:
            pred = peticion(f"Escribe en infinitivo la actividad realizada por «{z}» (ej: «comer»): ").lower().replace(" ", ".")
            return f"[do' ({x}, Ø)] CAUSE [do' ({z}, [{pred}' ({z}, {y})]) ∧ PROC being.consumed' ({y}) ∧ FIN consumed' ({y})]"
    else:
        return f"do' ({x}, [{pred}' ({x}, {y})]) ∧ PROC being.consumed' ({y}) ∧ FIN consumed' ({y})"

def manejar_otros(x, y, z, pred, es_causativa, oracion_original):
    if es_causativa:
        if z != "Ø":
            pred = peticion(f"Escribe en infinitivo la actividad realizada por «{z}» (ej: «comer»): ").lower().replace(" ", ".")
            participio = peticion(f"Escribe el participio de «{pred}» (ej: «comido»): ").lower().replace(" ", ".")
            return f"[do' ({x}, Ø)] CAUSE [do' ({z}, [{pred}' ({z}, {y})]) ∧ PROC {participio}' ({y}) ∧ FIN {participio}' ({y})]"
        elif input_si_no(f"¿Alguno de los constituyentes de «{oracion_original}» es un complemento de régimen\n(ej: «en mi amigo» en «Ana transformó a Pepe en mi amigo»)? (s/n): "):
            pred = peticion(f"Escribe en infinitivo la actividad realizada por «{y}» sin la preposición que rige (ej: «transformarse»): ").lower().replace(" ", ".")
            participio = peticion(f"Escribe el participio de «{pred}» (ej: «transformado»): ").lower().replace(" ", ".")
            prep = peticion("Escribe la preposición regida por el verbo (ej: «en»): ").lower().replace(" ", ".")
            suplemento = peticion("Escribe la información del complemento de régimen (sin preposición) (ej: «mi amigo»): ")
            return f"[do' ({x}, Ø)] CAUSE [do' ({y}, [{pred}.{prep}' ({y}, {suplemento})]) ∧ PROC {participio}.{prep}' ({y}, {suplemento}) ∧ FIN {participio}.{prep}' ({y}, {suplemento})]"
        else:
            pred = peticion(f"Escribe en infinitivo la actividad realizada por «{y}» (ej: «comer»): ").lower().replace(" ", ".")
            participio = peticion(f"Escribe el participio de «{pred}» (ej: «comido»): ").lower().replace(" ", ".")
            return f"[do' ({x}, Ø)] CAUSE [do' ({y}, [{pred}' ({y})]) ∧ PROC {participio}' ({y}) ∧ FIN {participio}' ({y})]"
    else:
        if y != "Ø":
            participio = peticion(f"Escribe el participio de «{pred}» (ej: «comido»): ").lower().replace(" ", ".")
            return f"do' ({x}, [{pred}' ({x}, {y})]) ∧ PROC {participio}' ({y}) ∧ FIN {participio}' ({y})"
        elif input_si_no(f"¿Alguno de los constituyentes de «{oracion_original}» es un complemento de régimen\n(ej: «en mi amigo» en «Pepe se transformó en mi amigo»)? (s/n): "):
            participio = peticion(f"Escribe el participio de «{pred}» (ej: «transformado»): ").lower().replace(" ", ".")
            prep = peticion("Escribe la preposición regida por el verbo (ej: «en»): ").lower().replace(" ", ".")
            suplemento = peticion("Escribe la información del complemento de régimen (sin preposición) (ej: «mi amigo»): ")
            return f"do' ({x}, [{pred}.{prep}' ({x}, {suplemento})]) ∧ PROC {participio}.{prep}' ({x}, {suplemento}) ∧ FIN {participio}.{prep}' ({x}, {suplemento})"
        else:
            participio = peticion(f"Escribe el participio de «{pred}» (ej: «comido»): ").lower().replace(" ", ".")
            return f"do' ({x}, [{pred}' ({x})]) ∧ PROC {participio}' ({x}) ∧ FIN {participio}' ({x})"

def manejar_desplazamiento(AKT, x, y, z, pred, locus, es_causativa, oracion_original):
    categoria_movimiento = buscar_verbo(pred, VERBOS_MOVIMIENTO)
    if categoria_movimiento:
        pred = categoria_movimiento

    if (locus == "Ø" or (locus != "Ø" and y != "Ø")) and not es_causativa: #"Pepe corrió una maratón" o "Pepe corrió un kilómetro hasta su casa"
        return f"do' ({x}, [{pred}' ({x})]) ∧ PROC covering.path.distance' ({x}, {y}) ∧ FIN be-LOC' ({locus}, {x})"


    lugar_tipo = peticion(f"¿«{locus}» es (1) la procedencia o (2) el destino? Escribe 1 o 2: ")
    fin_loc = "NOT be-LOC'" if lugar_tipo == "1" else "be-LOC'"
    
    if es_causativa:
        pred = peticion(f"Escribe en infinitivo la actividad realizada por «{y}» (ej: «correr»): ").lower().replace(" ", ".")
        return f"[do' ({x}, Ø)] CAUSE [do' ({y}, [{pred}' ({y})]) ∧ PROC covering.path.distance' ({y}) ∧ FIN {fin_loc} ({locus}, {y})]"
    else:
        return f"do' ({x}, [{pred}' ({x})]) ∧ PROC covering.path.distance' ({x}) ∧ FIN {fin_loc} ({locus}, {x})"


# Manejo de casos especiales de predicados
def verbos_doler_gustar(AKT, x, y, z, operador, es_dinamico, oracion_original): #A [OI] le [VERBO] [SUJETO]
    if "causativ" not in AKT and AKT != "realización activa" and x != "Ø" and y == "Ø" and z != "Ø":
        if input_si_no(f"¿«{x[0].upper() + x[1:]}» está situado en alguna parte de «{z}»? (s/n): "):
            pred = peticion("Escribe el infinitivo del verbo: ").lower().replace(" ", ".")
            if es_dinamico:
                return f"{operador + ' ' if operador else ''}do' ({x}, [{pred}' ({x})]) ∧ have.as.part' ({z}, {x})"
            else:
                return f"{operador + ' ' if operador else ''}{pred}' ({x}) ∧ have.as.part' ({z}, {x})"
        elif input_si_no(f"¿«{oracion_original[0].upper() + oracion_original[1:]}» tiene una estructura parecida a «A {z} le [verbo] {x}»? (s/n): "):
            pred = peticion("Escribe el infinitivo del verbo: ").lower().replace(" ", ".")
            if es_dinamico:
                return f"{operador + ' ' if operador else ''}do' ({x}, [{pred}' ({x}, {z})]) [MR1]"
            else:
                return f"{operador + ' ' if operador else ''}{pred}' ({x}, {z}) [MR1]"
    return None

def hacer_meteorologico(x, y, oracion_original, operador, es_dinamico):#Hace frío
    if x == "Ø" and y != "Ø" and input_si_no(f"¿El verbo de «{oracion_original}» es «hacer»? (s/n): "):
        pred = peticion("Escribe la sensación en forma de adjetivo (ej: «caluroso»): ").lower().replace(" ", ".")
        if es_dinamico:
            return f"{operador + ' ' if operador else ''}do' (weather, [{pred}' (weather)])"
        else:
            return f"{operador + ' ' if operador else ''}{pred}' (weather)"
    return None

def casos_impersonales(x, y, z, operador, es_dinamico): #A alguien le va bien / A alguien le basta/sobra con algo
    if not es_dinamico and x == "Ø" and y == "Ø" and z != "Ø":
        verbo = peticion("Escribe el infinitivo del verbo: ")
        verbo = verbo.lower().replace(" ", ".")
        if verbo in ["ir", "irme", "irte", "irle", "irnos", "iros", "irles"]:
            pred = peticion("Escribe el adverbio o equivalente (ej: «bien»): ").lower().replace(" ", ".")
            return f"{operador + ' ' if operador else ''}{pred}' ({z}) [MR0]"
        elif verbo in ["bastar", "sobrar"]:
            suplemento = peticion("Escribe la información del complemento sin preposición (ej: «tu amistad»): ")
            return f"{operador + ' ' if operador else ''}have.enough.with' ({z}, {suplemento}) [MR0]"
    return None

def casos_locativo_dativos(AKT, x, y, z, operador, es_dinamico): #Pepe se le aproximó a Ana
    if "causativ" not in AKT and AKT != "estado" and x != "Ø" and y == "Ø" and z != "Ø" and input_si_no(f"¿«{z[0].upper() + z[1:]}» señala el destino de un desplazamiento por parte de «{x}»? (s/n): "):
        if AKT == "realización activa":
            pred = peticion("Escribe el infinitivo del verbo: ").lower().replace(" ", ".")
            return f"do' ({x}, [{pred}' ({x})]) ∧ PROC covering.path.distance' ({x}) ∧ FIN be-LOC' ({z}, {x})"
        elif es_dinamico:
            return f"{operador + ' ' if operador else ''}do' ({x}, [be-LOC' ({z}, {x})])"
        else:
            return f"{operador + ' ' if operador else ''}be-LOC' ({z}, {x})"
    return None
    
def verbos_OI(AKT, x, y, z, operador): #Verbos triargumentales con complemento indirecto
    if z == "Ø":
        return None
    pred = peticion("Escribe el infinitivo del verbo: ").lower().replace(" ", ".")
    
    # Caso especial: realización activa causativa triargumental (ej: "enseñar francés a alguien")
    if AKT == "realización activa causativa":
        if input_si_no(f"¿Es «{pred}» un verbo como «enseñar» o «mostrar»? (s/n): "):
            return f"[do' ({x}, [{pred}' ({x}, {y})])] CAUSE [do' ({z}, [know' ({z}, {y})]) ∧ PROC being.created' ({y}) ∧ FIN exist' ({y})]"
        return None  # Si no es tipo "enseñar", no aplica este caso especial
    
    if AKT == "realización activa":
        return manejar_realizacion_activa_diccion(x, y, z, pred)
    
    es_transferencia = manejar_verbos_transferencia(x, y, z, pred, operador, AKT)
    
    if es_transferencia:
        return es_transferencia
    if input_si_no(f"¿Es «{pred}» un verbo de dicción? (s/n): "):
        return manejar_verbo_diccion(x, y, z, pred, operador)
    return manejar_otros_verbos(AKT, x, y, z, pred, operador)

def manejar_realizacion_activa_diccion(x, y, z, pred):
    if not input_si_no(f"¿Es «{pred}» un verbo de dicción? (s/n): "):
        return None
    
    # SANITIZACIÓN + SOMETHING
    y_clean = "something" if y in ["Ø", "0"] else y.replace(" ", ".")
    z_clean = z.replace(" ", ".")
    
    if pred in VERBOS_DICCION["preguntar"]:
        return f"[do' ({x}, [express.question' ({x}, pregunta)]) ∧ PROC being.created' (pregunta) ∧ FIN exist' (pregunta)] PURP [do' ({z}, [express.something' ({z}, {y})])]"
    elif pred in VERBOS_DICCION["agradecer"]:
        arg_incorporado = VERBOS_DICCION["agradecer"][pred]
        return f"[do' ({x}, [express.{arg_incorporado}' ({x}, {y})]) ∧ PROC being.created' ({arg_incorporado}) ∧ FIN exist' ({arg_incorporado})] PURP [know' ({z}, {arg_incorporado} por {y})]"
    elif pred in VERBOS_DICCION["bendecir"]:
        arg_incorporado = VERBOS_DICCION["bendecir"][pred]
        return f"[do' ({x}, [express.{arg_incorporado}' ({x}, {y})]) ∧ PROC being.created' ({arg_incorporado}) ∧ FIN exist' ({arg_incorporado})] PURP [know' ({z}, {arg_incorporado} de {y})]"
    else:
        return f"[do' ({x}, [express.something' ({x}, {y})]) ∧ PROC being.created' ({y}) ∧ FIN exist' ({y})] PURP [know' ({z}, {y})]"

def manejar_verbos_transferencia(x, y, z, pred, operador, AKT): # Añadimos AKT en los argumentos
    if pred in VERBOS_TRANSFERENCIA["sacar"]:
        
        if pred == "arrancar" and "causativ" not in AKT:
            return None

        return f"[do' ({x}, Ø)] CAUSE [{operador + ' ' if operador else ''}NOT have' ({z}, {y})] PURP [have' ({x}, {y})]"
    
    elif (pred in VERBOS_TRANSFERENCIA["dar_poner"] or input_si_no(f"¿El significado típico de «{pred}» es la transferencia de un objeto físico? (s/n): ")) or (pred == "pegar" and y!= "Ø"):
        return f"[do' ({x}, Ø)] CAUSE [{operador + ' ' if operador else ''}have' ({z}, {y})]"
    return None

def manejar_verbo_diccion(x, y, z, pred, operador):
    # SANITIZACIÓN + SOMETHING
    y_clean = "something" if y in ["Ø", "0"] else y.replace(" ", ".")
    z_clean = z.replace(" ", ".")

    if pred in VERBOS_DICCION["preguntar"]:
        return f"[{operador + ' ' if operador else ''}do' ({x}, [express.question' ({x})])] PURP [do' ({z}, [express.{y_clean}' ({z}, {y})])]"
    elif pred in VERBOS_DICCION["agradecer"]:
        arg_incorporado = VERBOS_DICCION["agradecer"][pred]
        return f"[{operador + ' ' if operador else ''}do' ({x}, [express.{arg_incorporado}' ({x}, {y})])] PURP [know' ({z}, {arg_incorporado} por {y})]"
    elif pred in VERBOS_DICCION["bendecir"]:
        arg_incorporado = VERBOS_DICCION["bendecir"][pred]
        return f"[{operador + ' ' if operador else ''}do' ({x}, [express.{arg_incorporado}' ({x}, {y})])] PURP [know' ({z}, {arg_incorporado} de {y})]"
    else:
        return f"[{operador + ' ' if operador else ''}do' ({x}, [express.something' ({x}, {y})])] PURP [know' ({z}, {y})]"

def manejar_otros_verbos(AKT, x, y, z, pred, operador):
    if pred in VERBOS_TRI_NEG["desatribuir"]:
        return f"[do' ({x}, Ø)] CAUSE [{operador + ' ' if operador else ''}NOT have' ({z}, {y})]"
    elif pred in VERBOS_TRI_NEG["ocultar"]:
        return f"[do' ({x}, Ø)] CAUSE [{operador + ' ' if operador else ''}NOT know' ({z}, {y})]"
    elif input_si_no(f"¿Es «{pred}» un verbo como «enseñar» o «mostrar»? (s/n): "):
        return f"[do' ({x}, Ø)] CAUSE [{operador + ' ' if operador else ''}know' ({z}, {y})]"
    elif pred in ["pegar", "pegarle"]:
        return f"{operador + ' ' if operador else ''}do' ({x}, [hit' ({x}, {z})]) [MR1]"
    else:
        raise ValueError(f"Asegúrate de que «{z}» sea un argumento de «{pred}» y de que no se trate de una construcción aplicativa.\nParámetros: aktionsart: «{AKT}»; verbo: «{pred}»; sujeto: «{x}»; c. directo: «{y}»; c. indirecto: «{z}».")

def casos_especiales_estado(AKT, x, y, oracion_original): #Maneja propiedades inherentes y sensaciones
    if AKT == "estado":
        # sin objeto directo
        if y == "Ø": 
            if x == "Ø": 
                if input_si_no(f"¿«{oracion_original[0].upper() + oracion_original[1:]}» describe una sensación o fenómeno climático usando «estar» como verbo no auxiliar (ej: «está nublado»)? (s/n): "):
                    pred = peticion("Escribe la sensación o fenómeno climático (ej: «frío», «nublado»): ").lower().replace(" ", ".")
                    return f"{pred}' (weather)"
            elif input_si_no(f"¿«{oracion_original[0].upper() + oracion_original[1:]}» expresa un atributo esencial del sujeto usando «ser» (ej: «Ana es alta»)? (s/n): "):
                pred = peticion("Escribe el atributo: ").lower().replace(" ", ".")
                return f"be' ({x}, [{pred}'])"
            if input_si_no("¿El estado es un tipo de sensación o sentimiento (ej: «frío» o «amor»)? \n(Si es un verbo de percepción sensorial, responde que no) (s/n): "):
                pred = peticion("Escribe esa sensación o sentimiento (ej: «frío» o «enamorado»): ").lower().replace(" ", ".")
                return f"feel' ({x}, [{pred}'])"
        # con objeto directo
        else:
            if input_si_no(f"¿«{y[0].upper() + y[1:]}» expresa una sensación o sentimiento? (s/n): "):
                # Sanitización del OD para convertirlo en predicado
                y_clean = y.replace(" ", ".")
                return f"feel' ({x}, [{y_clean}'])" 
    
    elif AKT == "estado causativo" and input_si_no("¿El estado es un tipo de sensación o sentimiento (ej: «frío» o «amor»)? (s/n): "):
            pred = peticion("Escribe esa sensación o sentimiento (ej: «frío» o «enamorado»): ").lower().replace(" ", ".")
            return f"[do' ({x}, Ø)] CAUSE [feel' ({y}, [{pred}'])]"
    return None

def informacion_mente(AKT, x, y, operador, es_dinamico, oracion_original):
    if y == "Ø" or "causativ" in AKT or AKT == "realización activa" or AKT == "actividad":
        return None
    pregunta = f"¿«{oracion_original[0].upper() + oracion_original[1:]}» describe que «{x}» tiene en su mente o llega a tener en su mente lo expresado en «{y}»?\n(Si se trata de un verbo de dicción o de percepción sensorial, responde que no). (s/n): "
    if input_si_no(pregunta):
        return f"{operador + ' ' if operador else ''}know' ({x}, {y})"
    return None

def complemento_regimen(AKT, x, y, operador, es_dinamico, oracion_original):
    if AKT in ["estado", "actividad", "proceso", "logro", "realización", "semelfactivo"] and y == "Ø" and input_si_no(f"¿Alguno de los constituyentes de «{oracion_original}» es un complemento de régimen\n(ej: «de defectos» en «la obra carece de defectos»)? (s/n): "):
        
        entrada_verbo = peticion("Escribe el infinitivo del verbo: ").lower().strip()
        
        # --- FILTRO DE SEGURIDAD PARA VERBOS RECÍPROCOS ---
        verbo_aislado = entrada_verbo.split()[0]
        
        # Si el verbo está en la lista de dicción recíproca (conversar, discutir, hablar...),
        # ABORTAMOS esta función para que lo maneje 'predicados_especiales' más adelante.
        categoria = buscar_verbo(verbo_aislado, VERBOS_DICCION)
        if categoria == "conversar":
            return None
        # --------------------------------------------------

        pred = entrada_verbo.replace(" ", ".")
        suplemento = peticion("Escribe la información del complemento de régimen (sin preposición): ")
        
        if es_dinamico:
            estructura_logica = f"{operador + ' ' if operador else ''}do' ({x}, [{pred}' ({x}, {suplemento})]) [MR1]"
        else:        
            estructura_logica = f"{operador + ' ' if operador else ''}{pred}' ({x}, {suplemento}) [MR1]"
        
        return estructura_logica
    return None

def casos_locativos(estructura_logica, AKT, x, y, z, operador, es_dinamico, oracion_original):
    locus = "Ø"

    args_presentes = [f"«{arg}»" for arg in [x, y] if arg != "Ø"]
    texto_participantes = " o ".join(args_presentes) if args_presentes else "los participantes"

    if input_si_no(f"Considera la cláusula «{oracion_original}». \n¿Alguno de sus constituyentes argumentales (no periféricos) indica la ubicación, \nel destino o el punto de partida de {texto_participantes}? (s/n): "):
        locus = peticion("Escribe la información del lugar, sin preposición: ")

        pred = peticion("Escribe el infinitivo del verbo: ").lower().replace(" ", ".")
        
        # verbo "haber" con locativo
        if pred == "haber":
            if y != "Ø":
                return f"be-LOC' ({locus}, {y}) [MR1]", locus
            elif x != "Ø":
                return f"be-LOC' ({locus}, {x}) [MR1]", locus
            else:
                return f"be-LOC' ({locus}, Ø) [MR1]", locus
            
        # verbo "tener" con locativo
        elif pred in VERBOS_POSESION["tener"]:
            if input_si_no(f"¿«{y[0].upper() + y[1:]}» está situado en alguna parte de «{x}»? (s/n): "):
                return f"have.as.part' ({x}, {y}) ∧ be-LOC' ({locus}, {y})", locus
            elif pred in ["tener", "poseer", "ostentar", "lucir"] and input_si_no(f"¿«{y[0].upper() + y[1:]}» indica una relación de parentesco? (s/n): "):
                return f"have.as.kin' ({x}, {y}) ∧ be-LOC' ({locus}, {y})", locus
            else:
                return f"{pred}' ({x}, {y}) ∧ be-LOC' ({locus}, {y})", locus
        
        # verbos tipo "irse" (MOVIMIENTO)
        elif AKT in ("actividad", "logro", "realización", "proceso", "semelfactivo") and (buscar_verbo(pred, VERBOS_MOVIMIENTO) or input_si_no(f"¿Como resultado del evento, «{x}» dejó de estar o llegó a estar en «{locus}»? (s/n): ")):
            if es_dinamico:
                lugar_tipo = peticion(f"¿«{locus[0].upper() + locus[1:]}» es (1) la procedencia o (2) el destino? Escribe 1 o 2: ")
                if lugar_tipo == "1":
                    return f"{operador + ' ' if operador else ''}do' ({x}, [NOT be-LOC' ({locus}, {x})])", locus
                if lugar_tipo == "2":
                    return f"{operador + ' ' if operador else ''}do' ({x}, [be-LOC' ({locus}, {x})])", locus
            else:
                lugar_tipo = peticion(f"¿«{locus[0].upper() + locus[1:]}» es (1) la procedencia o (2) el destino? Escribe 1 o 2: ")
                if lugar_tipo == "1":
                    return f"{operador + ' ' if operador else ''}NOT be-LOC' ({locus}, {x})", locus
                if lugar_tipo == "2":
                    return f"{operador + ' ' if operador else ''}be-LOC' ({locus}, {x})", locus
        
        # verbos tipo "echar"
        elif AKT in ("logro causativo", "realización causativa", "proceso causativo", "semelfactivo causativo") and input_si_no(f"¿Como resultado del evento, «{y}» dejó de estar o llegó a estar en «{locus}»? (s/n): "):
            if es_dinamico:
                lugar_tipo = peticion(f"¿«{locus[0].upper() + locus[1:]}» es (1) la procedencia o (2) el destino? Escribe 1 o 2: ")
                if lugar_tipo == "1":
                    return f"[do' ({x}, Ø)] CAUSE [{operador + ' ' if operador else ''}do' ({y}, [NOT be-LOC' ({locus}, {y})])]", locus
                if lugar_tipo == "2":
                    return f"[do' ({x}, Ø)] CAUSE [{operador + ' ' if operador else ''}do' ({y}, [be-LOC' ({locus}, {y})])]", locus
            else:
                lugar_tipo = peticion(f"¿«{locus[0].upper() + locus[1:]}» es (1) la procedencia o (2) el destino? Escribe 1 o 2: ")
                if lugar_tipo == "1":
                    return f"[do' ({x}, Ø)] CAUSE [{operador + ' ' if operador else ''}NOT be-LOC' ({locus}, {y})]", locus
                if lugar_tipo == "2":
                    return f"[do' ({x}, Ø)] CAUSE [{operador + ' ' if operador else ''}be-LOC' ({locus}, {y})]", locus
        
        # verbos tipo "sacar" (TRANSFERENCIA)
        elif pred in VERBOS_TRANSFERENCIA["sacar"] and not ((pred == "arrancar" or pred == "retirar") and "causativ" not in AKT):
            return f"[do' ({x}, Ø)] CAUSE [{operador + ' ' if operador else ''}NOT be-LOC' ({locus}, {y})]", locus
        
        # "olvidar" algo en un lugar
        elif pred == "olvidar":
            return f"{operador + ' ' if operador else ''}NOT know' ({x}, {y}) ∧ be-LOC' ({locus}, {y})", locus
        
        # Otros casos locativos
        else:
            if AKT != "realización activa":
                pred = "be-LOC"
            estructura_logica = generar_estructura_logica(AKT, x, y, z, pred, locus, es_dinamico, oracion_original)
            return estructura_logica, locus
    return estructura_logica, locus


def predicados_especiales(AKT, x, y, z, pred, operador, es_dinamico, oracion_original):
    # casos como "algo huele mal"
    if pred in VERBOS_PERCEPCION_IMPERSONAL and not es_dinamico and y == "Ø":
        verbo_infinitivo = VERBOS_PERCEPCION_IMPERSONAL[pred]
        cualidad = peticion(f"Escribe la cualidad percibida en «{oracion_original}» (ej: «mal», «raro», «a chocolate»): ").lower().replace(" ", ".")
        return f"{operador + ' ' if operador else ''}{verbo_infinitivo}.{cualidad}' ({x})", False
    
    # verbos meteorológicos propios
    if x == "Ø" and pred in VERBOS_METEOROLOGICOS:
        return f"{operador + ' ' if operador else ''}do' ([{pred}'])", False
    
    if pred in VERBOS_DICCION["conversar"] and input_si_no(f"¿Hay un interlocutor en «{oracion_original}»? (s/n): "):
        z = peticion("Escribe quién es el interlocutor: ")
        
        # SANITIZACIÓN
        x_clean = x.replace(" ", ".")
        y_clean = y.replace(" ", ".")
        z_clean = z.replace(" ", ".")
        
        parte1 = f"[do' ({x}, [express.something.to.{z_clean}' ({x}, {y})])] PURP [{operador + ' ' if operador else ''}know' ({z}, {y})]"
        parte2 = f"[do' ({z}, [express.something.to.{x_clean}' ({z}, {y})])] PURP [{operador + ' ' if operador else ''}know' ({x}, {y})]"
        
        if input_si_no(f"¿Tanto «{x}» como «{z}» actuaron de manera intencional en la conversación? (s/n): "):
            return f"DO ({parte1}) ∧ DO ({parte2})", True
        else:
            return f"{parte1} ∧ {parte2}", True
            
    # verbos de olvido
    if pred in ["olvidar", "desaprender"]:
        if es_dinamico:
            return f"{operador + ' ' if operador else ''}do' ({x}, [NOT know' ({x}, {y})])", False
        else:
            return f"{operador + ' ' if operador else ''}NOT know' ({x}, {y})", False
    
    # verbos como "perder"
    if pred in VERBOS_POSESION["perder"]:
        if es_dinamico:
            return f"{operador + ' ' if operador else ''}do' ({x}, [NOT have' ({x}, {y})])", False
        else:
            return f"{operador + ' ' if operador else ''}NOT have' ({x}, {y})", False
    
    # verbos como "obtener"
    if pred in VERBOS_POSESION["obtener"] and y != "Ø":
        if es_dinamico:
            return f"{operador + ' ' if operador else ''}do' ({x}, [INGR have' ({x}, {y})])", False
        else:
            return f"{operador + ' ' if operador else ''}have' ({x}, {y})", False
    
    # estados especiales
    if AKT == "estado":
        #verbos de desconocimiento
        if pred in ["ignorar", "desconocer"]:
            return f"NOT know' ({x}, {y})", False
        #verbos de existencia con sujeto
        elif pred in VERBOS_EXISTENCIA and y == "Ø":
            return f"exist' ({x})", False
        #verbos de existencia sin sujeto ("haber")
        elif pred == "haber":
            return f"exist' ({y}) [MR0]", False
        #posesión alienable, inalienable y de parentesco
        elif pred in VERBOS_POSESION["tener"] and y != "Ø":
            if input_si_no(f"¿«{y[0].upper() + y[1:]}» es una parte constituyente de «{x}»? (s/n): "):
                return f"have.as.part' ({x}, {y})", False
            elif pred in ["tener", "poseer", "ostentar", "lucir"] and input_si_no(f"¿«{y[0].upper() + y[1:]}» indica una relación de parentesco? (s/n): "):
                return f"have.as.kin' ({x}, {y})", False
            else:
                return f"have' ({x}, {y})", False
    return None, False

def traducir_ls_a_ingles(ls_string):
    """
    Traduce constantes al inglés y las pone en NEGRITA.
    Incluye un diccionario de correcciones ampliado para evitar ambigüedades 
    donde el traductor confunde participios con sustantivos.
    """
    if not ls_string:
        return ls_string

    # Códigos ANSI para formato en terminal
    NEGRITA = "\033[1m"
    RESET = "\033[0m"
    
    # --- DICCIONARIO DE CORRECCIONES MANUALES ---
    CORRECCIONES = {
        "pintada": "painted", "pintado": "painted",
        "comida": "eaten", "comido": "eaten",
        "bebida": "drunk", "bebido": "drunk",
        "parada": "stopped", "parado": "stopped",
        "herida": "wounded", "herido": "wounded",
        "llamada": "called", "llamado": "called",
        "vista": "seen", "visto": "seen",
        "hecha": "made", "hecho": "made",
        "vuelta": "returned", "vuelto": "returned",
        "puesta": "put", "puesto": "put",
        "escrito": "written", "escrita": "written",
        "abierto": "open", "abierta": "open", 
        "rota": "broken", "roto": "broken",
        "muerto": "dead", "muerta": "dead", 
        "dicho": "said", "dicha": "said"
    }

    translator = GoogleTranslator(source='es', target='en')

    def reemplazar_match(match):
        constante = match.group(1) 
        
        # Variable para guardar la palabra final
        palabra_final = constante
        constante_lower = constante.lower()

        # 1. Si está en la lista de palabras reservadas RRG, no tocar
        if constante_lower in RRG_KEYWORDS:
            pass
            
        # 2. Si está en nuestro DICCIONARIO DE CORRECCIONES, usar esa versión
        elif constante_lower in CORRECCIONES:
            palabra_final = CORRECCIONES[constante_lower]
            
        # 3. Si no, intentar traducción normal
        else:
            texto_limpio = constante.replace(".", " ")
            if texto_limpio in CACHE_TRADUCCION:
                palabra_final = CACHE_TRADUCCION[texto_limpio]
            else:
                try:
                    traduccion = translator.translate(texto_limpio)
                    if traduccion:
                        palabra_final = traduccion.lower().strip().replace(" ", ".")
                        CACHE_TRADUCCION[texto_limpio] = palabra_final
                except Exception:
                    pass 

        return f"{NEGRITA}{palabra_final}'{RESET}"

    patron = r"\b([a-zA-Zñáéíóúü\._Ø0-9\-]+)'"
    ls_traducida = re.sub(patron, reemplazar_match, ls_string)
    return ls_traducida

def main():
    set_spanish_locale()
    limpiar_consola()
    print("""
Este programa puede asistirte en la formalización de la estructura lógica básica
de una cláusula.

Advertencia: el programa solo maneja cláusulas simples, con su estructura argumental
típica, y puede dar resultados inexactos en construcciones que las alteran.
          
(Escribe «...» en cualquier momento para reiniciar el análisis)
    """)
    
    while True:
        try:
            if len(sys.argv) > 3:
                AKT = sys.argv[1]
                oracion_original = sys.argv[2]
                flag = sys.argv[3]
                es_dinamico = True if flag == "dinamico" else False
                print(f"El aktionsart que obtuviste en «{oracion_original}» fue: {AKT.upper()}")
                sys.argv = sys.argv[:1]
            else:
                AKT = obtener_aktionsart()
                oracion_original = peticion("\nEscribe la cláusula de la que quieres obtener su estructura lógica: ")
                es_dinamico = verificar_dinamicidad(AKT, oracion_original)

            x, y, z = obtener_argumentos(oracion_original)
            operador = MODIFICADORES_AKT.get(AKT, "")
            pred = ""
            locus = "Ø"
            estructura_logica = None

            if estructura_logica is None:
                estructura_logica = verbos_doler_gustar(AKT, x, y, z, operador, es_dinamico, oracion_original)
            if estructura_logica is None:
                estructura_logica = hacer_meteorologico(x, y, oracion_original, operador, es_dinamico)
            if estructura_logica is None:
                estructura_logica = casos_impersonales(x, y, z, operador, es_dinamico)
            if estructura_logica is None:
                estructura_logica = casos_locativo_dativos(AKT, x, y, z, operador, es_dinamico)
            if estructura_logica is None:
                estructura_logica = verbos_OI(AKT, x, y, z, operador)
            if estructura_logica is None:
                estructura_logica = casos_especiales_estado(AKT, x, y, oracion_original)
            if estructura_logica is None:
                estructura_logica = informacion_mente(AKT, x, y, operador, es_dinamico, oracion_original)
            if estructura_logica is None:
                estructura_logica, locus = casos_locativos(estructura_logica, AKT, x, y, z, operador, es_dinamico, oracion_original)
            if estructura_logica is None:
                estructura_logica = complemento_regimen(AKT, x, y, operador, es_dinamico, oracion_original)
            
            # Obtener el valor de pred si no es un caso especial
            if estructura_logica is None and not pred:
                pred = obtener_predicado(AKT, y, es_dinamico)
            
            # Manejo de verbos especiales ingresados por el usuario
            es_verbo_reciproco = False
            if estructura_logica is None:
                estructura_logica, es_verbo_reciproco = predicados_especiales(AKT, x, y, z, pred, operador, es_dinamico, oracion_original)
            
            # Genera la estructura lógica si no se ha hecho hasta el momento
            if estructura_logica is None:
                estructura_logica = generar_estructura_logica(AKT, x, y, z, pred, locus, es_dinamico, oracion_original)
            
            # Adición de la capa de intencionalidad DO
            if not es_verbo_reciproco and x != "Ø":
                estructura_logica = aplicar_DO(oracion_original, x, estructura_logica, es_dinamico, AKT)
            
            # Verificación de construcción anticausativa (se + verbo con contraparte causativa)
            if AKT in ["realización", "logro", "proceso", "semelfactivo"] and y == "Ø":
                if input_si_no(f"¿El verbo de la cláusula está construido con el clítico «se» \ny tiene una contraparte causativa (ej: «romperse» / «romper»)? (s/n): "):
                    estructura_logica = f"[do' (Ø, Ø)] CAUSE [{estructura_logica}]"    

            # --- TRADUCCIÓN AUTOMÁTICA ---
            try:
                ls_ingles = traducir_ls_a_ingles(estructura_logica)
            except Exception as e:
                # Si algo falla (ej. sin internet), usamos la versión en español
                ls_ingles = estructura_logica
            
            print(f"\nLa estructura lógica es: {ls_ingles}")
            
            # Usamos ls_ingles para que los operadores se añadan sobre la versión traducida
            añadir_operadores(ls_ingles)

        except ReiniciarAnalisis:
            print("\n" + "-" * 30)
            print("Análisis reiniciado.")
            print("-" * 30)
            time.sleep(0.8)
            limpiar_consola()
            continue

        except ValueError as ve:
            print(f"\nError: {ve}")
        except Exception as e:
            print(f"\nHa ocurrido un error inesperado: {e}")
            print(f"Tipo de error: {type(e).__name__}")

        if not input_si_no("\n¿Quieres obtener la estructura lógica de otra cláusula? (s/n): "):
            time.sleep(1)
            return
        else:
            time.sleep(0.5)
            limpiar_consola()

if __name__ == "__main__":
    main()
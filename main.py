import os
import sys
import subprocess

# 1. ANCLA: Obligar a Python a trabajar en la carpeta donde está este archivo
# Esto soluciona el error "No such file or directory"
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 2. CONFIGURACIÓN: Textos originales y archivos asociados
PROGRAMAS = {
    "1": ("Identificar el aktionsart de un predicado (y, opcionalmente, obtener su estructura lógica)", "aktionsart.py"),
    "2": ("Obtener la estructura lógica de una cláusula (si ya conoces el aktionsart de su predicado)", "ls.py"),
    "3": ("English version (only for Aktionsart detection)", "english.py"),
    "4": ("Mostrar información sobre el programa", "info.py")
}

def limpiar():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    while True:
        limpiar()
        print("\n¿Qué quieres hacer?:\n")
        
        for key, (desc, _) in PROGRAMAS.items():
            print(f"{key}. {desc}")
        print("5. Salir")

        opcion = input("\nPor favor, selecciona una opción (1-5): ")

        if opcion == "5":
            print("\n¡Gracias por usar Vendler! Si tienes comentarios, críticas o preguntas, escribe a cgonzalv@uc.cl")
            break
        
        if opcion in PROGRAMAS:
            archivo_py = PROGRAMAS[opcion][1]
            try:
                print(f"\nEjecutando la opción elegida...\n")
                # Ejecutar usando el mismo Python del sistema (-u para salida inmediata)
                subprocess.run([sys.executable, "-u", archivo_py], check=True)
            except Exception as e:
                print(f"\nERROR: {e}")
            
            # Pausa de seguridad para leer resultados antes de borrar pantalla
            input("\nPresiona [Enter] para volver al menú principal...")
        else:
            input("\nOpción no válida. Por favor, intenta de nuevo.")

if __name__ == "__main__":
    main()
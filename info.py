# ------------------------------------------------------------------------------
# Vendler – Analizador Lingüístico RRG
# Copyright (c) 2025 Carlos González Vergara
# Licensed under CC BY-NC-SA 4.0
# https://creativecommons.org/licenses/by-nc-sa/4.0/deed.es
# ------------------------------------------------------------------------------

def main():
    print("""
───────────────────────────────────────────────
Autor: Carlos González Vergara (cgonzalv@uc.cl)
Versión: 1.0 (2025)
Lenguaje: Python
───────────────────────────────────────────────

Descripción general:
Vendler es una herramienta computacional diseñada para asistir en la detección del aktionsart (aspecto léxico) de predicados en español y en la formalización de estructuras lógicas dentro del marco teórico de la Gramática de Papel y Referencia (Role and Reference Grammar, RRG). El programa implementa, en forma interactiva, las principales pruebas diagnósticas morfosintácticas que permiten determinar en español la clase aspectual de un predicado y su representación lógica asociada.

Propósito y alcance:
El desarrollo de esta aplicación busca ofrecer un entorno guiado que facilite tanto la investigación lingüística como la enseñanza avanzada de gramática y semántica. A través de una interfaz de preguntas sucesivas, el usuario reproduce el razonamiento analítico de la RRG, respondiendo a pruebas que juzgan los rasgos de causatividad, estatividad, puntualidad, telicidad y dinamicidad. El sistema genera como salida una clasificación aspectual y una estructura lógica formalizada, siguiendo la notación propuesta por Van Valin (2005) y actualizada en Van Valin (2023).

Aporte académico:
El programa constituye una de las primeras implementaciones pedagógicas en español del modelo de RRG con capacidad interactiva. Su valor reside en trasladar procedimientos teóricos abstractos al plano operativo del análisis computacional, promoviendo la reproducibilidad del razonamiento lingüístico y la exploración empírica de los tipos de predicado.

Aplicaciones:
• Apoyo a la docencia universitaria en gramática general, semántica léxica y teoría de la predicación.
• Herramienta de verificación aspectual para estudios de corpus o descripciones verbales.
• Modelo de referencia para proyectos de lingüística computacional en español orientados a la semántica.

Licencia Creative Commons Atribución-NoComercial-CompartirIgual 4.0 Internacional (CC BY-NC-SA 4.0)
https://creativecommons.org/licenses/by-nc-sa/4.0/deed.es
───────────────────────────────────────────────
""")

    input("\nAprieta Enter para volver al menú principal... ")

if __name__ == "__main__":
    main()

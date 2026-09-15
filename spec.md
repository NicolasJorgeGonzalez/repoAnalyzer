# Especificación Técnica: Repo Analyzer CLI

## 1. Visión General
Herramienta CLI en Python que explora repositorios locales y utiliza Gemini para generar resúmenes arquitectónicos y evaluar la salud del código.

## 2. Stack Tecnológico
- **Lenguaje:** Python 3.14.4
- **CLI Framework:** Typer / Rich (interfaz visual amigable en terminal)
- **LLM Engine:** SDK oficial `google-genai` (Modelo recomendado: gemini-3.8-flash)

## 3. Requerimientos Funcionales (MVP)
- Comando `scan <path>`:
  - Recorre el directorio ignorando reglas de `.gitignore`, carpetas `.git`, `venv`, etc.
  - Genera un árbol de archivos visual y estadísticas básicas (cantidad de archivos por extensión).
- Comando `analyze <path>`:
  - Convierte la estructura e impresiones clave del código en un prompt estructurado para Gemini.
  - Genera un reporte formateado en Markdown sobre la arquitectura y sugerencias de mejora.

## 4. Criterios de Aceptación y Restricciones
- Filtrado estricto para evitar enviar archivos binarios o pesados a la API.
- Manejo elegante de excepciones cuando la API de Gemini devuelva un error o no haya conexión.
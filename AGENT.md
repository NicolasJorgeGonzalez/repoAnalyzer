# AGENT.md

## Stack Teclógico
- **Python**: 3.10+
- **Typer**: CLI Framework (`typer>=0.12.0`)
- **Rich**: Formato y visualización enriquecida en terminal (`rich>=13.0.0`)
- **Google GenAI SDK**: Integración con la API de Gemini (`google-genai>=0.1.0`)

## Convenciones de Código
- **Type Hints**: Uso obligatorio de anotaciones de tipos explícitas en funciones, métodos y argumentos.
- **Docstrings**: Documentación descriptiva en módulos, clases y funciones principales.
- **Estructura Modular**: Separación de responsabilidades dentro del paquete `repo_analyzer/` (e.g., CLI, scanner, config).
- **Formato y Salida**: Uso de Rich para renderizado de tablas, paneles y salida estructurada en la CLI.
- **Calidad de Código**: Código limpio, legible y respetando PEP 8.

## Comando para Ejecutar Tests
Para ejecutar la suite de pruebas unitarias de manera detallada:

```bash
python -m unittest discover tests -v
```

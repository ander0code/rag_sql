import os
from dotenv import load_dotenv, find_dotenv

print("=== DEBUG DE VARIABLES DE ENTORNO ===")

# Buscar archivo .env
env_file = find_dotenv()
print(f"Archivo .env encontrado: {env_file}")

# Cargar explícitamente
load_dotenv(env_file, override=True)

# Mostrar variables
deepseek_key = os.getenv("DEEPSEEK_API_KEY", "NO_ENCONTRADA")
openai_key = os.getenv("OPENAI_API_KEY", "NO_ENCONTRADA")

print(f"DEEPSEEK_API_KEY: {deepseek_key[:30]}..." if len(deepseek_key) > 30 else deepseek_key)
print(f"OPENAI_API_KEY: {openai_key[:30]}..." if len(openai_key) > 30 else openai_key)

# Verificar formato
print(f"Deepseek válida: {deepseek_key.startswith('sk-')}")
print(f"OpenAI válida: {openai_key.startswith('sk-')}")

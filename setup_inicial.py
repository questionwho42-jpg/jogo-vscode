import os

def criar_estrutura():
    # Lista de pastas para criar
    pastas = [
        "core",           # O motor do jogo
        "core/systems",   # Sistemas (Movimento, Combate)
        "core/components",# Componentes (Vida, Posição)
        "editor",         # O código da sua ferramenta visual
        "data",           # Onde os JSONs serão salvos
        "data/maps",
        "data/items",
        "assets",         # Imagens e sons
        "assets/sprites",
        "backup-modificações" # Para nossos backups de segurança
    ]

    for pasta in pastas:
        os.makedirs(pasta, exist_ok=True)
        print(f"[OK] Pasta criada: {pasta}")

    # Criar arquivo de dependências (bibliotecas que vamos usar)
    requirements = """pygame-ce
dearpygui
pydantic
"""
    with open("requirements.txt", "w") as f:
        f.write(requirements)
    print("[OK] Arquivo requirements.txt criado.")

    # Criar um arquivo main.py simples
    main_code = """import pygame

def main():
    print("O Mundo de Pandorha - Inicializando...")
    # Aqui começará o jogo

if __name__ == "__main__":
    main()
"""
    with open("main.py", "w") as f:
        f.write(main_code)
    print("[OK] Arquivo main.py criado.")

    print("\n--- Configuração Concluída ---")
    print("Agora execute: pip install -r requirements.txt")

if __name__ == "__main__":
    criar_estrutura()
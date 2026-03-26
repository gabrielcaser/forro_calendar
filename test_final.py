#!/usr/bin/env python3
"""Script de teste para verificar as correções"""
import subprocess
import sys

# Simular respostas: 1 (processar), s (extrair), N (não criar eventos)
process = subprocess.Popen(
    [sys.executable, "main.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd="C:\\Users\\gabri\\Documents\\Github\\Personal\\forro_calendar"
)

responses = ["1\n", "s\n", "N\n"]
try:
    output, _ = process.communicate(input="".join(responses), timeout=180)
    print("=== RESULTADO DO TESTE ===")
    print("NOVO MENU DISPONÍVEL:")
    print("  [1] processar post")
    print("  [2] usar Excel existente")
    print("  [3] apagar eventos dessa semana e criar novamente")
    print("  [4] sair")
    print()
    print("MODO AUTOMÁTICO (--auto):")
    print("  - Apaga automaticamente eventos da semana atual")
    print("  - Processa post e cria novos eventos")
    print()
    print(output)
    print("\n=== VERIFICAÇÃO DAS IMAGENS ===")
    # Verificar se imagens foram salvas
    import os
    temp_dir = "C:\\Users\\gabri\\Documents\\Github\\Personal\\forro_calendar\\data\\temp_images"
    if os.path.exists(temp_dir):
        files = os.listdir(temp_dir)
        print(f"Imagens salvas em temp_images: {len(files)} arquivo(s)")
        for f in files[:3]:  # mostrar primeiras 3
            print(f"  - {f}")
    else:
        print("Diretório temp_images não encontrado")
except subprocess.TimeoutExpired:
    process.kill()
    print("Script timeout!")

#!/usr/bin/env python3
"""Teste rápido das correções: limpeza de imagens e nomes de locais"""
import subprocess
import sys

print("=== TESTE DAS CORREÇÕES ===")
print("1. Imagens antigas serão removidas automaticamente")
print("2. Nomes de locais serão lidos corretamente (Godofredo (408n), etc.)")
print("3. 'contribuição voluntária' será reconhecida como preço")
print()

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
    output, _ = process.communicate(input="".join(responses), timeout=300)
    print("=== RESULTADO ===")
    print(output)

    # Verificar imagens salvas
    import os
    temp_dir = "C:\\Users\\gabri\\Documents\\Github\\Personal\\forro_calendar\\data\\temp_images"
    if os.path.exists(temp_dir):
        files = [f for f in os.listdir(temp_dir) if f.endswith('.jpg')]
        print(f"\n=== IMAGENS SALVAS ===")
        print(f"Total de imagens: {len(files)}")
        for f in files:
            file_path = os.path.join(temp_dir, f)
            size_kb = os.path.getsize(file_path) // 1024
            print(f"  - {f} ({size_kb} KB)")
    else:
        print("ERRO: Diretório temp_images não encontrado!")

except subprocess.TimeoutExpired:
    process.kill()
    print("Script timeout!")

#!/usr/bin/env python3
"""Script de teste para a opção 3: apagar eventos dessa semana e criar novamente"""
import subprocess
import sys

# Simular respostas: 3 (apagar e recriar), s (extrair), s (criar eventos)
process = subprocess.Popen(
    [sys.executable, "main.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd="C:\\Users\\gabri\\Documents\\Github\\Personal\\forro_calendar"
)

responses = ["3\n", "s\n", "s\n"]
try:
    output, _ = process.communicate(input="".join(responses), timeout=300)
    print("=== TESTE DA OPÇÃO 3: APAGAR E RECRIAR ===")
    print(output)
except subprocess.TimeoutExpired:
    process.kill()
    print("Script timeout!")

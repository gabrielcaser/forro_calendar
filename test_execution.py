#!/usr/bin/env python3
"""Script para testar a execução completa sem criar eventos"""
import subprocess
import sys
import time

# Simular respostas do usuário: 1 (processar), s (extrair Excel), N (não criar eventos)
process = subprocess.Popen(
    [sys.executable, "main.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd="C:\\Users\\gabri\\Documents\\Github\\Personal\\forro_calendar"
)

# Enviar respostas
responses = ["1\n", "s\n", "N\n"]
try:
    output, _ = process.communicate(input="".join(responses), timeout=120)
    print(output)
except subprocess.TimeoutExpired:
    process.kill()
    print("Script timeout!")

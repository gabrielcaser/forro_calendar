#!/usr/bin/env python3
"""Teste para mostrar como um evento ficaria no Google Calendar com o emoji"""
from src.excel_export import load_events_from_excel
from pathlib import Path

excel_file = Path("output/forro_agenda_2026-03-24.xlsx")
if excel_file.exists():
    events = load_events_from_excel(excel_file)
    print("=" * 80)
    print("EXEMPLO DE COMO EVENTOS FICARIAM NO GOOGLE CALENDAR")
    print("=" * 80)
    for i, event in enumerate(events[:3], 1):
        location = event.get("location", "Local a confirmar")
        description = event.get("description", "")
        price = event.get("price", "R$??")
        
        # Simular como fica a descrição no Calendar
        desc_parts = []
        if description:
            desc_parts.append(f"🎸 {description}")
        desc_parts.append(f"💵 Preço do ingresso: {price}")
        desc_parts.append("📸 Fonte: @lelele_godoy")
        
        print(f"\nEvento {i}:")
        print(f"  Data: {event.get('date')}")
        print(f"  Local: {location}")
        print(f"  Descrição no Calendar:")
        for line in desc_parts:
            print(f"    {line}")
else:
    print("Arquivo Excel não encontrado")

#!/usr/bin/env python3
from src.calendar_sync import get_calendar_service, get_or_create_forro_calendar

service = get_calendar_service()
calendar_id = get_or_create_forro_calendar(service)

# Listar eventos de março
events = service.events().list(calendarId=calendar_id, timeMax='2026-04-01T00:00:00Z').execute().get('items', [])
print(f'Encontrados {len(events)} eventos em março')
for event in events:
    summary = event['summary']
    print(f'Deletando: {summary}')
    service.events().delete(calendarId=calendar_id, eventId=event['id']).execute()
print('Todos os eventos foram removidos!')

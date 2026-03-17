import base64
import json
import logging
import os
from pathlib import Path

from openai import OpenAI

from src.config import INSTAGRAM_PROFILE, OPENAI_MODEL

log = logging.getLogger(__name__)

_PROMPT = (
    "Esta imagem é um cartaz de agenda de bailes de forró em Brasília/DF, Brasil.\n\n"
    "Extraia TODOS os eventos da agenda, independente do dia da semana.\n"
    "Para cada evento retorne:\n"
    "  • day_of_week: dia da semana em português (ex: 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo')\n"
    "  • date: data no formato 'DD/MM' ou 'DD/MM/YYYY'\n"
    "  • time: horário de início no formato 'HH:MM', ou null se não informado\n"
    "  • location: nome do local / clube\n"
    "  • description: bandas, artistas ou detalhes adicionais (string vazia se nenhum)\n"
    "  • price: preço do ingresso (string com R$?? se nenhum)\n\n"
    "Responda SOMENTE com JSON válido, exatamente neste formato:\n"
    '{"events": [{"day_of_week": "...", "date": "DD/MM", "time": "HH:MM ou null", '
    '"location": "...", "description": "...", "price": "..."}]}'
    'Se não houver eventos, retorne: {"events": []}'
)


def extract_events_from_images(image_paths: list[Path]) -> list[dict]:
    """
    Send each image to GPT-4o Vision and return a list of event dicts:
      {day_of_week, date, time, location, description}
    Events for all days of the week are extracted.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY não configurada no arquivo .env")
    client = OpenAI(api_key=api_key)

    all_events: list[dict] = []
    for img_path in image_paths:
        image_b64 = base64.b64encode(img_path.read_bytes()).decode()
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=1500,
                response_format={"type": "json_object"},
            )
            raw    = response.choices[0].message.content
            events = json.loads(raw).get("events", [])
            log.info(f"{img_path.name}: {len(events)} evento(s) encontrado(s)")
            all_events.extend(events)
        except json.JSONDecodeError as exc:
            log.error(f"Resposta da IA não é JSON válido ({img_path.name}): {exc}")
        except Exception as exc:
            log.error(f"Erro ao processar imagem {img_path.name}: {exc}")

    return all_events

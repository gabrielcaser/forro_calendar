#!/usr/bin/env python3
"""
Forro Calendar Automation
Monitors Instagram @lelele_godoy for "Agenda bailes de forro (DF)" posts
and adds Friday/Saturday/Sunday events to Google Calendar.

Run every Tuesday at 8am via Windows Task Scheduler (see README.md).
"""

import os
import json
import base64
import logging
import requests
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import instaloader
from openai import OpenAI
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

INSTAGRAM_PROFILE = "lelele_godoy"
POST_KEYWORD = "Agenda bailes de forró (DF)"
CALENDAR_ID = os.getenv("CALENDAR_ID", "primary")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TZ = "America/Sao_Paulo"

CREDENTIALS_FILE = BASE_DIR / "google_credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"
PROCESSED_FILE = BASE_DIR / "processed_posts.json"
TEMP_DIR = BASE_DIR / "temp_images"
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "forro_calendar.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers: processed-posts tracking
# ---------------------------------------------------------------------------
def load_processed() -> set:
    if PROCESSED_FILE.exists():
        return set(json.loads(PROCESSED_FILE.read_text(encoding="utf-8")))
    return set()


def mark_processed(shortcode: str) -> None:
    posts = load_processed()
    posts.add(shortcode)
    PROCESSED_FILE.write_text(json.dumps(sorted(posts), ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Google Calendar
# ---------------------------------------------------------------------------
def get_calendar_service():
    """Return an authenticated Google Calendar service, triggering OAuth if needed."""
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"Arquivo de credenciais não encontrado: {CREDENTIALS_FILE}\n"
                    "Siga as instruções do README.md para baixar o google_credentials.json."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return build("calendar", "v3", credentials=creds)


# ---------------------------------------------------------------------------
# Instagram
# ---------------------------------------------------------------------------
def find_forro_post(max_posts: int = 25) -> Optional[instaloader.Post]:
    """Return the most recent post containing POST_KEYWORD from INSTAGRAM_PROFILE."""
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        post_metadata_txt_pattern="",
        quiet=True,
    )

    ig_user = os.getenv("INSTAGRAM_USERNAME", "").strip()
    ig_pass = os.getenv("INSTAGRAM_PASSWORD", "").strip()
    if ig_user and ig_pass:
        try:
            L.login(ig_user, ig_pass)
            log.info(f"Instagram: logado como @{ig_user}")
        except Exception as exc:
            log.warning(f"Instagram: falha ao logar (continuando sem login): {exc}")

    try:
        profile = instaloader.Profile.from_username(L.context, INSTAGRAM_PROFILE)
        log.info(f"Instagram: verificando @{INSTAGRAM_PROFILE} ({profile.mediacount} posts) ...")
        for i, post in enumerate(profile.get_posts()):
            if i >= max_posts:
                break
            caption = post.caption or ""
            if POST_KEYWORD.lower() in caption.lower():
                log.info(f"Post encontrado: {post.shortcode}  (publicado em {post.date_utc.date()})")
                return post
    except Exception as exc:
        log.error(f"Erro ao acessar Instagram: {exc}")

    return None


def download_post_images(post: instaloader.Post) -> list[Path]:
    """Download all images from a post and return their local paths."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    if post.typename == "GraphSidecar":
        urls = [node.display_url for node in post.get_sidecar_nodes() if not node.is_video]
    else:
        urls = [post.url]

    paths = []
    for i, url in enumerate(urls):
        dest = TEMP_DIR / f"{post.shortcode}_{i}.jpg"
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            paths.append(dest)
            log.info(f"Imagem baixada: {dest.name} ({len(resp.content) // 1024} KB)")
        except Exception as exc:
            log.error(f"Falha ao baixar imagem {i+1}: {exc}")

    return paths


# ---------------------------------------------------------------------------
# AI Vision – event extraction
# ---------------------------------------------------------------------------
def extract_events_from_images(image_paths: list[Path]) -> list[dict]:
    """
    Send each image to GPT-4o Vision and return a list of event dicts:
    {day_of_week, date, time, location, description}
    Only Friday/Saturday/Sunday events are requested.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY não configurada no arquivo .env")
    client = OpenAI(api_key=api_key)

    prompt = (
        "Esta imagem é um cartaz de agenda de bailes de forró em Brasília/DF, Brasil.\n\n"
        "Extraia APENAS os eventos de SEXTA-FEIRA, SÁBADO e DOMINGO.\n"
        "Para cada evento retorne:\n"
        "  • day_of_week: 'sexta', 'sábado' ou 'domingo'\n"
        "  • date: data no formato 'DD/MM' ou 'DD/MM/YYYY'\n"
        "  • time: horário de início no formato 'HH:MM', ou null se não informado\n"
        "  • location: nome do local / clube\n"
        "  • description: bandas, artistas ou detalhes adicionais (string vazia se nenhum)\n\n"
        "Responda SOMENTE com JSON válido, exatamente neste formato:\n"
        '{"events": [{"day_of_week": "...", "date": "DD/MM", "time": "HH:MM ou null", '
        '"location": "...", "description": "..."}]}\n\n'
        "Se não houver eventos de sexta/sábado/domingo, retorne: {\"events\": []}"
    )

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
                            {"type": "text", "text": prompt},
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
            raw = response.choices[0].message.content
            result = json.loads(raw)
            events = result.get("events", [])
            log.info(f"{img_path.name}: {len(events)} evento(s) encontrado(s)")
            all_events.extend(events)
        except json.JSONDecodeError as exc:
            log.error(f"Resposta da IA não é JSON válido ({img_path.name}): {exc}")
        except Exception as exc:
            log.error(f"Erro ao processar imagem {img_path.name}: {exc}")

    return all_events


# ---------------------------------------------------------------------------
# Calendar event creation
# ---------------------------------------------------------------------------
def resolve_date(date_str: str) -> date:
    """Parse 'DD/MM' or 'DD/MM/YYYY', choosing the nearest future date."""
    today = date.today()
    parts = date_str.strip().split("/")
    if len(parts) == 3:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
    day, month = int(parts[0]), int(parts[1])
    for year in [today.year, today.year + 1]:
        try:
            candidate = date(year, month, day)
            if candidate >= today - timedelta(days=1):
                return candidate
        except ValueError:
            pass
    raise ValueError(f"Não foi possível resolver a data: {date_str!r}")


def event_exists(service, event_date: date, location: str) -> bool:
    """Return True if a Google Calendar event for this date+location already exists."""
    try:
        time_min = f"{event_date.isoformat()}T00:00:00-03:00"
        time_max = f"{event_date.isoformat()}T23:59:59-03:00"
        items = (
            service.events()
            .list(
                calendarId=CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
            )
            .execute()
            .get("items", [])
        )
        return any(location.lower() in ev.get("summary", "").lower() for ev in items)
    except Exception as exc:
        log.warning(f"Não foi possível verificar duplicatas: {exc}")
        return False


def add_event(service, event: dict) -> bool:
    """Add one forró event to Google Calendar. Returns True if created."""
    try:
        event_date = resolve_date(event["date"])
    except Exception as exc:
        log.error(f"Data inválida '{event.get('date')}': {exc}")
        return False

    location = event.get("location") or "Local a confirmar"
    start_time = event.get("time") or "21:00"
    try:
        h, m = map(int, start_time.split(":"))
    except Exception:
        h, m = 21, 0
    end_h = (h + 4) % 24

    start_str = f"{event_date.isoformat()}T{h:02d}:{m:02d}:00"
    end_str   = f"{event_date.isoformat()}T{end_h:02d}:{m:02d}:00"
    summary   = f"🎵 Forró — {location}"

    desc_parts = []
    if event.get("description"):
        desc_parts.append(event["description"])
    desc_parts.append(f"📸 Fonte: @{INSTAGRAM_PROFILE}")

    if event_exists(service, event_date, location):
        log.info(f"Evento já existe (pulando): {summary} em {event_date}")
        return False

    body = {
        "summary": summary,
        "location": location,
        "description": "\n".join(desc_parts),
        "start": {"dateTime": start_str, "timeZone": TZ},
        "end":   {"dateTime": end_str,   "timeZone": TZ},
        "colorId": "3",  # Grape / roxo
    }
    result = service.events().insert(calendarId=CALENDAR_ID, body=body).execute()
    log.info(f"✅ Criado: {summary} em {event_date}  →  {result.get('htmlLink')}")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    log.info("=" * 60)
    log.info("Forró Calendar Automation — Iniciando")
    log.info("=" * 60)

    # 1. Busca o post no Instagram
    post = find_forro_post()
    if not post:
        log.warning("Nenhum post encontrado com a palavra-chave. Encerrando.")
        return

    # 2. Pula se já foi processado
    if post.shortcode in load_processed():
        log.info(f"Post {post.shortcode} já foi processado anteriormente. Encerrando.")
        return

    # 3. Baixa imagens
    images = download_post_images(post)
    if not images:
        log.error("Nenhuma imagem baixada. Encerrando.")
        return

    # 4. Extrai eventos via IA
    events = extract_events_from_images(images)
    if not events:
        log.warning("Nenhum evento extraído das imagens.")
    else:
        log.info(f"Total de eventos extraídos: {len(events)}")

    # 5. Adiciona ao Google Calendar
    calendar_svc = get_calendar_service()
    added = sum(add_event(calendar_svc, ev) for ev in events)
    log.info(f"Eventos adicionados ao calendário: {added}/{len(events)}")

    # 6. Marca post como processado
    mark_processed(post.shortcode)

    # 7. Limpa imagens temporárias
    for p in images:
        p.unlink(missing_ok=True)
    if TEMP_DIR.exists() and not any(TEMP_DIR.iterdir()):
        TEMP_DIR.rmdir()

    log.info("Concluído!")


if __name__ == "__main__":
    main()

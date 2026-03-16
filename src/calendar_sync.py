import logging
from datetime import date, datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.config import (
    CALENDAR_ID_FILE, CALENDAR_NAME, CREDENTIALS_FILE, INSTAGRAM_PROFILE,
    SCOPES, TOKEN_FILE, TZ,
)

log = logging.getLogger(__name__)


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


def get_or_create_forro_calendar(service) -> str:
    """
    Return the calendar ID of the dedicated forró calendar.
    Creates the calendar the first time and persists the ID to CALENDAR_ID_FILE.
    """
    CALENDAR_ID_FILE.parent.mkdir(parents=True, exist_ok=True)

    if CALENDAR_ID_FILE.exists():
        cal_id = CALENDAR_ID_FILE.read_text(encoding="utf-8").strip()
        log.info(f"Usando calendário existente: {CALENDAR_NAME} ({cal_id[:24]}…)")
        return cal_id

    # Check if it already exists on Google's side (e.g. after a file reset)
    calendars = service.calendarList().list().execute().get("items", [])
    for cal in calendars:
        if cal.get("summary") == CALENDAR_NAME:
            cal_id = cal["id"]
            CALENDAR_ID_FILE.write_text(cal_id, encoding="utf-8")
            log.info(f"Calendário encontrado no Google: {CALENDAR_NAME} ({cal_id[:24]}…)")
            return cal_id

    # Create it
    body = {
        "summary": CALENDAR_NAME,
        "description": "Agenda automática de bailes de forró pé-de-serra no DF, gerada a partir do @lelele_godoy.",
        "timeZone": TZ,
        "backgroundColor": "#4B2E83",
    }
    new_cal = service.calendars().insert(body=body).execute()
    cal_id  = new_cal["id"]
    CALENDAR_ID_FILE.write_text(cal_id, encoding="utf-8")
    log.info(f"✅ Calendário criado: {CALENDAR_NAME} ({cal_id[:24]}…)")
    return cal_id


def resolve_date(date_str: str) -> date:
    """Parse 'DD/MM' or 'DD/MM/YYYY', choosing the nearest occurrence (allows past week)."""
    today = date.today()
    parts = date_str.strip().split("/")
    if len(parts) == 3:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
    day, month = int(parts[0]), int(parts[1])
    for year in [today.year, today.year + 1]:
        try:
            candidate = date(year, month, day)
            if candidate >= today - timedelta(days=7):
                return candidate
        except ValueError:
            pass
    raise ValueError(f"Não foi possível resolver a data: {date_str!r}")


def event_exists(service, calendar_id: str, event_date: date, location: str) -> bool:
    """Return True if a Google Calendar event for this date+location already exists."""
    try:
        time_min = f"{event_date.isoformat()}T00:00:00-03:00"
        time_max = f"{event_date.isoformat()}T23:59:59-03:00"
        items = (
            service.events()
            .list(
                calendarId=calendar_id,
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


def add_event(service, calendar_id: str, event: dict) -> bool:
    """Add one forró event to Google Calendar. Returns True if created."""
    try:
        event_date = resolve_date(event["date"])
    except Exception as exc:
        log.error(f"Data inválida '{event.get('date')}': {exc}")
        return False

    location   = event.get("location") or "Local a confirmar"
    start_time = event.get("time") or "21:00"
    try:
        h, m = map(int, start_time.split(":"))
    except Exception:
        h, m = 21, 0

    end_h        = (h + 4) % 24
    end_date     = event_date + timedelta(days=1) if end_h < h else event_date

    # Use pre-computed end time from event dict if available
    time_end = event.get("time_end")
    if time_end and time_end != "—":
        try:
            end_h, end_m = map(int, time_end.split(":"))
            end_date = event_date + timedelta(days=1) if end_h < h else event_date
        except Exception:
            end_m = m
    else:
        end_m = m

    start_str = f"{event_date.isoformat()}T{h:02d}:{m:02d}:00"
    end_str   = f"{end_date.isoformat()}T{end_h:02d}:{end_m:02d}:00"
    summary   = f"🎵 Forró — {location}"

    desc_parts = []
    if event.get("description"):
        desc_parts.append(event["description"])
    desc_parts.append(f"📸 Fonte: @{INSTAGRAM_PROFILE}")

    if event_exists(service, calendar_id, event_date, location):
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
    result = service.events().insert(calendarId=calendar_id, body=body).execute()
    log.info(f"✅ Criado: {summary} em {event_date}  →  {result.get('htmlLink')}")
    return True

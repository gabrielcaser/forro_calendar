#!/usr/bin/env python3
"""
Forró Calendar Automation
Monitors Instagram @lelele_godoy for agenda posts and adds
Friday/Saturday/Sunday events to Google Calendar.

Run every Tuesday at 8am via Windows Task Scheduler (see README.md).
"""

import logging
import sys
import warnings
from datetime import datetime, timedelta
from typing import Optional

# Suppress FutureWarning messages about Python version
warnings.filterwarnings("ignore", category=FutureWarning)

# ── Logging must be configured before the src modules are used ────────────────
from src.config import LOGS_DIR

LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "forro_calendar.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ── Application imports ───────────────────────────────────────────────────────
from src.calendar_sync import add_event, get_calendar_service, get_or_create_forro_calendar
from src.config        import TEMP_DIR
from src.excel_export  import export_to_excel, get_excel_path_for_today, load_events_from_excel
from src.instagram     import download_post_images, find_forro_post
from src.utils         import load_processed, mark_processed
from src.vision        import extract_events_from_images


def _delete_current_week_events() -> int:
    """Delete all events from the current week and return the count of deleted events."""
    try:
        calendar_svc = get_calendar_service()
        calendar_id = get_or_create_forro_calendar(calendar_svc)

        # Get current week (Monday to Sunday)
        today = datetime.now().date()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)

        time_min = f"{monday.isoformat()}T00:00:00-03:00"
        time_max = f"{sunday.isoformat()}T23:59:59-03:00"

        events = calendar_svc.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True
        ).execute().get('items', [])

        deleted_count = 0
        for event in events:
            summary = event.get('summary', 'Unknown')
            log.info(f"Deletando evento da semana: {summary}")
            calendar_svc.events().delete(calendarId=calendar_id, eventId=event['id']).execute()
            deleted_count += 1

        log.info(f"Eventos deletados da semana atual: {deleted_count}")
        return deleted_count
    except Exception as e:
        log.error(f"Erro ao deletar eventos da semana: {e}")
        return 0


def main(auto: bool = False) -> None:
    log.info("=" * 60)
    log.info("Forró Calendar Automation — Iniciando%s", " [AUTO]" if auto else "")
    log.info("=" * 60)

    # 1. Busca o post no Instagram
    post = find_forro_post()
    today_excel = get_excel_path_for_today()

    if auto:
        if not post:
            log.warning("Nenhum post encontrado com a palavra-chave. Encerrando (modo automático).")
            return
    else:
        if today_excel.exists():
            choice = input("Escolha: [1] processar post, [2] usar Excel existente, [3] apagar eventos dessa semana e criar novamente, [4] sair [1/2/3/4]: ").strip()
            if choice == "2":
                events = load_events_from_excel(today_excel)
                log.info(f"{len(events)} evento(s) carregado(s) do Excel existente.")
                _pedir_calendar(None, events)
                return
            if choice == "3":
                log.info("Apagando eventos da semana atual...")
                deleted = _delete_current_week_events()
                log.info(f"{deleted} evento(s) deletado(s). Continuando processamento...")
                # Continue with normal processing
            elif choice == "4":
                log.info("Execução cancelada pelo usuário.")
                return
        if not post:
            log.warning("Nenhum post encontrado com a palavra-chave.")
            if today_excel.exists():
                events = load_events_from_excel(today_excel)
                log.info(f"{len(events)} evento(s) carregado(s) do Excel existente.")
                _pedir_calendar(None, events)
            else:
                log.error("Não há post e não há Excel para extrair. Encerrando.")
            return

    # 2. Avisa se já foi processado, mas deixa o usuário continuar
    if post and post.get("shortcode") in load_processed():
        if auto:
            log.info("Post já foi processado, mas continuando em modo automático.")
        else:
            resp = input(f"Post {post['shortcode']} já foi processado anteriormente. Continuar mesmo assim? [s/N] ").strip().lower()
            if resp != "s":
                log.info("Usuário optou por não seguir para baixar o post.")
                if today_excel.exists():
                    events = load_events_from_excel(today_excel)
                    log.info(f"{len(events)} evento(s) carregado(s) do Excel existente.")
                    _pedir_calendar(post, events)
                    return
                log.info("Nenhum Excel de hoje encontrado. Vou tentar continuar com o post mesmo assim.")

    # 3. Verifica se já existe Excel de hoje
    if today_excel.exists():
        if auto:
            log.info("Excel de hoje já existe, mas extraindo novamente em modo automático.")
        else:
            resposta = input(f"Excel de hoje já existe ({today_excel.name}). Extrair novamente e substituir? [s/N] ").strip().lower()
            if resposta != "s":
                log.info("Extração pulada. Usando Excel existente.")
                events = load_events_from_excel(today_excel)
                log.info(f"{len(events)} evento(s) carregado(s) do Excel existente.")
                _pedir_calendar(post, events)
                return

    # 4. Baixa imagens
    images = download_post_images(post)
    if not images:
        log.warning("Nenhuma imagem baixada.")
        if today_excel.exists():
            events = load_events_from_excel(today_excel)
            log.info(f"{len(events)} evento(s) carregado(s) do Excel existente.")
            if auto:
                _criar_calendar(post, events)
            else:
                _pedir_calendar(post, events)
            return
        log.error("Nenhum Excel de hoje para continuar. Encerrando.")
        return

    # 5. Extrai eventos via IA
    events = extract_events_from_images(images)
    if not events:
        log.warning("Nenhum evento extraído das imagens.")
    else:
        log.info(f"Total de eventos extraídos: {len(events)}")

    # 6. Exporta Excel
    if events:
        excel_path = export_to_excel(events)
        log.info(f"Agenda exportada: {excel_path.name}")

    # 7. Adiciona ao Google Calendar
    log.info(f"Iniciando criação de eventos no Google Calendar (auto={auto}, eventos={len(events)})")
    try:
        if auto:
            _criar_calendar(post, events)
        else:
            _pedir_calendar(post, events)
    except Exception as e:
        log.error(f"Erro ao criar eventos no Calendar: {e}", exc_info=True)

    # 8. Limpa imagens temporárias (apenas em modo automático)
    if auto:
        for p in images:
            p.unlink(missing_ok=True)
        if TEMP_DIR.exists() and not any(TEMP_DIR.iterdir()):
            TEMP_DIR.rmdir()
    else:
        log.info(f"Imagens mantidas em: {TEMP_DIR}")

    log.info("Concluído!")


def _criar_calendar(post: Optional[dict], events: list[dict]) -> None:
    """Cria eventos no Google Calendar sem perguntar (modo automático)."""
    if not events:
        log.warning("Nenhum evento disponível para o Calendar.")
        return

    # Delete current week events first (automatic mode)
    log.info("Apagando eventos da semana atual (modo automático)...")
    deleted = _delete_current_week_events()

    calendar_svc = get_calendar_service()
    calendar_id  = get_or_create_forro_calendar(calendar_svc)
    added = sum(add_event(calendar_svc, calendar_id, ev) for ev in events)
    log.info(f"Eventos adicionados ao calendário: {added}/{len(events)}")
    if post is not None and "shortcode" in post:
        mark_processed(post["shortcode"])


def _pedir_calendar(post: Optional[dict], events: list[dict]) -> None:
    """Pergunta ao usuário se deve criar os eventos no Google Calendar."""
    if not events:
        log.warning("Nenhum evento disponível para o Calendar.")
        return
    criar = input(f"{len(events)} evento(s) disponível(is). Criar no Google Calendar? [s/N] ").strip().lower()
    if criar != "s":
        log.info("Criação de eventos no Calendar pulada pelo usuário.")
        if post is not None and "shortcode" in post:
            mark_processed(post["shortcode"])
        return
    _criar_calendar(post, events)


if __name__ == "__main__":
    auto = "--auto" in sys.argv
    main(auto=auto)


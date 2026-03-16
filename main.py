#!/usr/bin/env python3
"""
Forró Calendar Automation
Monitors Instagram @lelele_godoy for agenda posts and adds
Friday/Saturday/Sunday events to Google Calendar.

Run every Tuesday at 8am via Windows Task Scheduler (see README.md).
"""

import logging
import sys

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


def main(auto: bool = False) -> None:
    log.info("=" * 60)
    log.info("Forró Calendar Automation — Iniciando%s", " [AUTO]" if auto else "")
    log.info("=" * 60)

    # 1. Busca o post no Instagram
    post = find_forro_post()
    if not post:
        log.warning("Nenhum post encontrado com a palavra-chave. Encerrando.")
        return

    # 2. Avisa se já foi processado, mas deixa o usuário continuar
    if post["shortcode"] in load_processed():
        if auto:
            log.info(f"Post {post['shortcode']} já foi processado. Encerrando (modo automático).")
            return
        resp = input(f"Post {post['shortcode']} já foi processado anteriormente. Continuar mesmo assim? [s/N] ").strip().lower()
        if resp != "s":
            log.info("Execução cancelada pelo usuário.")
            return

    # 3. Verifica se já existe Excel de hoje
    today_excel = get_excel_path_for_today()
    if today_excel.exists():
        if auto:
            log.info("Excel de hoje já existe. Usando existente (modo automático).")
            events = load_events_from_excel(today_excel)
            log.info(f"{len(events)} evento(s) carregado(s) do Excel existente.")
            _criar_calendar(post, events)
            return
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
        log.error("Nenhuma imagem baixada. Encerrando.")
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
    if auto:
        _criar_calendar(post, events)
    else:
        _pedir_calendar(post, events)

    # 8. Limpa imagens temporárias
    for p in images:
        p.unlink(missing_ok=True)
    if TEMP_DIR.exists() and not any(TEMP_DIR.iterdir()):
        TEMP_DIR.rmdir()

    log.info("Concluído!")


def _criar_calendar(post: dict, events: list[dict]) -> None:
    """Cria eventos no Google Calendar sem perguntar (modo automático)."""
    if not events:
        log.warning("Nenhum evento disponível para o Calendar.")
        return
    calendar_svc = get_calendar_service()
    calendar_id  = get_or_create_forro_calendar(calendar_svc)
    added = sum(add_event(calendar_svc, calendar_id, ev) for ev in events)
    log.info(f"Eventos adicionados ao calendário: {added}/{len(events)}")
    mark_processed(post["shortcode"])


def _pedir_calendar(post: dict, events: list[dict]) -> None:
    """Pergunta ao usuário se deve criar os eventos no Google Calendar."""
    if not events:
        log.warning("Nenhum evento disponível para o Calendar.")
        return
    criar = input(f"{len(events)} evento(s) disponível(is). Criar no Google Calendar? [s/N] ").strip().lower()
    if criar != "s":
        log.info("Criação de eventos no Calendar pulada pelo usuário.")
        mark_processed(post["shortcode"])
        return
    _criar_calendar(post, events)


if __name__ == "__main__":
    auto = "--auto" in sys.argv
    main(auto=auto)


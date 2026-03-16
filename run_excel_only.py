"""
Script para rodar apenas Instagram + Vision + Excel (sem Google Calendar).
Usado para gerar o Excel com dados reais antes de configurar o Google.
"""
import logging
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

from src.instagram    import download_post_images, find_forro_post
from src.vision       import extract_events_from_images
from src.excel_export import export_to_excel, get_excel_path_for_today
from src.utils        import load_processed
from src.config       import TEMP_DIR

# ── Verifica se já existe Excel de hoje ─────────────────────────────────────────────
today_excel = get_excel_path_for_today()
if today_excel.exists():
    resposta = input(f"Excel de hoje já existe ({today_excel.name}). Extrair novamente e substituir? [s/N] ").strip().lower()
    if resposta != "s":
        log.info("Extração cancelada pelo usuário. Arquivo existente mantido.")
        exit(0)

post = find_forro_post()
if not post:
    log.warning("Nenhum post encontrado.")
    exit(1)

log.info(f"Post: {post['shortcode']} — {len(post['image_urls'])} imagem(ns)")

images = download_post_images(post)
log.info(f"{len(images)} imagem(ns) baixada(s)")

events = extract_events_from_images(images)
log.info(f"{len(events)} evento(s) extraído(s)")

if events:
    path = export_to_excel(events)
    log.info(f"Excel gerado: {path}")
    for ev in events:
        log.info(f"  {ev.get('day_of_week'):8s} {ev.get('date'):7s} {ev.get('time') or '--:--':6s}  {ev.get('location')}")
else:
    log.warning("Nenhum evento extraído das imagens.")

for p in images:
    p.unlink(missing_ok=True)
    p.unlink(missing_ok=True)

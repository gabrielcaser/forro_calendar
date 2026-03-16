import logging
import os
from pathlib import Path
from typing import Optional

import instaloader
import requests

from src.config import INSTAGRAM_PROFILE, IG_SESSION_FILE, POST_KEYWORD, TEMP_DIR

log = logging.getLogger(__name__)


def _make_instaloader_with_session() -> instaloader.Instaloader:
    """Return an Instaloader instance with session loaded (or fresh login)."""
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
    if ig_user:
        try:
            session_file = Path(str(IG_SESSION_FILE) + f"-{ig_user}")
            if session_file.exists():
                L.load_session_from_file(ig_user, str(session_file))
                log.info(f"Instagram: sessão carregada para @{ig_user}")
            elif ig_pass:
                L.login(ig_user, ig_pass)
                L.save_session_to_file(str(session_file))
                log.info(f"Instagram: logado e sessão salva para @{ig_user}")
            else:
                log.warning("Instagram: INSTAGRAM_PASSWORD não configurada, sem login.")
        except Exception as exc:
            log.warning(f"Instagram: falha ao logar (continuando sem login): {exc}")
    return L


def find_forro_post(max_posts: int = 25) -> Optional[dict]:
    """
    Return a dict for the most recent agenda post from INSTAGRAM_PROFILE:
      {shortcode, typename, image_urls}
    Uses the web_profile_info endpoint to avoid blocked GraphQL queries.
    """
    L = _make_instaloader_with_session()
    try:
        headers = {
            "User-Agent": L.context.user_agent,
            "X-IG-App-ID": "936619743392459",
            "Referer": "https://www.instagram.com/",
        }
        resp = L.context._session.get(
            "https://www.instagram.com/api/v1/users/web_profile_info/",
            params={"username": INSTAGRAM_PROFILE},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        edges = resp.json()["data"]["user"]["edge_owner_to_timeline_media"]["edges"]
        log.info(f"Instagram: {len(edges)} posts recentes obtidos de @{INSTAGRAM_PROFILE}")

        for edge in edges[:max_posts]:
            node = edge["node"]
            caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
            caption = caption_edges[0]["node"]["text"] if caption_edges else ""
            if POST_KEYWORD.lower() in caption.lower():
                shortcode = node["shortcode"]
                typename  = node["__typename"]
                log.info(f"Post encontrado: {shortcode} (tipo: {typename})")
                if typename == "GraphSidecar":
                    image_urls = [
                        e["node"]["display_url"]
                        for e in node.get("edge_sidecar_to_children", {}).get("edges", [])
                        if not e["node"].get("is_video")
                    ]
                else:
                    image_urls = [node["display_url"]]
                return {"shortcode": shortcode, "typename": typename, "image_urls": image_urls}
    except Exception as exc:
        log.error(f"Erro ao acessar Instagram: {exc}")

    return None


def download_post_images(post: dict) -> list[Path]:
    """Download all images from a post dict and return their local paths."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    paths = []
    for i, url in enumerate(post.get("image_urls", [])):
        dest = TEMP_DIR / f"{post['shortcode']}_{i}.jpg"
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            paths.append(dest)
            log.info(f"Imagem baixada: {dest.name} ({len(resp.content) // 1024} KB)")
        except Exception as exc:
            log.error(f"Falha ao baixar imagem {i+1}: {exc}")
    return paths

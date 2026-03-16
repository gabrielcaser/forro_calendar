import json

from src.config import PROCESSED_FILE


def load_processed() -> set:
    if PROCESSED_FILE.exists():
        return set(json.loads(PROCESSED_FILE.read_text(encoding="utf-8")))
    return set()


def mark_processed(shortcode: str) -> None:
    posts = load_processed()
    posts.add(shortcode)
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_FILE.write_text(
        json.dumps(sorted(posts), ensure_ascii=False, indent=2), encoding="utf-8"
    )

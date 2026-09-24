"""把 content/*.json 拼成给小程序的内容清单。

两个刻意的设计：

1. 清单里只放相对路径（/portfolio-images/...），域名由小程序自己拼。换域名只改小程序一处。

2. 每个图片 URL 都带 ?v=<版本号>，版本号覆盖内容 JSON 和图片文件本身的 size/mtime。
   小程序因此可以放心用一年期的强缓存；而换了图或改了文案之后版本号跟着变，
   URL 变了就立刻拿到新的，不会看到旧图。把文件名相同的图换掉也能生效。
"""

import hashlib
import json
import threading
from pathlib import Path

from PIL import Image

from .config import CONTENT_DIR, FULL_DIR, IMAGE_PREFIX

_lock = threading.Lock()
_size_cache: dict[str, tuple[float, int, int]] = {}


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def _image_size(path: Path) -> tuple[int, int]:
    st = path.stat()
    key = str(path)
    cached = _size_cache.get(key)
    if cached and cached[0] == st.st_mtime:
        return cached[1], cached[2]
    with Image.open(path) as im:
        width, height = im.size
    _size_cache[key] = (st.st_mtime, width, height)
    return width, height


def version() -> str:
    """内容版本号 = 内容 JSON + 原图文件状态的哈希。"""
    digest = hashlib.sha1()
    files = sorted(CONTENT_DIR.glob("*.json"))
    files += sorted(FULL_DIR.glob("*.jpg"))
    for path in files:
        st = path.stat()
        digest.update(f"{path.name}|{st.st_size}|{int(st.st_mtime)}\n".encode())
    return digest.hexdigest()[:8]


def _describe(file_name: str, suffix: str) -> dict:
    """给一张图生成 {thumb, full, w, h}；文件不在就标 missing（前端跳过，别放破图）。"""
    path = FULL_DIR / file_name
    if not path.is_file():
        return {"missing": True, "thumb": None, "full": None}
    width, height = _image_size(path)
    return {
        "thumb": f"{IMAGE_PREFIX}/thumb/{file_name}{suffix}",
        "full": f"{IMAGE_PREFIX}/full/{file_name}{suffix}",
        "w": width,
        "h": height,
    }


def missing_files() -> list[str]:
    """gallery/profile 里引用了、但 images/full/ 下还没有的文件。

    首次部署最容易踩的坑就是忘了传图 —— 让 /health 直接把它喊出来。
    """
    gallery = _read_json(CONTENT_DIR / "gallery.json", {})
    profile = _read_json(CONTENT_DIR / "profile.json", {})
    names = [page["file"] for page in gallery.get("pages", [])]
    if profile.get("resumeImage"):
        names.append(profile["resumeImage"])
    return [name for name in names if not (FULL_DIR / name).is_file()]


def build() -> dict:
    profile = _read_json(CONTENT_DIR / "profile.json", {})
    gallery = _read_json(CONTENT_DIR / "gallery.json", {})
    suffix = f"?v={version()}"

    pages = []
    for page in gallery.get("pages", []):
        entry = {
            "id": page["id"],
            "role": page.get("role", "work"),
            "title": page.get("title", ""),
            "subtitle": page.get("subtitle", ""),
            "note": page.get("note", ""),
            "category": page.get("category"),
        }
        entry.update(_describe(page["file"], suffix))
        pages.append(entry)

    resume_name = profile.pop("resumeImage", None)
    resume = _describe(resume_name, suffix) if resume_name else None

    return {
        "version": suffix.removeprefix("?v="),
        "profile": profile,
        "categories": gallery.get("categories", []),
        "pages": pages,
        "resume": resume,
    }

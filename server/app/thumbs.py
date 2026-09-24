"""缩略图：请求到了才做，做完落盘；源图比缓存新就重做。

首屏那条长流里放的是 750px 缩略图（约 80KB/张），点开大图才走原图 —— 这是
「19MB 不进小程序包体、长流又秒开」的关键。

以后往 images/full/ 丢一张新图不用做任何额外操作：第一次请求时自动生成。
"""

import logging
import threading
from pathlib import Path

from PIL import Image, ImageOps

from .config import FULL_DIR, THUMB_DIR, THUMB_QUALITY, THUMB_WIDTH

log = logging.getLogger("thumbs")

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _is_fresh(dst: Path, src: Path) -> bool:
    return dst.is_file() and dst.stat().st_mtime >= src.stat().st_mtime


def ensure(name: str) -> Path | None:
    """返回缩略图路径；源图不存在时返回 None。"""
    src = FULL_DIR / name
    if not src.is_file():
        return None

    dst = THUMB_DIR / name
    if _is_fresh(dst, src):
        return dst

    # 预热线程和真实请求可能撞在同一张图上，按文件名串行化，避免写坏文件
    with _locks_guard:
        lock = _locks.setdefault(name, threading.Lock())

    with lock:
        if _is_fresh(dst, src):
            return dst
        THUMB_DIR.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            if im.width > THUMB_WIDTH:
                height = round(im.height * THUMB_WIDTH / im.width)
                im = im.resize((THUMB_WIDTH, height), Image.LANCZOS)
            tmp = dst.with_name(dst.name + ".tmp")
            im.save(tmp, "JPEG", quality=THUMB_QUALITY, progressive=True, optimize=True)
        tmp.replace(dst)  # 先写临时文件再改名，避免半个文件被读到
    return dst


def prewarm() -> None:
    """启动时后台把已有的图都做一遍，别让第一个人等。"""
    for src in sorted(FULL_DIR.glob("*.jpg")):
        try:
            ensure(src.name)
        except Exception:
            log.exception("缩略图生成失败：%s", src.name)
    log.info("缩略图预热完成")

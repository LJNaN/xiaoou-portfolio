"""xiaoou-portfolio 后端：给小程序返回内容清单和图片。

对外只经 gateway 暴露两条路径（见 gateway 仓库的 routes.inc）：
    /portfolio-api/     内容清单
    /portfolio-images/  图片

前端那条长流用的是 750px 缩略图，点开放大才走原图，所以这里两条都要有。
"""

import json
import logging
import re
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse

from . import content, thumbs
from .config import API_PREFIX, FULL_DIR, IMAGE_PREFIX, PORT

log = logging.getLogger("xiaoou")

# 只允许纯文件名，挡掉 ../ 这类路径穿越
SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+\.jpg$")


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=thumbs.prewarm, daemon=True).start()
    log.info("内容版本 %s，缺图 %s", content.version(), content.missing_files() or "无")
    yield


app = FastAPI(title="xiaoou-portfolio-api", lifespan=lifespan, docs_url=None, redoc_url=None)


def _image_headers(request: Request) -> dict:
    """带 ?v= 的请求可以放心 immutably 长缓存：换图后版本号会变，URL 跟着变。

    不带 v 的（比如浏览器直接打开）只给一小时，免得换了图一直看到旧的。
    """
    if request.query_params.get("v"):
        cache = "public, max-age=31536000, immutable"
    else:
        cache = "public, max-age=3600"
    return {"Cache-Control": cache, "Access-Control-Allow-Origin": "*"}


@app.get(f"{API_PREFIX}/health")
def health():
    missing = content.missing_files()
    return {
        "ok": not missing,
        "version": content.version(),
        "missing": missing,
    }


@app.get(f"{API_PREFIX}/content")
def get_content(request: Request):
    data = content.build()
    etag = f'"{data["version"]}"'

    # 内容很小，但每次冷启动都会问一次：命中就直接 304，省掉一次传输
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return Response(
        payload,
        media_type="application/json; charset=utf-8",
        headers={
            "ETag": etag,
            "Cache-Control": "no-cache",  # 每次都带 ETag 来问，改了立刻生效
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.get(f"{IMAGE_PREFIX}/full/{{name}}")
def full_image(name: str, request: Request):
    if not SAFE_NAME.match(name):
        raise HTTPException(status_code=404)
    path = FULL_DIR / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="图片还没上传到服务器")
    return FileResponse(path, media_type="image/jpeg", headers=_image_headers(request))


@app.get(f"{IMAGE_PREFIX}/thumb/{{name}}")
def thumb_image(name: str, request: Request):
    if not SAFE_NAME.match(name):
        raise HTTPException(status_code=404)
    path = thumbs.ensure(name)
    if path is None:
        raise HTTPException(status_code=404, detail="原图不存在，无法生成缩略图")
    return FileResponse(path, media_type="image/jpeg", headers=_image_headers(request))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)

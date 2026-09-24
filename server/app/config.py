import os
from pathlib import Path

# 路径前缀。网关的 proxy_pass 是变量形式、不剥离前缀，所以后端自己带上网关里配的那两段。
API_PREFIX = os.getenv("API_PREFIX", "/portfolio-api")
IMAGE_PREFIX = os.getenv("IMAGE_PREFIX", "/portfolio-images")

IMAGES_DIR = Path(os.getenv("IMAGES_DIR", "/data/images"))
CONTENT_DIR = Path(os.getenv("CONTENT_DIR", "/data/content"))

FULL_DIR = IMAGES_DIR / "full"
THUMB_DIR = IMAGES_DIR / "thumb"

THUMB_WIDTH = int(os.getenv("THUMB_WIDTH", "750"))
THUMB_QUALITY = int(os.getenv("THUMB_QUALITY", "80"))

PORT = int(os.getenv("PORT", "5003"))

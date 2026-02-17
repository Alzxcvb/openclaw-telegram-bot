import time
import random
import yaml
import uvicorn
import logging
import os
from fastapi import FastAPI, Query
from ddgs import DDGS
from pathlib import Path

# Load configuration
config_file = Path(__file__).parent / "brave_shim.conf"
if not config_file.exists():
    raise FileNotFoundError("brave_shim.conf not found")

with open(config_file, "r") as f:
    config = yaml.safe_load(f)

# Logging setup
log_dir = Path(config['logging']['file_path']).parent
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=config['logging']['level'],
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config['logging']['file_path']),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("brave_shim")

app = FastAPI(title="Brave Search API Shim (DuckDuckGo)", docs_url=None, redoc_url=None)

search_cache = {}


def get_from_cache(q):
    expiration = config['bot_protection']['cache_expiration']
    if q in search_cache:
        timestamp, data = search_cache[q]
        if time.time() - timestamp < expiration:
            return data
    return None


@app.get("/status")
async def health_check():
    return {"status": "online", "cache_entries": len(search_cache)}


@app.get("/res/v1/web/search")
async def search_proxy(q: str = Query(...), count: int = None):
    res_count = count or config['search']['default_count']

    cached_res = get_from_cache(q)
    if cached_res:
        logger.info(f"CACHE HIT: {q}")
        return cached_res

    time.sleep(random.uniform(
        config['bot_protection']['min_delay'],
        config['bot_protection']['max_delay']
    ))

    logger.info(f"FETCH WEB: {q}")
    try:
        with DDGS() as ddgs:
            results = []
            for r in ddgs.text(q, max_results=res_count):
                results.append({
                    "title": r.get("title"),
                    "url": r.get("href"),
                    "description": r.get("body"),
                    "meta_url": {"path": r.get("href")}
                })

        response_data = {"web": {"results": results}}
        search_cache[q] = (time.time(), response_data)
        return response_data
    except Exception as e:
        logger.error(f"Error searching for '{q}': {e}")
        return {"web": {"results": []}, "error": str(e)}


@app.get("/res/v1/local/pois")
async def local_proxy(q: str = Query(...), count: int = None):
    res_count = count or config['search']['local_count']
    logger.info(f"FETCH LOCAL: {q}")
    try:
        with DDGS() as ddgs:
            res = [
                {
                    "id": str(i),
                    "name": r["title"],
                    "address": r["body"][:100],
                    "phone": "",
                    "coordinates": {"latitude": 0.0, "longitude": 0.0}
                }
                for i, r in enumerate(ddgs.text(f"place {q}", max_results=res_count))
            ]
        return {"results": res}
    except Exception as e:
        logger.error(f"Error in local search for '{q}': {e}")
        return {"results": []}


@app.get("/res/v1/local/descriptions")
async def local_descriptions(id: str = Query(...)):
    return {"descriptions": {id: "Data via DuckDuckGo proxy."}}


@app.get("/res/v1/summarizer/summary")
async def summarizer_proxy(key: str = Query(...)):
    return {"summary": "Summary complete.", "status": "complete"}


if __name__ == "__main__":
    logger.info(f"Starting Brave-Shim on {config['server']['host']}:{config['server']['port']}")
    uvicorn.run(
        app,
        host=config['server']['host'],
        port=config['server']['port'],
        access_log=False,
        log_level="critical"
    )

import asyncio
import importlib.util
import json
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

import psutil
import uvicorn
import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).parent.parent
WIDGETS_DIR = ROOT / "widgets"
FRONTEND_DIR = Path(__file__).parent / "frontend"

connected: list[WebSocket] = []

# warm up psutil so first reading isn't zero
psutil.cpu_percent(percpu=True)


def load_config() -> dict:
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def collect_metrics() -> dict:
    metrics: dict = {
        "cpu": {
            "percent": psutil.cpu_percent(),
            "per_core": psutil.cpu_percent(percpu=True),
        },
        "ram": {
            "percent": psutil.virtual_memory().percent,
            "used_gb": round(psutil.virtual_memory().used / 1024**3, 1),
            "total_gb": round(psutil.virtual_memory().total / 1024**3, 1),
        },
    }

    try:
        temps = psutil.sensors_temperatures()
        pkg = next(
            (t for t in temps.get("coretemp", []) if "Package" in t.label), None
        )
        if pkg:
            metrics["cpu"]["temp"] = round(pkg.current)
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            timeout=2,
        ).decode().strip()
        util, temp, vram_used, vram_total = [x.strip() for x in out.split(",")]
        metrics["gpu"] = {
            "percent": int(util),
            "temp": int(temp),
            "vram_used_mb": int(vram_used),
            "vram_total_mb": int(vram_total),
        }
    except Exception:
        pass

    return metrics


async def broadcaster():
    while True:
        if connected:
            msg = json.dumps({"type": "tick", "metrics": collect_metrics()})
            dead = []
            for ws in connected:
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                connected.remove(ws)
        await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(broadcaster())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/api/config")
def get_config():
    return load_config()


@app.get("/api/widgets")
def list_widgets():
    result = []
    for path in WIDGETS_DIR.glob("*/manifest.json"):
        with open(path) as f:
            result.append(json.load(f))
    return result


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected.append(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if ws in connected:
            connected.remove(ws)


# Mount each widget's static files and optional backend router
for widget_dir in sorted(WIDGETS_DIR.iterdir()):
    if not widget_dir.is_dir():
        continue
    app.mount(
        f"/widgets/{widget_dir.name}",
        StaticFiles(directory=widget_dir),
        name=f"widget_{widget_dir.name}",
    )
    backend = widget_dir / "backend.py"
    if backend.exists():
        spec = importlib.util.spec_from_file_location(f"widget_{widget_dir.name}_backend", backend)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "router"):
            app.include_router(mod.router, prefix=f"/api/widgets/{widget_dir.name}")

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

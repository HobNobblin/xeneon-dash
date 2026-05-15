import subprocess
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class LaunchRequest(BaseModel):
    command: str


@router.post("/launch")
async def launch(req: LaunchRequest):
    try:
        subprocess.Popen(
            req.command,
            shell=True,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

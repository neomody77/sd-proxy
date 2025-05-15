# sd_mock.py
import os
import time
import random
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
import uvicorn
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.prompts = {}  # 初始化
    yield  # 应用生命周期中持续运行


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.post("/api/prompt")
async def generate_prompt(request: Request):
    data = await request.json()
    prompt_id = str(random.randint(100000, 999999))
    app.state.prompts[prompt_id] = {
        "status": "pending",
        "start_time": time.time(),
        "result": None
    }
    return {"prompt_id": prompt_id}


@app.get("/api/history/{prompt_id}")
async def get_history(prompt_id: str):
    prompt = app.state.prompts.get(prompt_id)
    if not prompt:
        return {}
    if time.time() - prompt["start_time"] > 3:
        prompt["status"] = "done"
        prompt["result"] = {
            "outputs": {
                "9": {
                    "images": [
                        {"filename": "mock.png", "subfolder": "", "type": "output"}
                        for _ in range(4)
                    ]
                }
            }
        }
    return {prompt_id: prompt["result"] or {}}


# @app.get("/api/view")
# async def view_image(filename: str, subfolder: str = "", type: str = "output"):
#     return {"url": "/static/mock.png"}


@app.get("/api/view")
async def view_image(filename: str, subfolder: str = "", type: str = "output"):
    path = os.path.join("static", "mock.png")
    return FileResponse(
        path,
        media_type="image/png",
        filename="mock.png",
        headers={"Content-Disposition": 'inline; filename="mock.png"'}
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8188)

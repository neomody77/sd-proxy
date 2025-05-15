import json
from contextlib import asynccontextmanager
from time import time
from uuid import uuid4

import redis.asyncio as redis
import uvicorn
from fastapi import FastAPI, HTTPException, status

from config import settings, QUEUE_RUNNING, QUEUE_CANCEL, QUEUE_PENDING
from logger import setup_logger
from models import TaskStatusResponse, SimpleTaskRequest, StoryTxt2ImgRequest
from workflows import prompt_adapter

logger = setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    yield
    await app.state.redis.aclose()


app = FastAPI(lifespan=lifespan)



@app.post("/tasks")
async def generate_image(task: SimpleTaskRequest | StoryTxt2ImgRequest):
    task_id = str(uuid4())
    now = int(time())

    full_prompt = prompt_adapter(task)
    print(full_prompt)
    await app.state.redis.hset(f"task_map:{task_id}", mapping={
        "prompt": full_prompt,
        "status": "pending",
        "error": "",
        "worker": "",
        "result": "",
        "updated_logs": json.dumps([{"status": "pending", "timestamp": now}])
    })
    await app.state.redis.rpush(QUEUE_PENDING, task_id)
    logger.info(f"Submitted task {task_id}")
    return {"task_id": task_id}


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_status(task_id: str):
    data = await app.state.redis.hgetall(f"task_map:{task_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Task not found")

    if "updated_logs" in data:
        data["updated_logs"] = json.loads(data["updated_logs"])
    data["result"] = json.loads(data["result"]) if data.get("result") else []
    return TaskStatusResponse(**data)


@app.delete("/tasks/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(task_id: str):
    r = app.state.redis

    # 从所有相关队列/集合中移除任务 ID
    await r.lrem(QUEUE_PENDING, 0, task_id)
    await r.srem(QUEUE_RUNNING, task_id)
    await r.srem(QUEUE_CANCEL, task_id)

    # 检查任务是否存在
    key = f"task_map:{task_id}"
    task_data = await r.hgetall(key)
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")

    # 添加删除状态日志
    logs = json.loads(task_data.get("updated_logs", "[]"))
    logs.append({"status": "deleted", "timestamp": int(time())})
    await r.hset(key, mapping={
        "status": "deleted",
        "updated_logs": json.dumps(logs)
    })

    logger.info(f"✅ Deleted task {task_id}")
    return {"status": "deleted"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

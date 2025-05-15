import json
import time
import asyncio
import traceback

import httpx
import redis.asyncio as redis

from config import settings, QUEUE_RUNNING, QUEUE_CANCEL, FREE_ENDPOINTS, QUEUE_PENDING, QUEUE_FAILED
from logger import setup_logger

logger = setup_logger()


async def update_task_status(r, task_id: str, status: str, error: str = "", result: str = ""):
    key = f"task_map:{task_id}"
    now = int(time.time())
    task_data = await r.hgetall(key)
    logs = json.loads(task_data.get("updated_logs", "[]"))
    logs.append({"status": status, "timestamp": now})

    mapping = {
        "status": status,
        "error": error,
        "updated_logs": json.dumps(logs)
    }

    if result:
        mapping["result"] = result

    await r.hset(key, mapping=mapping)


async def simulate_sd_call(prompt: dict, endpoint: str) -> list[str]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{endpoint}/api/prompt", json=prompt)
            response.raise_for_status()
            prompt_id = response.json()["prompt_id"]

            for _ in range(30):
                await asyncio.sleep(1)
                res = await client.get(f"{endpoint}/api/history/{prompt_id}")
                res.raise_for_status()
                data = res.json().get(prompt_id, {})
                logger.info("request task[%s] status: %s", prompt_id, data)
                if "outputs" in data:
                    return [
                        str(httpx.URL(f"{endpoint}/api/view", params=img))
                        for output in data["outputs"].values()
                        if "images" in output
                        for img in output["images"]
                    ]

            raise TimeoutError("Image generation timed out")
    except Exception as e:
        raise e


async def get_available_endpoint(r, timeout=0):
    # timeout=0 表示永久阻塞直到有值
    result = await r.blpop(FREE_ENDPOINTS, timeout=timeout)
    if result:
        _, endpoint = result
        return endpoint
    return None  # 可选：你也可以 raise 超时异常


async def handle_task(r: redis.Redis, task_id: str):
    endpoint = await get_available_endpoint(r, timeout=3)
    if not endpoint:
        await r.rpush(QUEUE_PENDING, task_id)
        return

    try:
        await r.sadd(QUEUE_RUNNING, task_id)
        await r.hset(f"task_map:{task_id}", "worker", endpoint)
        await update_task_status(r, task_id, "running")

        task_data = await r.hgetall(f"task_map:{task_id}")
        prompt = json.loads(task_data.get("prompt", "{}"))

        if await r.sismember(QUEUE_CANCEL, task_id):
            raise Exception("cancelled")

        result_urls = await asyncio.wait_for(simulate_sd_call(prompt, endpoint), timeout=settings.MAX_EXECUTION_TIME)
        await r.set(f"task_result:{task_id}", json.dumps(result_urls))
        await update_task_status(r, task_id, "done", result=json.dumps(result_urls))

        logger.info(f"✅ Task {task_id} done via {endpoint}")

    except Exception as e:
        traceback.print_exc()
        await r.rpush(QUEUE_FAILED, task_id)
        await update_task_status(r, task_id, "failed", error=str(e))
        logger.error(f"❌ Task {task_id} failed: {e}")

    finally:
        await r.srem(QUEUE_RUNNING, task_id)
        await r.srem(QUEUE_CANCEL, task_id)
        await r.rpush(FREE_ENDPOINTS, endpoint)


async def worker_loop():
    r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    while True:
        task_id = await r.lpop(QUEUE_PENDING)
        if task_id:
            asyncio.create_task(handle_task(r, task_id))
        else:
            await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(worker_loop())

# failed_watcher.py

import asyncio
import logging
import redis.asyncio as redis
from config import settings, QUEUE_FAILED, QUEUE_FAILED_KNOWN

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


async def watch_failed_tasks():
    r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

    while True:
        task_id = await r.lpop(QUEUE_FAILED)
        if task_id:
            logging.warning(f"⚠️  New failed task detected: {task_id}")

            # 更新状态为 known_failed
            await r.hset(f"task_map:{task_id}", mapping={"status": "known_failed"})

            # 放入已知失败队列
            await r.rpush(QUEUE_FAILED_KNOWN, task_id)
        else:
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(watch_failed_tasks())

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    MAX_EXECUTION_TIME: int = int(os.getenv("MAX_EXECUTION_TIME", 10))


settings = Settings()
print("REDIS_URL:", settings.REDIS_URL)
print("MAX_EXECUTION_TIME:", settings.MAX_EXECUTION_TIME)




QUEUE_PENDING = "task_queue_pending"
QUEUE_RUNNING = "task_queue_running"
QUEUE_DONE    = "task_queue_done"
QUEUE_FAILED  = "task_queue_failed"
QUEUE_CANCEL  = "task_queue_cancelled"
FREE_ENDPOINTS = "free_sd_endpoints"
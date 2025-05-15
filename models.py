from pydantic import BaseModel

from typing import List, TypedDict


class TaskRequest(BaseModel):
    timeout: int = 30


class SimpleTaskRequest(TaskRequest):
    prompt: str


class StoryTxt2ImgRequest(BaseModel):
    role_text: str
    scene_text: str
    pos_text: str
    neg_text: str


class TaskLog(TypedDict):
    status: str
    timestamp: int


class TaskStatusResponse(BaseModel):
    prompt: str
    status: str
    error: str = ""
    worker: str = ""
    result: List[str] = []
    updated_logs: List[TaskLog] = []

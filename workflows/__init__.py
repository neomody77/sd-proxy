import json
import random

from models import TaskRequest, StoryTxt2ImgRequest, SimpleTaskRequest


def get_simple_full_prompt(task: SimpleTaskRequest):
    with open('workflows/sample-template.json', 'r', encoding='utf8') as f:
        template = json.load(fp=f)
        template['prompt']['3']['inputs']['seed'] = random.randint(1, 10000)
        template['prompt']['6']['inputs']['text'] = task.prompt
        full_prompt = json.dumps(template, ensure_ascii=False)
    return full_prompt


def get_storytxt2img_full_prompt(task: StoryTxt2ImgRequest):
    with open('workflows/storytxt2img-template.json', 'r', encoding='utf8') as f:
        template = json.load(fp=f)
        template['prompt']['5']['inputs']['seed'] = random.randint(1, 10000)
        template['prompt']['3']['inputs']['role_text'] = task.role_text
        template['prompt']['3']['inputs']['scene_text'] = task.scene_text
        template['prompt']['3']['inputs']['pos_text'] = task.pos_text
        template['prompt']['3']['inputs']['neg_text'] = task.neg_text
        full_prompt = json.dumps(template, ensure_ascii=False)
    return full_prompt


TaskRequestTemplateMap = {
    SimpleTaskRequest: get_simple_full_prompt,
    StoryTxt2ImgRequest: get_storytxt2img_full_prompt,
}


def prompt_adapter(task: TaskRequest):
    for cls, handler in TaskRequestTemplateMap.items():
        if not isinstance(task, cls):
            continue
        return handler(task)

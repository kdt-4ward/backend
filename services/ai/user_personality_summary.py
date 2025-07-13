from services.ai.prompt_templates import PROMPT_REGISTRY
from core.dependencies import get_openai_client

# 1. 프롬프트 생성 함수(이름 통일 및 개선)
def build_trait_prompt(responses: list[dict], user_name: str = "User") -> str:
    trait_lines = []
    for item in responses:
        code = item.get("code", "")
        tag = item.get("tag", "")
        custom = item.get("custom_input")
        if custom:
            trait_lines.append(f"- {code}: {custom.strip()}")
        elif code and tag:
            trait_lines.append(f"- {code}: {tag}")
    trait_list = "\n".join(trait_lines)
    
    return PROMPT_REGISTRY["user_trait_summary_prompt"].format(
        user_name=user_name,
        trait_list=trait_list
    )

async def summarize_personality_from_tags(responses: list[dict], user_name: str = "user") -> str:
    if not responses:
        return f"No survey responses for {user_name}."
    prompt = build_trait_prompt(responses, user_name=user_name)

    client = await get_openai_client()
    # OpenAI의 chat completion API 사용 (role 구조 직접 전달)
    completion = await client.chat.completions.create(
        model="gpt-4o",  # 또는 gpt-3.5-turbo 등
        messages=[
            {"role": "user", "content": prompt}
        ],
    )
    # 응답 파싱 (최신 openai 라이브러리 기준)
    return completion.choices[0].message.content.strip()
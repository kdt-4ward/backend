from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
from models.schema import ChatRequest, BotConfigRequest
from config import router, semaphore
from core.bot import PersonaChatBot
from tenacity import retry, stop_after_attempt, wait_fixed, RetryError
from services.openai_client import call_openai_stream_async
from core.dependencies import get_connection_manager

@router.post("/chat/stream")
async def stream_chat_with_persona(req: ChatRequest):
    async def event_generator() -> AsyncGenerator[str, None]:
        async with semaphore:
            bot = PersonaChatBot(user_id=req.user_id)

            history = bot.get_history()
            history.append({"role": "user", "content": req.message})
            bot.save_history(history)
            bot.save_to_db(req.user_id, "user", req.message)

            last_k_turns = bot.get_last_turns(10)

            try:
                response = await call_openai_stream_async(last_k_turns)
            except RetryError:
                yield "[ERROR] GPT 응답 실패\n"
                return

            full_reply = ""
            batch_buffer = ""
            batch_size = 5

            async for chunk in response:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    batch_buffer += delta.content
                    full_reply += delta.content
                    if len(batch_buffer) >= batch_size:
                        yield batch_buffer
                        batch_buffer = ""

            if batch_buffer:
                yield batch_buffer

            history.append({"role": "assistant", "content": full_reply})
            bot.save_history(history)
            bot.save_to_db("assistant", "assistant", full_reply)

    return StreamingResponse(event_generator(), media_type="text/plain")

@router.post("/chat/reset")
async def reset_ai_chat_session(req: ChatRequest):
    bot = PersonaChatBot(user_id=req.user_id)
    bot.reset()
    return {"message": f"{req.user_id} 님의 AI 세션이 초기화되었습니다."}

@router.post("/chat/configure")
async def set_ai_bot_config(req: BotConfigRequest):
    # 함께 키우는 반려펫이기 때문에 이름 같이 변경
    partner_id = get_connection_manager().get_partner(req.user_id)
    bot = PersonaChatBot(req.user_id)
    bot.set_persona_name(req.persona_name)

    bot = PersonaChatBot(partner_id)
    bot.set_persona_name(req.persona_name)

    return {"message": "챗봇 설정이 저장되었습니다."}

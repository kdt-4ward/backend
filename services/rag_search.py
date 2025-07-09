from core.bot import PersonaChatBot
from services.openai_client import get_openai_embedding
from core.dependencies import get_db_session
from models.db_models import AIMessage
from core.redis import RedisFaissChunkCache
import faiss
import numpy as np


def build_multi_turn_chunks(messages, turns_per_chunk=4):
    """
    messages: [{"role": "user"/"assistant", "content": ..., "created_at": ..., "id": ...}, ...]
    turns_per_chunk: 한 chunk에 들어갈 user-assistant 턴 개수
    return: [chunk_dict, ...]
    """
    n = len(messages)
    i = 0
    result = []
    while i < n:
        chunk_lines = []
        msg_ids = []
        start_time, end_time = None, None
        turn_count = 0
        # 한 chunk에 최대 N턴씩 담기
        while turn_count < turns_per_chunk and i < n:
            # user 메시지
            if messages[i]["role"] == "user":
                if start_time is None:
                    start_time = messages[i]["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                chunk_lines.append(f'user: {messages[i]["content"]}')
                msg_ids.append(messages[i].get("id"))
                i += 1
                # 다음이 assistant면 같이 묶기
                if i < n and messages[i]["role"] == "assistant":
                    chunk_lines.append(f'assistant: {messages[i]["content"]}')
                    msg_ids.append(messages[i].get("id"))
                    end_time = messages[i]["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                    i += 1
                else:
                    # 짝이 없으면 끝
                    end_time = start_time
                turn_count += 1
            else:
                # user로 시작하지 않는 경우 skip (이론상 거의 없음)
                i += 1
        if chunk_lines and len(msg_ids) >= 8:
            chunk_text = f'[{start_time} ~ {end_time}]\n' + "\n".join(chunk_lines)
            result.append({
                "text": chunk_text,
                "start_time": start_time,
                "end_time": end_time,
                "msg_ids": msg_ids
            })
    return result

# 2. chunk 생성 + embedding + 인덱스 관리 통합
async def process_and_build_faiss_index(user_id, messages, turns_per_chunk=4):
    # chunk 생성 (4턴 단위)
    chunks = build_multi_turn_chunks(messages, turns_per_chunk)
    # embedding & faiss 인덱스 생성
    embeddings = []
    for idx, chunk in enumerate(chunks):
        emb = await get_openai_embedding(chunk["text"])
        embeddings.append(emb)
        # DB에 embed_index 기록
        for msg_id in chunk["msg_ids"]:
            with get_db_session() as db:
                msg = db.query(AIMessage).filter_by(id=msg_id, user_id=user_id).first()
                if msg:
                    msg.embed_index = idx
                    db.commit()
    embeddings_np = np.array(embeddings).astype("float32")
    index = faiss.IndexFlatL2(embeddings_np.shape[1])
    index.add(embeddings_np)
    # 캐싱
    RedisFaissChunkCache.save(user_id, chunks, embeddings_np)
    return index, embeddings_np, chunks

async def process_incremental_faiss_embedding(user_id, turns_per_chunk=4):
    # 1. Redis에서 기존 chunk/embedding 불러오기
    chunks, embeddings_np = RedisFaissChunkCache.load(user_id)
    if chunks is None or embeddings_np is None:
        # 없으면 전체 새로 빌드
        bot = PersonaChatBot(user_id)
        messages = bot.get_full_history()
        if len(messages) < 8:
            return
        await process_and_build_faiss_index(user_id, messages, turns_per_chunk)
        return

    # 2. DB에서 embed_index가 None인 메시지만 불러오기 (새로 추가된 메시지)
    with get_db_session() as db:
        new_msgs = (
            db.query(AIMessage)
            .filter_by(user_id=user_id)
            .filter(AIMessage.embed_index == None)
            .filter(AIMessage.role != "function")
            .order_by(AIMessage.created_at)
            .all()
        )
        # 메시지가 없으면 종료
        if not new_msgs:
            return

        # dict 포맷으로 맞추기
        messages = [
            {
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at,
                "id": msg.id,
            }
            for msg in new_msgs
        ]

    # 3. chunking: 기존 chunk와 이어지도록 조정 필요
    # 기존 chunk의 마지막 embed_index
    prev_chunk_count = len(chunks)
    # (실제로는 기존 마지막 chunk의 end_time, msg_ids 등 활용해서 부드럽게 이어붙이면 더 좋음)

    # 새 메시지들로 multi-turn chunk 생성
    new_chunks = build_multi_turn_chunks(messages, turns_per_chunk)
    if not new_chunks or len(new_chunks) < 2:
        return

    # 4. embedding
    new_embeddings = []
    for idx, chunk in enumerate(new_chunks):
        emb = await get_openai_embedding(chunk["text"])
        new_embeddings.append(emb)
        # DB에 embed_index 기록(증분으로 prev_chunk_count + idx)
        for msg_id in chunk["msg_ids"]:
            with get_db_session() as db:
                msg = db.query(AIMessage).filter_by(id=msg_id, user_id=user_id).first()
                if msg:
                    msg.embed_index = prev_chunk_count + idx
                    db.commit()
    
    # 5. Redis에 append 저장 (concat)
    all_chunks = chunks + new_chunks
    all_embeddings_np = np.concatenate([embeddings_np, np.array(new_embeddings).astype("float32")], axis=0)
    RedisFaissChunkCache.save(user_id, all_chunks, all_embeddings_np)

# 3. 검색시: 캐시/DB에서 인덱스/embedding 활용
async def search_past_chats(query, top_k=3, user_id=None, couple_id=None, turns_per_chunk=4, threshold=1.5):
    chunks, embeddings_np = RedisFaissChunkCache.load(user_id)
    # 1. 캐시 우선 사용, 없으면 새로 생성
    if chunks is None or embeddings_np is None:
        bot = PersonaChatBot(user_id)
        messages = bot.get_full_history()
        index, embeddings_np, chunks = await process_and_build_faiss_index(user_id, messages, turns_per_chunk)
    else:
        index = faiss.IndexFlatL2(embeddings_np.shape[1])
        index.add(embeddings_np)
    if not chunks or len(chunks) == 0:
        return "검색할 대화 chunk가 없습니다."
    # 2. 쿼리 임베딩
    query_emb = await get_openai_embedding(query)
    query_emb = np.array([query_emb]).astype("float32")
    # 3. FAISS에서 top_k 검색
    D, I = index.search(query_emb, min(top_k, len(chunks)))

    # 4. 일정 유사도 이상인 것만 선택
    selected = []
    for dist, idx in zip(D[0], I[0]):
        if dist <= threshold:   # 거리값이 threshold 이하인 것만
            selected.append(chunks[idx]["text"])
    if not selected:
        return "관련성 높은 대화 chunk가 없습니다."
    
    return "\n\n".join(selected)
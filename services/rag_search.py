from core.bot import PersonaChatBot
from services.openai_client import get_openai_embedding

import faiss
import numpy as np

async def build_faiss_index(chunks):
    # chunks: [str, ...] (원본/요약 chunk 텍스트 리스트)
    embeddings = []
    for chunk in chunks:
        emb = await get_openai_embedding(chunk)
        embeddings.append(emb)
    embeddings_np = np.array(embeddings).astype("float32")
    index = faiss.IndexFlatL2(embeddings_np.shape[1])
    index.add(embeddings_np)
    return index, embeddings_np, chunks

# TODO: index 기존 있으면 읽어오기, 코드 모듈화
async def search_past_chats__(query, top_k=3, user_id=None, couple_id=None):
    bot = PersonaChatBot(user_id)
    # 1. DB에서 원본 메시지 chunk화
    messages = bot.get_full_history()
    # chunking: 메시지 n개씩 묶기(3~5개 권장)
    chunk_size = 5
    chunks = [
        " ".join([m["content"] for m in messages[i:i+chunk_size]])
        for i in range(0, len(messages), chunk_size)
    ]

    # 2. (최초1회) 임베딩/FAISS 인덱스 생성
    index, embeddings_np, chunk_texts = await build_faiss_index(chunks)

    # 3. 쿼리 임베딩
    query_emb = await get_openai_embedding(query)
    query_emb = np.array([query_emb]).astype("float32")

    # 4. FAISS에서 top_k 검색
    D, I = index.search(query_emb, top_k)
    result_chunks = [chunk_texts[i] for i in I[0]]

    # 5. 반환 포맷(프롬프트 삽입용)
    return "\n\n".join(result_chunks)

async def search_past_chats(query, top_k=3, user_id=None, couple_id=None):
    return "어릴적 내 우상은 아빠야"
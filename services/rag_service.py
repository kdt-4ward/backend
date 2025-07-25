from typing import List, Dict, Optional, Tuple
from db.db import get_session
from db.db_tables import AIMessage, ChunkMetadata
from services.openai_client import get_openai_embedding
import numpy as np
import json
from datetime import datetime
from utils.log_utils import get_logger

logger = get_logger(__name__)

class RAGService:
    def __init__(self, turns_per_chunk: int = 4, overlap_turns: int = 1):
        self.turns_per_chunk = turns_per_chunk
        self.overlap_turns = overlap_turns  # overlap할 턴 수
    
    async def build_chunks_and_embeddings(self, user_id: str) -> List[Dict]:
        """DB에서 메시지를 읽어서 chunk 생성 및 embedding 저장"""
        session = get_session()
        
        try:
            # embed_index가 None인 메시지들만 가져오기 (새로 추가된 메시지)
            new_messages = (
                session.query(AIMessage)
                .filter_by(user_id=user_id)
                .filter(AIMessage.embed_index == None)
                .filter(AIMessage.role != "function")
                .order_by(AIMessage.created_at)
                .all()
            )
            
            if not new_messages:
                logger.info(f"No new messages for user {user_id}")
                return []
            
            logger.info(f"Processing {len(new_messages)} new messages for user {user_id}")
            
            # chunk 생성
            chunks = self._create_chunks_from_messages(new_messages)
            
            if not chunks:
                logger.info(f"No valid chunks created for user {user_id}")
                return []
            
            # embedding 생성 및 저장
            for chunk in chunks:
                await self._process_chunk_embedding(session, user_id, chunk)
            
            session.commit()
            logger.info(f"Successfully processed {len(chunks)} chunks for user {user_id}")
            return chunks
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to build chunks for user {user_id}: {e}")
            return []
        finally:
            session.close()
    
    def _create_chunks_from_messages(self, messages: List[AIMessage]) -> List[Dict]:
        """메시지 리스트에서 chunk 생성 (overlap 포함)"""
        chunks = []
        i = 0
        
        while i < len(messages):
            chunk_messages = []
            turn_count = 0
            
            # turns_per_chunk만큼의 턴을 찾아서 chunk 생성
            while turn_count < self.turns_per_chunk and i < len(messages):
                if messages[i].role == "user":
                    # user 메시지 추가
                    chunk_messages.append(messages[i])
                    i += 1
                    
                    # 다음 assistant 메시지를 찾기 (사이에 다른 메시지가 있어도 상관없음)
                    assistant_found = False
                    j = i
                    while j < len(messages) and not assistant_found:
                        if messages[j].role == "assistant":
                            chunk_messages.append(messages[j])
                            assistant_found = True
                            j += 1
                        else:
                            # assistant가 아닌 메시지도 chunk에 포함 (function, system 등)
                            chunk_messages.append(messages[j])
                            j += 1
                    
                    i = j  # 다음 처리할 인덱스 업데이트
                    turn_count += 1  # user-assistant 쌍을 1턴으로 카운트
                else:
                    # user가 아닌 메시지는 그냥 추가 (턴 카운트는 증가하지 않음)
                    chunk_messages.append(messages[i])
                    i += 1
            
            if len(chunk_messages) >= self.turns_per_chunk * 2:  # 최소 8개 메시지 이상
                chunk = self._build_chunk_dict(chunk_messages)
                chunks.append(chunk)
                
                # overlap을 위해 인덱스를 뒤로 이동
                if self.overlap_turns > 0 and len(chunks) > 1:
                    # overlap_turns만큼의 턴을 뒤로 이동
                    overlap_turn_count = 0
                    overlap_start = 0
                    
                    # chunk_messages에서 뒤에서부터 user 메시지를 찾아서 overlap_turns만큼 앞으로 이동
                    for idx in range(len(chunk_messages) - 1, -1, -1):
                        if chunk_messages[idx].role == "user":
                            overlap_turn_count += 1
                            if overlap_turn_count >= self.overlap_turns:
                                overlap_start = idx
                                break
                    
                    # i를 overlap_start 위치로 되돌리기
                    i = i - (len(chunk_messages) - overlap_start)
        
        return chunks
    
    def _build_chunk_dict(self, messages: List[AIMessage]) -> Dict:
        """메시지 리스트를 chunk 딕셔너리로 변환"""
        start_time = messages[0].created_at
        end_time = messages[-1].created_at
        
        chunk_text = f'[{start_time.strftime("%Y-%m-%d %H:%M:%S")} ~ {end_time.strftime("%Y-%m-%d %H:%M:%S")}]\n'
        chunk_text += "\n".join([f'{msg.role}: {msg.content}' for msg in messages])
        
        return {
            "text": chunk_text,
            "start_time": start_time,
            "end_time": end_time,
            "start_msg_id": messages[0].id,
            "end_msg_id": messages[-1].id,
            "msg_ids": [msg.id for msg in messages]
        }
    
    async def _process_chunk_embedding(self, session, user_id: str, chunk: Dict):
        """chunk의 embedding 생성 및 저장"""
        try:
            # embedding 생성
            embedding = await get_openai_embedding(chunk["text"])
            
            # 기존 chunk_id 확인
            existing_chunk = (
                session.query(ChunkMetadata)
                .filter_by(user_id=user_id)
                .order_by(ChunkMetadata.chunk_id.desc())
                .first()
            )
            
            new_chunk_id = (existing_chunk.chunk_id + 1) if existing_chunk else 0
            
            # chunk metadata 저장
            chunk_metadata = ChunkMetadata(
                user_id=user_id,
                chunk_id=new_chunk_id,
                start_msg_id=chunk["start_msg_id"],
                end_msg_id=chunk["end_msg_id"],
                start_time=chunk["start_time"],
                end_time=chunk["end_time"],
                embedding=json.dumps(embedding)
            )
            session.add(chunk_metadata)
            
            # 메시지들의 embed_index 업데이트
            for msg_id in chunk["msg_ids"]:
                msg = session.query(AIMessage).filter_by(id=msg_id).first()
                if msg:
                    msg.embed_index = new_chunk_id
            
            logger.debug(f"Saved chunk {new_chunk_id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to process chunk embedding: {e}")
            raise
    
    async def rebuild_all_chunks(self, user_id: str) -> List[Dict]:
        """사용자의 모든 메시지로부터 chunk 재구성"""
        session = get_session()
        
        try:
            # 기존 chunk metadata 삭제
            session.query(ChunkMetadata).filter_by(user_id=user_id).delete()
            
            # 모든 메시지의 embed_index 초기화
            session.query(AIMessage).filter_by(user_id=user_id).update({"embed_index": None})
            
            # 모든 메시지 가져오기
            all_messages = (
                session.query(AIMessage)
                .filter_by(user_id=user_id)
                .filter(AIMessage.role != "function")
                .order_by(AIMessage.created_at)
                .all()
            )
            
            session.commit()
            
            if not all_messages:
                logger.info(f"No messages found for user {user_id}")
                return []
            
            logger.info(f"Rebuilding chunks for {len(all_messages)} messages for user {user_id}")
            
            # chunk 생성 및 저장
            chunks = self._create_chunks_from_messages(all_messages)
            
            for chunk in chunks:
                await self._process_chunk_embedding(session, user_id, chunk)
            
            session.commit()
            logger.info(f"Successfully rebuilt {len(chunks)} chunks for user {user_id}")
            return chunks
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to rebuild chunks for user {user_id}: {e}")
            return []
        finally:
            session.close()
    
    def get_chunk_count(self, user_id: str) -> int:
        """사용자의 chunk 개수 반환"""
        session = get_session()
        try:
            count = session.query(ChunkMetadata).filter_by(user_id=user_id).count()
            return count
        finally:
            session.close()
    
    def get_chunk_by_id(self, user_id: str, chunk_id: int) -> Optional[Dict]:
        """특정 chunk 정보 반환"""
        session = get_session()
        try:
            chunk_metadata = (
                session.query(ChunkMetadata)
                .filter_by(user_id=user_id, chunk_id=chunk_id)
                .first()
            )
            
            if not chunk_metadata:
                return None
            
            # 실제 메시지들로부터 텍스트 재구성
            messages = (
                session.query(AIMessage)
                .filter(
                    AIMessage.id >= chunk_metadata.start_msg_id,
                    AIMessage.id <= chunk_metadata.end_msg_id,
                    AIMessage.user_id == user_id
                )
                .order_by(AIMessage.created_at)
                .all()
            )
            
            chunk_text = f'[{chunk_metadata.start_time.strftime("%Y-%m-%d %H:%M:%S")} ~ {chunk_metadata.end_time.strftime("%Y-%m-%d %H:%M:%S")}]\n'
            chunk_text += "\n".join([f'{msg.role}: {msg.content}' for msg in messages])
            
            return {
                "chunk_id": chunk_metadata.chunk_id,
                "text": chunk_text,
                "start_time": chunk_metadata.start_time,
                "end_time": chunk_metadata.end_time,
                "start_msg_id": chunk_metadata.start_msg_id,
                "end_msg_id": chunk_metadata.end_msg_id,
                "embedding": json.loads(chunk_metadata.embedding)
            }
            
        finally:
            session.close()
    
    def get_all_chunks(self, user_id: str) -> List[Dict]:
        """사용자의 모든 chunk 정보 반환"""
        session = get_session()
        try:
            chunk_metadatas = (
                session.query(ChunkMetadata)
                .filter_by(user_id=user_id)
                .order_by(ChunkMetadata.chunk_id)
                .all()
            )
            
            chunks = []
            for chunk_metadata in chunk_metadatas:
                chunk = self.get_chunk_by_id(user_id, chunk_metadata.chunk_id)
                if chunk:
                    chunks.append(chunk)
            
            return chunks
            
        finally:
            session.close()
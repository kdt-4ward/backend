# db/result_saver.py
import json
from db.db_tables import (
    WeeklySolution, CoupleWeeklyAnalysisResult,
    CoupleWeeklyComparisonResult, CoupleWeeklyRecommendation
)
from datetime import datetime
from jobs.content_recommendation import enhance_movie_info, enhance_song_info
import asyncio

class WeeklyResultSaver:
    def __init__(self, db_session, week_dates):
        self.db = db_session
        self.week_start = week_dates[0]
        self.week_end = week_dates[-1]
        self.now = datetime.utcnow()

    async def save(self, couple_id: str, user1_id: str, user2_id: str, result: dict):
        try:
            # 커플 주간 요약
            if result.get("주간커플분석") and result["주간커플분석"]["success"]:
                self.db.add(CoupleWeeklyAnalysisResult(
                    couple_id=couple_id,
                    week_start_date=self.week_start,
                    week_end_date=self.week_end,
                    result=json.dumps(result["주간커플분석"]["result"], ensure_ascii=False),
                    created_at=self.now
                ))

            # 개인 주간 요약
            for user_key, user_id in [("user1", user1_id), ("user2", user2_id)]:
                user_result = result.get("개인분석", {}).get(user_key, {})
                if user_result.get("success"):
                    # content가 딕셔너리인 경우 JSON 문자열로 변환
                    content = user_result["result"]
                    if isinstance(content, dict):
                        content = json.dumps(content, ensure_ascii=False)
                    
                    self.db.add(WeeklySolution(
                        user_id=user_id,
                        content=content,
                        created_at=self.now
                    ))

            # 비교 분석
            if result.get("커플vsAI차이") and result["커플vsAI차이"]["success"]:
                comparison_content = result["커플vsAI차이"]["result"]
                if isinstance(comparison_content, dict):
                    comparison_content = json.dumps(comparison_content, ensure_ascii=False)
                
                self.db.add(CoupleWeeklyComparisonResult(
                    couple_id=couple_id,
                    week_start_date=self.week_start,
                    week_end_date=self.week_end,
                    comparison=comparison_content,
                    created_at=self.now
                ))

            # 추천 조언 - TMDB와 YouTube API로 정보 강화
            if result.get("추천") and result["추천"]["success"]:
                recommendation_result = result["추천"]["result"]
                
                # recommendation_result가 문자열인 경우 JSON으로 파싱
                if isinstance(recommendation_result, str):
                    try:
                        parsed = json.loads(recommendation_result)
                    except json.JSONDecodeError:
                        parsed = {"solution": recommendation_result}
                else:
                    parsed = recommendation_result
                
                # advice 필드가 비어있지 않은지 확인
                advice = parsed.get("solution", "") or parsed.get("조언", "") or "추천 내용이 없습니다."
                
                # recommendation 구조에서 song과 movie 정보 추출
                recommendation = parsed.get("recommendation", {})
                song_info = recommendation.get("song", {})
                movie_info = recommendation.get("movie", {})
                
                # TMDB와 YouTube API로 정보 강화
                enhanced_song_data = None
                enhanced_movie_data = None
                
                # 노래 정보 강화 (비동기)
                if song_info.get("title"):
                    try:
                        enhanced_song_info = await enhance_song_info(song_info.get("title"), song_info.get("reason", ""))
                        enhanced_song_data = json.dumps(enhanced_song_info, ensure_ascii=False)
                    except Exception as e:
                        print(f"노래 정보 강화 실패: {e}")
                        enhanced_song_data = json.dumps({
                            "title": song_info.get("title", ""),
                            "reason": song_info.get("reason", ""),
                            "youtube_info": {
                                "title": song_info.get("title", ""),
                                "description": "상세 정보를 찾을 수 없습니다.",
                                "youtube_url": None,
                                "video_id": None,
                                "thumbnail_url": None
                            }
                        }, ensure_ascii=False)
                
                # 영화 정보 강화 (비동기)
                if movie_info.get("title"):
                    try:
                        enhanced_movie_info = await enhance_movie_info(movie_info.get("title"), movie_info.get("reason", ""))
                        enhanced_movie_data = json.dumps(enhanced_movie_info, ensure_ascii=False)
                    except Exception as e:
                        print(f"영화 정보 강화 실패: {e}")
                        enhanced_movie_data = json.dumps({
                            "title": movie_info.get("title", ""),
                            "reason": movie_info.get("reason", ""),
                            "tmdb_info": {
                                "title": movie_info.get("title", ""),
                                "overview": "상세 정보를 찾을 수 없습니다.",
                                "poster_url": None,
                                "tmdb_id": None
                            }
                        }, ensure_ascii=False)
                
                # 기본 정보 추출 (강화된 정보에서 우선, 없으면 원본에서)
                song_title = ""
                song_reason = ""
                movie_title = ""
                movie_reason = ""
                
                if enhanced_song_data:
                    try:
                        song_data = json.loads(enhanced_song_data)
                        song_title = song_data.get("title", song_info.get("title", ""))
                        song_reason = song_data.get("reason", song_info.get("reason", ""))
                    except:
                        song_title = song_info.get("title", "")
                        song_reason = song_info.get("reason", "")
                else:
                    song_title = song_info.get("title", "")
                    song_reason = song_info.get("reason", "")
                
                if enhanced_movie_data:
                    try:
                        movie_data = json.loads(enhanced_movie_data)
                        movie_title = movie_data.get("title", movie_info.get("title", ""))
                        movie_reason = movie_data.get("reason", movie_info.get("reason", ""))
                    except:
                        movie_title = movie_info.get("title", "")
                        movie_reason = movie_info.get("reason", "")
                else:
                    movie_title = movie_info.get("title", "")
                    movie_reason = movie_info.get("reason", "")
                
                # 하나의 레코드에 모든 정보 저장
                self.db.add(CoupleWeeklyRecommendation(
                    couple_id=couple_id,
                    week_start_date=self.week_start,
                    week_end_date=self.week_end,
                    advice=advice,
                    song_title=song_title,
                    song_reason=song_reason,
                    movie_title=movie_title,
                    movie_reason=movie_reason,
                    enhanced_song_data=enhanced_song_data,
                    enhanced_movie_data=enhanced_movie_data,
                    created_at=self.now
                ))

            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"WeeklyResultSaver save 실패: {e}")

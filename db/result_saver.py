# db/result_saver.py
import json
from models.db_tables import (
    WeeklySolution, CoupleWeeklyAnalysisResult,
    CoupleWeeklyComparisonResult, CoupleWeeklyRecommendation
)
from datetime import datetime

class WeeklyResultSaver:
    def __init__(self, db_session, week_dates):
        self.db = db_session
        self.week_start = week_dates[0]
        self.week_end = week_dates[-1]
        self.now = datetime.utcnow()

    def save(self, couple_id: str, user1_id: str, user2_id: str, result: dict):
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
                self.db.add(WeeklySolution(
                    user_id=user_id,
                    content=user_result["result"],
                    created_at=self.now
                ))

        # 비교 분석
        if result.get("커플vsAI차이") and result["커플vsAI차이"]["success"]:
            self.db.add(CoupleWeeklyComparisonResult(
                couple_id=couple_id,
                week_start_date=self.week_start,
                week_end_date=self.week_end,
                comparison=result["커플vsAI차이"]["result"],
                created_at=self.now
            ))

        # 추천 조언
        if result.get("추천") and result["추천"]["success"]:
            parsed = result["추천"]["result"]
            self.db.add(CoupleWeeklyRecommendation(
                couple_id=couple_id,
                week_start_date=self.week_start,
                week_end_date=self.week_end,
                advice=parsed.get("조언", ""),
                content_type=parsed.get("추천컨텐츠", {}).get("type"),
                content_title=parsed.get("추천컨텐츠", {}).get("제목"),
                content_reason=parsed.get("추천컨텐츠", {}).get("이유"),
                created_at=self.now
            ))

        self.db.commit()

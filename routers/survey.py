from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.db import get_session  # DB 세션 의존성 주입
from models.db_tables import UserSurveyResponse, SurveyQuestion, SurveyChoice
from models.schema import SurveyResponseInput
from datetime import datetime

router = APIRouter()

@router.post("/survey/response")
def submit_survey_response(data: SurveyResponseInput, db: Session = Depends(get_session)):
    # 1. 질문 존재 여부 확인
    question = db.query(SurveyQuestion).filter_by(id=data.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="해당 설문 문항이 존재하지 않습니다.")

    # 2. 선택지가 있다면 유효성 확인
    if data.choice_id:
        choice = db.query(SurveyChoice).filter_by(id=data.choice_id, question_id=data.question_id).first()
        if not choice:
            raise HTTPException(status_code=400, detail="선택한 choice_id가 유효하지 않습니다.")

    # 3. 저장
    response = UserSurveyResponse(
        user_id=data.user_id,
        question_id=data.question_id,
        choice_id=data.choice_id,
        custom_input=data.custom_input,
        submitted_at=datetime.utcnow()
    )

    db.add(response)
    db.commit()
    db.refresh(response)

    return {"message": "설문 응답이 저장되었습니다.", "response_id": response.id}

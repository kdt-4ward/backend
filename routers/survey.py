from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.dependencies import get_db_session  # DB 세션 의존성 주입
from db.db_tables import UserSurveyResponse, SurveyQuestion, SurveyChoice
from models.schema import SurveyResponseInput
from datetime import datetime
from typing import List

router = APIRouter()

@router.post("/response")
def submit_survey_response(data_list: List[SurveyResponseInput], db: Session = Depends(get_db_session)):
    print('데이터', data_list)
    try:
        responses = []
        # 1. 질문 존재 여부 확인
        for data in data_list:
            question = db.query(SurveyQuestion).filter_by(id=data.question_id).first()
            if not question:
                raise HTTPException(status_code=404, detail=f"{data.question_id}번 문항이 존재하지 않습니다.")

            # 2. 선택지가 있다면 유효성 확인
            if data.choice_id:
                ## choice_id 맞춰 주기
                ### 처음 5개 질문은 5지선다 + 기타
                # if question.id < 6:
                #     data.choice_id -= (question.id - 1) * 6
                # else:
                #     ### 이후론 4지선다 + 기타
                #     data.choice_id -= (question.id - 6) * 5 + 30
                
                actual_choice_id = (data.question_id - 1) * 6 + data.choice_id
                choice = db.query(SurveyChoice).filter_by(id=actual_choice_id, question_id=data.question_id).first()
                if not choice:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"{data.question_id}번 문항에서 선택한 choice_id({data.choice_id})가 유효하지 않습니다. (실제: {actual_choice_id})"
                    )
                data.choice_id = actual_choice_id

            # 3. 저장
            response = UserSurveyResponse(
                user_id=data.user_id,
                question_id=data.question_id,
                choice_id=data.choice_id,
                custom_input=data.custom_input,
                submitted_at=datetime.utcnow()
            )

            db.add(response)
            responses.append(response)
            
        db.commit()
        db.refresh(response)
        # 성공적으로 다 저장된 경우에만!
        return {"message": "설문 응답이 저장되었습니다.", "user_id": data_list[0].user_id}
    
    except Exception as e:
        db.rollback()  # 한 개라도 실패하면 모두 롤백!
        print("설문 저장 오류:", e)
        raise

@router.get("/check")
def check_survey(user_id: str, db: Session = Depends(get_db_session)):
    # 유저가 한 번이라도 설문 응답했으면 "done": True 반환
    resp = db.query(UserSurveyResponse).filter_by(user_id=user_id).first()
    return {"done": bool(resp)}
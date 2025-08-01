import re
from datetime import datetime
from pprint import pprint

def parse_kakao_log(raw_text: str, couple_id: str, name2id: dict, partner_id: str):
    messages = []
    current_date = None
    current_msg = None  # 현재 작성 중인 메시지

    date_pattern = re.compile(r"^-{10,}\s+(\d{4}년 \d{1,2}월 \d{1,2}일 [가-힣]+요일)\s+-{10,}")
    msg_pattern = re.compile(r"^\[([^\]]+)\] \[([^\]]+)\] (.+)$")

    def strip_korean_weekday(date_str: str) -> str:
        return re.sub(r"\s[가-힣]+요일$", "", date_str)

    def parse_korean_time(time_str: str) -> datetime.time:
        match = re.match(r"(오전|오후)\s*(\d{1,2}):(\d{2})", time_str)
        if not match:
            raise ValueError(f"시간 파싱 실패: {time_str}")
        period, hour, minute = match.groups()
        hour, minute = int(hour), int(minute)
        if period == "오후" and hour != 12:
            hour += 12
        if period == "오전" and hour == 12:
            hour = 0
        return datetime.strptime(f"{hour:02}:{minute:02}", "%H:%M").time()

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue

        # 날짜 변경
        date_match = date_pattern.match(line)
        if date_match:
            raw_date = strip_korean_weekday(date_match.group(1))
            current_date = datetime.strptime(raw_date, "%Y년 %m월 %d일").date()
            continue

        # 메시지 시작 줄
        msg_match = msg_pattern.match(line)
        if msg_match and current_date:
            # 이전 메시지 저장
            if current_msg:
                messages.append(current_msg)
                current_msg = None

            user, time_str, content = msg_match.groups()

            if "삭제된 메시지입니다" in content:
                continue

            try:
                time_obj = parse_korean_time(time_str)
            except ValueError as e:
                print(f"[경고] 시간 파싱 실패: {e}")
                continue

            created_at = datetime.combine(current_date, time_obj)
            current_msg = {
                "user_id": name2id.get(user, partner_id),
                "couple_id": couple_id,
                "content": content,
                "image_url": None,
                "has_image": False,
                "created_at": created_at
            }
        else:
            # 이어지는 줄 → 이전 메시지에 붙임
            if current_msg:
                current_msg["content"] += "\n" + line

    # 마지막 메시지 저장
    if current_msg:
        messages.append(current_msg)

    return messages




if __name__ == "__main__":
    # 예시 실행

    raw_text = """IBM 아카데미 2조 님과 카카오톡 대화
저장한 날짜 : 2025-08-01 13:07:26

--------------- 2025년 5월 31일 토요일 ---------------
[IBM 아카데미 김병천] [오전 11:57] 삭제된 메시지입니다.
[IBM 아카데미 김병천] [오전 11:57] 삭제된 메시지입니다.
[IBM 아카데미 김병천] [오전 11:58] 삭제된 메시지입니다.
[IBM 아카데미 김병천] [오후 12:00] https://www.notion.so/StyleMatch-AI-204041afb72480ebad20c70b5c33dbd4?source=copy_link
[IBM 아카데미 김병천] [오후 12:00] https://www.notion.so/FinInsight-AI-203041afb724806ead70fb1d78c3b3c3?source=copy_link
[IBM 아카데미 김병천] [오후 12:00] https://www.notion.so/MoodTune-AI-203041afb724806b95a0e4a485afe559?source=copy_link
--------------- 2025년 6월 2일 월요일 ---------------
[이정두] [오전 9:42] slack 초대 링크 입니다. 파일 공유 여기에 하는게 깔끔할 것 같아서 만들었습니다 ! 

https://join.slack.com/t/ibm-redhataiacademy-2/shared_invite/zt-36sezwqy9-LawSJeNKoiX9O2RFplyUoA"""

    parsed_messages = parse_kakao_log(raw_text, "ibm_group_2", {"IBM 아카데미 김병천": "김병천"}, partner_id="이정두_1")
    pprint(parsed_messages)  # 일부 출력 확인

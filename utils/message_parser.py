import re
from datetime import datetime
from pprint import pprint

def parse_kakao_log(raw_text: str, couple_id: str, name2id: dict, partner_id: str):
    messages = []
    current_date = None
    current_msg = None  # 현재 작성 중인 메시지

    # 형식 1: --------------- 2025년 5월 31일 토요일 ---------------
    date_pattern_1 = re.compile(r"^-{10,}\s+(\d{4}년 \d{1,2}월 \d{1,2}일 [가-힣]+요일)\s+-{10,}")
    # 형식 2: 2025년 2월 10일 월요일
    date_pattern_2 = re.compile(r"^(\d{4}년 \d{1,2}월 \d{1,2}일 [가-힣]+요일)$")
    
    # 형식 1: [사용자명] [오전/오후 시간] 내용
    msg_pattern_1 = re.compile(r"^\[([^\]]+)\] \[([^\]]+)\] (.+)$")
    # 형식 2: 2025. 2. 10. 오후 5:03, 사용자명 : 내용
    msg_pattern_2 = re.compile(r"^\d{4}\. \d{1,2}\. \d{1,2}\. (오전|오후) (\d{1,2}):(\d{2}), ([^:]+) : (.+)$")

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

    def parse_korean_time_alt(period: str, hour: str, minute: str) -> datetime.time:
        """형식 2용 시간 파싱"""
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

        # 날짜 변경 (형식 1)
        date_match_1 = date_pattern_1.match(line)
        if date_match_1:
            raw_date = strip_korean_weekday(date_match_1.group(1))
            current_date = datetime.strptime(raw_date, "%Y년 %m월 %d일").date()
            continue

        # 날짜 변경 (형식 2)
        date_match_2 = date_pattern_2.match(line)
        if date_match_2:
            raw_date = strip_korean_weekday(date_match_2.group(1))
            current_date = datetime.strptime(raw_date, "%Y년 %m월 %d일").date()
            continue

        # 메시지 시작 줄 (형식 1)
        msg_match_1 = msg_pattern_1.match(line)
        if msg_match_1 and current_date:
            # 이전 메시지 저장
            if current_msg:
                messages.append(current_msg)
                current_msg = None

            user, time_str, content = msg_match_1.groups()

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
            continue

        # 메시지 시작 줄 (형식 2)
        msg_match_2 = msg_pattern_2.match(line)
        if msg_match_2 and current_date:
            # 이전 메시지 저장
            if current_msg:
                messages.append(current_msg)
                current_msg = None

            period, hour, minute, user, content = msg_match_2.groups()

            try:
                time_obj = parse_korean_time_alt(period, hour, minute)
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
            continue

        # 이어지는 줄 → 이전 메시지에 붙임
        if current_msg:
            current_msg["content"] += "\n" + line

    # 마지막 메시지 저장
    if current_msg:
        messages.append(current_msg)

    return messages

if __name__ == "__main__":
    # 예시 실행

    test_case_1 = """IBM 아카데미 2조 님과 카카오톡 대화
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

    test_case_2 = """
    Talk_2025.8.1 12:20-1.txt
저장한 날짜 : 2025. 8. 1. 오후 3:16



2025년 2월 10일 월요일
2025. 2. 10. 오후 5:03, ☀️진 : 해솔아 너가 프런트 개발한다구 했나??
2025. 2. 10. 오후 5:03, 강해솔 : 마쟈!
2025. 2. 10. 오후 5:03, ☀️진 : 웹앱 둘다?
2025. 2. 10. 오후 5:04, 강해솔 : 웹만!
2025. 2. 10. 오후 5:04, ☀️진 : 아항
2025. 2. 10. 오후 5:04, ☀️진 : 아니 우리 창업팀 개발자를 모색중인데
2025. 2. 10. 오후 5:04, ☀️진 : 저번에 너가 얘기했던게 생각나가지고
2025. 2. 10. 오후 5:04, 강해솔 : 융웅! 어떤 개발자가 필요한데?
2025. 2. 10. 오후 5:05, ☀️진 : 음 일단 요즘 사업계획서를 쓰고있는데
2025. 2. 10. 오후 5:05, ☀️진 : 젤 필요한 건 풀스택 개발자고.. 거래플랫폼 관련 프로젝트를 해본 경험이 있으면 더 좋은 느낌이야
2025. 2. 10. 오후 5:06, 강해솔 : 풀스택은 주변에서 찾기쉽진 않은데..
2025. 2. 10. 오후 5:06, 강해솔 : 딱 나기는 한데 내가 웹 프론트백 둘다 하니까
    """

    print("=== Test Case 1 ===")
    parsed_messages_1 = parse_kakao_log(test_case_1, "ibm_group_2", {"IBM 아카데미 김병천": "김병천"}, partner_id="이정두_1")
    pprint(parsed_messages_1)

    print("\n=== Test Case 2 ===")
    parsed_messages_2 = parse_kakao_log(test_case_2, "couple_2", {"☀️진": "진"}, partner_id="user_1")
    pprint(parsed_messages_2)
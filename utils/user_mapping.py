import re
from typing import Dict, Tuple


def get_korean_particle(name: str, particle: str) -> str:
    """
    한국어 조사를 이름에 맞게 적절히 변경하는 함수
    
    Args:
        name: 사용자 이름 (이미 "님"이 포함된 형태)
        particle: 원본 조사 (가, 을, 이, 는, 도, 에서, 에게 등)
    
    Returns:
        적절히 변경된 조사
    """
    # "님"이 붙으면 받침이 있는 형태로 처리
    if name.endswith("님"):
        has_batchim = True
    else:
        # 받침이 있는지 확인 (한글 유니코드 범위: 44032-55203)
        last_char = name[-1]
        has_batchim = (ord(last_char) - 44032) % 28 != 0
    
    # 조사 매핑 규칙
    particle_mapping = {
    '가': '이' if has_batchim else '가',   # 주격조사
    '이': '이' if has_batchim else '가',   # 주격조사 (역전 가능)
    '을': '을' if has_batchim else '를',   # 목적격조사
    '를': '을' if has_batchim else '를',   # 목적격조사 (역전 가능)
    '은': '은' if has_batchim else '는',   # 보조사
    '는': '은' if has_batchim else '는',   # 보조사
    '과': '과' if has_batchim else '와',   # 접속조사
    '와': '과' if has_batchim else '와',   # 접속조사 (역전 가능)
    '으로': '으로' if has_batchim else '로',  # 방향/수단 조사
    '로': '으로' if has_batchim else '로',    # 방향/수단 조사 (역전 가능)
    
    # 받침 무관: 동일 반환
    '에게': '에게',
    '께': '께',
    '한테': '한테',
    '에서': '에서',
    '에': '에',
    '도': '도',
    '만': '만',
    '까지': '까지',
    '부터': '부터',
    '보다': '보다',
    '처럼': '처럼',
    '조차': '조차',
    '마저': '마저',
    '이나': '이나' if has_batchim else '나',
    '나': '이나' if has_batchim else '나',
    '든지': '든지',
    '라도': '이라도' if has_batchim else '라도',  # "사람이라도", "물이라도"
    '밖에': '밖에',
    '이며': '이며' if has_batchim else '며',      # "학생이며", "의사며"
    }
    return particle_mapping.get(particle, particle)


def replace_user_ids_with_names(text: str, user1_id: str, user1_name: str, 
                               user2_id: str, user2_name: str) -> str:
    """
    텍스트 내의 사용자 ID를 이름으로 매핑하고 조사를 적절히 변경하는 함수
    """
    # 사용자 ID와 이름 매핑 - 다양한 형태 지원
    user_mappings = [
        # user1, user2 형태
        {f"user{user1_id}": user1_name, f"user{user2_id}": user2_name},
        # 숫자만 있는 형태 (1, 2)
        {user1_id: user1_name, user2_id: user2_name},
        # 문자열로 변환된 형태 ("1", "2")
        {str(user1_id): user1_name, str(user2_id): user2_name},
    ]
    
    # 조사 패턴 (가, 을, 이, 은, 는, 과, 으로, 에게, 에서, 도 등) - '는' 추가
    particle_pattern = r'(은|는|이|가|을|를|과|와|으로|로|에|에서|에게|께|한테|도|만|까지|부터|보다|처럼|조차|마저|이나|나|이며|든지|라도|밖에)'
    
    # 모든 매핑에 대해 처리
    for user_mapping in user_mappings:
        for user_id, user_name in user_mapping.items():
            # 먼저 조사가 없는 단독 형태를 처리 (순서 중요!)
            # 특수 공백 문자들을 포함한 더 포괄적인 패턴
            standalone_pattern = rf'(?<![a-zA-Z0-9가-힣]){re.escape(user_id)}(?![a-zA-Z0-9가-힣])'
            
            def replace_standalone(match):
                return f"{user_name}님"
            
            text = re.sub(standalone_pattern, replace_standalone, text)
            
            # 그 다음 조사가 있는 경우를 처리
            pattern = rf'{re.escape(user_id)}({particle_pattern})'
            
            def replace_with_name(match):
                particle = match.group(1)
                # "님"이 붙은 이름으로 조사 결정
                name_with_nim = f"{user_name}님"
                adjusted_particle = get_korean_particle(name_with_nim, particle)
                return f"{name_with_nim}{adjusted_particle}"
            
            text = re.sub(pattern, replace_with_name, text)
    
    return text


# 사용 예시
if __name__ == "__main__":
    # 테스트 케이스
    test_text = "2가 먼저 시작하고, 1이 따라했어. 2에게 말했는데 1도 같이 왔어."
    result = replace_user_ids_with_names(
        text=test_text,
        user1_id="1",
        user1_name="민수",
        user2_id="2", 
        user2_name="지우"
    )
    print(f"원본: {test_text}")
    print(f"결과: {result}")
    # 출력: 원본: 2가 먼저 시작하고, 1이 따라했어. 2에게 말했는데 1도 같이 왔어.
    #       결과: 지우님이 먼저 시작하고, 민수님이 따라했어. 지우님에게 말했는데 민수님도 같이 왔어.

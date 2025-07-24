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
            # 1단계: 이미 "님"이 붙은 형태를 먼저 처리 (user1님 -> 지민님)
            nim_pattern = rf'{re.escape(user_id)}님'
            
            def replace_with_nim(match):
                return f"{user_name}님"
            
            text = re.sub(nim_pattern, replace_with_nim, text)
            
            # 2단계: 조사가 있는 경우를 처리 (user1은 -> 지민님은)
            pattern = rf'{re.escape(user_id)}({particle_pattern})'
            
            def replace_with_name(match):
                particle = match.group(1)
                # "님"이 붙은 이름으로 조사 결정
                name_with_nim = f"{user_name}님"
                adjusted_particle = get_korean_particle(name_with_nim, particle)
                return f"{name_with_nim}{adjusted_particle}"
            
            text = re.sub(pattern, replace_with_name, text)
            
            # 3단계: 조사가 없는 단독 형태를 처리 (user1 -> 지민님)
            standalone_pattern = rf'(?<![a-zA-Z0-9가-힣]){re.escape(user_id)}(?![a-zA-Z0-9가-힣])'
            
            def replace_standalone(match):
                return f"{user_name}님"
            
            text = re.sub(standalone_pattern, replace_standalone, text)
    
    return text


# 테스트 케이스들
def run_tests():
    """모든 테스트 케이스를 실행하고 결과를 확인"""
    test_cases = [
        # 기본 케이스
        {
            "text": "user1과 user2는 서로를 이해하고 배려하기 위해 노력하는 모습을 보였습니다.",
            "user1_id": "1", "user1_name": "지민",
            "user2_id": "2", "user2_name": "수아",
            "expected": "지민님과 수아님은 서로를 이해하고 배려하기 위해 노력하는 모습을 보였습니다."
        },
        # 숫자 ID 케이스
        {
            "text": "1이 먼저 시작하고, 2가 따라했어. 1에게 말했는데 2도 같이 왔어.",
            "user1_id": "1", "user1_name": "민수",
            "user2_id": "2", "user2_name": "지우",
            "expected": "민수님이 먼저 시작하고, 지우님이 따라했어. 민수님에게 말했는데 지우님도 같이 왔어."
        },
        # 다양한 조사 케이스
        {
            "text": "user1은 적극적이고, user2는 소극적이야. user1에게 말해봐. user2와 함께 가자.",
            "user1_id": "1", "user1_name": "철수",
            "user2_id": "2", "user2_name": "영희",
            "expected": "철수님은 적극적이고, 영희님은 소극적이야. 철수님에게 말해봐. 영희님과 함께 가자."
        },
        # 이미 "님"이 붙은 케이스 (중복 방지)
        {
            "text": "지민님과 user2는 친구입니다. user1님도 함께 왔습니다.",
            "user1_id": "1", "user1_name": "지민",
            "user2_id": "2", "user2_name": "수아",
            "expected": "지민님과 수아님은 친구입니다. 지민님도 함께 왔습니다."
        },
        # 복잡한 문장 케이스
        {
            "text": "이번 주 user1과 user2는 서로를 이해하고 배려하기 위해 노력하는 모습을 보였습니다. user1은 주로 적극적인 데이트 계획과 책임 있는 태도를 보였고, user2는 애정 표현을 통해 감정적으로 교류하려는 노력을 했습니다. 하지만 user2는 연락 문제로 인한 갈등을 여러 차례 표현했으며, 이는 두 사람 간의 의사소통 개선이 필요함을 시사합니다.",
            "user1_id": "1", "user1_name": "지민",
            "user2_id": "2", "user2_name": "수아",
            "expected": "이번 주 지민님과 수아님은 서로를 이해하고 배려하기 위해 노력하는 모습을 보였습니다. 지민님은 주로 적극적인 데이트 계획과 책임 있는 태도를 보였고, 수아님은 애정 표현을 통해 감정적으로 교류하려는 노력을 했습니다. 하지만 수아님은 연락 문제로 인한 갈등을 여러 차례 표현했으며, 이는 두 사람 간의 의사소통 개선이 필요함을 시사합니다."
        },
        # 특수 문자 포함 케이스
        {
            "text": "user1! user2? user1... user2!!!",
            "user1_id": "1", "user1_name": "김철수",
            "user2_id": "2", "user2_name": "박영희",
            "expected": "김철수님! 박영희님? 김철수님... 박영희님!!!"
        },
        # 대화문 케이스
        {
            "text": '"user1이 뭐라고 했어?" "user2가 그렇게 말했어."',
            "user1_id": "1", "user1_name": "민수",
            "user2_id": "2", "user2_name": "지우",
            "expected": '"민수님이 뭐라고 했어?" "지우님이 그렇게 말했어."'
        },
        # 혼합 케이스 (user1, user2, 1, 2 모두 포함)
        {
            "text": "user1과 2는 친구이고, 1과 user2도 친구입니다.",
            "user1_id": "1", "user1_name": "철수",
            "user2_id": "2", "user2_name": "영희",
            "expected": "철수님과 영희님은 친구이고, 철수님과 영희님도 친구입니다."
        }
    ]
    
    print("=== 테스트 시작 ===")
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- 테스트 {i} ---")
        print(f"입력: {test_case['text']}")
        print(f"user1_id: {test_case['user1_id']}, user1_name: {test_case['user1_name']}")
        print(f"user2_id: {test_case['user2_id']}, user2_name: {test_case['user2_name']}")
        
        result = replace_user_ids_with_names(
            test_case['text'],
            test_case['user1_id'],
            test_case['user1_name'],
            test_case['user2_id'],
            test_case['user2_name']
        )
        
        print(f"결과: {result}")
        print(f"기대: {test_case['expected']}")
        
        if result == test_case['expected']:
            print("✅ 통과")
        else:
            print("❌ 실패")
            all_passed = False
    
    print(f"\n=== 테스트 완료 ===")
    if all_passed:
        print("🎉 모든 테스트 통과!")
    else:
        print("⚠️ 일부 테스트 실패")
    
    return all_passed


# 사용 예시
if __name__ == "__main__":
    # 테스트 실행
    run_tests()

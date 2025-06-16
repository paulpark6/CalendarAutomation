import pandas as pd
from methods import *
from auth import *
from creating_calendar import *

def main():
    # INITIALIZATIONS
    recent_keys_stack = []  # list of tuples (event_key, google_event_id)

    # Authenticate and get Google Calendar service
    service = get_user_service()

    # User’s calendar ID (must already exist in Google Calendar)
    calendar_id = (
        "712bca2ad174d70e6f53a3a479e17159a4f8de4d159f1b7a9fc18aac76bfa5f6@group.calendar.google.com"
    )

    # Example “user_response” dictionary (could be replaced by store_response or file input)
    user_response = {'title': ['TOEIC',
  'Calendar API Project',
  'Workout',
  'Other',
  'TOEIC',
  'Calendar API Project',
  'Workout',
  'Other',
  'TOEIC',
  'Calendar API Project',
  'Workout',
  'Other',
  'TOEIC',
  'Calendar API Project',
  'Workout',
  'TOEIC',
  'Calendar API Project',
  'Workout',
  'TOEIC',
  'Calendar API Project',
  'Workout',
  'Other',
  'TOEIC',
  'Calendar API Project',
  'Workout',
  'TOEIC',
  'Calendar API Project',
  'Workout',
  'TOEIC',
  'Calendar API Project',
  'Workout',
  'TOEIC',
  'Calendar API Project',
  'Workout',
  'TOEIC',
  'Calendar API Project',
  'Workout',
  'TOEIC',
  'Calendar API Project',
  'Workout',
  'TOEIC',
  'Calendar API Project',
  'Workout',
  'TOEIC',
  'Other'],
 'event_date': ['2025-06-17',
  '2025-06-17',
  '2025-06-17',
  '2025-06-17',
  '2025-06-18',
  '2025-06-18',
  '2025-06-18',
  '2025-06-18',
  '2025-06-19',
  '2025-06-19',
  '2025-06-19',
  '2025-06-19',
  '2025-06-20',
  '2025-06-20',
  '2025-06-20',
  '2025-06-21',
  '2025-06-21',
  '2025-06-21',
  '2025-06-22',
  '2025-06-22',
  '2025-06-22',
  '2025-06-22',
  '2025-06-23',
  '2025-06-23',
  '2025-06-23',
  '2025-06-24',
  '2025-06-24',
  '2025-06-24',
  '2025-06-25',
  '2025-06-25',
  '2025-06-25',
  '2025-06-26',
  '2025-06-26',
  '2025-06-26',
  '2025-06-27',
  '2025-06-27',
  '2025-06-27',
  '2025-06-28',
  '2025-06-28',
  '2025-06-28',
  '2025-06-29',
  '2025-06-29',
  '2025-06-29',
  '2025-06-30',
  '2025-06-30'],
 'description': ['TOEIC Listening (Part 2, 3)',
  'txt → dict 구조 완성',
  '전신 근력',
  '루틴 적응 시작',
  'TOEIC Reading (Timed)',
  '파싱 결과 테스트',
  '스트레칭',
  '감정 일기 시작',
  'Listening + Shadowing',
  '오류 케이스 추가',
  '전신 근력',
  '가볍게 복습만',
  'Vocabulary 집중',
  'Streamlit 시작',
  '코어 중심',
  '실전 모의고사 (2시간)',
  'UI 컴포넌트 만들기',
  '유산소',
  'Listening 고난이도',
  'UI - 결과 표시',
  '전신 근력',
  '중간 점검 (회고)',
  'Reading 오답 분석',
  'Streamlit 이벤트 미리보기',
  '스트레칭',
  '실전 모의고사 2회차',
  'bulk 입력 예외처리',
  '전신 근력',
  '어휘 & Part 5 집중',
  '예외 이벤트 처리',
  '휴식 or 걷기',
  'Listening + Note-taking',
  'API 호출 검증',
  '유산소',
  'Reading 모의고사',
  '전체 테스트',
  '전신 근력',
  '문제 유형별 약점 정리',
  '마무리 커밋 & readme 작성',
  '코어 or 요가',
  '실전 시뮬레이션',
  '휴식',
  '가볍게만',
  'TOEIC 시험',
  '시험일']}

    # Convert the dictionary into a DataFrame
    df_calendar = pd.DataFrame(user_response)

    # Create new events (skipping duplicates) and get back the updated stack
    recent_keys_stack = create_schedule(
        service,
        calendar_id,
        df_calendar,
        recent_keys_stack
    )


    # Persist each newly generated (key, google_event_id) tuple into JSON
    for key, mapping in recent_keys_stack:
        save_recent_keys({key: mapping})

    # Print the final stack for confirmation
    print("Final recent keys stack: \n", recent_keys_stack)

    # # Deleting some events given the key
    for key, google_event_id in recent_keys_stack:
        delete_event(service, calendar_id, google_event_id)
    # delete_event(service, calendar_id, recent_keys_stack[0])
    # recent_keys_stack.pop(0)  # Remove the first event after deletion



if __name__ == "__main__":
    main()

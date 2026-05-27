import pytest
from xapi_tools.analytics.applied import (
    assessment_history,
    assessment_grade_history,
    subject_correct_rate,
    assessment_tag_correct_rate,
    wrong_answers,
    wrong_answers_assessment_type,
    wrong_answers_tag,
    wrong_answers_test,
    wrong_answers_chapter_test
)

@pytest.fixture
def mock_dataset():
    # Construct a dataset formatted as Pandas to_dict('dict')
    # Struct: {col: {idx: val}}
    return {
        "statement": {
            0: {
                "object": {
                    "id": "http://lecognizer.com/xapi/activities/assessment/q1",
                    "definition": {
                        "name": {"ko-KR": "문항1"}
                    }
                },
                "context": {
                    "extensions": {
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/grade": "5",
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/subject": "수학",
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/assessment-type": "차시평가",
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/semester": "2",
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/tag": "통분"
                    }
                },
                "result": {"success": True}
            },
            1: {
                "object": {
                    "id": "http://lecognizer.com/xapi/activities/assessment/q2",
                    "definition": {
                        "name": {"ko-KR": "문항2"}
                    }
                },
                "context": {
                    "extensions": {
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/grade": "5",
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/subject": "수학",
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/assessment-type": "차시평가",
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/semester": "2",
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/tag": "통분"
                    }
                },
                "result": {"success": False}
            },
            2: {
                "object": {
                    "id": "http://lecognizer.com/xapi/activities/assessment/q2",
                    "definition": {
                        "name": {"ko-KR": "문항2"}
                    }
                },
                "context": {
                    "extensions": {
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/grade": "5",
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/subject": "수학",
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/assessment-type": "단원평가",
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/semester": "2",
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/tag": "약분"
                    }
                },
                "result": {"success": False}
            },
            3: {
                "object": {
                    "id": "http://lecognizer.com/xapi/activities/assessment/q3",
                    "definition": {
                        "name": {"ko-KR": "문항3"}
                    }
                },
                "context": {
                    "extensions": {
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/grade": "6",
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/subject": "과학",
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/assessment-type": "단원평가",
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/semester": "1",
                        "http://lecognizer.com/xapi/profiles/assessment/extensions/context/tag": "우주"
                    }
                },
                "result": {"success": True}
            }
        }
    }

def test_assessment_history(mock_dataset):
    res = assessment_history(mock_dataset)
    # grade 컬럼과 subject 컬럼을 검증
    # 5학년 수학: 3개 중 1개 성공 = 0.33
    # 6학년 과학: 1개 중 1개 성공 = 1.00
    # 전체 전체: 4개 중 2개 성공 = 0.50
    
    assert "grade" in res
    assert "subject" in res
    assert "correct_rate" in res
    
    # 딕셔너리를 rows로 바꾸어 매칭하는지 확인
    from xapi_tools.utils.pandas_helper import dict_to_rows
    rows = dict_to_rows(res)
    
    match_5 = next(r for r in rows if r["grade"] == "5" and r["subject"] == "수학")
    assert match_5["correct_rate"] == 0.33
    
    match_6 = next(r for r in rows if r["grade"] == "6" and r["subject"] == "과학")
    assert match_6["correct_rate"] == 1.00
    
    match_total = next(r for r in rows if r["grade"] == "전체" and r["subject"] == "전체")
    assert match_total["correct_rate"] == 0.50

def test_assessment_grade_history(mock_dataset):
    res = assessment_grade_history(mock_dataset, "5")
    from xapi_tools.utils.pandas_helper import dict_to_rows
    rows = dict_to_rows(res)
    
    # 5학년 수학: 0.33, 5학년 전체: 0.33
    match_math = next(r for r in rows if r["subject"] == "수학")
    assert match_math["correct_rate"] == 0.33
    
    match_total = next(r for r in rows if r["subject"] == "전체")
    assert match_total["correct_rate"] == 0.33

def test_subject_correct_rate(mock_dataset):
    res = subject_correct_rate(mock_dataset, "5", "수학")
    from xapi_tools.utils.pandas_helper import dict_to_rows
    rows = dict_to_rows(res)
    
    # 통분: 2개 중 1개 성공 = 0.50
    # 약분: 1개 중 0개 성공 = 0.00
    # 전체: 3개 중 1개 성공 = 0.33
    match_tongbun = next(r for r in rows if r["tag"] == "통분")
    assert match_tongbun["correct_rate"] == 0.50
    
    match_yakbun = next(r for r in rows if r["tag"] == "약분")
    assert match_yakbun["correct_rate"] == 0.00
    
    match_total = next(r for r in rows if r["tag"] == "전체")
    assert match_total["correct_rate"] == 0.33

def test_assessment_tag_correct_rate(mock_dataset):
    res = assessment_tag_correct_rate(mock_dataset, "5", "수학", "통분")
    from xapi_tools.utils.pandas_helper import dict_to_rows
    rows = dict_to_rows(res)
    
    # q1: 1/1 = 1.0, q2: 0/1 = 0.0
    match_q1 = next(r for r in rows if "q1" in r["question_id"])
    assert match_q1["correct_rate"] == 1.0
    
    match_q2 = next(r for r in rows if "q2" in r["question_id"])
    assert match_q2["correct_rate"] == 0.0

def test_wrong_answers(mock_dataset):
    res = wrong_answers(mock_dataset)
    from xapi_tools.utils.pandas_helper import dict_to_rows
    rows = dict_to_rows(res)
    
    # q2는 2번 틀림 (attempt_count = 2)
    match_q2 = next(r for r in rows if "q2" in r["question_id"])
    assert match_q2["attempt_count"] == 2

def test_wrong_answers_assessment_type(mock_dataset):
    res = wrong_answers_assessment_type(mock_dataset, "차시평가")
    from xapi_tools.utils.pandas_helper import dict_to_rows
    rows = dict_to_rows(res)
    
    # 차시평가에서 q2는 1번 틀림
    match_q2 = next(r for r in rows if "q2" in r["question_id"])
    assert match_q2["attempt_count"] == 1

def test_wrong_answers_tag(mock_dataset):
    res = wrong_answers_tag(mock_dataset, "통분")
    from xapi_tools.utils.pandas_helper import dict_to_rows
    rows = dict_to_rows(res)
    
    match_q2 = next(r for r in rows if "q2" in r["question_id"])
    assert match_q2["attempt_count"] == 1

def test_wrong_answers_test(mock_dataset):
    res = wrong_answers_test(mock_dataset, "수학")
    from xapi_tools.utils.pandas_helper import dict_to_rows
    rows = dict_to_rows(res)
    
    assert len(rows) == 1  # q2가 리턴되어야 함
    assert "q2" in rows[0]["question_id"]
    assert rows[0]["recommend_level"] == "복습필수"

def test_wrong_answers_chapter_test(mock_dataset):
    res = wrong_answers_chapter_test(mock_dataset, "수학", "5", "2", "통분")
    from xapi_tools.utils.pandas_helper import dict_to_rows
    rows = dict_to_rows(res)
    
    assert len(rows) == 1
    assert "q2" in rows[0]["question_id"]
    assert rows[0]["recommend_level"] == "단원정복"

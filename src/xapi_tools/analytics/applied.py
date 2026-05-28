from typing import Dict, Any, List, Optional
from xapi_tools.utils.pandas_helper import dict_to_rows, rows_to_dict
from xapi_tools.analytics.utils import ensure_data

def _extract_assessment_metadata(stmt: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper function to parse assessment-related metadata from xAPI statements.
    """
    stmt = stmt.get("statement", stmt)
    
    obj = stmt.get("object", {})
    question_id = obj.get("id", "Unknown Question ID")
    
    # Extract question name
    names = obj.get("definition", {}).get("name", {})
    question_name = "Unknown Question"
    if isinstance(names, dict):
        question_name = names.get("ko-KR", names.get("en-US", next(iter(names.values())) if names else obj.get("id", question_name)))
    else:
        question_name = names or obj.get("id", question_name)
        
    context = stmt.get("context") or {}
    extensions_dict = context.get("extensions") or {}
    
    EXT_PREFIX = "http://lecognizer.com/xapi/profiles/assessment/extensions/context/"
    ext_keys = ["assessment-type", "subject", "grade", "semester", "tag"]
    
    info = {}
    for key in ext_keys:
        val = extensions_dict.get(f"{EXT_PREFIX}{key}") or extensions_dict.get(key)
        info[key] = val
        
    info["question_id"] = question_id
    info["question_name"] = question_name
    
    result = stmt.get("result", {})
    info["success"] = result.get("success")
    info["completion"] = result.get("completion")
    
    return info

# ==============================================================================
# APPLIED ANALYTICS APIS
# ==============================================================================

@ensure_data
def assessment_history(dataset: Dict[str, Dict[int, Any]]) -> Dict[str, Dict[int, Any]]:
    """
    학년 및 과목별 평균 정답률 및 전체 평균 정답률 반환.
    """
    rows = dict_to_rows(dataset)
    groups = {}  # (grade, subject) -> {correct: 0, total: 0}
    total_correct = 0
    total_count = 0
    
    for r in rows:
        meta = _extract_assessment_metadata(r)
        success = meta["success"]
        if success is None: continue
            
        grade = str(meta["grade"]) if meta["grade"] else "5"
        subject = meta["subject"] or "수학"
        
        key = (grade, subject)
        if key not in groups: groups[key] = {"correct": 0, "total": 0}
            
        groups[key]["total"] += 1
        total_count += 1
        if success is True:
            groups[key]["correct"] += 1
            total_correct += 1
            
    results = []
    for (grade, subject), counts in groups.items():
        rate = counts["correct"] / counts["total"] if counts["total"] > 0 else 0.0
        results.append({
            "grade": grade,
            "subject": subject,
            "correct_rate": round(rate, 2),
            "total_questions": counts["total"]
        })
        
    if total_count > 0:
        results.append({
            "grade": "전체",
            "subject": "전체",
            "correct_rate": round(total_correct / total_count, 2),
            "total_questions": total_count
        })
        
    return rows_to_dict(results)

@ensure_data
def assessment_grade_history(dataset: Dict[str, Dict[int, Any]], grade: str) -> Dict[str, Dict[int, Any]]:
    """
    특정 학년의 과목별 및 전체 평균 정답률 반환.
    """
    rows = dict_to_rows(dataset)
    groups = {}  # subject -> {correct: 0, total: 0}
    total_correct = 0
    total_count = 0
    
    for r in rows:
        meta = _extract_assessment_metadata(r)
        if str(meta["grade"]) != str(grade): continue
        success = meta["success"]
        if success is None: continue
            
        subject = meta["subject"] or "수학"
        if subject not in groups: groups[subject] = {"correct": 0, "total": 0}
            
        groups[subject]["total"] += 1
        total_count += 1
        if success is True:
            groups[subject]["correct"] += 1
            total_correct += 1
            
    results = []
    for subject, counts in groups.items():
        rate = counts["correct"] / counts["total"] if counts["total"] > 0 else 0.0
        results.append({
            "requested_grade": grade,
            "subject": subject,
            "correct_rate": round(rate, 2),
            "total_questions": counts["total"]
        })
        
    if total_count > 0:
        results.append({
            "requested_grade": grade,
            "subject": "전체",
            "correct_rate": round(total_correct / total_count, 2),
            "total_questions": total_count
        })
        
    return rows_to_dict(results)

@ensure_data
def subject_correct_rate(dataset: Dict[str, Dict[int, Any]], grade: str, subject: str) -> Dict[str, Dict[int, Any]]:
    """
    특정 학년과 과목의 단원(tag)별 및 전체 정답률 반환.
    """
    rows = dict_to_rows(dataset)
    groups = {}  # tag -> {correct: 0, total: 0}
    total_correct = 0
    total_count = 0
    
    for r in rows:
        meta = _extract_assessment_metadata(r)
        if str(meta["grade"]) != str(grade) or meta["subject"] != subject: continue
        success = meta["success"]
        if success is None: continue
            
        tag = meta["tag"] or "기본개념"
        if tag not in groups: groups[tag] = {"correct": 0, "total": 0}
            
        groups[tag]["total"] += 1
        total_count += 1
        if success is True:
            groups[tag]["correct"] += 1
            total_correct += 1
            
    results = []
    for tag, counts in groups.items():
        rate = counts["correct"] / counts["total"] if counts["total"] > 0 else 0.0
        results.append({
            "requested_grade": grade,
            "requested_subject": subject,
            "tag": tag,
            "correct_rate": round(rate, 2),
            "total_questions": counts["total"]
        })
    
    if total_count > 0:
        results.append({
            "requested_grade": grade,
            "requested_subject": subject,
            "tag": "전체 평균",
            "correct_rate": round(total_correct / total_count, 2),
            "total_questions": total_count
        })
        
    return rows_to_dict(results)

@ensure_data
def assessment_tag_correct_rate(dataset: Dict[str, Dict[int, Any]], grade: str, subject: str, tags: List[str]) -> Dict[str, Any]:
    """
    특정 개념(태그)들의 문항별 상세 정답률을 태그별로 그룹화하여 반환.
    """
    rows = dict_to_rows(dataset)
    tag_results = {}
    
    for tag in tags:
        groups = {}  # question_id -> {correct: 0, total: 0, name: ""}
        for r in rows:
            meta = _extract_assessment_metadata(r)
            if str(meta["grade"]) != str(grade) or meta["subject"] != subject or meta["tag"] != tag: continue
            success = meta["success"]
            if success is None: continue
                
            q_id = meta["question_id"]
            if q_id not in groups: groups[q_id] = {"correct": 0, "total": 0, "name": meta["question_name"]}
                
            groups[q_id]["total"] += 1
            if success is True: groups[q_id]["correct"] += 1
                
        results = []
        for q_id, counts in groups.items():
            rate = counts["correct"] / counts["total"] if counts["total"] > 0 else 0.0
            results.append({
                "requested_grade": grade,
                "requested_subject": subject,
                "requested_tag": tag,
                "question_id": q_id,
                "question_name": counts["name"],
                "correct_count": counts["correct"],
                "total_count": counts["total"],
                "correct_rate": round(rate, 2)
            })
            
        tag_results[tag] = rows_to_dict(results)
        
    return tag_results

@ensure_data
def wrong_answers(dataset: Dict[str, Dict[int, Any]]) -> Dict[str, Dict[int, Any]]:
    """
    유저의 오답 상세 목록(문항, 개념, 시도 횟수 등) 반환.
    """
    rows = dict_to_rows(dataset)
    questions = {}
    for r in rows:
        meta = _extract_assessment_metadata(r)
        if meta["success"] is False:
            q_id = meta["question_id"]
            if q_id not in questions:
                questions[q_id] = {
                    "question_id": q_id,
                    "question_name": meta["question_name"],
                    "tag": meta["tag"],
                    "attempt_count": 0
                }
            questions[q_id]["attempt_count"] += 1
            
    return rows_to_dict(list(questions.values()))

@ensure_data
def wrong_answers_assessment_type(dataset: Dict[str, Dict[int, Any]], assessment_types: List[str]) -> Dict[str, Any]:
    """
    특정 평가 유형들의 오답 목록을 유형별로 그룹화하여 반환.
    """
    rows = dict_to_rows(dataset)
    type_results = {}
    
    for a_type in assessment_types:
        questions = {}
        for r in rows:
            meta = _extract_assessment_metadata(r)
            if meta["assessment-type"] != a_type:
                continue
            if meta["success"] is False:
                q_id = meta["question_id"]
                if q_id not in questions:
                    questions[q_id] = {
                        "question_id": q_id,
                        "question_name": meta["question_name"],
                        "assessment_type": a_type,
                        "tag": meta["tag"],
                        "attempt_count": 0
                    }
                questions[q_id]["attempt_count"] += 1
                
        type_results[a_type] = rows_to_dict(list(questions.values()))
            
    return type_results

@ensure_data
def wrong_answers_tag(dataset: Dict[str, Dict[int, Any]], tags: List[str]) -> Dict[str, Any]:
    """
    특정 개념(태그)들의 오답 목록을 태그별로 그룹화하여 반환.
    """
    rows = dict_to_rows(dataset)
    tag_results = {}
    
    for tag in tags:
        questions = {}
        for r in rows:
            meta = _extract_assessment_metadata(r)
            if meta["tag"] != tag:
                continue
            if meta["success"] is False:
                q_id = meta["question_id"]
                if q_id not in questions:
                    questions[q_id] = {
                        "question_id": q_id,
                        "question_name": meta["question_name"],
                        "tag": tag,
                        "attempt_count": 0
                    }
                questions[q_id]["attempt_count"] += 1
                
        tag_results[tag] = rows_to_dict(list(questions.values()))
            
    return tag_results

@ensure_data
def wrong_answers_test(dataset: Dict[str, Dict[int, Any]], subjects: List[str]) -> Dict[str, Any]:
    """
    특정 과목들의 오답 문항으로 재구성한 복습 시험지를 과목별로 그룹화하여 반환.
    """
    rows = dict_to_rows(dataset)
    subject_results = {}
    
    for subject in subjects:
        questions = {}
        for r in rows:
            meta = _extract_assessment_metadata(r)
            if meta["subject"] != subject:
                continue
            if meta["success"] is False:
                q_id = meta["question_id"]
                if q_id not in questions:
                    questions[q_id] = {
                        "question_id": q_id,
                        "question_name": meta["question_name"],
                        "tag": meta["tag"],
                        "recommend_level": "복습필수"
                    }
                    
        subject_results[subject] = rows_to_dict(list(questions.values()))
            
    return subject_results

@ensure_data
def wrong_answers_chapter_test(
    dataset: Dict[str, Dict[int, Any]], 
    subjects: List[str], 
    grades: List[str], 
    semesters: List[str], 
    chapters: List[str]
) -> Dict[str, Any]:
    """
    단원별 복습 시험지를 단원별로 그룹화하여 반환.
    """
    rows = dict_to_rows(dataset)
    chapter_results = {}
    
    # Standardize input to lists of strings
    subjects = [str(s) for s in subjects]
    grades = [str(g) for g in grades]
    semesters = [str(s) for s in semesters]
    
    for chapter in chapters:
        questions = {}
        for r in rows:
            meta = _extract_assessment_metadata(r)
            if str(meta["subject"]) not in subjects or str(meta["grade"]) not in grades or str(meta["semester"]) not in semesters:
                continue
            
            # Tag and chapter match logic (flexible inclusion check)
            tag_str = str(meta["tag"])
            if chapter not in tag_str and tag_str not in chapter:
                continue
                
            if meta["success"] is False:
                q_id = meta["question_id"]
                if q_id not in questions:
                    questions[q_id] = {
                        "question_id": q_id,
                        "question_name": meta["question_name"],
                        "tag": meta["tag"],
                        "recommend_level": "단원정복"
                    }
                    
        chapter_results[chapter] = rows_to_dict(list(questions.values()))
            
    return chapter_results

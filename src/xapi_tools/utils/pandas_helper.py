from typing import Dict, Any, List

def dict_to_rows(dataset: Dict[str, Dict[int, Any]]) -> List[Dict[str, Any]]:
    """
    Pandas의 DataFrame.to_dict() 형태(열지향 딕셔너리: {컬럼: {인덱스: 값}})를
    파이썬의 행지향 딕셔너리 리스트([{컬럼: 값}])로 변환합니다.
    """
    if not dataset:
        return []
        
    # 첫 번째 컬럼의 인덱스 목록을 오름차순으로 정렬하여 기준으로 사용
    first_col = next(iter(dataset.values()))
    indices = sorted(list(first_col.keys()))
    
    rows = []
    for idx in indices:
        row = {}
        for col, col_data in dataset.items():
            row[col] = col_data.get(idx)
        rows.append(row)
        
    return rows

def rows_to_dict(rows: List[Dict[str, Any]]) -> Dict[str, Dict[int, Any]]:
    """
    파이썬의 행지향 딕셔너리 리스트([{컬럼: 값}])를
    Pandas의 DataFrame.to_dict() 형태(열지향 딕셔너리: {컬럼: {인덱스: 값}})로 변환합니다.
    """
    if not rows:
        return {}
        
    cols = list(rows[0].keys())
    result = {col: {} for col in cols}
    
    for idx, row in enumerate(rows):
        for col in cols:
            result[col][idx] = row.get(col)
            
    return result

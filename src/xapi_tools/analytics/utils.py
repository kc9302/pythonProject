import functools
from typing import Dict, Any, Callable
from xapi_tools.utils.pandas_helper import dict_to_rows

def ensure_data(func: Callable):
    """
    분석 데이터셋이 비어있는지 확인하는 데코레이터.
    데이터가 없으면 '저장소에 데이터가 없습니다'를 반환하고 함수 실행을 건너뜜.
    지원 형식: Dict[str, Dict[int, Any]] (Column-oriented) 또는 List[Dict[str, Any]] (Row-oriented)
    """
    @functools.wraps(func)
    def wrapper(data: Any, *args, **kwargs):
        is_empty = False

        if data is None:
            is_empty = True
        elif isinstance(data, dict):
            # Column-oriented check: {"col": {0: val}}
            if not data:
                is_empty = True
            else:
                first_col = next(iter(data.values()))
                if not first_col:
                    is_empty = True
        elif isinstance(data, (list, set, tuple)):
            # Row-oriented check
            if not data:
                is_empty = True

        if is_empty:
            return {"result": "데이터 없음"}

        return func(data, *args, **kwargs)

    return wrapper

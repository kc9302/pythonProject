import re
from datetime import datetime
from typing import Any, Dict, Optional
from .canonical_model import CanonicalStatement, CanonicalActor, CanonicalTarget, CanonicalResult

def parse_iso8601_duration(duration_str: str) -> float:
    """
    ISO 8601 duration 문자열(예: PT2M30S, PT1H, P1DT2H)을 초(seconds) 단위의 실수로 변환합니다.
    숫자 형태의 문자열이 들어오면 그대로 float로 변환합니다.
    """
    if not duration_str:
        return 0.0
    
    # 만약 이미 숫자 형태라면 바로 변환
    try:
        return float(duration_str)
    except ValueError:
        pass
        
    pattern = re.compile(
        r'^P?(?:(?P<days>\d+)D)?T?(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?$'
    )
    match = pattern.match(duration_str)
    if not match:
        return 0.0
        
    parts = match.groupdict()
    days = float(parts['days'] or 0)
    hours = float(parts['hours'] or 0)
    minutes = float(parts['minutes'] or 0)
    seconds = float(parts['seconds'] or 0)
    
    return (days * 86400) + (hours * 3600) + (minutes * 60) + seconds

def resolve_path(data: dict, path: str) -> Any:
    """
    딕셔너리에서 점(.) 표기법 경로를 사용해 값을 추출합니다.
    - 예: "statement.actor.account.name"
    - extensions의 URI 키와 같이 중간에 점(.)이 들어가는 경우를 위해
      '.extensions.' 또는 '.extension.' 키를 특수 처리합니다.
    """
    if not data or not path:
        return None
        
    # 만약 데이터의 루트에 'statement' 키가 없는데 경로가 'statement.'으로 시작하는 경우 fallback 처리
    if "statement" not in data and path.startswith("statement."):
        fallback_path = path[10:] # len("statement.") == 10
        val = resolve_path(data, fallback_path)
        if val is not None:
            return val

    # extensions 특수 처리
    for marker in [".extensions.", ".extension."]:
        if marker in path:
            prefix, uri_key = path.split(marker, 1)
            parent = resolve_path(data, prefix)
            if isinstance(parent, dict):
                # parent 자체 혹은 parent.extensions에서 값을 가져옴
                ext_dict = parent.get("extensions", parent.get("extension", parent))
                if isinstance(ext_dict, dict):
                    return ext_dict.get(uri_key)
            return None

    # 일반적인 dot-path 탐색
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current

class MappingEngine:
    def __init__(self, config: Dict[str, Any]):
        """
        config 예시:
        {
          "client_id": "company_a",
          "mappings": {
            "actor_id_path": "statement.actor.account.name",  # 혹은 "statement.actor.mbox"
            "actor_name_path": "statement.actor.name",
            "verb_mapping": {
              "http://aidtbook.kr/xapi/profiles/media/verbs/played": "played",
              "http://hy.com/xapi/profiles/assessment/1.0/verbs/submitted": "completed"
            },
            "score_path": "statement.result.score.raw",
            "score_min": 0,
            "score_max": 100,
            "duration_path": "statement.result.duration",
            "is_success_path": "statement.result.success",
            "is_completion_path": "statement.result.completion",
            "target_id_path": "statement.object.id",
            "target_type_path": "statement.object.definition.type",
            "extensions": {
              "device": "statement.context.extensions.http://example.com/ext/device"
            }
          }
        }
        """
        self.client_id = config.get("client_id", "default_client")
        self.mappings = config.get("mappings", {})
        self.actor_id_path = self.mappings.get("actor_id_path")
        self.actor_name_path = self.mappings.get("actor_name_path")
        self.verb_mapping = self.mappings.get("verb_mapping", {})
        self.score_path = self.mappings.get("score_path")
        self.score_min = self.mappings.get("score_min")
        self.score_max = self.mappings.get("score_max")
        self.duration_path = self.mappings.get("duration_path")
        self.is_success_path = self.mappings.get("is_success_path")
        self.is_completion_path = self.mappings.get("is_completion_path")
        self.target_id_path = self.mappings.get("target_id_path", "statement.object.id")
        self.target_type_path = self.mappings.get("target_type_path", "statement.object.definition.type")
        self.extension_mappings = self.mappings.get("extensions", {})

    def normalize(self, raw_doc: Dict[str, Any]) -> CanonicalStatement:
        """
        원시 xAPI 문서를 매핑 설정을 기반으로 정규화된 CanonicalStatement 객체로 변환합니다.
        """
        # 1. Actor 추출
        actor_id = None
        if self.actor_id_path:
            actor_id = resolve_path(raw_doc, self.actor_id_path)
        
        # actor_id가 검색되지 않은 경우 표준 경로들 자동 폴백
        if not actor_id:
            for fallback_path in ["statement.actor.mbox", "statement.actor.account.name", "actor.mbox", "actor.account.name"]:
                actor_id = resolve_path(raw_doc, fallback_path)
        
        # 여전히 없다면 알 수 없음 처리
        if not actor_id:
            actor_id = "unknown_actor"
            
        actor_name = None
        if self.actor_name_path:
            actor_name = resolve_path(raw_doc, self.actor_name_path)
        if not actor_name:
            actor_name = resolve_path(raw_doc, "statement.actor.name") or resolve_path(raw_doc, "actor.name")

        canonical_actor = CanonicalActor(id=str(actor_id), name=actor_name)

        # 2. Verb 카테고리화
        original_verb_id = resolve_path(raw_doc, "statement.verb.id") or resolve_path(raw_doc, "verb.id") or ""
        verb_category = self.verb_mapping.get(original_verb_id)
        
        if not verb_category:
            # 매핑에 없는 경우 URI의 마지막 단어를 카테고리로 추론 시도
            verb_category = original_verb_id.split("/")[-1] if "/" in original_verb_id else "unknown"
            
        # 3. Target (Object) 추출
        target_id = resolve_path(raw_doc, self.target_id_path) or resolve_path(raw_doc, "statement.object.id") or resolve_path(raw_doc, "object.id") or "unknown_target"
        target_type_raw = resolve_path(raw_doc, self.target_type_path) or resolve_path(raw_doc, "statement.object.definition.type") or resolve_path(raw_doc, "object.definition.type")
        
        # Target Type 표준화 추론
        target_type = None
        if target_type_raw:
            target_type_raw_str = str(target_type_raw).lower()
            if "media" in target_type_raw_str or "video" in target_type_raw_str or "audio" in target_type_raw_str:
                target_type = "media"
            elif "assessment" in target_type_raw_str or "quiz" in target_type_raw_str or "test" in target_type_raw_str:
                target_type = "assessment"
            else:
                target_type = target_type_raw_str.split("/")[-1]
                
        target_name = resolve_path(raw_doc, "statement.object.definition.name.ko-KR") or resolve_path(raw_doc, "statement.object.definition.name.en-US") or resolve_path(raw_doc, "statement.object.definition.name")
        if isinstance(target_name, dict):
            target_name = next(iter(target_name.values()))
            
        canonical_target = CanonicalTarget(id=str(target_id), type=target_type, name=target_name)

        # 4. Result 정규화
        score_scaled = None
        if self.score_path:
            raw_score = resolve_path(raw_doc, self.score_path)
            if raw_score is not None:
                try:
                    raw_score = float(raw_score)
                    if self.score_min is not None and self.score_max is not None and (self.score_max - self.score_min) > 0:
                        score_scaled = (raw_score - self.score_min) / (self.score_max - self.score_min)
                    else:
                        # 이미 0.0 ~ 1.0 사이 값인 경우 그대로 적용
                        if 0.0 <= raw_score <= 1.0:
                            score_scaled = raw_score
                except ValueError:
                    pass
        
        # Pydantic validation에서 scaled score가 직접 존재하는 경우 자동 폴백
        if score_scaled is None:
            raw_scaled = resolve_path(raw_doc, "statement.result.score.scaled") or resolve_path(raw_doc, "result.score.scaled")
            if raw_scaled is not None:
                try:
                    score_scaled = float(raw_scaled)
                except ValueError:
                    pass

        # Duration 처리
        duration_seconds = None
        if self.duration_path:
            raw_duration = resolve_path(raw_doc, self.duration_path)
            if raw_duration is not None:
                duration_seconds = parse_iso8601_duration(str(raw_duration))
        if duration_seconds is None:
            raw_duration = resolve_path(raw_doc, "statement.result.duration") or resolve_path(raw_doc, "result.duration")
            if raw_duration is not None:
                duration_seconds = parse_iso8601_duration(str(raw_duration))

        # Success / Completion
        is_success = None
        if self.is_success_path:
            is_success = resolve_path(raw_doc, self.is_success_path)
        if is_success is None:
            is_success = resolve_path(raw_doc, "statement.result.success") or resolve_path(raw_doc, "result.success")
            
        is_completion = None
        if self.is_completion_path:
            is_completion = resolve_path(raw_doc, self.is_completion_path)
        if is_completion is None:
            is_completion = resolve_path(raw_doc, "statement.result.completion") or resolve_path(raw_doc, "result.completion")

        canonical_result = CanonicalResult(
            score_scaled=score_scaled,
            is_success=is_success if isinstance(is_success, bool) else None,
            is_completion=is_completion if isinstance(is_completion, bool) else None,
            duration_seconds=duration_seconds
        )

        # 5. Timestamp 파싱
        raw_timestamp = resolve_path(raw_doc, "statement.timestamp") or resolve_path(raw_doc, "timestamp")
        if raw_timestamp:
            try:
                # ISO 형식 파싱
                if isinstance(raw_timestamp, datetime):
                    timestamp = raw_timestamp
                else:
                    timestamp_str = str(raw_timestamp).replace("Z", "+00:00")
                    timestamp = datetime.fromisoformat(timestamp_str)
            except Exception:
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()

        # 6. Custom Metadata 추출
        custom_metadata = {}
        for meta_key, meta_path in self.extension_mappings.items():
            val = resolve_path(raw_doc, meta_path)
            if val is not None:
                custom_metadata[meta_key] = val

        return CanonicalStatement(
            client_id=self.client_id,
            actor=canonical_actor,
            verb_category=verb_category,
            original_verb_id=original_verb_id,
            target=canonical_target,
            result=canonical_result,
            custom_metadata=custom_metadata,
            timestamp=timestamp
        )

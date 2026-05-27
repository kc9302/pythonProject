# xAPI 도구 (xAPI Tools)

xAPI 데이터 조작, 검증 및 분석을 위한 포괄적인 툴킷입니다.
이 패키지는 세션 프로파일 검증 및 verb 흐름 확인을 포함한 다양한 xAPI 유틸리티를 통합합니다.

## 기능

- **세션 검증기 (Session Validator)**: Session Profile 로직에 따라 xAPI statement를 검증하고, 선택적 키(optional key)의 일관성을 확인합니다.
- **평가 흐름 확인 (Assessment Flow Check)**: 평가(Assessment) 프로파일의 verb 흐름을 분석합니다 (스트리밍 모드 지원).
- **유틸리티 함수**: xAPI 데이터를 위한 일반적인 도우미 함수들 (예: 행위자(Actor) 이름 추출).

## 설치

이 프로젝트는 `uv`로 관리됩니다.

1. **uv 설치**: [uv 문서 참조](https://docs.astral.sh/uv/)
2. **의존성 동기화**:
   ```bash
   uv sync
   ```

## 사용법

이 패키지는 메인 CLI `xapi-tools`를 제공합니다.

### 세션 검증기 (Session Validator)
```bash
uv run xapi-tools session-validator --input-jsonl data.jsonl --out output_dir
```

### 평가 흐름 확인 (Assessment Flow Check)
```bash
uv run xapi-tools assessment-flow-check --host localhost --db lrs --coll statements
```

## 개발

### 디렉터리 구조
- `src/xapi_tools`: 소스 코드.
- `src/xapi_tools/session_validator`: 포팅된 세션 검증 로직.
- `src/xapi_tools/verb_flow_checks`: 포팅된 verb 흐름 확인 로직.
- `src/xapi_tools/utils`: 일반 유틸리티.
- `tests`: 유닛 테스트.

### 테스트 실행
TDD(Test-Driven Development) 방식을 따릅니다.

```bash
uv run pytest
```

### 새 기능 추가
1. `tests/` 또는 `src/xapi_tools/.../tests/`에 테스트 케이스 생성.
2. 테스트 실행하여 실패 확인.
3. 기능 구현.
4. 테스트 실행하여 통과 확인.

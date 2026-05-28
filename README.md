# xAPI Unified Analytics Platform (Adapter & Sandbox)

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688?logo=fastapi)
![MongoDB](https://img.shields.io/badge/MongoDB-Production--Grade-47A248?logo=mongodb)
![Standalone](https://img.shields.io/badge/Demo-Offline--Compatible-orange)

대규모 학습 행동 데이터(xAPI)를 실시간으로 정규화, 분석 및 시각화하기 위한 고성능 플랫폼입니다. 7억 건 이상의 운영 데이터를 처리할 수 있는 아키텍처를 기반으로 설계되었습니다.

## 🚀 주요 특징

- **Adaptive Normalizer**: 서로 다른 xAPI 규격을 가진 여러 교육 업체(AIDT 등)의 데이터를 하나의 표준(Canonical Model)으로 실시간 변환.
- **Unified Analytics**: 미디어 시청 패턴, 문제 풀이 효율성, 학습 흐름 진단 등 20종 이상의 전문 분석 API 제공.
- **Hybrid Sandbox**:
  - **Live Mode**: 실제 FastAPI 백엔드 및 MongoDB와 연동되는 운영/개발용 환경.
  - **Standalone Mode**: 서버 없이 브라우저에서 즉시 실행 가능한 고정밀 데모 환경.
- **High Performance**: MongoDB 인덱스 최적화를 통해 수억 건의 로그 중 특정 유저의 학습 이력을 100ms 이내에 분석.

## 🛠 아키텍처

본 프로젝트는 **Canonical Model** 아키텍처를 따릅니다.
1. **Raw Layer**: 업체별 상이한 xAPI JSON 수집.
2. **Adapter Layer**: Mapping Config를 통해 표준 필드로 변환.
3. **Core Layer**: 표준화된 데이터를 기반으로 공통 분석 로직 수행.
4. **API Layer**: 분석 결과를 RESTful JSON으로 서빙.

## 📁 프로젝트 구조

```text
D:/Workspace/xAPI_Vaildator/pythonProject/
├── src/xapi_tools/
│   ├── web_app.py          # FastAPI 메인 서버
│   ├── adapter/            # 정규화 및 매핑 엔진
│   ├── analytics/          # 프로파일별 분석 로직 (Media, Assessment, etc.)
│   └── utils/              # DB 및 공통 유틸리티
├── sandbox/                # 샌드박스 인터페이스 (Live & Static)
│   ├── live_sandbox.html   # [LIVE] 실시간 서버 연동 샌드박스
│   └── static_demo.html    # [STATIC] 완전 독립형 데모 파일
├── tools/                  # API 테스트 도구 (Postman, HTTP)
│   ├── xapi_postman_collection.json
│   └── xapi_api.http
├── archive/                # 개발 중 사용된 임시 스크립트 보관
├── API_SPEC.md            # 상세 API 명세서
└── GEMINI.md              # AI 에이전트 작업 지침
```

## 🚥 시작하기

### 1. 의존성 설치 (uv 권장)
```bash
uv sync
```

### 2. 서버 실행
```bash
uvicorn xapi_tools.web_app:app --app-dir src --host 0.0.0.0 --port 8000 --reload
```

### 3. 접속
- **라이브 샌드박스**: [http://localhost:8000/](http://localhost:8000/)
- **API 문서 (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **오프라인 데모**: `static_demo.html` 파일을 브라우저로 직접 열기

## 📄 상세 문서
- [상세 API 명세서 (API_SPEC.md)](./API_SPEC.md): 모든 엔드포인트와 파라미터 정보.
- [개발 로그](./GEMINI.md): 주요 아키텍처 결정 및 변경 이력.

---
© 2026 xAPI Adapter Team. Built with Performance & Integrity.

# xAPI Unified API Specification

이 문서는 **xAPI Unified Analytics Platform**에서 제공하는 모든 REST API 엔드포인트의 명세와 사용법을 설명합니다. 모든 분석 API는 기본적으로 운영 DB(`lrs`)를 조회하며, 고유한 정규화 엔진을 거쳐 결과를 반환합니다.

---

## 📂 카테고리별 API 목록

### 1. 핵심 활동 분석 (Activities)
| Endpoint | Method | 파라미터 | 설명 |
| :--- | :--- | :--- | :--- |
| `/api/v1/analytics/activities` | `GET` | `user_id` (List), `verb_category` (List) | 특정 유저의 활동 내역을 표준 모델로 정규화하여 일괄 반환합니다. |

### 2. 공통 기초 통계 (Common)
| Endpoint | Method | 파라미터 | 설명 |
| :--- | :--- | :--- | :--- |
| `/api/v1/analytics/common/active-days-count` | `GET` | `user_id` (List) | 유저가 실제로 학습 활동을 수행한 총 날짜 수(출석일) 반환. |
| `/api/v1/analytics/common/verb-distribution` | `GET` | `user_id` (List) | 유저가 발생시킨 전체 행동(Verbs)의 종류별 횟수와 비중 추출. |

### 3. 미디어 분석 프로파일 (Media)
| Endpoint | Method | 파라미터 | 설명 |
| :--- | :--- | :--- | :--- |
| `/api/v1/analytics/media/watched-list` | `GET` | `user_id` | 유저가 시청한 미디어 명칭 및 유형 목록. |
| `/api/v1/analytics/media/watched-count` | `GET` | `user_id`, `verb` (List) | 행동(played 등)별 영상/오디오 시청 횟수 합계. |
| `/api/v1/analytics/media/initialized-info`| `GET` | `user_id` | 미디어 세션 ID, 프레임레이트 등 초기화 정보. |
| `/api/v1/analytics/media/heatmap` | `GET` | `activity_id` | 5초 간격의 구간별 Pause/Seek 집중도 분석. |
| `/api/v1/analytics/media/frustration` | `GET` | `user_id` | 짧은 간격의 반복 행동을 통한 학습자 좌절 지수 진단. |

### 3. 평가 및 학습 성취 분석 (Assessment)
| Endpoint | Method | 파라미터 | 설명 |
| :--- | :--- | :--- | :--- |
| `/api/v1/analytics/assessment/solved-question-count` | `GET` | `user_id` | 완료된 문항 목록 및 총 풀이 수. |
| `/api/v1/analytics/assessment/efficiency` | `GET` | `user_id` | 문항별 점수 대비 소요 시간을 분석하여 학습 효율 도출. |
| `/api/v1/analytics/applied/assessment-history` | `GET` | `user_id` | 학년/과목별 누적 정답률 통계. |
| `/api/v1/analytics/applied/assessment-tag-correct-rate` | `GET` | `user_id`, `grade`, `subject`, `tag` (List) | 특정 개념(태그)들의 문항별 상세 정답률 반환 (태그별 그룹화). |
| `/api/v1/analytics/applied/wrong-answers` | `GET` | `user_id` | 상세 오답 목록 및 문항별 누적 오답 횟수. |
| `/api/v1/analytics/applied/wrong-answers-test` | `GET` | `user_id`, `subject` (List) | 특정 과목들의 오답 문항으로 재구성한 복습 시험지 반환 (과목별 그룹화). |
| `/api/v1/analytics/applied/wrong-answers-chapter-test` | `GET` | `user_id`, `subject`, `grade`, `semester`, `chapter` (List) | 단원별 복습 시험지 반환 (단원별 그룹화). |
| `/api/v1/analytics/applied/wrong-answers-tag` | `GET` | `user_id`, `tag` (List) | 특정 개념(태그)들의 오답 목록 반환 (태그별 그룹화). |
| `/api/v1/analytics/applied/wrong-answers-assessment-type` | `GET` | `user_id`, `assessment_type` (List) | 특정 평가 유형들의 오답 목록 반환 (유형별 그룹화). |

### 4. 세션 및 이동 경로 분석 (Session & Navigation)
| Endpoint | Method | 파라미터 | 설명 |
| :--- | :--- | :--- | :--- |
| `/api/v1/analytics/session/time-list` | `GET` | `user_id` | 일자별 로그인/로그아웃 시간 및 체류 시간 기록. |
| `/api/v1/analytics/navigation/ratio` | `GET` | `user_id` | 각 학습 메뉴(홈, 플레이어, 평가 등)별 체류 비중(%). |
| `/api/v1/analytics/navigation/churn` | `GET` | `user_id` | 페이지 이동 흐름 중 이탈이 발생하는 지점 분석. |

---

## 📝 공통 응답 구조 (Batch Mode)

사용자가 여러 명의 `user_id`를 요청하거나 여러 개의 `verb`를 요청하는 경우, API는 다음과 같은 일괄 처리(Batch) 구조를 반환합니다.

### Request 예시
`GET /api/v1/analytics/activities?user_id=uid1&user_id=uid2&verb_category=played`

### Response 예시
```json
{
  "batch_mode": true,
  "results": [
    {
      "user_id": "11572119-...",
      "count": 12,
      "activities": [...]
    },
    {
      "user_id": "50834687-...",
      "count": 5,
      "activities": [...]
    }
  ]
}
```

---

## 🛠 시스템 진단 API

개발 및 운영 관리를 위한 메타데이터 API들입니다.

- `GET /api/v1/diagnostics/profile`: DB 전체 문서 수 및 유저 그룹별(Real/Tester/Bot) 통계.
- `GET /api/v1/metrics`: 서버 상태, DB 연결 지연 시간, 가동 시간 등.
- `GET /api/databases`: 현재 MongoDB 인스턴스의 데이터베이스 목록.

---
*모든 API 응답은 UTF-8 인코딩된 JSON 포맷을 따릅니다.*

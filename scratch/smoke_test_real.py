import urllib.request
import json
import time

BASE = "http://localhost:8000"
UID = "11572119-e321-4bc2-b57c-4189e5f80936" # Real Student: 김태윤

endpoints = [
    # Diagnostics Route
    (f"{BASE}/api/v1/diagnostics/profile", "diagnostics/profile"),
    # Media Profile
    (f"{BASE}/api/v1/analytics/media/watched-list?user_id={UID}", "media/watched-list"),
    (f"{BASE}/api/v1/analytics/media/watched-count?user_id={UID}&verb=played", "media/watched-count"),
    (f"{BASE}/api/v1/analytics/media/initialized-info?user_id={UID}", "media/initialized-info"),
    (f"{BASE}/api/v1/analytics/media/now-play-time?user_id={UID}", "media/now-play-time"),
    (f"{BASE}/api/v1/analytics/media/play-pause-time-interval?user_id={UID}", "media/play-pause-time-interval"),
    (f"{BASE}/api/v1/analytics/media/seeked-time-interval?user_id={UID}", "media/seeked-time-interval"),
    (f"{BASE}/api/v1/analytics/media/completed-time-interval?user_id={UID}", "media/completed-time-interval"),
    (f"{BASE}/api/v1/analytics/media/terminated-time-interval?user_id={UID}", "media/terminated-time-interval"),
    (f"{BASE}/api/v1/analytics/media/interacted-time-interval?user_id={UID}", "media/interacted-time-interval"),
    # Session Profile
    (f"{BASE}/api/v1/analytics/session/time-list?user_id={UID}", "session/time-list"),
    # Assessment Profile
    (f"{BASE}/api/v1/analytics/assessment/solved-question-count?user_id={UID}", "assessment/solved-question-count"),
    (f"{BASE}/api/v1/analytics/assessment/attempt-question-count?user_id={UID}", "assessment/attempt-question-count"),
    (f"{BASE}/api/v1/analytics/assessment/extensions?user_id={UID}", "assessment/extensions"),
    (f"{BASE}/api/v1/analytics/assessment/interaction?user_id={UID}", "assessment/interaction"),
    # Navigation Profile
    (f"{BASE}/api/v1/analytics/navigation/list?user_id={UID}", "navigation/list"),
    (f"{BASE}/api/v1/analytics/navigation/ratio?user_id={UID}", "navigation/ratio"),
    # Applied
    (f"{BASE}/api/v1/analytics/applied/assessment-history?user_id={UID}", "applied/assessment-history"),
    (f"{BASE}/api/v1/analytics/applied/assessment-grade-history?user_id={UID}&grade=5", "applied/assessment-grade-history"),
    (f"{BASE}/api/v1/analytics/applied/subject-correct-rate?user_id={UID}&grade=5&subject=%EC%88%98%ED%95%99", "applied/subject-correct-rate"),
    (f"{BASE}/api/v1/analytics/applied/wrong-answers?user_id={UID}", "applied/wrong-answers"),
    (f"{BASE}/api/v1/analytics/applied/wrong-answers-test?user_id={UID}&subject=%EC%88%98%ED%95%99", "applied/wrong-answers-test"),
]

print(f"Testing {len(endpoints)} endpoints against {BASE} with Real User UUID (김태윤): {UID}\n")
all_ok = True

for url, label in endpoints:
    t0 = time.time()
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            body = json.loads(resp.read())
            row_count = None
            if isinstance(body, dict):
                # Detect row-oriented dict format {col: {0: val, 1: val, ...}}
                vals = list(body.values())
                if vals and isinstance(vals[0], dict):
                    row_count = len(vals[0])
                else:
                    row_count = len(body)
            print(f"  ✅ {status} {label}  (keys/rows={row_count}) in {time.time() - t0:.3f}s")
    except Exception as ex:
        print(f"  ❌ FAIL {label}  -> {ex} in {time.time() - t0:.3f}s")
        all_ok = False

print("\n" + ("All endpoints OK ✅" if all_ok else "Some endpoints failed ❌"))

"""
Quick smoke test - tests 3 key endpoints that were previously unhandled.
Uses hy11 which has 20 real statements in the DB.
"""
import urllib.request, json

BASE = "http://localhost:8000"
UID = "hy11"

tests = [
    (f"{BASE}/api/v1/analytics/session/time-list?user_id={UID}", "session/time-list"),
    (f"{BASE}/api/v1/analytics/assessment/solved-question-count?user_id={UID}", "assessment/solved-question-count"),
    (f"{BASE}/api/v1/analytics/navigation/ratio?user_id={UID}", "navigation/ratio"),
    (f"{BASE}/api/v1/analytics/media/watched-list?user_id={UID}", "media/watched-list"),
    (f"{BASE}/api/v1/analytics/applied/assessment-grade-history?user_id={UID}&grade=5", "applied/assessment-grade-history"),
    (f"{BASE}/api/v1/analytics/applied/subject-correct-rate?user_id={UID}&grade=5&subject=%EC%88%98%ED%95%99", "applied/subject-correct-rate"),
    (f"{BASE}/api/v1/analytics/media/initialized-info?user_id={UID}", "media/initialized-info"),
    (f"{BASE}/api/v1/analytics/media/now-play-time?user_id={UID}", "media/now-play-time"),
]

print(f"Testing {len(tests)} endpoints with user_id={UID}\n")
for url, label in tests:
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            body = json.loads(resp.read())
            print(f"  ✅ 200  {label}")
            # Show small sample
            if body and isinstance(body, dict):
                keys = list(body.keys())[:3]
                print(f"       keys: {keys}")
    except Exception as ex:
        print(f"  ❌ FAIL {label} -> {ex}")

print("\nDone.")

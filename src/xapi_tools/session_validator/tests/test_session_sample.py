from xapi_tools.session_validator.core.loader import load_rules
from xapi_tools.session_validator.core.session_validate import validate_one

def test_sample_ok():
    rules = load_rules()
    doc = {
      "statement": {
        "timestamp": "2025-04-01T00:00:01.027236Z",
        "context": {
          "contextActivities": {
            "category": [
              {
                "id": "http://lecognizer.com/xapi/profiles/session",
                "definition": {
                  "name": {"en-US": "Session Profile"},
                  "description": {"en-US": "Session Profile"}
                }
              }
            ]
          },
          "extensions": {
            "http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/session-id": "s-1",
            "http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/user-agent": "UA",
            "http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/client-ip": "1.2.3.4",
            "http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/login-type": "7",
            "http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/grade-sn": 6,
            "http://lecognizer.com/xapi/profiles/session/1.0/extensions/context/school-id-sn": 7419
          }
        }
      }
    }
    month, errs = validate_one(doc, rules)
    assert month == "2025-04"
    assert errs == []

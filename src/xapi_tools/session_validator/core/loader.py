import json
from importlib.resources import files

def load_rules() -> dict:
    text = files("xapi_tools.session_validator.rules").joinpath("session.rules.json").read_text(encoding="utf-8")
    return json.loads(text)

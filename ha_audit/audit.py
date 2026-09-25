import json
import os
from datetime import datetime, timezone

import requests

TOKEN = os.environ["SUPERVISOR_TOKEN"]
SUPERVISOR = "http://supervisor"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}


def get(path):
    response = requests.get(
        f"{SUPERVISOR}{path}",
        headers=HEADERS,
        timeout=20,
    )
    response.raise_for_status()

    payload = response.json()

    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]

    return payload


snapshot = {
    "audit_version": "0.1.0",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "supervisor": get("/supervisor/info"),
    "core": get("/core/info"),
    "os": get("/os/info"),
    "home_assistant": get("/core/api/config"),
}

output_file = "/config/audit_snapshot.json"

with open(output_file, "w", encoding="utf-8") as file:
    json.dump(snapshot, file, indent=2)

print(
    json.dumps(
        {
            "status": "success",
            "core_version": snapshot["core"].get("version"),
            "supervisor_version": snapshot["supervisor"].get("version"),
            "os_version": snapshot["os"].get("version"),
            "output": output_file,
        },
        indent=2,
    )
)

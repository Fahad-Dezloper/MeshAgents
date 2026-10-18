"""Run the relay checker and write Harbor's reward files."""
import json
import subprocess
import sys

task = sys.argv[1]
proc = subprocess.run(
    [sys.executable, "-B", "/opt/relay/check.py", task, "/app/project", "/opt/relay/fixture"],
    capture_output=True, text=True, timeout=150,
)
try:
    res = json.loads(proc.stdout)
except ValueError:
    res = {"s1_pass": False, "s2_pass": False, "failure_count": 99, "checks": {}, "failures": [
        {"type": "checker_error", "detail": (proc.stderr or proc.stdout)[-300:]}]}

checks = res.get("checks", {})
passed = sum(1 for v in checks.values() if v)
total = max(1, len(checks))
reward = {
    "relay_pass": 1.0 if res.get("s2_pass") else 0.0,
    "s1_pass": 1.0 if res.get("s1_pass") else 0.0,
    "checks_failed": float(res.get("failure_count", 0)),
    "checks_passed_fraction": round(passed / total, 4),
}
with open("/logs/verifier/reward.json", "w") as f:
    json.dump(reward, f)
with open("/logs/verifier/check.json", "w") as f:
    json.dump(res, f, indent=2)
print(json.dumps(reward))

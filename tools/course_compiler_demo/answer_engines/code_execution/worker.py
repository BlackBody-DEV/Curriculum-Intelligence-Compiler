"""Minimal isolated worker. Never import this module in the host process."""

import json
import sys

payload = json.loads(sys.stdin.read())
chunks = []
size = 0
limit = payload["output_limit"]

def bounded_print(*values, sep=" ", end="\n"):
    global size
    text = sep.join(str(value) for value in values) + end
    size += len(text.encode("utf-8"))
    if size > limit:
        raise RuntimeError("output limit exceeded")
    chunks.append(text)

safe_builtins = {
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
    "enumerate": enumerate, "float": float, "int": int, "len": len,
    "list": list, "max": max, "min": min, "print": bounded_print,
    "range": range, "reversed": reversed, "round": round, "sorted": sorted,
    "str": str, "sum": sum, "tuple": tuple, "zip": zip,
}
scope = {"__builtins__": safe_builtins}
try:
    exec(compile(payload["source"], "<student>", "exec"), scope, scope)
    result = None
    if payload.get("entrypoint"):
        result = scope[payload["entrypoint"]](*payload.get("args", []))
    response = {"status": "PASS", "stdout": "".join(chunks), "return_value": result}
except BaseException as exc:
    response = {"status": "RUNTIME_ERROR", "reason": type(exc).__name__ + ": " + str(exc)}
encoded = json.dumps(response, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
if len(encoded.encode("utf-8")) > limit + 1024:
    encoded = json.dumps({"status": "LIMIT", "reason": "result exceeds output limit"}, sort_keys=True, separators=(",", ":"))
sys.stdout.write(encoded)

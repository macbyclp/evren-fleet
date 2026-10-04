"""evren-agent.sh çıktısındaki (opencode --format json) token kullanımını toplar.
Kullanım: python agent_tokens.py lane.log"""
import json, sys
tot = {"input": 0, "output": 0, "reasoning": 0, "cache_read": 0}; steps = 0; tools = []
for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
    line = line.strip()
    if not line.startswith("{"):
        continue
    try:
        e = json.loads(line)
    except ValueError:
        continue
    if e.get("type") == "step_finish":
        steps += 1; tk = e["part"].get("tokens", {})
        for k in ("input", "output", "reasoning"):
            tot[k] += tk.get(k, 0)
        tot["cache_read"] += (tk.get("cache") or {}).get("read", 0)
    elif e.get("type") == "tool_use":
        tools.append(e["part"]["tool"])
print("adım", steps, "araçlar", tools, tot)

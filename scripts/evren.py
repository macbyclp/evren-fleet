#!/usr/bin/env python3
"""EVREN LLM client for the evren-fleet skill. Stdlib only.

  evren.py status                       public fleet table (no key needed)
  evren.py models                       models your key may call
  evren.py quota                        credit / quota info
  evren.py terms [--accept]             usage-terms status (accept needs the user's OK)
  evren.py ask -m MODEL "prompt"        one chat completion
  evren.py fleet jobs.jsonl             many jobs in parallel

Key: env EVREN_LLM_API_KEY, else the first line of ~/.evren/api_key.
"""
import argparse, concurrent.futures as cf, json, os, pathlib, sys, time
import urllib.error, urllib.request

API = os.environ.get("EVREN_LLM_BASE", "https://evren-llmapi.ssyz.org.tr")
PUBLIC = "https://api.ssyz.org.tr/api/v1/public/llm-stats"
UA = "evren-fleet/1.0"
DEFAULT_MODEL = "deepseek-v4.1-flash"

for s in (sys.stdout, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def get_key():
    k = os.environ.get("EVREN_LLM_API_KEY", "").strip()
    if not k:
        p = pathlib.Path.home() / ".evren" / "api_key"
        if p.is_file():
            k = p.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    if not k:
        sys.exit("HATA: API anahtarı yok. evren.ssyz.org.tr/api-keys sayfasından 'evren_llm_...' "
                 "anahtarı üretip EVREN_LLM_API_KEY ortam değişkenine veya ~/.evren/api_key dosyasına koy.")
    return k


def call(method, path, body=None, key=None, timeout=600, retries=4, base=API):
    """JSON request with backoff on 429/5xx/network. Returns (status, json_or_text)."""
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if key:
        headers["X-API-Key"] = key
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    for attempt in range(retries + 1):
        req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read().decode("utf-8", "replace")
                return r.status, (json.loads(raw) if raw else {})
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            try:
                out = json.loads(raw)
            except Exception:
                out = raw
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                wait = float(e.headers.get("Retry-After") or 0) or min(60, 3 * 2 ** attempt)
                time.sleep(wait)
                continue
            return e.code, out
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt < retries:
                time.sleep(min(60, 3 * 2 ** attempt))
                continue
            return 0, f"ağ hatası: {e}"
    return 0, "bilinmeyen hata"


def err_text(out):
    if isinstance(out, dict):
        e = out.get("error")
        if isinstance(e, dict):
            return f"{e.get('code', '')}: {e.get('message', e)}"
        return json.dumps(out, ensure_ascii=False)[:500]
    return str(out)[:500]


def build_messages(prompt, system=None, files=()):
    parts = []
    for f in files:
        p = pathlib.Path(f)
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception as e:
            sys.exit(f"HATA: dosya okunamadı {f}: {e}")
        parts.append(f"<file path=\"{p.as_posix()}\">\n{txt}\n</file>")
    parts.append(prompt)
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": "\n\n".join(parts)})
    return msgs


def chat(job, key):
    """Run one job dict. Returns result dict with content/reasoning/usage/error."""
    body = {
        "model": job.get("model") or DEFAULT_MODEL,
        "messages": job.get("messages") or build_messages(
            job["prompt"], job.get("system"), job.get("files", [])),
        "max_tokens": int(job.get("max_tokens") or 8192),
        "stream": False,
    }
    if job.get("temperature") is not None:
        body["temperature"] = job["temperature"]
    if job.get("effort"):
        body["reasoning_effort"] = job["effort"]
    if job.get("json"):
        body["response_format"] = {"type": "json_object"}
    t0 = time.time()
    status, out = call("POST", "/v1/chat/completions", body, key)
    res = {"id": job.get("id"), "model": body["model"], "status": status,
           "seconds": round(time.time() - t0, 1)}
    if status != 200 or not isinstance(out, dict) or not out.get("choices"):
        res["error"] = err_text(out)
        return res
    ch = out["choices"][0]
    msg = ch.get("message") or {}
    res["content"] = msg.get("content") or ""
    res["reasoning"] = msg.get("reasoning") or msg.get("reasoning_content") or ""
    res["finish_reason"] = ch.get("finish_reason")
    res["usage"] = out.get("usage")
    if not res["content"].strip():
        res["error"] = ("boş yanıt" + (" — düşünme aşaması max_tokens bütçesini tüketti, "
                        "max_tokens'ı artır veya --effort low kullan"
                        if ch.get("finish_reason") == "length" else ""))
    return res


# ---------------------------------------------------------------- commands
def cmd_status(a):
    st, d = call("GET", "", None, None, base=PUBLIC)
    if st != 200:
        sys.exit(f"HATA {st}: {err_text(d)}")
    d = d.get("data", d)
    print(f"çevrimiçi {d['online_models']}/{d['total_models']} · sağlık {d['health']} · "
          f"bekleme {d['wait']} · ~{d.get('tokens_per_second') or '?'} tok/s")
    print(f"{'model':<24}{'görev':<14}{'bağlam':>9}{'çıktı':>7}  {'yük':<7}yetenekler")
    for m in sorted(d["models"], key=lambda m: (m["task"] != "chat", m["api_name"])):
        caps = ",".join(k for k, v in m["capabilities"].items() if v)
        flag = "" if m["is_online"] else "  [ÇEVRİMDIŞI]"
        print(f"{m['api_name']:<24}{m['task']:<14}{m['context_length']:>9}"
              f"{m['max_output_tokens'] or '-':>7}  {m['load']:<7}{caps}{flag}")


def cmd_models(a):
    st, d = call("GET", "/v1/models", None, get_key())
    if st != 200:
        sys.exit(f"HATA {st}: {err_text(d)}")
    for m in d.get("data", []):
        print(m.get("id") or m)


def cmd_quota(a):
    st, d = call("GET", "/v1/quota", None, get_key())
    print(json.dumps(d, ensure_ascii=False, indent=2) if st == 200 else f"HATA {st}: {err_text(d)}")


def cmd_terms(a):
    key = get_key()
    st, d = call("GET", "/v1/terms/status", None, key)
    print(json.dumps(d, ensure_ascii=False, indent=2) if st == 200 else f"HATA {st}: {err_text(d)}")
    if not a.accept:
        return
    ver = d.get("current_version")
    st, d = call("POST", "/v1/terms/accept", {"version": ver}, key)
    print(f"kabul: {st} {json.dumps(d, ensure_ascii=False)}")


def read_prompt(a):
    if a.prompt:
        return a.prompt
    if a.prompt_file:
        return pathlib.Path(a.prompt_file).read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    sys.exit("HATA: prompt yok (argüman, --prompt-file veya stdin ver)")


def cmd_ask(a):
    job = {"model": a.model, "prompt": read_prompt(a), "system": a.system,
           "files": a.file, "max_tokens": a.max_tokens, "effort": a.effort,
           "temperature": a.temperature, "json": a.json}
    r = chat(job, get_key())
    if a.show_reasoning and r.get("reasoning"):
        print("--- düşünme ---\n" + r["reasoning"] + "\n--- yanıt ---", file=sys.stderr)
    if r.get("error") and not r.get("content", "").strip():
        sys.exit(f"HATA [{r['model']}] {r['status']}: {r['error']}")
    if a.out:
        pathlib.Path(a.out).write_text(r["content"], encoding="utf-8")
        print(f"yazıldı: {a.out}", file=sys.stderr)
    else:
        print(r["content"])
    u = r.get("usage") or {}
    print(f"[{r['model']} · {r['seconds']}s · tokens {u.get('prompt_tokens', '?')}"
          f"+{u.get('completion_tokens', '?')} · {r.get('finish_reason')}]", file=sys.stderr)


def cmd_fleet(a):
    key = get_key()
    jobs = []
    for i, line in enumerate(pathlib.Path(a.jobs).read_text(encoding="utf-8").splitlines(), 1):
        if line.strip() and not line.lstrip().startswith("#"):
            j = json.loads(line)
            j.setdefault("id", f"job{i:03d}")
            j.setdefault("model", a.model)
            jobs.append(j)
    outdir = pathlib.Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    def run(idx_job):
        idx, j = idx_job
        time.sleep(idx * a.stagger)
        r = chat(j, key)
        (outdir / f"{j['id']}.md").write_text(r.get("content", ""), encoding="utf-8")
        if r.get("reasoning"):
            (outdir / f"{j['id']}.reasoning.md").write_text(r["reasoning"], encoding="utf-8")
        ok = "ok " if not r.get("error") else "ERR"
        print(f"[{ok}] {j['id']} {r['model']} {r['seconds']}s"
              + (f" — {r['error']}" if r.get("error") else ""), flush=True)
        return {k: v for k, v in r.items() if k not in ("content", "reasoning")}

    with cf.ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        results = list(ex.map(run, enumerate(jobs)))
    with open(outdir / "results.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    bad = sum(1 for r in results if r.get("error"))
    print(f"\n{len(results) - bad}/{len(results)} başarılı → {outdir}")
    sys.exit(1 if bad else 0)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("status").set_defaults(fn=cmd_status)
    sp.add_parser("models").set_defaults(fn=cmd_models)
    sp.add_parser("quota").set_defaults(fn=cmd_quota)
    t = sp.add_parser("terms"); t.add_argument("--accept", action="store_true"); t.set_defaults(fn=cmd_terms)

    q = sp.add_parser("ask")
    q.add_argument("prompt", nargs="?")
    q.add_argument("-m", "--model", default=DEFAULT_MODEL)
    q.add_argument("-s", "--system")
    q.add_argument("-f", "--file", action="append", default=[], help="dosyayı prompt'a göm (tekrarlanabilir)")
    q.add_argument("--prompt-file")
    q.add_argument("--effort", choices=["low", "medium", "high"])
    q.add_argument("--max-tokens", type=int, default=8192)
    q.add_argument("--temperature", type=float)
    q.add_argument("--json", action="store_true")
    q.add_argument("--show-reasoning", action="store_true")
    q.add_argument("-o", "--out")
    q.set_defaults(fn=cmd_ask)

    f = sp.add_parser("fleet")
    f.add_argument("jobs", help='JSONL: {"id","model","prompt","system","files":[],"max_tokens","effort"}')
    f.add_argument("-m", "--model", default=DEFAULT_MODEL, help="işte model yoksa varsayılan")
    f.add_argument("-c", "--concurrency", type=int, default=8)
    f.add_argument("--stagger", type=float, default=1.0, help="iş başlatmaları arası sn")
    f.add_argument("-o", "--outdir", default="evren-out")
    f.set_defaults(fn=cmd_fleet)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

import json, re, sys, time, concurrent.futures as cf, statistics, subprocess, os, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import evren

KEY = evren.get_key()
OUT = pathlib.Path(__file__).parent / "bench_results.json"  # results.json bu çıktıdan türetildi (kota alanları çıkarılarak)
MODELS = ["deepseek-v4.1-flash", "deepseek-v4-flash", "glm-5.3", "mimo-v2.6-pro", "qwen3.8-flash-next", "gemma-4-31b"]

def code_of(txt):
    m = re.findall(r"```(?:python)?\n(.*?)```", txt, re.S)
    return m[0] if m else txt

def run_tests(code, tests):
    try:
        g = {}
        exec(code, g)
        exec(tests, g)
        return True
    except Exception:
        return False

NEEDLE = "KIRMIZI-4417"
filler = ("Bu paragraf dolgu metnidir ve önemli bir bilgi içermez. " * 12 + "\n") * 40
hay = filler[: len(filler) // 2] + f"\nGizli proje kodu: {NEEDLE}\n" + filler[len(filler) // 2:]

TASKS = {
 "mantik": dict(
   prompt="Bir markette 17 elma 23 TL'den alınıyor ve ayrıca 89 TL poşet ücreti var. Toplam kaç TL? Yalnızca sayıyı yaz.",
   check=lambda t: re.sub(r"[^\d]", "", t.strip().splitlines()[-1] if t.strip() else "") == "480" or "480" in t[-40:]),
 "kod_yaz": dict(
   prompt="Python'da `uniq_sorted(xs)` fonksiyonunu yaz: listeyi tekrarsız ve artan sıralı döndürsün. Yalnızca tek bir python kod bloğu ver.",
   check=lambda t: run_tests(code_of(t), "assert uniq_sorted([3,1,3,2,1])==[1,2,3]\nassert uniq_sorted([])==[]\nassert uniq_sorted([5])==[5]")),
 "hata_duzelt": dict(
   prompt="Aşağıdaki fonksiyon hatalı: n=0 için 0, n=1 için 1 dönmeli ama yanlış sonuç veriyor. Düzeltilmiş fonksiyonun tamamını tek bir python kod bloğu olarak ver.\n\n```python\ndef fib(n):\n    a, b = 1, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n```",
   check=lambda t: run_tests(code_of(t), "assert [fib(i) for i in range(8)]==[0,1,1,2,3,5,8,13]")),
 "json_cikar": dict(
   prompt='Metinden alanları çıkar ve YALNIZCA JSON nesnesi döndür: {"ad":str,"yas":int,"sehir":str}.\n\nMetin: "Ayşe Demir geçen hafta 34 yaşına girdi ve Eskişehir\'de yaşıyor."',
   json=True,
   check=lambda t: (lambda d: d.get("ad") == "Ayşe Demir" and d.get("yas") == 34 and d.get("sehir") == "Eskişehir")(json.loads(re.search(r"\{.*\}", t, re.S).group(0)))),
 "uzun_baglam": dict(
   prompt=hay + "\n\nYukarıdaki metinde geçen 'Gizli proje kodu' nedir? Yalnızca kodu yaz.",
   check=lambda t: NEEDLE in t),
}

def one(model, task, effort=None, rep=0):
    spec = TASKS[task]
    job = {"model": model, "prompt": spec["prompt"], "max_tokens": 6000, "effort": effort, "json": spec.get("json", False)}
    r = evren.chat(job, KEY)
    u = r.get("usage") or {}
    ok = False
    if not r.get("error"):
        try: ok = bool(spec["check"](r["content"]))
        except Exception: ok = False
    det = u.get("completion_tokens_details") or {}
    return dict(model=model, task=task, effort=effort, rep=rep, seconds=r["seconds"], ok=ok, err=r.get("error"),
                prompt_tokens=u.get("prompt_tokens"), completion_tokens=u.get("completion_tokens"),
                reasoning_tokens=det.get("reasoning_tokens"), cached=(u.get("prompt_tokens_details") or {}).get("cached_tokens"),
                reasoning_chars=len(r.get("reasoning") or ""), content_chars=len(r.get("content") or ""))

def model_matrix(model):
    rows = []
    for task in TASKS:
        for rep in range(2):
            rows.append(one(model, task, None, rep))
    return rows

def main():
    res = {"matrix": [], "effort": [], "parallel": {}, "quota_before": None, "quota_after": None}
    res["quota_before"] = evren.call("GET", "/v1/quota", None, KEY)[1]
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=len(MODELS)) as ex:
        for rows in ex.map(model_matrix, MODELS):
            res["matrix"] += rows
    res["matrix_wall"] = round(time.time() - t0, 1)
    print("matrix done", res["matrix_wall"], flush=True)
    # effort test (sequential, reps=3)
    for effort in ("low", None, "high"):
        for task in ("mantik", "hata_duzelt"):
            for rep in range(3):
                res["effort"].append(one("deepseek-v4.1-flash", task, effort, rep))
    print("effort done", flush=True)
    # parallel scaling: 12 short jobs
    jobs = [{"model": "deepseek-v4.1-flash", "prompt": f"Tek cümleyle: {x} nedir?", "max_tokens": 1500}
            for x in ["HTTP 404", "DNS", "TCP", "SQL JOIN", "REST", "JSON", "Git rebase", "Docker", "CI/CD", "OAuth", "CORS", "TLS"]]
    t = time.time(); [evren.chat(j, KEY) for j in jobs]; seq = time.time() - t
    t = time.time()
    with cf.ThreadPoolExecutor(max_workers=12) as ex: list(ex.map(lambda j: evren.chat(j, KEY), jobs))
    par = time.time() - t
    res["parallel"] = {"jobs": len(jobs), "sequential_s": round(seq, 1), "parallel_s": round(par, 1)}
    print("parallel", res["parallel"], flush=True)
    res["quota_after"] = evren.call("GET", "/v1/quota", None, KEY)[1]
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", OUT)

if __name__ == "__main__":
    main()

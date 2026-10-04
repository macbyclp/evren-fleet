"""results.json -> SVG grafikler (GitHub açık/koyu temada okunur: nötr gri metin, orta tonlu renkler)."""
import json, pathlib, statistics as st, collections
H = pathlib.Path(__file__).parent
D = json.load(open(H / "results.json", encoding="utf-8"))
TXT, GRID = "#8b949e", "#8b949e33"
COL = {"deepseek-v4.1-flash": "#2a78d6", "deepseek-v4-flash": "#eb6834", "glm-5.3": "#1baf7a",
       "mimo-v2.6-pro": "#eda100", "qwen3.8-flash-next": "#e87ba4", "gemma-4-31b": "#4a9a4a"}

def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{title}" '
            f'font-family="system-ui,Segoe UI,sans-serif" font-size="12"><title>{title}</title>{body}</svg>')

def t(x, y, s, anchor="start", size=12, fill=TXT, weight="400"):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" fill="{fill}" font-weight="{weight}">{s}</text>'

def hbars(rows, title, unit, fname, label_w=230, fmt="{:.1f}"):
    """rows: [(label, value, color, extra)]"""
    W, bh, gap, top = 760, 20, 12, 40
    mx = max(v for _, v, _, _ in rows); plot = W - label_w - 230
    body = t(8, 20, title, size=14, weight="500")
    for i, (lab, v, c, ex) in enumerate(rows):
        y = top + i * (bh + gap); bw = max(2, v / mx * plot)
        body += t(label_w - 8, y + 14, lab, "end") + f'<rect x="{label_w}" y="{y}" width="{bw:.1f}" height="{bh}" rx="4" fill="{c}"/>'
        body += t(label_w + bw + 6, y + 14, fmt.format(v) + unit + (f"  {ex}" if ex else ""))
    H_ = top + len(rows) * (bh + gap)
    (H / fname).write_text(svg(W, H_, body, title), encoding="utf-8")

# 1) medyan süre
M = collections.defaultdict(list)
for r in D["matrix"]: M[r["model"]].append(r)
rows = sorted(((m, st.median(r["seconds"] for r in rs), COL[m], f'({sum(r["ok"] for r in rs)}/{len(rs)} doğru)') for m, rs in M.items()), key=lambda x: x[1])
hbars(rows, "Medyan yanıt süresi (sn, düşük iyi)", " sn", "latency.svg")

# 2) çağrı başı çıktı tokenı: düşünme vs görünen (uzun bağlam hariç)
rows2 = []
for m, rs in M.items():
    s = [r for r in rs if r["task"] != "uzun_baglam"]
    c = st.mean(r["completion_tokens"] for r in s); rz = st.mean((r["reasoning_tokens"] or 0) for r in s)
    rows2.append((m, rz, c - rz))
rows2.sort(key=lambda x: x[1] + x[2])
W, bh, gap, top, lw = 760, 20, 12, 60, 230
mx = max(a + b for _, a, b in rows2); plot = W - lw - 120
body = t(8, 20, "Çağrı başına çıktı tokenı (uzun bağlam görevi hariç)", size=14, weight="500")
body += f'<rect x="{lw}" y="30" width="10" height="10" rx="2" fill="#2a78d6"/>' + t(lw + 16, 39, "Düşünme") + f'<rect x="{lw+90}" y="30" width="10" height="10" rx="2" fill="#eb6834"/>' + t(lw + 106, 39, "Görünen yanıt")
for i, (m, a, b) in enumerate(rows2):
    y = top + i * (bh + gap); aw = a / mx * plot; bw = b / mx * plot
    body += t(lw - 8, y + 14, m, "end") + f'<rect x="{lw}" y="{y}" width="{aw:.1f}" height="{bh}" rx="4" fill="#2a78d6"/>'
    body += f'<rect x="{lw+aw+2:.1f}" y="{y}" width="{bw:.1f}" height="{bh}" rx="4" fill="#eb6834"/>' + t(lw + aw + bw + 8, y + 14, f"{a+b:.0f}")
(H / "tokens.svg").write_text(svg(W, top + len(rows2) * (bh + gap), body, "Çağrı başına çıktı tokenı"), encoding="utf-8")

# 3) düşünme çabası
E = collections.defaultdict(list)
for r in D["effort"]: E[(r["task"], r["effort"] or "varsayılan")].append(r)
rows3 = []
for task, lab in (("mantik", "mantık"), ("hata_duzelt", "hata düzeltme")):
    for eff, c in (("low", "#2a78d6"), ("varsayılan", "#eb6834"), ("high", "#1baf7a")):
        rs = E[(task, eff)]; rows3.append((f"{lab} · {eff}", st.mean(x["completion_tokens"] for x in rs), c, f'({sum(x["ok"] for x in rs)}/{len(rs)} doğru)'))
hbars(rows3, "Düşünme çabası etkisi: ortalama çıktı tokenı (deepseek-v4.1-flash)", " tok", "effort.svg", fmt="{:.0f}")

# 4) doğrudan vs ajan
a = D["agent_vs_direct"]; ag = a["agent_lane"]; dr = a["direct"]
rows4 = [("doğrudan ask", dr["prompt"] + dr["completion"], "#2a78d6", ""),
         ("ajan lane'i · yeni giriş+çıktı", ag["input"] + ag["output"], "#2a78d6", f'({ag["steps"]} adım)'),
         ("ajan lane'i · önbellekten okunan", ag["cache_read"], "#7aa7e0", "")]
hbars(rows4, "Aynı hata düzeltme işi: token", " tok", "agent_vs_direct.svg", fmt="{:,.0f}")
print("svg üretildi")

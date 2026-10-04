---
name: evren-fleet
description: EVREN platformunun (evren.ssyz.org.tr) OpenAI-uyumlu LLM API'si üzerinden DeepSeek, GLM, Qwen, MiMo, Gemma gibi açık modelleri çağırıp Claude'un yardımcı/ikinci görüş/paralel işçi olarak kullanmasını sağlar — codex-fleet'in EVREN karşılığı. Her zaman ÇALIŞTIRIR (anlatmaz). Triggers on: "evren", "evren fleet", "deepseek ile", "glm ile", "qwen ile", "mimo ile", "kimi ile", "ikinci görüş al", "başka bir modele sor", "açık modellerle paralel çalıştır", "ssyz api", "evren_llm".
---

# Evren Fleet — EVREN LLM API ile çoklu model çalıştırıcı

EVREN, Savunma Sanayii Başkanlığı'nın yerli H200 kümesinde açık ağırlıklı modelleri **OpenAI uyumlu tek API** ile sunar. Bu skill o API'yi Claude Code'dan sürmek içindir: tek soru, ikinci görüş, ya da N işi paralel "fleet" olarak.

Bu bir **eylem skill'idir**: çağrıldığında `scripts/evren.py`'yi Bash ile gerçekten çalıştır, kullanıcıya "şunu çalıştır" deme. Uzun işleri `run_in_background: true` ile başlat.

## API gerçekleri (2026-10-04'te doğrulandı)

| | |
|---|---|
| Base URL | `https://evren-llmapi.ssyz.org.tr` |
| Kimlik | `X-API-Key: evren_llm_...` (Bearer de tanınıyor) |
| Anahtar üretimi | evren.ssyz.org.tr → e-Devlet girişi → **API Anahtarları** (`/api-keys`) |
| Çıkarım | `POST /v1/chat/completions` (OpenAI formatı; `stream`, `tools`, `response_format`, `reasoning_effort` modele göre) |
| Diğer | `GET /v1/models`, `GET /v1/quota`, `/v1/embeddings`, `/v1/rerank`, `/v1/audio/transcriptions`, `/v1/ocr` |
| Anthropic `/v1/messages` | **YOK** (404) — Claude Code'un kendisini bu API'ye yönlendiremezsin; modeller *işçi* olarak çağrılır |
| Herkese açık model tablosu | `https://api.ssyz.org.tr/api/v1/public/llm-stats` (anahtarsız; `evren.py status` bunu okur) |

İlk kullanımdan önce hesap **kullanım şartlarını kabul etmiş olmalı** (`GET /v1/terms/status` → `/v1/terms/text` → `POST /v1/terms/accept {"version": current_version}`). Kabul kullanıcı adına yapılan bir sözleşmedir: metni kullanıcıya göster, **açık onayını al**, ancak sonra `evren.py terms --accept` çalıştır.

## Kurulum (bir kez)

1. Kullanıcıdan anahtarı kendisinin üretmesini iste. Anahtarı sohbete yapıştırtma; şu ikisinden birine koysun:
   - ortam değişkeni `EVREN_LLM_API_KEY`
   - `~/.evren/api_key` dosyası (tek satır)
2. `python ~/.claude/skills/evren-fleet/scripts/evren.py models` ile doğrula.

Anahtarı asla komut satırına, loga, brief'e veya commit'e yazma.

## Komutlar

`E="python $HOME/.claude/skills/evren-fleet/scripts/evren.py"`

```bash
$E status                      # canlı model tablosu: bağlam, yük, yetenekler (anahtar gerekmez)
$E models                      # bu anahtarın çağırabildiği modeller
$E quota                       # kredi/kota
$E terms                       # şart durumu (--accept yalnız kullanıcı onayıyla)

# tek soru
$E ask -m deepseek-v4.1-flash "Bu fonksiyondaki yarış koşullarını bul" -f src/foo.ts
$E ask -m glm-5.3 --effort high -o out.md --prompt-file brief.md

# fleet: JSONL, satır başına bir iş
$E fleet jobs.jsonl -c 8 --stagger 1 -o evren-out
```

`jobs.jsonl` satırı: `{"id":"gozden-gecir-auth","model":"glm-5.3","system":"...","prompt":"...","files":["src/auth.ts"],"max_tokens":8192,"effort":"medium"}`. Çıktı: `evren-out/<id>.md` (yanıt), `<id>.reasoning.md` (varsa düşünme), `results.jsonl` (durum/süre/token; yanıt metni yok).

## Model seçimi (anlık tabloyu `status` ile doğrula — liste değişir)

| Model | Bağlam | Ne için |
|---|---|---|
| `deepseek-v4.1-flash` | 1M | **varsayılan** — genel kodlama/akıl yürütme, görsel girdi, ucuz ve hızlı |
| `deepseek-v4-flash` | 1M | v4.1 sorun çıkarırsa yedek |
| `glm-5.3` | 512K | ikinci görüş; kod ve ajan işleri |
| `mimo-v2.6-pro` | 1M | uzun bağlam, görsel+video girdi (yük "orta") |
| `qwen3.8-flash-next` | 256K | hızlı genel iş, görsel girdi |
| `gemma-4-31b` | 256K | hafif okuma/özetleme |
| `qwen3-vl-30b` | 256K | görsel anlama (araç çağırma + görsel girdi) |

`auto` (32K bağlam, platform yönlendirir) hesapta çağrılabiliyor ama bağlamı küçük ve hangi modele gittiği belirsiz; ciddi iş için kullanma.

**Sohbet dışı modeller (örnek hesapta, 2026-10-04 listesi):** endpoint'ler platformun Test Alanı kodundan alındı, `evren.py` henüz bunlar için alt komut sunmuyor — gerekirse `curl`/Python ile çağır, ilk kullanımda yanıt biçimini doğrula.

| Model | Görev | Endpoint |
|---|---|---|
| `qwen3-embedding-8b` | embedding (40K bağlam) | `POST /v1/embeddings` `{model, input}` |
| `qwen3-reranker-8b` | yeniden sıralama (4K) | `POST /v1/rerank` `{model, query, documents}` |
| `qwen3-asr-1.7b` | ses → metin | `POST /v1/audio/transcriptions` (multipart: `file`, `model`, `response_format`, `language`) |
| `deepseek-ocr-2`, `dots-ocr` | belge/OCR (sohbet ucunu desteklemez) | `POST /v1/ocr` — istek biçimi doğrulanmadı |

Örnek hesaptaki tam liste (12): dots-ocr, deepseek-v4-flash, qwen3-embedding-8b, qwen3-reranker-8b, deepseek-ocr-2, qwen3-asr-1.7b, gemma-4-31b, qwen3-vl-30b, mimo-v2.6-pro, deepseek-v4.1-flash, qwen3.8-flash-next, glm-5.3.

**Kimi şu an katalogta yok.** Kullanıcı Kimi isterse önce `status`/`models` ile kontrol et; yoksa söyle, en yakın alternatifi öner. Katalogda olmayan bir model kimliği uydurma.

## İşçiler ne yapabilir — ve ne yapamaz

codex-fleet'teki Codex lane'leri dosya sistemine erişip düzenleme yapar. **`evren.py` işçileri yalnızca metin döndürür**: araç yok, dosya sistemi yok, komut çalıştırma yok (düzenleyen ajan gerekiyorsa aşağıdaki opencode bölümüne bak). `evren.py` için sonuçları:

- Bağlamı **sen** verirsin: `-f dosya` (veya `files`) içeriği prompt'a gömer. Bağlam penceresine sığacak kadarını ver; büyük repo için önce ilgili dosyaları seç.
- Çıktıyı **sen** uygularsın (patch'i okuyup Edit ile işlersin). İşçiye "dosyayı düzenle" deme.
- Brief kendi başına yeterli olmalı: hedef, kısıtlar, beklenen çıktı biçimi (örn. "unified diff", "madde madde bulgu + satır no", "yalnız JSON").
- Yazma işi paralel lane'lerde çakışmaz (hiçbiri dosyaya yazmaz); çakışmayı entegrasyon sırasında sen yönetirsin.

## Ajan lane'leri — opencode ile (dosya düzenleyen/komut çalıştıran işçiler)

`evren.py` yalnız metin döndürür. Dosya okuyup yazan, komut çalıştıran **ajan** işçisi gerekiyorsa opencode CLI'ı EVREN'e bağlıdır (kurulu: `opencode-ai` 1.18.34; yapılandırma `~/.config/opencode/opencode.json`, sağlayıcı `evren`, `@ai-sdk/openai-compatible`). **2026-10-04'te gerçek anahtarla doğrulandı:** `glm-5.3` ve `deepseek-v4.1-flash` lane'leri `read`/`edit`/`write`/`bash` araçlarını çağırıp hatalı kodu düzeltti ve testi çalıştırdı; iki lane paralel çalıştı.

Çalışan tarif **`scripts/evren-agent.sh`** içinde kodlandı — elle `opencode run` yazma, bu script'i kullan:

```bash
A="$HOME/.claude/skills/evren-fleet/scripts/evren-agent.sh"
$A <LANE_DIR> glm-5.3 "<KENDİ KENDİNE YETEN BRIEF>" 600 > /tmp/evren-lane-A.log 2>&1   # run_in_background: true
```

Çıktı JSON olay akışıdır; sonda `EXIT=<kod>` vardır. Biten lane'de log'daki `"tool":"..."` olaylarına (hangi araçlar çağrıldı) ve son `"type":"text"` olayına (modelin özeti) bak; ardından dosya değişikliklerini ve kabul kontrolünü **kendin** doğrula.

Script'in gömülü kuralları (neden önemli): stdin `/dev/null` (yoksa opencode sessizce çıkabilir), lane dizinine `cd`, ayrı `XDG_DATA_HOME=~/.evren/opencode-data` (varsa mevcut `~/.local/share/opencode/opencode.db` daha yeni bir opencode sürümüne ait, 1.18.x açamaz — silme/değiştirme), anahtar dosyadan okunur.

**GÜVENLİK — opencode bir sandbox değildir.** Başsız modda `edit` ve `bash` izinleri sormadan çalışır; lane dizini yalnız başlangıç dizinidir, model dizin dışına yazabilir veya istediği komutu çalıştırabilir. Bu yüzden:
- Yazan lane'leri **her zaman izole git worktree'de** (veya atılabilir kopyada) çalıştır; asıl repoda doğrudan çalıştırma.
- Brief'te yasakları açık yaz (DO-NOT-TOUCH, "ağ/silme/git push yok"); modelin uyduğunu varsayma, sonuçta `git status`/`git diff` ile kontrol et.
- Sır içeren dizinde (`.env`, anahtar dosyaları) lane çalıştırma.
- Yıkıcı sonuç ihtimali olan işi (toplu silme, deploy) lane'e verme.

Kullanılabilir modeller: `opencode models evren` (deepseek-v4.1-flash, deepseek-v4-flash, glm-5.3, mimo-v2.6-pro, qwen3.8-flash-next, gemma-4-31b, qwen3-vl-30b).

- Paralel **yazma** lane'leri: codex-fleet'teki worktree-per-lane düzeni (`git worktree add --detach ../evren-lane-A <BASE_SHA>`, lane o dizinde, tek commit, entegrasyonu sen yap). Lane'leri 2–5 sn arayla başlat; arka planda çalıştır.
- Brief codex-fleet'tekiyle aynı sözleşmedir: hedef, OWNS, DO-NOT-TOUCH, kabul kontrolü, rapor biçimi. Lane'in "bitti" demesi kanıt değildir.
- Henüz denenmeyen: büyük repolarda uzun lane'ler, `mimo-v2.6-pro`/`qwen3.8-flash-next`/`gemma-4-31b` ile araç çağırma kalitesi, çok adımlı refactor. İlk gerçek işi küçük ve geri alınabilir seç.

## Ne zaman hangisi

- **Paralel bağımsız işler** (N dosya incelemesi, N modelden ikinci görüş, N aday çözüm) → `fleet`, `-c` 4–10. Compute değil throughput sınırdır ama kredi ve model başı eşzamanlılık limiti (`concurrency_limit` ≈ 100–200) vardır; `429` gelirse script kendi başına geri çekilip yeniden dener.
- **Çapraz doğrulama**: aynı soruyu 2–3 farklı modele (`deepseek`, `glm`, `mimo`) sor, anlaşmazlıkları kullanıcıya göster.
- **Hassas/ağır mühendislik** (mimari, güvenlik, son karar) → kendin yap veya `codex-fleet`; Evren çıktısını ucuz ikinci göz/taslak olarak kullan.

## Düşünme (reasoning) modelleri

`thinking` yeteneği olan modellerde düşünme tokenları `max_tokens` bütçesini paylaşır. Boş yanıt + `finish_reason=length` = bütçe düşünmede bitti → `--max-tokens` artır (çıktı tavanı çoğu modelde 16384) veya `--effort low`. Script bunu "boş yanıt" hatası olarak bildirir. Düşünme metnini ancak istenirse göster (`--show-reasoning`).

## Hata ve doğrulama

- `401` anahtar eksik/geçersiz → kurulum adımı; **403/şart hatası** → kullanım şartları kabul edilmemiş; `429/5xx` → script 4 kez üstel geri çekilmeyle dener, sonra raporlar. Kör yeniden deneme döngüsü kurma.
- **Çıktı bir iddiadır, kanıt değil.** Açık modeller kendinden emin biçimde yanlış API/sürüm bilgisi üretebilir. Kodu çalıştırıp/testle, kritik iddiayı kendin doğrula; uyuşmazlıkta kendi bilginle çapraz kontrol et.
- Her fleet sonunda `results.jsonl`'daki `error` alanlarına bak; başarısız işi yalnız onu yeniden çalıştırarak düzelt.

## Gizlilik ve maliyet

- İstekler EVREN'in yurt içi altyapısına gider, ama yine de **sır, parola, anahtar, kişisel veri gömme**. Bir dosyayı `-f` ile göndermeden önce içinde sır olmadığından emin ol (`.env`, kimlik bilgisi dosyaları asla).
- Krediler kullanıcının hesabından düşer. Çok büyük fleet'ten (≈20+ iş veya 100K+ bağlamlı işler) önce `quota` bak ve kullanıcıya say.
- Yalnız kendi başlattığın fleet'in çıktılarına dokun; `-o` dizinini her fleet için ayrı seç.

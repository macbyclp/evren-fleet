# evren-fleet

[Claude Code](https://claude.com/claude-code) skill'i: [EVREN](https://evren.ssyz.org.tr) platformunun OpenAI uyumlu LLM API'si üzerinden DeepSeek, GLM, Qwen, MiMo, Gemma gibi açık modelleri Claude'a yardımcı işçi olarak bağlar. `codex-fleet` skill'inin EVREN karşılığıdır.

> Resmî olmayan, bağımsız bir istemcidir; EVREN veya Savunma Sanayii Başkanlığı ile bağlantısı yoktur. Kullanmak için kendi EVREN hesabın, API anahtarın ve kullanım şartlarını kabul etmen gerekir.

## İki katman

| Katman | Ne yapar | Araç |
|---|---|---|
| Metin işçileri | Tek soru, ikinci görüş, N işi paralel (fleet) | `scripts/evren.py` (yalnız Python stdlib) |
| Ajan lane'leri | Dosya okuyan/düzenleyen/komut çalıştıran işçi | `scripts/evren-agent.sh` + [opencode](https://opencode.ai) |

## Kurulum

1. EVREN'de e-Devlet ile giriş yapıp **API Anahtarları** sayfasından `evren_llm_...` anahtarı üret; hesabın kullanım şartlarını kabul et.
2. Anahtarı sohbete yapıştırma; ortam değişkenine veya dosyaya koy:
   ```bash
   export EVREN_LLM_API_KEY=evren_llm_...      # veya
   mkdir -p ~/.evren && printf '%s' 'evren_llm_...' > ~/.evren/api_key
   ```
3. Skill'i kopyala: `cp -r . ~/.claude/skills/evren-fleet`
4. Ajan lane'leri için opencode kur (`npm i -g opencode-ai`) ve `opencode.json` içine `evren` sağlayıcısını ekle (örnek `SKILL.md` ve aşağıda).

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "evren": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "EVREN",
      "options": {
        "baseURL": "https://evren-llmapi.ssyz.org.tr/v1",
        "apiKey": "{env:EVREN_LLM_API_KEY}"
      },
      "models": {
        "deepseek-v4.1-flash": { "name": "DeepSeek v4.1 Flash" },
        "glm-5.3": { "name": "GLM 5.3" }
      }
    }
  }
}
```

## Kullanım

```bash
E=scripts/evren.py
python $E status                                  # canlı model tablosu (anahtarsız)
python $E models                                  # hesabının çağırabildiği modeller
python $E ask -m deepseek-v4.1-flash "soru" -f dosya.py
python $E fleet jobs.jsonl -c 8 -o out            # paralel
scripts/evren-agent.sh /yol/lane glm-5.3 "görev" 600   # ajan lane'i
```

## Güvenlik

- `evren.py` yalnız metin döndürür. `evren-agent.sh` opencode'u başsız çalıştırır; **opencode sandbox değildir**, `edit` ve `bash` izin sormadan çalışır. Yazan lane'leri izole git worktree'de çalıştır.
- Anahtarı depoya, loga veya komut satırına yazma. İstekler EVREN'e gider; sır ve kişisel veri gönderme.

Ayrıntılar ve model seçimi: [SKILL.md](SKILL.md).

## Lisans

MIT

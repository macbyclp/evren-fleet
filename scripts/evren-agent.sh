#!/bin/bash
# EVREN ajan lane'i: opencode'u EVREN modeliyle başsız çalıştırır.
# Kullanım: evren-agent.sh <LANE_DIR> <MODEL> "<BRIEF>" [TIMEOUT_SN]
#   evren-agent.sh /c/proj/lane-A glm-5.3 "src/x.ts içindeki hatayı düzelt" 600
# Çıktı: JSON olay akışı (stdout) + sonda EXIT=<kod>. Arka planda ve log'a yönlendirerek çalıştır.
#
# Neden böyle (2026-10-04'te doğrulandı):
#  - stdin /dev/null olmalı; yoksa opencode sessizce bekleyip hiçbir şey yapmadan çıkabiliyor.
#  - Lane dizinine cd edilir (--dir yerine; --dir ile ilk deneme sessiz kaldı).
#  - XDG_DATA_HOME ayrı: mevcut ~/.local/share/opencode/opencode.db daha yeni opencode
#    sürümüne ait ve 1.18.x ile açılmaz; ona dokunma.
#  - Anahtar dosyadan okunur, argümana/loga yazılmaz.
set -u
DIR="${1:?lane dizini}"; MODEL="${2:?model}"; BRIEF="${3:?brief}"; TMO="${4:-600}"
export XDG_DATA_HOME="${EVREN_OPENCODE_DATA:-$HOME/.evren/opencode-data}"
mkdir -p "$XDG_DATA_HOME"
if [ -z "${EVREN_LLM_API_KEY:-}" ]; then
  [ -s "$HOME/.evren/api_key" ] || { echo "HATA: EVREN_LLM_API_KEY veya ~/.evren/api_key yok"; exit 2; }
  EVREN_LLM_API_KEY="$(head -1 "$HOME/.evren/api_key" | tr -d '\r\n')"
fi
export EVREN_LLM_API_KEY
cd "$DIR" || { echo "HATA: dizin yok: $DIR"; exit 2; }
timeout "$TMO" opencode run -m "evren/$MODEL" --format json "$BRIEF" < /dev/null
echo "EXIT=$?"

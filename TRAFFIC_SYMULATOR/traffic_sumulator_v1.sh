#!/usr/bin/env bash
set -euo pipefail

VERSION="v1"
THREAD_TAG="traffic_sumulator_${VERSION}"

HOME_DIR="/home/potrzebuje"
PROJECT_ROOT="/home/potrzebuje/Projects/anonymous_app"
MODULE_DIR="$PROJECT_ROOT/TRAFFIC_SYMULATOR"
RUNTIME_DIR="$MODULE_DIR/runtime"
LOG_DIR="$PROJECT_ROOT/logs"

SCRIPT_PATH="$MODULE_DIR/traffic_sumulator_v1.sh"
STATE_FILE="$MODULE_DIR/traffic_sumulator_v1.state"
PID_FILE="$MODULE_DIR/traffic_sumulator_v1.pid"
LAST_LOG_FILE="$MODULE_DIR/traffic_sumulator_v1.lastlog"

BASE_URL="https://potrzebuje.pl/apps/anonymous"

mkdir -p "$MODULE_DIR" "$RUNTIME_DIR" "$LOG_DIR"

UA_LIST=(
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/144.0.0.0 Safari/537.36"
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/18.0 Safari/605.1.15"
"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0"
"Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 Chrome/145.0.0.0 Mobile Safari/537.36"
"Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1"
)

LANG_LIST=("pl" "en" "de" "fr")
STAT_RANGE_LIST=("today" "daily" "weekly" "monthly" "yearly")

format_hm() {
  local total="${1:-0}"
  [ "$total" -lt 0 ] && total=0
  local h=$(( total / 3600 ))
  local m=$(( (total % 3600) / 60 ))
  printf "%d:%02d" "$h" "$m"
}

hours_to_seconds() {
  local hours="$1"
  awk -v h="$hours" 'BEGIN { if (h <= 0) exit 1; printf "%.0f\n", h * 3600 }'
}

rand_ua() {
  echo "${UA_LIST[$RANDOM % ${#UA_LIST[@]}]}"
}

rand_lang() {
  echo "${LANG_LIST[$RANDOM % ${#LANG_LIST[@]}]}"
}

rand_stats_range() {
  echo "${STAT_RANGE_LIST[$RANDOM % ${#STAT_RANGE_LIST[@]}]}"
}

write_state() {
  local status="$1"
  cat > "$STATE_FILE" <<EOF_STATE
VERSION="$VERSION"
STATUS="$status"
RUN_ID="$RUN_ID"
PID="${PID:-}"
START_EPOCH="$START_EPOCH"
RUN_SECONDS="$RUN_SECONDS"
CZAS_HOURS="$CZAS_HOURS"
LOG_FILE="$LOG_FILE"
RUNTIME_RUN_DIR="$RUNTIME_RUN_DIR"
EOF_STATE
}

load_state() {
  if [ ! -f "$STATE_FILE" ]; then
    echo "STATUS=NO_STATE"
    exit 1
  fi
  # shellcheck disable=SC1090
  source "$STATE_FILE"
}

create_seed_files() {
  SEED_A="$RUNTIME_RUN_DIR/seed_a.txt"
  SEED_B="$RUNTIME_RUN_DIR/seed_b.txt"
  SEED_C="$RUNTIME_RUN_DIR/seed_c.txt"

  echo "Jan Kowalski mieszka w Warszawie i pracuje w firmie ABC." > "$SEED_A"
  echo "Anna Nowak z Krakowa kontakt: anna@example.com tel 123456789." > "$SEED_B"
  echo "Firma XYZ Sp. z o.o. ul. Testowa 1, 00-001 Warszawa NIP 1234567890." > "$SEED_C"

  SEEDS=("$SEED_A" "$SEED_B" "$SEED_C")
}

rand_seed() {
  echo "${SEEDS[$RANDOM % ${#SEEDS[@]}]}"
}

sleep_between_scenarios() {
  local s=$((RANDOM % (MAX_SLEEP - MIN_SLEEP + 1) + MIN_SLEEP))
  sleep "$s"
}

micro_pause() {
  local s=$((RANDOM % 2))
  [ "$s" -gt 0 ] && sleep "$s"
}

http_get_code() {
  local url="$1"
  local ua="$2"
  local lang="$3"
  curl -s -o /dev/null -w "%{http_code}" -A "$ua" -H "Accept-Language: $lang" "$url" || true
}

http_post_encode() {
  local file="$1"
  local out="$2"
  local ua="$3"
  local lang="$4"
  curl -s -o "$out" -w "%{http_code}" -A "$ua" -H "Accept-Language: $lang" -F "file=@$file" "$BASE_URL/encode" || true
}

http_post_decode() {
  local file="$1"
  local ua="$2"
  local lang="$3"
  curl -s -o /dev/null -w "%{http_code}" -A "$ua" -H "Accept-Language: $lang" -F "file=@$file" "$BASE_URL/decode" || true
}

do_visit() {
  local ua="$1"
  local lang="$2"
  local code
  code="$(http_get_code "$BASE_URL/?lang=$lang" "$ua" "$lang")"
  TOTAL_REQUESTS=$((TOTAL_REQUESTS+1))
  if [ "$code" = "200" ]; then
    VISITS_OK=$((VISITS_OK+1))
    return 0
  fi
  FAILED=$((FAILED+1))
  return 1
}

do_statistics() {
  local ua="$1"
  local lang="$2"
  local stats_range="$3"
  local code
  code="$(http_get_code "$BASE_URL/statistics?lang=$lang&range=$stats_range" "$ua" "$lang")"
  TOTAL_REQUESTS=$((TOTAL_REQUESTS+1))
  if [ "$code" = "200" ]; then
    STATISTICS_OK=$((STATISTICS_OK+1))
    return 0
  fi
  FAILED=$((FAILED+1))
  return 1
}

do_encode() {
  local ua="$1"
  local lang="$2"
  local seed="$3"
  local out="$4"
  local code
  ENCODE_ATTEMPTS=$((ENCODE_ATTEMPTS+1))
  code="$(http_post_encode "$seed" "$out" "$ua" "$lang")"
  TOTAL_REQUESTS=$((TOTAL_REQUESTS+1))
  if [ "$code" = "200" ]; then
    ENCODE_OK=$((ENCODE_OK+1))
    ENCODED_FILES+=("$out")
    return 0
  fi
  FAILED=$((FAILED+1))
  rm -f "$out"
  return 1
}

do_decode() {
  local ua="$1"
  local lang="$2"
  local file="$3"
  local code
  DECODE_ATTEMPTS=$((DECODE_ATTEMPTS+1))
  code="$(http_post_decode "$file" "$ua" "$lang")"
  TOTAL_REQUESTS=$((TOTAL_REQUESTS+1))
  if [ "$code" = "200" ]; then
    DECODE_OK=$((DECODE_OK+1))
    return 0
  fi
  FAILED=$((FAILED+1))
  return 1
}

scenario_seq_visit_encode_decode() {
  SEQ_VISIT_ENCODE_DECODE=$((SEQ_VISIT_ENCODE_DECODE+1))
  local ua lang seed out idx
  ua="$(rand_ua)"
  lang="$(rand_lang)"
  do_visit "$ua" "$lang" || true
  micro_pause
  seed="$(rand_seed)"
  out="$RUNTIME_RUN_DIR/encoded_${RANDOM}_$(date +%s%N).txt"
  if do_encode "$ua" "$lang" "$seed" "$out"; then
    micro_pause
    idx=$((RANDOM % ${#ENCODED_FILES[@]}))
    do_decode "$ua" "$lang" "${ENCODED_FILES[$idx]}" || true
  fi
}

scenario_seq_visit_statistics() {
  SEQ_VISIT_STATISTICS=$((SEQ_VISIT_STATISTICS+1))
  local ua lang range1 range2
  ua="$(rand_ua)"
  lang="$(rand_lang)"
  range1="$(rand_stats_range)"
  range2="$(rand_stats_range)"
  do_visit "$ua" "$lang" || true
  micro_pause
  do_statistics "$ua" "$lang" "$range1" || true
  micro_pause
  do_statistics "$ua" "$lang" "$range2" || true
}

scenario_seq_visit_encode() {
  SEQ_VISIT_ENCODE=$((SEQ_VISIT_ENCODE+1))
  local ua lang seed out
  ua="$(rand_ua)"
  lang="$(rand_lang)"
  seed="$(rand_seed)"
  out="$RUNTIME_RUN_DIR/encoded_${RANDOM}_$(date +%s%N).txt"
  do_visit "$ua" "$lang" || true
  micro_pause
  do_encode "$ua" "$lang" "$seed" "$out" || true
}

scenario_single_random() {
  SINGLE_RANDOM=$((SINGLE_RANDOM+1))
  local ua lang seed out idx action range1
  ua="$(rand_ua)"
  lang="$(rand_lang)"
  action=$((RANDOM % 4))
  case "$action" in
    0)
      do_visit "$ua" "$lang" || true
      ;;
    1)
      range1="$(rand_stats_range)"
      do_statistics "$ua" "$lang" "$range1" || true
      ;;
    2)
      seed="$(rand_seed)"
      out="$RUNTIME_RUN_DIR/encoded_${RANDOM}_$(date +%s%N).txt"
      do_encode "$ua" "$lang" "$seed" "$out" || true
      ;;
    3)
      if [ "${#ENCODED_FILES[@]}" -eq 0 ]; then
        seed="$(rand_seed)"
        out="$RUNTIME_RUN_DIR/encoded_${RANDOM}_$(date +%s%N).txt"
        do_encode "$ua" "$lang" "$seed" "$out" || true
      else
        idx=$((RANDOM % ${#ENCODED_FILES[@]}))
        do_decode "$ua" "$lang" "${ENCODED_FILES[$idx]}" || true
      fi
      ;;
  esac
}

worker() {
  RUN_ID="$2"
  CZAS_HOURS="$3"
  RUN_SECONDS="$4"
  START_EPOCH="$5"
  RUNTIME_RUN_DIR="$RUNTIME_DIR/$RUN_ID"
  LOG_FILE="$LOG_DIR/traffic_sumulator_${VERSION}_${RUN_ID}.log"

  mkdir -p "$RUNTIME_RUN_DIR"
  echo "$LOG_FILE" > "$LAST_LOG_FILE"

  TOTAL_SCENARIOS=0
  TOTAL_REQUESTS=0
  VISITS_OK=0
  STATISTICS_OK=0
  ENCODE_ATTEMPTS=0
  ENCODE_OK=0
  DECODE_ATTEMPTS=0
  DECODE_OK=0
  FAILED=0

  SEQ_VISIT_ENCODE_DECODE=0
  SEQ_VISIT_STATISTICS=0
  SEQ_VISIT_ENCODE=0
  SINGLE_RANDOM=0

  MIN_SLEEP=0
  MAX_SLEEP=3

  ENCODED_FILES=()

  create_seed_files

  PID="$$"
  write_state "RUNNING"

  while true; do
    NOW_EPOCH="$(date +%s)"
    ELAPSED=$((NOW_EPOCH - START_EPOCH))
    [ "$ELAPSED" -ge "$RUN_SECONDS" ] && break

    TOTAL_SCENARIOS=$((TOTAL_SCENARIOS+1))
    ROLL=$((RANDOM % 100))

    if [ "$ROLL" -lt 45 ]; then
      scenario_seq_visit_encode_decode
    elif [ "$ROLL" -lt 70 ]; then
      scenario_seq_visit_statistics
    elif [ "$ROLL" -lt 90 ]; then
      scenario_seq_visit_encode
    else
      scenario_single_random
    fi

    sleep_between_scenarios
  done

  END_EPOCH="$(date +%s)"
  END_TS="$(date '+%d/%m/%y %H:%M CET')"
  START_TS_FMT="$(date -d "@$START_EPOCH" '+%d/%m/%y %H:%M CET' 2>/dev/null || date '+%d/%m/%y %H:%M CET')"

  {
    echo "VERSION=$VERSION"
    echo "RUN_ID=$RUN_ID"
    echo "START_TS=$START_TS_FMT"
    echo "END_TS=$END_TS"
    echo "BASE_URL=$BASE_URL"
    echo "CZAS_HOURS=$CZAS_HOURS"
    echo "RUN_SECONDS=$RUN_SECONDS"
    echo "MIN_SLEEP=$MIN_SLEEP"
    echo "MAX_SLEEP=$MAX_SLEEP"
    echo "TOTAL_SCENARIOS=$TOTAL_SCENARIOS"
    echo "TOTAL_REQUESTS=$TOTAL_REQUESTS"
    echo "SEQ_VISIT_ENCODE_DECODE=$SEQ_VISIT_ENCODE_DECODE"
    echo "SEQ_VISIT_STATISTICS=$SEQ_VISIT_STATISTICS"
    echo "SEQ_VISIT_ENCODE=$SEQ_VISIT_ENCODE"
    echo "SINGLE_RANDOM=$SINGLE_RANDOM"
    echo "[SUMMARY]"
    echo "VISITS_OK=$VISITS_OK"
    echo "STATISTICS_OK=$STATISTICS_OK"
    echo "ENCODE_ATTEMPTS=$ENCODE_ATTEMPTS"
    echo "ENCODE_OK=$ENCODE_OK"
    echo "DECODE_ATTEMPTS=$DECODE_ATTEMPTS"
    echo "DECODE_OK=$DECODE_OK"
    echo "FAILED=$FAILED"
    echo "ENCODED_FILES_STORED=${#ENCODED_FILES[@]}"
    echo "NOTE_COUNTRY_SIMULATION=NO"
  } > "$LOG_FILE"

  PID=""
  write_state "FINISHED"
  rm -f "$PID_FILE"
}

start_cmd() {
  if [ -f "$PID_FILE" ]; then
    OLD_PID="$(tr -d '[:space:]' < "$PID_FILE" || true)"
    if [ -n "${OLD_PID:-}" ] && ps -p "$OLD_PID" > /dev/null 2>&1; then
      echo "STATUS=ALREADY_RUNNING"
      echo "PID=$OLD_PID"
      exit 1
    fi
  fi

  read -r -p "CZAS (hours, decimal allowed, np. 0.5): " CZAS_HOURS
  if ! RUN_SECONDS="$(hours_to_seconds "$CZAS_HOURS" 2>/dev/null)"; then
    echo "STATUS=BAD_CZAS"
    exit 1
  fi

  RUN_ID="$(date '+%Y%m%d_%H%M%S')"
  START_EPOCH="$(date +%s)"
  LOG_FILE="$LOG_DIR/traffic_sumulator_${VERSION}_${RUN_ID}.log"
  RUNTIME_RUN_DIR="$RUNTIME_DIR/$RUN_ID"
  PID=""
  mkdir -p "$RUNTIME_RUN_DIR"
  write_state "STARTING"

  nohup bash "$SCRIPT_PATH" worker "$RUN_ID" "$CZAS_HOURS" "$RUN_SECONDS" "$START_EPOCH" >/dev/null 2>&1 &
  PID="$!"
  echo "$PID" > "$PID_FILE"
  write_state "RUNNING"

  sleep 2

  echo "STATUS=STARTED"
  echo "PID=$PID"
  echo "RUN_ID=$RUN_ID"
  echo "CZAS_HOURS=$CZAS_HOURS"
  echo "RUN_SECONDS=$RUN_SECONDS"
  echo "STATUS_COMMAND=bash $SCRIPT_PATH status"
  echo "STOP_COMMAND=bash $SCRIPT_PATH stop"
}

status_cmd() {
  load_state

  NOW_EPOCH="$(date +%s)"
  END_EPOCH=$((START_EPOCH + RUN_SECONDS))
  ELAPSED=$((NOW_EPOCH - START_EPOCH))
  [ "$ELAPSED" -lt 0 ] && ELAPSED=0
  REMAINING=$((END_EPOCH - NOW_EPOCH))
  [ "$REMAINING" -lt 0 ] && REMAINING=0

  if [ "$RUN_SECONDS" -gt 0 ]; then
    PCT="$(awk -v e="$ELAPSED" -v r="$RUN_SECONDS" 'BEGIN { p=(e/r)*100; if (p>100) p=100; printf "%.1f", p }')"
  else
    PCT="0.0"
  fi

  echo "STATUS=$STATUS"
  echo "RUN_ID=$RUN_ID"
  echo "PID=${PID:-NONE}"
  if [ -n "${PID:-}" ] && ps -p "$PID" > /dev/null 2>&1; then
    echo "PROCESS_RUNNING=YES"
  else
    echo "PROCESS_RUNNING=NO"
  fi
  echo "CZAS_HOURS=$CZAS_HOURS"
  echo "ELAPSED_HM=$(format_hm "$ELAPSED")"
  echo "REMAINING_HM=$(format_hm "$REMAINING")"
  echo "PROGRESS_PCT=$PCT"
  echo "LOG_FILE=$LOG_FILE"
}

stop_cmd() {
  if [ ! -f "$PID_FILE" ]; then
    echo "STATUS=NOT_RUNNING"
    exit 0
  fi

  PID="$(tr -d '[:space:]' < "$PID_FILE" || true)"
  if [ -z "${PID:-}" ]; then
    echo "STATUS=PID_EMPTY"
    exit 1
  fi

  if ps -p "$PID" > /dev/null 2>&1; then
    kill "$PID"
    sleep 2
    if ps -p "$PID" > /dev/null 2>&1; then
      kill -9 "$PID" || true
    fi
  fi

  rm -f "$PID_FILE"
  if [ -f "$STATE_FILE" ]; then
    # shellcheck disable=SC1090
    source "$STATE_FILE"
    STATUS="STOPPED"
    PID=""
    write_state "$STATUS"
  fi

  echo "STATUS=STOPPED"
}

case "${1:-}" in
  start)
    start_cmd
    ;;
  worker)
    worker "$@"
    ;;
  status)
    status_cmd
    ;;
  stop)
    stop_cmd
    ;;
  *)
    echo "Usage:"
    echo "  bash $SCRIPT_PATH start"
    echo "  bash $SCRIPT_PATH status"
    echo "  bash $SCRIPT_PATH stop"
    exit 1
    ;;
esac

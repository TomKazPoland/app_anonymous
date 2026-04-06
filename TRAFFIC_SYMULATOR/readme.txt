========================
TRAFFIC SIMULATOR MODULE
========================

[EN]

1. PURPOSE
Synthetic traffic generator for Anonymous app.
Used to populate statistics, test routing, and verify logs without real users.

2. HOW IT WORKS
- Main loop with random and sequential actions
- Actions:
  - GET /
  - GET /statistics
  - POST /encode
  - POST /decode
- Uses randomized User-Agent headers
- Uses generated seed text files

3. WHAT IT SIMULATES
- browser diversity (Chrome, Safari, Firefox, mobile)
- realistic user flows (visit → encode → decode)
- event types: visit, tool_use

4. WHAT IT DOES NOT SIMULATE
- real country diversity (single IP)
- concurrency
- infrastructure failures

5. PARAMETERS
- RUN_SECONDS
- MAX_ACTIONS
- MIN_SLEEP / MAX_SLEEP
- USER AGENTS
- SEED FILES

6. USAGE
Run script manually or in background:
bash traffic_sumulator_v1.sh

7. DEVELOPMENT NOTES
- used for regression testing Statistics
- must be combined with HTML + app.log verification

---

[PL]

1. CEL
Generator sztucznego ruchu dla aplikacji Anonymous.
Służy do zasilania statystyk i testowania bez realnych użytkowników.

2. DZIAŁANIE
- pętla główna
- losowy wybór akcji:
  - GET /
  - GET /statistics
  - POST /encode
  - POST /decode
- losowe User-Agent
- pliki testowe generowane dynamicznie

3. SYMULACJA
- różne przeglądarki
- realistyczne scenariusze użytkownika
- typy zdarzeń: visit, tool_use

4. OGRANICZENIA
- brak różnych krajów (1 IP)
- brak równoległości
- brak testów infrastruktury

5. PARAMETRY
- RUN_SECONDS
- MAX_ACTIONS
- MIN_SLEEP / MAX_SLEEP

6. UŻYCIE
bash traffic_sumulator_v1.sh

7. UWAGI
- używać razem z testami HTML i app.log
- nie wystarcza do testów UI

# Anonymous – uruchomienie na nowym serwerze

Ta instrukcja pozwala uruchomić aplikację Anonymous nawet osobie,
która nie zna wcześniej projektu.

------------------------------------------------------------

WYMAGANIA

Serwer musi mieć zainstalowane:

- git
- python >= 3.8 (najlepiej 3.11)

Sprawdzenie:

python3 --version
git --version

------------------------------------------------------------

1. POBRANIE PROJEKTU

git clone https://github.com/TomKazPoland/app_anonymous.git
cd app_anonymous

------------------------------------------------------------

2. AUTOMATYCZNE PRZYGOTOWANIE ŚRODOWISKA

Uruchom skrypt:

bash tools/setup_and_verify_runtime.sh

Skrypt zrobi automatycznie:

- utworzy virtualenv (.venv)
- zainstaluje biblioteki z requirements.txt
- utworzy katalogi runtime
- sprawdzi czy działa aplikacja
- zapisze log instalacji

------------------------------------------------------------

3. SPRAWDZENIE CZY WSZYSTKO DZIAŁA

Na końcu logu musi pojawić się linia:

FINAL OK

Jeśli tak jest – środowisko jest poprawnie przygotowane.

Log instalacji znajduje się w katalogu:

logs/

------------------------------------------------------------

4. URUCHOMIENIE LOKALNE (TEST)

bash run_local.sh

Aplikacja będzie dostępna pod:

http://127.0.0.1:8001

------------------------------------------------------------

5. URUCHOMIENIE PRODUKCYJNE (Passenger / cPanel)

Konfiguracja serwera musi zawierać:

PassengerAppRoot /home/.../anonymous_app
PassengerPython /home/.../anonymous_app/.venv/bin/python
PassengerStartupFile wsgi.py

Po zmianach wykonaj restart aplikacji:

touch tmp/restart.txt

------------------------------------------------------------

6. DIAGNOSTYKA PROBLEMÓW

Jeżeli aplikacja nie działa:

1. sprawdź log skryptu w katalogu logs/
2. sprawdź czy istnieje plik wsgi.py
3. sprawdź czy Python w .venv działa:

.venv/bin/python --version

4. sprawdź czy aplikacja się importuje:

.venv/bin/python -c "from app.main import create_app; create_app(); print('OK')"

------------------------------------------------------------

To wszystko. W większości przypadków wystarczy wykonać:

git clone ...
cd app_anonymous
bash tools/setup_and_verify_runtime.sh

QUICK START (NAJSZYBSZA INSTALACJA)

Jeżeli nie znasz projektu i chcesz po prostu uruchomić aplikację,
wykonaj tylko te trzy komendy:

git clone https://github.com/TomKazPoland/app_anonymous.git
cd app_anonymous
bash install.sh

Skrypt install.sh automatycznie:

- utworzy środowisko Python (.venv)
- zainstaluje wszystkie biblioteki
- sprawdzi czy aplikacja działa
- zapisze log instalacji

Jeżeli na końcu logu pojawi się:

FINAL OK

to aplikacja jest poprawnie przygotowana do uruchomienia.

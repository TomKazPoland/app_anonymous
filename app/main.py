from __future__ import annotations

import os
from pathlib import Path
import traceback
from flask import Flask, render_template, request, send_file, abort, g, make_response

from .utils import now_timestamp_ms, sanitize_filename, project_root
from .db import init_db, connect, get_db_path, create_job, insert_mapping, load_mapping_dict
from .pii_detector import detect
from .tokenizer import anonymize
from .decoder import extract_job_id_from_text, extract_job_id_from_filename, deanonymize
from .hardening import (
    MAX_UPLOAD_BYTES,
    RATE_LIMIT_MAX_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    InMemoryRateLimiter,
    extract_client_ip,
    log_event,
    setup_app_logger,
    validate_txt_upload,
)



SUPPORTED_LANGS = ("pl", "en", "de", "fr", "es")
DEFAULT_LANG = "pl"

I18N = {
    "pl": {
        "html_lang": "pl",
        "title": "ANONYMOUS – anonimizacja odwracalna (TXT)",
        "h1": "ANONYMOUS (MVP)",
        "about_title": "ANONYMOUS – anonimizacja odwracalna (TXT)",
        "about_p1": "To narzędzie służy do anonimizacji danych wrażliwych w plikach tekstowych (TXT). Wrażliwe informacje (np. dane osobowe, identyfikatory) są zamieniane na specjalne tokeny, które można później przywrócić do oryginalnej formy.",
        "how_title": "Jak używać:",
        "how_1": '1. Wybierz plik TXT i kliknij "KODUJ", aby przeprowadzić anonimizację.',
        "how_2": "2. Pobierz wygenerowany plik i zachowaj jego nazwę bez zmian.",
        "how_3": "3. Plik po anonimizacji możesz edytować (np. zmieniać treść lub kolejność fragmentów), ale nie usuwaj ani nie modyfikuj tokenów w nawiasach { ... }.",
        "how_4": '4. Aby przywrócić dane, użyj "DEKODUJ" i wskaż plik po anonimizacji.',
        "rules_title": "Ważne zasady:",
        "rule_1": "Nazwa pliku po anonimizacji musi pozostać dokładnie taka sama – na jej podstawie system odnajduje dane do przywrócenia.",
        "rule_2": "Tokeny { ... } muszą pozostać w pliku – ich usunięcie lub zmiana uniemożliwi poprawne odtworzenie danych.",
        "rule_3": "Plik może być edytowany przez inne osoby bez dostępu do danych wrażliwych – dane zostaną przywrócone dopiero po dekodowaniu.",
        "warning_title": "Uwaga:",
        "warning_text": "System automatycznie wykrywa dane wrażliwe, ale nie gwarantuje 100% skuteczności. Przed dalszym użyciem pliku zawsze sprawdź wynik anonimizacji, aby upewnić się, że nie zawiera błędów ani niezanonimizowanych danych.",
        "encode_title": "KODUJ (anonimizuj)",
        "encode_button": "KODUJ",
        "encode_result": "Wynik: plik TXT z tokenami + nagłówek",
        "decode_title": "DEKODUJ (przywróć dane)",
        "decode_button": "DEKODUJ",
        "decode_note": "Plik musi zawierać nagłówek",
        "decode_note_2": "(dodawany automatycznie przy KODUJ).",
        "footer_1": "© potrzebuje.pl — All rights reserved.",
        "footer_2": "Vibe Coding using ChatGPT (v5.2)",
        "file_pick": "Wybierz plik",
        "file_empty": "Nie wybrano pliku",
        "lang_label": "Język:",
        "error_400_title": "Nieprawidłowe żądanie",
        "error_400_desc": "Żądanie nie mogło zostać przetworzone. Sprawdź plik lub parametry i spróbuj ponownie.",
        "error_404_title": "Nie znaleziono strony",
        "error_404_desc": "Strona, której szukasz, nie istnieje albo adres jest nieprawidłowy.",
        "error_413_title": "Plik jest za duży",
        "error_413_desc": "Przesłany plik przekracza dozwolony rozmiar.",
        "error_429_title": "Zbyt wiele żądań",
        "error_429_desc": "Wykonano zbyt wiele prób w krótkim czasie. Odczekaj chwilę i spróbuj ponownie.",
        "error_500_title": "Wewnętrzny błąd serwera",
        "error_500_desc": "Wystąpił nieoczekiwany błąd po stronie aplikacji.",
        "error_back": "Wróć do strony głównej",
    },
    "en": {
        "html_lang": "en",
        "title": "ANONYMOUS – reversible anonymization (TXT)",
        "h1": "ANONYMOUS (MVP)",
        "about_title": "ANONYMOUS – reversible anonymization (TXT)",
        "about_p1": "This tool is used to anonymize sensitive data in text files (TXT). Sensitive information (for example personal data or identifiers) is replaced with special tokens that can later be restored to their original form.",
        "how_title": "How to use:",
        "how_1": '1. Select a TXT file and click "ENCODE" to anonymize it.',
        "how_2": "2. Download the generated file and keep its name unchanged.",
        "how_3": "3. You may edit the anonymized file (for example change text or reorder fragments), but do not remove or modify the tokens inside { ... }.",
        "how_4": '4. To restore the data, use "DECODE" and select the anonymized file.',
        "rules_title": "Important rules:",
        "rule_1": "The anonymized file name must remain exactly the same – the system uses it to find the data for restoration.",
        "rule_2": "The { ... } tokens must remain in the file – removing or changing them will prevent correct data restoration.",
        "rule_3": "The file may be edited by other people without access to sensitive data – the data will only be restored during decoding.",
        "warning_title": "Warning:",
        "warning_text": "The system automatically detects sensitive data, but it does not guarantee 100% accuracy. Always review the anonymized file before further use to make sure it does not contain errors or unmasked sensitive data.",
        "encode_title": "ENCODE (anonymize)",
        "encode_button": "ENCODE",
        "encode_result": "Result: TXT file with tokens + header",
        "decode_title": "DECODE (restore data)",
        "decode_button": "DECODE",
        "decode_note": "The file must contain the header",
        "decode_note_2": "(added automatically during ENCODE).",
        "footer_1": "© potrzebuje.pl — All rights reserved.",
        "footer_2": "Vibe Coding using ChatGPT (v5.2)",
        "file_pick": "Choose file",
        "file_empty": "No file selected",
        "lang_label": "Language:",
        "error_400_title": "Bad request",
        "error_400_desc": "The request could not be processed. Check the file or parameters and try again.",
        "error_404_title": "Page not found",
        "error_404_desc": "The page you are looking for does not exist or the address is invalid.",
        "error_413_title": "File too large",
        "error_413_desc": "The uploaded file exceeds the allowed size limit.",
        "error_429_title": "Too many requests",
        "error_429_desc": "Too many attempts were made in a short time. Please wait a moment and try again.",
        "error_500_title": "Internal server error",
        "error_500_desc": "An unexpected application-side error has occurred.",
        "error_back": "Back to home page",
    },
    "de": {
        "html_lang": "de",
        "title": "ANONYMOUS – reversible Anonymisierung (TXT)",
        "h1": "ANONYMOUS (MVP)",
        "about_title": "ANONYMOUS – reversible Anonymisierung (TXT)",
        "about_p1": "Dieses Werkzeug dient zur Anonymisierung sensibler Daten in Textdateien (TXT). Sensible Informationen (z. B. personenbezogene Daten oder Kennungen) werden durch spezielle Tokens ersetzt, die später wieder in ihre ursprüngliche Form zurückgeführt werden können.",
        "how_title": "Verwendung:",
        "how_1": '1. Wähle eine TXT-Datei aus und klicke auf "ENCODE", um sie zu anonymisieren.',
        "how_2": "2. Lade die erzeugte Datei herunter und ändere ihren Namen nicht.",
        "how_3": "3. Du kannst die anonymisierte Datei bearbeiten (z. B. Text ändern oder Abschnitte verschieben), aber entferne oder ändere die Tokens in { ... } nicht.",
        "how_4": '4. Um die Daten wiederherzustellen, verwende "DECODE" und wähle die anonymisierte Datei aus.',
        "rules_title": "Wichtige Regeln:",
        "rule_1": "Der Dateiname nach der Anonymisierung muss exakt gleich bleiben – anhand dieses Namens findet das System die Daten zur Wiederherstellung.",
        "rule_2": "Die Tokens { ... } müssen in der Datei erhalten bleiben – ihre Entfernung oder Änderung verhindert eine korrekte Wiederherstellung.",
        "rule_3": "Die Datei kann von anderen Personen ohne Zugriff auf sensible Daten bearbeitet werden – die Daten werden erst beim Dekodieren wiederhergestellt.",
        "warning_title": "Hinweis:",
        "warning_text": "Das System erkennt sensible Daten automatisch, garantiert jedoch keine 100%ige Genauigkeit. Prüfe die anonymisierte Datei vor der weiteren Verwendung immer, um sicherzustellen, dass sie keine Fehler oder nicht anonymisierte sensible Daten enthält.",
        "encode_title": "ENCODE (anonymisieren)",
        "encode_button": "ENCODE",
        "encode_result": "Ergebnis: TXT-Datei mit Tokens + Kopfzeile",
        "decode_title": "DECODE (Daten wiederherstellen)",
        "decode_button": "DECODE",
        "decode_note": "Die Datei muss die Kopfzeile enthalten",
        "decode_note_2": "(wird automatisch beim ENCODE hinzugefügt).",
        "footer_1": "© potrzebuje.pl — All rights reserved.",
        "footer_2": "Vibe Coding using ChatGPT (v5.2)",
        "file_pick": "Datei wählen",
        "file_empty": "Keine Datei ausgewählt",
        "lang_label": "Sprache:",
        "error_400_title": "Ungültige Anfrage",
        "error_400_desc": "Die Anfrage konnte nicht verarbeitet werden. Prüfe die Datei oder die Parameter und versuche es erneut.",
        "error_404_title": "Seite nicht gefunden",
        "error_404_desc": "Die gesuchte Seite existiert nicht oder die Adresse ist ungültig.",
        "error_413_title": "Datei zu groß",
        "error_413_desc": "Die hochgeladene Datei überschreitet die zulässige Größe.",
        "error_429_title": "Zu viele Anfragen",
        "error_429_desc": "In kurzer Zeit wurden zu viele Versuche ausgeführt. Bitte warte einen Moment und versuche es erneut.",
        "error_500_title": "Interner Serverfehler",
        "error_500_desc": "Auf der Anwendungsseite ist ein unerwarteter Fehler aufgetreten.",
        "error_back": "Zurück zur Startseite",
    },
    "fr": {
        "html_lang": "fr",
        "title": "ANONYMOUS – anonymisation réversible (TXT)",
        "h1": "ANONYMOUS (MVP)",
        "about_title": "ANONYMOUS – anonymisation réversible (TXT)",
        "about_p1": "Cet outil sert à anonymiser les données sensibles dans les fichiers texte (TXT). Les informations sensibles (par exemple les données personnelles ou les identifiants) sont remplacées par des jetons spéciaux qui peuvent ensuite être restaurés dans leur forme d’origine.",
        "how_title": "Mode d’emploi :",
        "how_1": '1. Sélectionnez un fichier TXT et cliquez sur "ENCODE" pour l’anonymiser.',
        "how_2": "2. Téléchargez le fichier généré et conservez exactement le même nom.",
        "how_3": "3. Vous pouvez modifier le fichier anonymisé (par exemple changer le texte ou déplacer des fragments), mais ne supprimez pas et ne modifiez pas les jetons entre { ... }.",
        "how_4": '4. Pour restaurer les données, utilisez "DECODE" et sélectionnez le fichier anonymisé.',
        "rules_title": "Règles importantes :",
        "rule_1": "Le nom du fichier anonymisé doit rester exactement le même – le système l’utilise pour retrouver les données à restaurer.",
        "rule_2": "Les jetons { ... } doivent rester dans le fichier – leur suppression ou leur modification empêchera une restauration correcte.",
        "rule_3": "Le fichier peut être modifié par d’autres personnes sans accès aux données sensibles – les données ne seront restaurées qu’au moment du décodage.",
        "warning_title": "Attention :",
        "warning_text": "Le système détecte automatiquement les données sensibles, mais il ne garantit pas une exactitude de 100 %. Vérifiez toujours le fichier anonymisé avant toute utilisation ultérieure afin de vous assurer qu’il ne contient ni erreurs ni données sensibles non anonymisées.",
        "encode_title": "ENCODE (anonymiser)",
        "encode_button": "ENCODE",
        "encode_result": "Résultat : fichier TXT avec jetons + en-tête",
        "decode_title": "DECODE (restaurer les données)",
        "decode_button": "DECODE",
        "decode_note": "Le fichier doit contenir l’en-tête",
        "decode_note_2": "(ajouté automatiquement lors de ENCODE).",
        "footer_1": "© potrzebuje.pl — All rights reserved.",
        "footer_2": "Vibe Coding using ChatGPT (v5.2)",
        "file_pick": "Choisir un fichier",
        "file_empty": "Aucun fichier sélectionné",
        "lang_label": "Langue :",
        "error_400_title": "Requête invalide",
        "error_400_desc": "La requête n'a pas pu être traitée. Vérifie le fichier ou les paramètres et réessaie.",
        "error_404_title": "Page introuvable",
        "error_404_desc": "La page demandée n'existe pas ou l'adresse est invalide.",
        "error_413_title": "Fichier trop volumineux",
        "error_413_desc": "Le fichier envoyé dépasse la taille autorisée.",
        "error_429_title": "Trop de requêtes",
        "error_429_desc": "Trop de tentatives ont été effectuées en peu de temps. Attends un instant puis réessaie.",
        "error_500_title": "Erreur interne du serveur",
        "error_500_desc": "Une erreur inattendue s'est produite du côté de l'application.",
        "error_back": "Retour à la page d'accueil",
    },
    "es": {
        "html_lang": "es",
        "title": "ANONYMOUS – anonimización reversible (TXT)",
        "h1": "ANONYMOUS (MVP)",
        "about_title": "ANONYMOUS – anonimización reversible (TXT)",
        "about_p1": "Esta herramienta sirve para anonimizar datos sensibles en archivos de texto (TXT). La información sensible (por ejemplo, datos personales o identificadores) se sustituye por tokens especiales que después pueden restaurarse a su forma original.",
        "how_title": "Cómo usarlo:",
        "how_1": '1. Selecciona un archivo TXT y haz clic en "ENCODE" para anonimizarlo.',
        "how_2": "2. Descarga el archivo generado y conserva exactamente el mismo nombre.",
        "how_3": "3. Puedes editar el archivo anonimizado (por ejemplo cambiar el texto o mover fragmentos), pero no elimines ni modifiques los tokens dentro de { ... }.",
        "how_4": '4. Para restaurar los datos, usa "DECODE" y selecciona el archivo anonimizado.',
        "rules_title": "Reglas importantes:",
        "rule_1": "El nombre del archivo anonimizado debe permanecer exactamente igual: el sistema lo usa para localizar los datos y restaurarlos.",
        "rule_2": "Los tokens { ... } deben permanecer en el archivo: su eliminación o modificación impedirá la restauración correcta de los datos.",
        "rule_3": "El archivo puede ser editado por otras personas sin acceso a datos sensibles: los datos solo se restaurarán durante la decodificación.",
        "warning_title": "Aviso:",
        "warning_text": "El sistema detecta automáticamente datos sensibles, pero no garantiza una precisión del 100 %. Revisa siempre el archivo anonimizado antes de seguir utilizándolo para asegurarte de que no contiene errores ni datos sensibles sin anonimizar.",
        "encode_title": "ENCODE (anonimizar)",
        "encode_button": "ENCODE",
        "encode_result": "Resultado: archivo TXT con tokens + encabezado",
        "decode_title": "DECODE (restaurar datos)",
        "decode_button": "DECODE",
        "decode_note": "El archivo debe contener el encabezado",
        "decode_note_2": "(añadido automáticamente durante ENCODE).",
        "footer_1": "© potrzebuje.pl — All rights reserved.",
        "footer_2": "Vibe Coding using ChatGPT (v5.2)",
        "file_pick": "Elegir archivo",
        "file_empty": "Ningún archivo seleccionado",
        "lang_label": "Idioma:",
        "error_400_title": "Solicitud no válida",
        "error_400_desc": "No se pudo procesar la solicitud. Revisa el archivo o los parámetros e inténtalo de nuevo.",
        "error_404_title": "Página no encontrada",
        "error_404_desc": "La página solicitada no existe o la dirección es incorrecta.",
        "error_413_title": "Archivo demasiado grande",
        "error_413_desc": "El archivo enviado supera el tamaño permitido.",
        "error_429_title": "Demasiadas solicitudes",
        "error_429_desc": "Se realizaron demasiados intentos en poco tiempo. Espera un momento e inténtalo de nuevo.",
        "error_500_title": "Error interno del servidor",
        "error_500_desc": "Se produjo un error inesperado en la aplicación.",
        "error_back": "Volver a la página principal",
    },
}

def _resolve_lang() -> str:
    manual = request.args.get("lang", "").strip().lower()
    if manual in SUPPORTED_LANGS:
        return manual

    cookie_lang = request.cookies.get("lang", "").strip().lower()
    if cookie_lang in SUPPORTED_LANGS:
        return cookie_lang

    return DEFAULT_LANG

def _lang_labels():
    return {
        "pl": "PL",
        "en": "EN",
        "de": "DE",
        "fr": "FR",
        "es": "ES",
    }

# === I18N_V1_PATCH ===

def create_app() -> Flask:
    root = project_root()
    app = Flask(
        __name__,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )

    data_dir = root / "data"
    storage_dir = root / "storage"
    logs_dir = root / "logs"
    for d in (data_dir, storage_dir, logs_dir):
        d.mkdir(parents=True, exist_ok=True)

    db_path = get_db_path(data_dir)
    init_db(db_path)
    app_logger = setup_app_logger(logs_dir)
    rate_limiter = InMemoryRateLimiter(RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/")
    def index():
        client_ip = extract_client_ip(request)
        g.client_ip = client_ip
        g.route = request.path
        g.job_id = None
        g.file_size = None
        g.entities_found = None

        lang = _resolve_lang()
        t = I18N.get(lang, I18N[DEFAULT_LANG])
        response = make_response(
            render_template(
                "index.html",
                t=t,
                current_lang=lang,
                supported_langs=SUPPORTED_LANGS,
                lang_labels=_lang_labels(),
            )
        )
        log_event(
            app_logger,
            route=request.path,
            client_ip=client_ip,
            job_id=None,
            file_size=None,
            entities_found=None,
            status_code=200,
            event_type="visit",
            method=request.method,
            lang=lang,
            mode="index",
            success_flag=True,
        )
        manual = request.args.get("lang", "").strip().lower()
        if manual in SUPPORTED_LANGS:
            response.set_cookie("lang", manual, max_age=60 * 60 * 24 * 365, samesite="Lax")
        return response

    @app.get("/statistics")
    def statistics_route():
        import json
        from datetime import datetime, timedelta, timezone

        lang = _resolve_lang()
        t = I18N.get(lang, I18N[DEFAULT_LANG])

        ranges = [
            {"value": "today", "label": "Today"},
            {"value": "daily", "label": "24H"},
            {"value": "weekly", "label": "7D"},
            {"value": "monthly", "label": "30D"},
            {"value": "yearly", "label": "12M"},
        ]

        stats_range = request.args.get("range", "today").strip().lower()
        allowed_ranges = {item["value"] for item in ranges}
        if stats_range not in allowed_ranges:
            stats_range = "today"

        def _parse_ts(raw):
            if not raw:
                return None
            try:
                raw = raw.replace("Z", "+00:00")
                dt = datetime.fromisoformat(raw)
            except Exception:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        def _month_start(dt):
            return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        def _add_months(dt, months):
            year = dt.year + ((dt.month - 1 + months) // 12)
            month = ((dt.month - 1 + months) % 12) + 1
            return dt.replace(year=year, month=month, day=1)

        def _read_events(log_path):
            events = []
            if not log_path.exists():
                return events
            with log_path.open("r", encoding="utf-8", errors="replace") as fh:
                for raw_line in fh:
                    line = raw_line.strip()
                    if not line or not line.startswith("{"):
                        continue
                    try:
                        item = json.loads(line)
                    except Exception:
                        continue
                    dt = _parse_ts(item.get("timestamp"))
                    if not dt:
                        continue
                    item["_dt"] = dt
                    events.append(item)
            return events

        def _in_current_window(dt, now_utc, range_name):
            if range_name == "today":
                return dt.date() == now_utc.date()
            if range_name == "daily":
                return dt.date() >= (now_utc.date() - timedelta(days=29))
            if range_name == "weekly":
                start = (now_utc - timedelta(days=83)).date()
                return dt.date() >= start
            if range_name == "monthly":
                start = _add_months(_month_start(now_utc), -11)
                return dt >= start
            return True

        def _in_previous_window(dt, now_utc, range_name):
            if range_name == "today":
                prev_day = now_utc.date() - timedelta(days=1)
                return dt.date() == prev_day
            if range_name == "daily":
                start = now_utc.date() - timedelta(days=59)
                end = now_utc.date() - timedelta(days=30)
                return start <= dt.date() <= end
            if range_name == "weekly":
                start = now_utc.date() - timedelta(days=167)
                end = now_utc.date() - timedelta(days=84)
                return start <= dt.date() <= end
            if range_name == "monthly":
                start = _add_months(_month_start(now_utc), -23)
                end = _add_months(_month_start(now_utc), -11)
                return start <= dt < end
            return dt.year == (now_utc.year - 1)

        def _period_key(dt, range_name):
            if range_name in ("today", "daily"):
                return dt.strftime("%Y-%m-%d")
            if range_name == "weekly":
                iso = dt.isocalendar()
                year = iso[0]
                week = iso[1]
                return f"{year}-W{week:02d}"
            if range_name == "monthly":
                return dt.strftime("%Y-%m")
            return dt.strftime("%Y")

        def _trend_key(dt, range_name):
            if range_name in ("today", "daily"):
                return dt.strftime("%Y-%m-%d %H:00")
            if range_name == "weekly":
                return dt.strftime("%Y-%m-%d")
            if range_name == "monthly":
                return dt.strftime("%Y-%m-%d")
            return dt.strftime("%Y-%m")

        def _metric_counts(events_subset):
            visits = 0
            tool_uses = 0
            encode = 0
            decode = 0
            errors = 0
            successes = 0

            for item in events_subset:
                event_type = item.get("event_type")
                mode = item.get("mode")
                success_flag = item.get("success_flag")

                if event_type == "visit":
                    visits += 1
                if event_type == "tool_use":
                    tool_uses += 1
                if mode == "encode" and event_type == "tool_use":
                    encode += 1
                if mode == "decode" and event_type == "tool_use":
                    decode += 1
                if event_type == "error":
                    errors += 1
                if success_flag is True:
                    successes += 1

            attempts = tool_uses + errors
            success_rate = 0.0 if attempts == 0 else (100.0 * tool_uses / attempts)

            return {
                "visits": visits,
                "tool_uses": tool_uses,
                "encode": encode,
                "decode": decode,
                "errors": errors,
                "success_rate": success_rate,
            }

        def _delta_str(cur, prev, is_percent=False):
            if is_percent:
                diff = cur - prev
                return f"{diff:+.1f} pp"
            diff = cur - prev
            return f"{diff:+d}"

        app_log_path = logs_dir / "app.log"
        all_events = _read_events(app_log_path)
        now_utc = datetime.now(timezone.utc)

        excluded_routes = {"/statistics", "/_anonymous_version_probe"}
        filtered_events = [e for e in all_events if (e.get("route") or "") not in excluded_routes]

        display_events = [e for e in filtered_events if _in_current_window(e["_dt"], now_utc, stats_range)]
        prev_events = [e for e in filtered_events if _in_previous_window(e["_dt"], now_utc, stats_range)]

        cur_metrics = _metric_counts(display_events)
        # === BOT / HUMAN COUNTS (SAFE SIDE COMPUTATION) ===
        def _is_bot_user_agent(ua: str) -> bool:
            if not ua:
                return False
            ua = ua.lower()
            bot_markers = ["bot", "crawler", "spider", "curl", "python", "wget"]
            return any(m in ua for m in bot_markers)

        bot_count = 0
        human_count = 0

        for e in display_events:
            ua = e.get("user_agent", "") or ""
            if _is_bot_user_agent(ua):
                bot_count += 1
            else:
                human_count += 1

        prev_metrics = _metric_counts(prev_events)

        grouped = {}
        for item in display_events:
            key = (
                _period_key(item["_dt"], stats_range),
                item.get("route") or "",
                item.get("event_type") or "",
                item.get("mode") or "",
                item.get("lang") or "",
                item.get("status_code"),
            )
            if key not in grouped:
                grouped[key] = {
                    "period": key[0],
                    "route": key[1],
                    "event_type": key[2],
                    "mode": key[3],
                    "lang": key[4],
                    "status_code": key[5],
                    "count": 0,
                    "success_count": 0,
                    "error_count": 0,
                }
            grouped[key]["count"] += 1
            if item.get("success_flag") is True:
                grouped[key]["success_count"] += 1
            if item.get("success_flag") is False:
                grouped[key]["error_count"] += 1

        rows = sorted(
            grouped.values(),
            key=lambda r: (
                r["period"],
                r["count"],
                r["route"],
                r["event_type"],
                r["mode"],
                r["lang"],
                str(r["status_code"]),
            ),
            reverse=True,
        )

        
        visit_events = [e for e in display_events if e.get("event_type") == "visit"]

        from datetime import timedelta

        trend_map = {}

        def add_point(key):
            trend_map[key] = trend_map.get(key, 0) + 1

        if stats_range in ("today", "daily"):
            # hourly
            for h in range(24):
                key = f"{h:02d}:00"
                trend_map[key] = 0

            for e in visit_events:
                dt = e["_dt"]
                key = f"{dt.hour:02d}:00"
                add_point(key)

        elif stats_range == "weekly":
            for d in range(7):
                key = (now_utc - timedelta(days=6 - d)).strftime("%Y-%m-%d")
                trend_map[key] = 0

            for e in visit_events:
                key = e["_dt"].strftime("%Y-%m-%d")
                if key in trend_map:
                    add_point(key)

        elif stats_range == "monthly":
            for d in range(30):
                key = (now_utc - timedelta(days=29 - d)).strftime("%Y-%m-%d")
                trend_map[key] = 0

            for e in visit_events:
                key = e["_dt"].strftime("%Y-%m-%d")
                if key in trend_map:
                    add_point(key)

        elif stats_range == "yearly":
            for m in range(12):
                key = (now_utc - timedelta(days=330 - m*30)).strftime("%Y-%m")
                trend_map[key] = 0

            for e in visit_events:
                key = e["_dt"].strftime("%Y-%m")
                if key in trend_map:
                    add_point(key)

        trend_labels = sorted(trend_map.keys())
        trend_values = [trend_map[k] for k in trend_labels]

        # --- PIE CHART AGGREGATIONS ---
        route_counts_map = {}
        event_type_counts_map = {}
        status_counts_map = {}

        for e in display_events:
            route = e.get("route") or "unknown"
            et = e.get("event_type") or "unknown"
            status = str(e.get("status_code"))

            route_counts_map[route] = route_counts_map.get(route, 0) + 1
            event_type_counts_map[et] = event_type_counts_map.get(et, 0) + 1
            status_counts_map[status] = status_counts_map.get(status, 0) + 1

        route_counts = sorted(route_counts_map.items(), key=lambda x: x[1], reverse=True)
        event_type_counts = sorted(event_type_counts_map.items(), key=lambda x: x[1], reverse=True)
        status_counts = sorted(status_counts_map.items(), key=lambda x: x[1], reverse=True)




        total_events = len(display_events)
        unknown_event_count = sum(
            1 for e in display_events
            if (e.get("event_type") or "unknown") == "unknown"
        )

        error_route_counts = {}
        for e in display_events:
            if e.get("event_type") == "error":
                r = e.get("route") or "unknown"
                error_route_counts[r] = error_route_counts.get(r, 0) + 1

        top_route = route_counts[0][0] if route_counts else "n/a"
        top_error_route = (
            sorted(error_route_counts.items(), key=lambda x: x[1], reverse=True)[0][0]
            if error_route_counts else "n/a"
        )
        error_share = 0.0 if total_events == 0 else (100.0 * cur_metrics["errors"] / total_events)

        insights = [
            {"label": "Top route", "value": top_route},
            {"label": "Top error route", "value": top_error_route},
            {"label": "Error share", "value": f"{error_share:.1f}%"},
            {"label": "Success rate", "value": f"{cur_metrics['success_rate']:.1f}%"},
            {"label": "Legacy / unknown events", "value": str(unknown_event_count)},
        ]

        kpis = [
            {
                "label": "Visits",
                "value": cur_metrics["visits"],
                "delta": _delta_str(cur_metrics["visits"], prev_metrics["visits"]),
            },
            {
                "label": "Tool uses",
                "value": cur_metrics["tool_uses"],
                "delta": _delta_str(cur_metrics["tool_uses"], prev_metrics["tool_uses"]),
            },
            {
                "label": "Encode",
                "value": cur_metrics["encode"],
                "delta": _delta_str(cur_metrics["encode"], prev_metrics["encode"]),
            },
            {
                "label": "Decode",
                "value": cur_metrics["decode"],
                "delta": _delta_str(cur_metrics["decode"], prev_metrics["decode"]),
            },
            {
                "label": "Errors",
                "value": cur_metrics["errors"],
                "delta": _delta_str(cur_metrics["errors"], prev_metrics["errors"]),
            },
            {
                "label": "User errors",
                "value": cur_metrics.get("user_errors", 0),
                "delta": _delta_str(cur_metrics.get("user_errors", 0), prev_metrics.get("user_errors", 0)),
            },
            {
                "label": "System errors",
                "value": cur_metrics.get("system_errors", 0),
                "delta": _delta_str(cur_metrics.get("system_errors", 0), prev_metrics.get("system_errors", 0)),
            },
            {
                "label": "Success rate",
                "value": f"{cur_metrics['success_rate']:.1f}%",
                "delta": _delta_str(cur_metrics["success_rate"], prev_metrics["success_rate"], is_percent=True),
            },
        ]

        return render_template(
            "statistics.html",
            t=t,
            current_lang=lang,
            supported_langs=SUPPORTED_LANGS,
            lang_labels=_lang_labels(),
            stats_range=stats_range,
            ranges=ranges,
            kpis=kpis,
            insights=insights,
            rows=rows,
            trend_labels=trend_labels,
            trend_values=trend_values,
            bot_count=bot_count,
            human_count=human_count,
            route_counts=route_counts,
            event_type_counts=event_type_counts,
            status_counts=status_counts,
        )

    @app.post("/encode")
    def encode_route():
        client_ip = extract_client_ip(request)
        g.client_ip = client_ip
        g.route = request.path
        g.job_id = None
        g.file_size = None
        g.entities_found = None

        if not rate_limiter.allow(client_ip):
            abort(429)

        f = request.files.get("file")
        if not f or not f.filename:
            abort(400, "No file uploaded")
        validation_error = validate_txt_upload(f)
        if validation_error:
            abort(400, validation_error)

        original_full = f.filename
        original_safe = sanitize_filename(original_full)
        raw = f.read()
        g.file_size = len(raw)
        if len(raw) > MAX_UPLOAD_BYTES:
            abort(413)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            abort(400, "File must be valid UTF-8 TXT.")

        ts = now_timestamp_ms()
        with connect(db_path) as conn:
            temp_job_id = f"JOB-TEMP-{ts}--{original_full}"
            job_no = create_job(conn, temp_job_id, original_full, original_safe, ts)
            job_id = f"JOB-{job_no:06d}-{ts}--{original_full}"
            g.job_id = job_id
            conn.execute("UPDATE jobs SET job_id=? WHERE job_no=?", (job_id, job_no))
            conn.commit()

            job_dir = storage_dir / job_id
            (job_dir / "input").mkdir(parents=True, exist_ok=True)
            (job_dir / "output").mkdir(parents=True, exist_ok=True)

            input_path = job_dir / "input" / original_safe
            input_path.write_text(text, encoding="utf-8")

            entities = detect(text)
            g.entities_found = len(entities)
            anon_text, mappings = anonymize(text, entities)

            anon_text_with_header = f"## ANON_JOB: {job_id}\n" + anon_text

            for m in mappings:
                insert_mapping(conn, job_id, m.token, m.entity_type, m.original_value)
            conn.commit()

            encode_stem = (Path(original_safe).stem[:20] or "file")
            encode_stamp = "_".join(ts.split("-")[:2])
            out_name = f"{encode_stem}__CODE__{encode_stamp}{Path(original_safe).suffix or '.txt'}"
            out_path = job_dir / "output" / out_name
            out_path.write_text(anon_text_with_header, encoding="utf-8")

        log_event(
            app_logger,
            route=request.path,
            client_ip=client_ip,
            job_id=g.job_id,
            file_size=g.file_size,
            entities_found=g.entities_found,
            status_code=200,
            event_type="tool_use",
            method=request.method,
            lang=_resolve_lang(),
            mode="encode",
            success_flag=True,
        )
        return send_file(
            out_path,
            as_attachment=True,
            download_name=out_name,
            mimetype="text/plain; charset=utf-8",
        )

    @app.post("/decode")
    def decode_route():
        client_ip = extract_client_ip(request)
        g.client_ip = client_ip
        g.route = request.path
        g.job_id = None
        g.file_size = None
        g.entities_found = None

        if not rate_limiter.allow(client_ip):
            abort(429)

        f = request.files.get("file")
        if not f or not f.filename:
            abort(400, "No file uploaded")
        validation_error = validate_txt_upload(f)
        if validation_error:
            abort(400, validation_error)


        try:
            uploaded_name = f.filename

            raw = f.read()
            g.file_size = len(raw)

            if len(raw) > MAX_UPLOAD_BYTES:
                abort(413)

            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                abort(400, "File must be valid UTF-8 TXT.")

            job_id = extract_job_id_from_text(text) or extract_job_id_from_filename(uploaded_name)

            if not job_id:
                abort(400, "Cannot find job_id. File must include '## ANON_JOB: ...' header or correct filename.")
            g.job_id = job_id

            with connect(db_path) as conn:
                mapping = load_mapping_dict(conn, job_id)

            mapping_size = len(mapping) if mapping else 0

            if not mapping:
                abort(404, f"No mapping found for job_id: {job_id}")

            restored = deanonymize(text, mapping)

            ts2 = now_timestamp_ms()
            job_dir = storage_dir / job_id
            (job_dir / "output").mkdir(parents=True, exist_ok=True)

            safe_uploaded = sanitize_filename(uploaded_name)
            uploaded_stem = Path(safe_uploaded).stem
            user_stem = uploaded_stem.split("__",1)[0]
            base_stem = (user_stem[:20] or "file")
            decode_stamp = "_".join(ts2.split("-")[:2])
            out_name = f"{base_stem}__DECODE__{decode_stamp}.txt"
            out_path = job_dir / "output" / out_name
            out_path.write_text(restored, encoding="utf-8")

        except Exception as e:
            raise

        log_event(
            app_logger,
            route=request.path,
            client_ip=client_ip,
            job_id=g.job_id,
            file_size=g.file_size,
            entities_found=None,
            status_code=200,
            event_type="tool_use",
            method=request.method,
            lang=_resolve_lang(),
            mode="decode",
            success_flag=True,
        )
        return send_file(
            out_path,
            as_attachment=True,
            download_name=out_name,
            mimetype="text/plain; charset=utf-8",
        )

    @app.errorhandler(400)
    def error_400(err):
        log_event(
            app_logger,
            route=request.path,
            client_ip=getattr(g, "client_ip", extract_client_ip(request)),
            job_id=getattr(g, "job_id", None),
            file_size=getattr(g, "file_size", request.content_length),
            entities_found=getattr(g, "entities_found", None),
            status_code=400,
            event_type="error",
            method=request.method,
            lang=_resolve_lang(),
            mode="encode" if request.path == "/encode" else ("decode" if request.path == "/decode" else "other"),
            success_flag=False,
        )
        lang = _resolve_lang()
        t = I18N.get(lang, I18N[DEFAULT_LANG])
        return render_template(
            "errors/400.html",
            t=t,
            current_lang=lang,
            supported_langs=SUPPORTED_LANGS,
            lang_labels=_lang_labels(),
            message=getattr(err, "description", "Invalid request."),
            limit_mb=MAX_UPLOAD_BYTES // (1024 * 1024),
        ), 400

    @app.errorhandler(404)
    def error_404(_err):
        log_event(
            app_logger,
            route=request.path,
            client_ip=getattr(g, "client_ip", extract_client_ip(request)),
            job_id=getattr(g, "job_id", None),
            file_size=getattr(g, "file_size", request.content_length),
            entities_found=getattr(g, "entities_found", None),
            status_code=404,
            event_type="error",
            method=request.method,
            lang=_resolve_lang(),
            mode="encode" if request.path == "/encode" else ("decode" if request.path == "/decode" else "other"),
            success_flag=False,
        )
        lang = _resolve_lang()
        t = I18N.get(lang, I18N[DEFAULT_LANG])
        return render_template(
            "errors/404.html",
            t=t,
            current_lang=lang,
            supported_langs=SUPPORTED_LANGS,
            lang_labels=_lang_labels(),
            message=None,
            limit_mb=MAX_UPLOAD_BYTES // (1024 * 1024),
        ), 404

    @app.errorhandler(413)
    def error_413(_err):
        log_event(
            app_logger,
            route=request.path,
            client_ip=getattr(g, "client_ip", extract_client_ip(request)),
            job_id=getattr(g, "job_id", None),
            file_size=getattr(g, "file_size", request.content_length),
            entities_found=getattr(g, "entities_found", None),
            status_code=413,
            event_type="error",
            method=request.method,
            lang=_resolve_lang(),
            mode="encode" if request.path == "/encode" else ("decode" if request.path == "/decode" else "other"),
            success_flag=False,
        )
        lang = _resolve_lang()
        t = I18N.get(lang, I18N[DEFAULT_LANG])
        return render_template(
            "errors/413.html",
            t=t,
            current_lang=lang,
            supported_langs=SUPPORTED_LANGS,
            lang_labels=_lang_labels(),
            message=None,
            limit_mb=MAX_UPLOAD_BYTES // (1024 * 1024),
        ), 413

    @app.errorhandler(429)
    def error_429(_err):
        log_event(
            app_logger,
            route=request.path,
            client_ip=getattr(g, "client_ip", extract_client_ip(request)),
            job_id=getattr(g, "job_id", None),
            file_size=getattr(g, "file_size", request.content_length),
            entities_found=getattr(g, "entities_found", None),
            status_code=429,
            event_type="error",
            method=request.method,
            lang=_resolve_lang(),
            mode="encode" if request.path == "/encode" else ("decode" if request.path == "/decode" else "other"),
            success_flag=False,
        )
        lang = _resolve_lang()
        t = I18N.get(lang, I18N[DEFAULT_LANG])
        return render_template(
            "errors/429.html",
            t=t,
            current_lang=lang,
            supported_langs=SUPPORTED_LANGS,
            lang_labels=_lang_labels(),
            message=None,
            limit_mb=MAX_UPLOAD_BYTES // (1024 * 1024),
        ), 429

    @app.errorhandler(500)
    def error_500(_err):
        log_event(
            app_logger,
            route=request.path,
            client_ip=getattr(g, "client_ip", extract_client_ip(request)),
            job_id=getattr(g, "job_id", None),
            file_size=getattr(g, "file_size", request.content_length),
            entities_found=getattr(g, "entities_found", None),
            status_code=500,
            event_type="error",
            method=request.method,
            lang=_resolve_lang(),
            mode="encode" if request.path == "/encode" else ("decode" if request.path == "/decode" else "other"),
            success_flag=False,
        )
        lang = _resolve_lang()
        t = I18N.get(lang, I18N[DEFAULT_LANG])
        return render_template(
            "errors/500.html",
            t=t,
            current_lang=lang,
            supported_langs=SUPPORTED_LANGS,
            lang_labels=_lang_labels(),
            message=None,
            limit_mb=MAX_UPLOAD_BYTES // (1024 * 1024),
        ), 500


    @app.route("/_anonymous_version_probe", methods=["GET"])
    def _anonymous_version_probe():
        return "ANON_PROBE_20260318_155635", 200

    return app

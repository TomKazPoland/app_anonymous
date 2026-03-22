from __future__ import annotations

import os
from pathlib import Path
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
        manual = request.args.get("lang", "").strip().lower()
        if manual in SUPPORTED_LANGS:
            response.set_cookie("lang", manual, max_age=60 * 60 * 24 * 365, samesite="Lax")
        return response

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

            out_name = f"{Path(original_safe).stem}__ANON__{job_id}{Path(original_safe).suffix or '.txt'}"
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

        if not mapping:
            abort(404, f"No mapping found for job_id: {job_id}")

        restored = deanonymize(text, mapping)

        ts2 = now_timestamp_ms()
        job_dir = storage_dir / job_id
        (job_dir / "output").mkdir(parents=True, exist_ok=True)

        safe_uploaded = sanitize_filename(uploaded_name)
        base_stem = Path(safe_uploaded).stem
        out_name = f"{base_stem}__DEANON__{job_id}__{ts2}.txt"
        out_path = job_dir / "output" / out_name
        out_path.write_text(restored, encoding="utf-8")

        log_event(
            app_logger,
            route=request.path,
            client_ip=client_ip,
            job_id=g.job_id,
            file_size=g.file_size,
            entities_found=None,
            status_code=200,
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

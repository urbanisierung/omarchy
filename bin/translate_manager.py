#!/usr/bin/env python3
import sys
import subprocess
import re

# --- CONFIGURATION ---
# Get your key at: https://www.deepl.com/pro-api
# Leave empty if you don't intend to use DeepL
DEEPL_AUTH_KEY = ""  

def notify(title, message):
    """Send a desktop notification."""
    subprocess.run(['notify-send', title, message])

def show_wofi_loading():
    """
    Show a loading wofi modal (non-blocking).
    Returns the Popen process so it can be terminated later.
    """
    proc = subprocess.Popen(
        ['wofi', '--dmenu', '--prompt', '⏳ Translating... Please wait', 
         '--cache-file', '/dev/null'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )
    # Write content with padding lines to ensure modal has reasonable height
    content = "\n".join([
        "╔══════════════════════════════════════╗",
        "║                                      ║",
        "║        Translation in progress       ║",
        "║                                      ║",
        "╚══════════════════════════════════════╝",
    ]) + "\n"
    proc.stdin.write(content.encode('utf-8'))
    proc.stdin.flush()
    return proc

def show_wofi_result(label, text):
    """
    Opens Wofi with the translation result in a multiline area.
    Returns True if user hits Enter (to copy), False if Esc.
    """
    try:
        # Calculate number of lines needed (minimum 5, maximum 15)
        line_count = min(max(text.count('\n') + 3, 5), 15)
        
        # We pipe the result text as the input choice for wofi
        proc = subprocess.run(
            ['wofi', '--dmenu', '--prompt', f'{label} (Enter to copy)', 
             '--width', '800', '--height', '400', '--lines', str(line_count),
             '--cache-file', '/dev/null'],
            input=text.encode('utf-8'),
            capture_output=True
        )
        return proc.returncode == 0
    except FileNotFoundError:
        notify("Error", "Wofi not found")
        return False

def parse_input(text):
    """
    Parses input patterns:
    - "text"          -> Auto detect source -> Target (default de/en swap)
    - "es:text"       -> Source ES -> Target DE (default)
    - "es:en:text"    -> Source ES -> Target EN
    """
    # Regex matches: optional "xx:", optional "xx:", rest of text
    pattern = r"^(?:([a-z]{2}):)?(?:([a-z]{2}):)?(.*)"
    match = re.match(pattern, text)
    code1, code2, content = match.groups()
    
    if content:
        content = content.strip()
    else:
        return 'en', 'de', '' # Empty fallback
    
    source_lang = 'auto'
    target_lang = 'de' # Default target if not specified

    if code1 and code2:
        # Format: es:en:text
        source_lang = code1
        target_lang = code2
    elif code1:
        # Format: es:text
        # If source is explicitly DE, target becomes EN. Otherwise target is DE.
        source_lang = code1
        target_lang = 'en' if source_lang == 'de' else 'de'
    
    # Auto-detection if no source specified
    if source_lang == 'auto':
        try:
            from fast_langdetect import detect
            detected = detect(content)
            # fast-langdetect returns list or dict depending on version
            s_code = detected[0]['lang'] if isinstance(detected, list) else detected.get('lang', 'en')
            source_lang = s_code
            
            # Context switch: If input is German, translate to English
            if source_lang == 'de':
                target_lang = 'en'
        except:
            source_lang = 'en' # Fallback

    return source_lang, target_lang, content

def translate_offline(source, target, text):
    try:
        import argostranslate.package
        import argostranslate.translate
        installed = argostranslate.translate.get_installed_languages()
        from_lang = next((l for l in installed if l.code == source), None)
        to_lang = next((l for l in installed if l.code == target), None)

        if from_lang and to_lang:
            translation = from_lang.get_translation(to_lang)
            return translation.translate(text)
        else:
            return f"Error: Model {source}->{target} not installed. Run install_models.py."
    except Exception as e:
        return f"Offline Error: {str(e)}"

def translate_deepl(source, target, text):
    if not DEEPL_AUTH_KEY:
        return "Error: DeepL API Key missing in script."
    
    import requests
    url = "https://api-free.deepl.com/v2/translate"
    headers = {
        "Authorization": f"DeepL-Auth-Key {DEEPL_AUTH_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "text": [text],
        "target_lang": target.upper()
    }
    # Only include source_lang if not auto-detecting
    if source and source != 'auto':
        payload["source_lang"] = source.upper()
    
    try:
        r = requests.post(url, headers=headers, json=payload)
        data = r.json()
        if "translations" in data:
            return data["translations"][0]["text"]
        return f"DeepL Error: {data.get('message', str(data))}"
    except Exception as e:
        return f"Connection Error: {str(e)}"

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "offline"
    
    # 1. Get Input
    try:
        # Empty input piped to wofi to open it in text entry mode
        p = subprocess.run(['wofi', '--dmenu', '--prompt', f'Translate ({mode})'], 
                           input=b"", capture_output=True)
        user_input = p.stdout.decode('utf-8').strip()
    except Exception:
        return

    if not user_input:
        return

    # 2. Process & Translate
    src, tgt, text_to_translate = parse_input(user_input)
    
    if not text_to_translate:
        notify("Error", "No text to translate")
        return
    
    # Show loading wofi immediately (non-blocking)
    loading_proc = show_wofi_loading()
    
    try:
        if mode == "deepl":
            final_text = translate_deepl(src, tgt, text_to_translate)
        else:
            final_text = translate_offline(src, tgt, text_to_translate)
    except Exception as e:
        loading_proc.terminate()
        loading_proc.wait()
        notify("Translation Error", str(e))
        return
    
    # Close loading wofi
    loading_proc.terminate()
    loading_proc.wait()
    
    # Check for error responses from translation functions
    if final_text.startswith(("Error:", "Offline Error:", "DeepL Error:", "Connection Error:")):
        notify("Translation Failed", final_text)
        return

    # 3. Show Result
    # User sees result in Wofi. Hitting Enter returns True.
    confirmed = show_wofi_result(f"{src} -> {tgt}", final_text)

    # 4. Copy to Clipboard
    if confirmed:
        subprocess.run(['wl-copy', final_text])
        notify("Copied", final_text)

if __name__ == "__main__":
    main()
# HyprTranslation Configuration

## 0. Installation

```bash
sudo dnf install wofi wl-clipboard libnotify python3-pip
pip install argostranslate fast-langdetect requests
```

Download Models:

```bash
python3 ~/.local/bin/install_models.py
```

Set DeepL API Key (Optional): Open `translate_manager.py` in your text editor and paste your key into the `DEEPL_AUTH_KEY` variable at the top.

## 1. Hyprland Integration


import sys

if sys.version_info < (3, 11):
    raise RuntimeError(
        f"Smart Orchid backend требует Python 3.11+, а запущен Python {sys.version.split()[0]}.\n"
        "Установите Python 3.12 и пересоздайте окружение:\n"
        "  rm -rf .venv && python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    )

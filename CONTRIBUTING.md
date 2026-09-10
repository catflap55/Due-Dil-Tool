# Contributing

Issues and pull requests are welcome for register adapters, clearer dossier cards, or identifier checks.

Please keep live network calls behind optional keys. Local identifier checks and official link-outs should work with no secrets.

Do not commit API keys, `data/`, or `.env` files.

## Tests

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest
```

On Windows use `Windows\Start.cmd` to run the app; tests still use the commands above in a terminal after Python is on PATH.

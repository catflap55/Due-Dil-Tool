# Security

This application runs **on your computer**. It is not a public website.

- Optional API keys are stored in a local SQLite file under `data/` (ignored by Git). They are not encrypted at rest. Protect the machine.
- The preview listens on this computer only (`127.0.0.1` / `localhost`, port 8765).
- There is no login. Anyone who can use this computer can use the app and see keys you saved.
- Do not commit `data/`, `.env` files, API keys, or passwords.

Report a vulnerability privately with [GitHub security advisories](https://github.com/catflap55/Due-Dil-Tool/security/advisories/new) on this repository.

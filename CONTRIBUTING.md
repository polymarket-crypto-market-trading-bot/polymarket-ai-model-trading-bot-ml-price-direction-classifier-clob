# Contributing

Thank you for your interest in this **Polymarket AI model trading bot**.

Please read the **[Contributing — Live Trading](README.md#contributing--live-trading)** section in the README for areas where help is most valuable.

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -v
python scripts/verify_readme_assets.py
```

## Pull request guidelines

- Keep changes focused and tested
- Run `pytest -v` before submitting
- Do not commit `.env` or credentials
- Describe live-trading impact if touching `execution/`

## Discuss first

Open an Issue or Discussion before large architectural changes. The maintainer is actively trading and happy to collaborate on real-world improvements.

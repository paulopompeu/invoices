PYTHON ?= python3
VENV_PYTHON = .venv/bin/python
DATA ?= invoice-04.json

.PHONY: setup install-browser invoice dry-run debug

setup:
	$(PYTHON) -m venv .venv
	$(VENV_PYTHON) -m pip install -r requirements.txt
	$(VENV_PYTHON) -m playwright install chromium

install-browser:
	$(VENV_PYTHON) -m playwright install chromium

invoice:
	$(VENV_PYTHON) generate_invoice.py --data $(DATA)

dry-run:
	$(VENV_PYTHON) generate_invoice.py --data $(DATA) --dry-run

debug:
	$(VENV_PYTHON) generate_invoice.py --data $(DATA) --keep-html

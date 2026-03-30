PYTHON ?= python3
VENV_PYTHON = .venv/bin/python
DATA ?= invoice-ford.json

.PHONY: setup install-browser invoice dry-run debug check test weekly-dry-run weekly-draft

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

check:
	$(PYTHON) -m py_compile generate_invoice.py
	$(PYTHON) -m unittest discover -s tests -v
	$(VENV_PYTHON) generate_invoice.py --data invoice-data.example.json --dry-run

test:
	$(PYTHON) -m unittest discover -s tests -v

weekly-dry-run:
	$(VENV_PYTHON) prepare_weekly_invoice.py --data $(DATA) --dry-run

weekly-draft:
	$(VENV_PYTHON) prepare_weekly_invoice.py --data $(DATA)

%-dry-run:
	@if [ -f "invoice-$*.json" ]; then \
		$(VENV_PYTHON) generate_invoice.py --data "invoice-$*.json" --dry-run; \
	else \
		echo "make: unknown target '$@' and file 'invoice-$*.json' was not found." >&2; \
		exit 2; \
	fi

%:
	@if [ -f "invoice-$@.json" ]; then \
		$(VENV_PYTHON) generate_invoice.py --data "invoice-$@.json"; \
	else \
		echo "make: unknown target '$@' and file 'invoice-$@.json' was not found." >&2; \
		exit 2; \
	fi

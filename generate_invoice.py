#!/usr/bin/env python3

import argparse
import asyncio
import html
import json
import re
import sys
import tempfile
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TEMPLATE_PATH = ROOT / "invoice-template.html"
OUTPUT_DIR = ROOT / "output"
SEQUENCE_PATH = ROOT / "sequence.txt"
REQUIRED_FIELDS = [
    "seller_name",
    "seller_legal_name",
    "seller_tax_id",
    "seller_address_line1",
    "seller_address_line2",
    "seller_email",
    "client_name",
    "client_department",
    "client_address_line1",
    "client_address_line2",
    "client_email",
    "issue_date",
    "due_date",
    "currency",
    "notes",
    "items",
]


def money(value: Decimal, currency: str) -> str:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{currency} {quantized:,.2f}"


def load_data(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def fail(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def parse_decimal(value: object, label: str) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"'{label}' must be a valid number.") from exc


def validate_data(data: object) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Top-level JSON must be an object.")

    missing_fields = [field for field in REQUIRED_FIELDS if field not in data]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    for field in REQUIRED_FIELDS:
        if field == "items":
            continue
        if not isinstance(data[field], str):
            raise ValueError(f"'{field}' must be a string.")

    items = data["items"]
    if not isinstance(items, list) or not items:
        raise ValueError("'items' must be a non-empty list.")

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"'items[{index}]' must be an object.")

        for field in ["description", "quantity", "unit_price"]:
            if field not in item:
                raise ValueError(f"'items[{index}].{field}' is required.")

        if not isinstance(item["description"], str) or not item["description"].strip():
            raise ValueError(f"'items[{index}].description' must be a non-empty string.")

        quantity = parse_decimal(item["quantity"], f"items[{index}].quantity")
        unit_price = parse_decimal(item["unit_price"], f"items[{index}].unit_price")

        if quantity <= 0:
            raise ValueError(f"'items[{index}].quantity' must be greater than zero.")
        if unit_price < 0:
            raise ValueError(f"'items[{index}].unit_price' must be zero or greater.")

    parse_decimal(data.get("tax", 0), "tax")
    return data


def detect_highest_output_number(output_dir: Path = OUTPUT_DIR) -> int:
    highest = 0

    if not output_dir.exists():
        return 0

    for path in output_dir.iterdir():
        if path.is_dir():
            continue

        match = re.search(r"invoice-(\d+)$", path.stem, re.IGNORECASE)
        if match:
            highest = max(highest, int(match.group(1)))

    return highest


def read_sequence_value(sequence_path: Path = SEQUENCE_PATH, output_dir: Path = OUTPUT_DIR) -> int:
    if sequence_path.exists():
        raw_value = read_text(sequence_path).strip()
        if not raw_value:
            raise ValueError("sequence.txt is empty.")
        try:
            return int(raw_value)
        except ValueError as exc:
            raise ValueError("sequence.txt must contain an integer.") from exc

    return detect_highest_output_number(output_dir)


def next_invoice_number(sequence_path: Path = SEQUENCE_PATH, output_dir: Path = OUTPUT_DIR) -> int:
    current = read_sequence_value(sequence_path, output_dir)
    return current + 1 if current >= 0 else 1


def write_sequence_value(number: int, sequence_path: Path = SEQUENCE_PATH) -> None:
    sequence_path.write_text(f"{number}\n", encoding="utf-8")


def build_items_rows(items: list[dict], currency: str) -> tuple[str, Decimal]:
    rows = []
    subtotal = Decimal("0")

    for item in items:
        quantity = Decimal(str(item["quantity"]))
        unit_price = Decimal(str(item["unit_price"]))
        amount = quantity * unit_price
        subtotal += amount

        rows.append(
            "\n".join(
                [
                    "<tr>",
                    f"  <td>{html.escape(str(item['description']))}</td>",
                    f"  <td class=\"qty\">{quantity}</td>",
                    f"  <td class=\"unit\">{money(unit_price, currency)}</td>",
                    f"  <td class=\"amount\">{money(amount, currency)}</td>",
                    "</tr>",
                ]
            )
        )

    return "\n".join(rows), subtotal


def render(template: str, values: dict) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    return rendered


async def render_pdf(html_path: Path, pdf_path: Path) -> None:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency 'playwright'. Install requirements and run "
            "'python3 -m playwright install chromium'."
        ) from exc

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page()
        await page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        await page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        await browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a standardized invoice PDF file.")
    parser.add_argument("--data", required=True, help="Path to the JSON data file.")
    parser.add_argument("--number", type=int, help="Invoice sequence number. Defaults to the next detected number.")
    parser.add_argument("--dry-run", action="store_true", help="Preview the next invoice number and output path without writing files.")
    parser.add_argument("--keep-html", action="store_true", help="Keep the rendered HTML alongside the PDF for debugging.")
    args = parser.parse_args()

    try:
        data = validate_data(load_data(Path(args.data)))
    except FileNotFoundError:
        fail(f"Data file not found: {args.data}")
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON in {args.data}: {exc}")
    except ValueError as exc:
        fail(str(exc))

    try:
        invoice_number = args.number if args.number is not None else next_invoice_number()
    except ValueError as exc:
        fail(str(exc))

    if invoice_number <= 0:
        fail("Invoice number must be greater than zero.")

    currency = str(data["currency"])
    items_rows, subtotal = build_items_rows(data["items"], currency)
    tax = Decimal(str(data.get("tax", 0)))
    total = subtotal + tax

    values = {
        "invoice_number": f"{invoice_number:04d}",
        "seller_name": html.escape(str(data["seller_name"])),
        "seller_legal_name": html.escape(str(data["seller_legal_name"])),
        "seller_tax_id": html.escape(str(data["seller_tax_id"])),
        "seller_address_line1": html.escape(str(data["seller_address_line1"])),
        "seller_address_line2": html.escape(str(data["seller_address_line2"])),
        "seller_email": html.escape(str(data["seller_email"])),
        "client_name": html.escape(str(data["client_name"])),
        "client_department": html.escape(str(data["client_department"])),
        "client_address_line1": html.escape(str(data["client_address_line1"])),
        "client_address_line2": html.escape(str(data["client_address_line2"])),
        "client_email": html.escape(str(data["client_email"])),
        "issue_date": html.escape(str(data["issue_date"])),
        "due_date": html.escape(str(data["due_date"])),
        "currency": html.escape(currency),
        "notes": html.escape(str(data["notes"])),
        "items_rows": items_rows,
        "subtotal": money(subtotal, currency),
        "tax": money(tax, currency),
        "total": money(total, currency),
    }

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    rendered = render(template, values)

    OUTPUT_DIR.mkdir(exist_ok=True)
    pdf_path = OUTPUT_DIR / f"invoice-{invoice_number:04d}.pdf"
    html_path = OUTPUT_DIR / f"invoice-{invoice_number:04d}.html"

    if args.dry_run:
        print(f"invoice_number={invoice_number:04d}")
        print(f"output_path={pdf_path}")
        print(f"total={money(total, currency)}")
        return

    if args.keep_html:
        html_path.write_text(rendered, encoding="utf-8")
        source_html_path = html_path
    else:
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as temp_file:
            temp_file.write(rendered)
            source_html_path = Path(temp_file.name)

    try:
        asyncio.run(render_pdf(source_html_path, pdf_path))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    finally:
        if not args.keep_html and source_html_path.exists():
            source_html_path.unlink()

    try:
        current_sequence = read_sequence_value()
        write_sequence_value(max(current_sequence, invoice_number))
    except ValueError as exc:
        fail(str(exc))

    print(pdf_path)


if __name__ == "__main__":
    main()

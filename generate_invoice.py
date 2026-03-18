#!/usr/bin/env python3

import argparse
import html
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TEMPLATE_PATH = ROOT / "invoice-template.html"
OUTPUT_DIR = ROOT / "output"


def money(value: Decimal, currency: str) -> str:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{currency} {quantized:,.2f}"


def load_data(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def detect_next_number() -> int:
    highest = 0

    if not OUTPUT_DIR.exists():
        return 1

    for path in OUTPUT_DIR.iterdir():
        if path.is_dir():
            continue

        match = re.search(r"invoice-(\d+)$", path.stem, re.IGNORECASE)
        if match:
            highest = max(highest, int(match.group(1)))

    return highest + 1 if highest else 1


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a standardized invoice HTML file.")
    parser.add_argument("--data", required=True, help="Path to the JSON data file.")
    parser.add_argument("--number", type=int, help="Invoice sequence number. Defaults to the next detected number.")
    parser.add_argument("--dry-run", action="store_true", help="Preview the next invoice number and output path without writing files.")
    args = parser.parse_args()

    data = load_data(Path(args.data))
    invoice_number = args.number if args.number is not None else detect_next_number()
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
    output_path = OUTPUT_DIR / f"invoice-{invoice_number:04d}.html"

    if args.dry_run:
        print(f"invoice_number={invoice_number:04d}")
        print(f"output_path={output_path}")
        print(f"total={money(total, currency)}")
        return

    output_path.write_text(rendered, encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()

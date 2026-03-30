import json
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

import generate_invoice
import prepare_weekly_invoice


def example_data() -> dict:
    return {
        "seller_name": "Alex Carter",
        "seller_legal_name": "Northwind Digital Services LLC",
        "seller_tax_id": "Tax ID / Document: 11.222.333/0001-44",
        "seller_address_line1": "128 Market Street",
        "seller_address_line2": "Austin, TX 78701",
        "seller_email": "alex.carter@example.com",
        "client_name": "Blue Ridge Hospitality Group",
        "client_department": "Accounts Payable",
        "client_address_line1": "450 West Harbor Blvd",
        "client_address_line2": "Tampa, FL 33602",
        "client_email": "ap@blueridge.example.com",
        "issue_date": "2026-03-18",
        "due_date": "2026-03-25",
        "currency": "USD",
        "notes": "Consulting and software development services.",
        "tax": 0,
        "items": [
            {
                "description": "Software consulting and development services.",
                "quantity": 40,
                "unit_price": 80.0,
            }
        ],
    }


class InvoiceGeneratorTests(unittest.TestCase):
    def test_build_items_rows_returns_expected_subtotal(self) -> None:
        rows, subtotal = generate_invoice.build_items_rows(example_data()["items"], "USD")
        self.assertIn("USD 3,200.00", rows)
        self.assertEqual(subtotal, Decimal("3200.0"))

    def test_validate_data_rejects_missing_field(self) -> None:
        data = example_data()
        del data["client_email"]

        with self.assertRaisesRegex(ValueError, "Missing required fields: client_email"):
            generate_invoice.validate_data(data)

    def test_validate_data_rejects_invalid_quantity(self) -> None:
        data = example_data()
        data["items"][0]["quantity"] = 0

        with self.assertRaisesRegex(ValueError, "items\\[1\\]\\.quantity"):
            generate_invoice.validate_data(data)

    def test_next_invoice_number_uses_output_when_sequence_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "output"
            output_dir.mkdir()
            (output_dir / "invoice-0003.pdf").write_text("", encoding="utf-8")
            (output_dir / "invoice-0007.html").write_text("", encoding="utf-8")

            next_number = generate_invoice.next_invoice_number(
                sequence_path=root / "sequence.txt",
                output_dir=output_dir,
            )

            self.assertEqual(next_number, 8)

    def test_read_sequence_value_prefers_sequence_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "output"
            output_dir.mkdir()
            (output_dir / "invoice-0009.pdf").write_text("", encoding="utf-8")
            (root / "sequence.txt").write_text("12\n", encoding="utf-8")

            value = generate_invoice.read_sequence_value(
                sequence_path=root / "sequence.txt",
                output_dir=output_dir,
            )

            self.assertEqual(value, 12)

    def test_read_sequence_value_rejects_invalid_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sequence_path = root / "sequence.txt"
            sequence_path.write_text("abc\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "sequence.txt must contain an integer"):
                generate_invoice.read_sequence_value(sequence_path=sequence_path, output_dir=root / "output")

    def test_generate_invoice_document_dry_run_returns_paths_and_total(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            result = generate_invoice.generate_invoice_document(
                example_data(),
                invoice_number=12,
                dry_run=True,
                output_dir=root / "output",
                sequence_path=root / "sequence.txt",
            )

            self.assertEqual(result["invoice_number"], 12)
            self.assertEqual(result["pdf_path"], root / "output" / "invoice-0012.pdf")
            self.assertEqual(result["total"], "USD 3,200.00")

    def test_previous_workweek_returns_previous_monday_and_friday(self) -> None:
        start_date, end_date = prepare_weekly_invoice.previous_workweek(date(2026, 3, 30))
        self.assertEqual(start_date.isoformat(), "2026-03-23")
        self.assertEqual(end_date.isoformat(), "2026-03-27")

    def test_format_period_label_uses_single_month_format(self) -> None:
        label = prepare_weekly_invoice.format_period_label(date(2026, 3, 16), date(2026, 3, 20))
        self.assertEqual(label, "March 16 to 20")

    def test_greeting_for_hour_changes_after_noon(self) -> None:
        self.assertEqual(prepare_weekly_invoice.greeting_for_hour(9), "Good morning")
        self.assertEqual(prepare_weekly_invoice.greeting_for_hour(15), "Good afternoon")

    def test_build_weekly_invoice_data_updates_dates_and_description(self) -> None:
        invoice_data, context = prepare_weekly_invoice.build_weekly_invoice_data(
            example_data(),
            reference_date=date(2026, 3, 30),
            due_days=7,
            hours="40",
            description_template="Services provided from {start_date} to {end_date} totaling {hours} hours.",
        )

        self.assertEqual(invoice_data["issue_date"], "2026-03-30")
        self.assertEqual(invoice_data["due_date"], "2026-04-06")
        self.assertEqual(invoice_data["items"][0]["quantity"], "40")
        self.assertEqual(
            invoice_data["items"][0]["description"],
            "Services provided from 2026-03-23 to 2026-03-27 totaling 40 hours.",
        )
        self.assertEqual(context["seller_name"], "Alex Carter")
        self.assertEqual(context["recipient_name"], "Amy")
        self.assertEqual(context["sender_display_name"], "Paulo Oliveira")
        self.assertEqual(context["signature_name"], "Paulo")

    def test_parse_recipients_supports_commas_and_semicolons(self) -> None:
        recipients = prepare_weekly_invoice.parse_recipients(
            "first@example.com, second@example.com; third@example.com"
        )
        self.assertEqual(
            recipients,
            ["first@example.com", "second@example.com", "third@example.com"],
        )

    def test_format_outlook_body_wraps_paragraphs_in_html(self) -> None:
        body = "Good morning, Amy!\n\nAttached is invoice 0006.\n\nThank you,\nPaulo"
        formatted = prepare_weekly_invoice.format_outlook_body(body)
        self.assertIn("<div style='margin:0; padding:0;'>", formatted)
        self.assertIn("Good morning, Amy!", formatted)
        self.assertIn("Thank you,<br>Paulo", formatted)


if __name__ == "__main__":
    unittest.main()

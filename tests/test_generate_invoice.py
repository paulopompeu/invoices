import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import generate_invoice


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


if __name__ == "__main__":
    unittest.main()

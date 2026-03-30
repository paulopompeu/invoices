#!/usr/bin/env python3

import argparse
import copy
import html
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import generate_invoice


DEFAULT_DESCRIPTION_TEMPLATE = (
    "Software consulting and development services provided from "
    "{start_date} to {end_date}, totaling {hours} hours for the week."
)
DEFAULT_EMAIL_SUBJECT_TEMPLATE = "Contractor - {sender_display_name} - {period_label} (Invoice)"
DEFAULT_EMAIL_BODY_TEMPLATE = """{greeting}, {recipient_name}!

Attached is invoice {invoice_number} for the hours worked from {start_date} to {end_date}.

Thank you,
{signature_name}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a weekly invoice and prepare an Outlook draft without sending it."
    )
    parser.add_argument("--data", required=True, help="Path to the base JSON data file.")
    parser.add_argument(
        "--reference-date",
        help="Reference date in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument(
        "--due-days",
        type=int,
        default=7,
        help="Days to add to the issue date when calculating due_date. Defaults to 7.",
    )
    parser.add_argument(
        "--hours",
        type=str,
        help="Hours for the week. Defaults to the quantity from the first item in the base JSON.",
    )
    parser.add_argument(
        "--description-template",
        default=DEFAULT_DESCRIPTION_TEMPLATE,
        help="Template for the first invoice item description.",
    )
    parser.add_argument(
        "--email-subject-template",
        default=DEFAULT_EMAIL_SUBJECT_TEMPLATE,
        help="Template for the Outlook draft subject.",
    )
    parser.add_argument(
        "--email-body-template",
        default=DEFAULT_EMAIL_BODY_TEMPLATE,
        help="Template for the Outlook draft body.",
    )
    parser.add_argument(
        "--recipient",
        help="Override the destination email. Defaults to client_email from the base JSON.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the generated period, invoice path, and draft content without writing files.",
    )
    return parser.parse_args()


def resolve_reference_date(raw_value: str | None) -> date:
    if raw_value is None:
        return date.today()
    return datetime.strptime(raw_value, "%Y-%m-%d").date()


def previous_workweek(reference_date: date) -> tuple[date, date]:
    monday_of_current_week = reference_date - timedelta(days=reference_date.weekday())
    monday_of_previous_week = monday_of_current_week - timedelta(days=7)
    friday_of_previous_week = monday_of_previous_week + timedelta(days=4)
    return monday_of_previous_week, friday_of_previous_week


def build_template_context(
    base_data: dict,
    start_date: date,
    end_date: date,
    issue_date: date,
    due_date: date,
    hours: str,
) -> dict[str, str]:
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "issue_date": issue_date.isoformat(),
        "due_date": due_date.isoformat(),
        "hours": str(hours),
        "period_label": format_period_label(start_date, end_date),
        "seller_name": str(base_data["seller_name"]),
        "client_name": str(base_data["client_name"]),
        "recipient_name": str(base_data.get("client_contact_name", "Amy")),
        "sender_display_name": str(base_data.get("seller_display_name", "Paulo Oliveira")),
        "signature_name": str(base_data.get("seller_signature_name", "Paulo")),
    }


def normalize_invoice_number(invoice_number: int) -> str:
    return f"{invoice_number:04d}"


def format_period_label(start_date: date, end_date: date) -> str:
    start_month = start_date.strftime("%B")
    end_month = end_date.strftime("%B")
    if start_date.year == end_date.year and start_date.month == end_date.month:
        return f"{start_month} {start_date.day} to {end_date.day}"
    return f"{start_month} {start_date.day} to {end_month} {end_date.day}"


def greeting_for_hour(hour: int) -> str:
    return "Good morning" if hour < 12 else "Good afternoon"


def parse_recipients(raw_value: str) -> list[str]:
    recipients = [part.strip() for part in raw_value.replace(";", ",").split(",")]
    return [recipient for recipient in recipients if recipient]


def format_outlook_body(body: str) -> str:
    normalized_body = body.replace("\r\n", "\n").replace("\r", "\n").strip()
    paragraphs = normalized_body.split("\n\n")
    escaped_paragraphs = [html.escape(paragraph).replace("\n", "<br>") for paragraph in paragraphs]
    html_paragraphs = [f"<div style='margin:0 0 12px 0;'>{paragraph}</div>" for paragraph in escaped_paragraphs]
    return "<div style='margin:0; padding:0;'>" + "".join(html_paragraphs) + "</div>"


def build_weekly_invoice_data(
    base_data: dict,
    *,
    reference_date: date,
    due_days: int,
    hours: str | None,
    description_template: str,
) -> tuple[dict, dict[str, str]]:
    start_date, end_date = previous_workweek(reference_date)
    issue_date = reference_date
    due_date = reference_date + timedelta(days=due_days)

    invoice_data = copy.deepcopy(base_data)
    first_item = invoice_data["items"][0]
    resolved_hours = str(hours if hours is not None else first_item["quantity"])
    context = build_template_context(base_data, start_date, end_date, issue_date, due_date, resolved_hours)

    first_item["quantity"] = resolved_hours
    first_item["description"] = description_template.format(**context)
    invoice_data["issue_date"] = context["issue_date"]
    invoice_data["due_date"] = context["due_date"]

    return invoice_data, context


def create_outlook_draft(recipients: list[str], subject: str, body: str, attachment_path: Path) -> None:
    applescript = """
on run argv
    set recipientCount to (count of argv) - 3
    set recipientEmails to items 1 thru recipientCount of argv
    set subjectLine to item (recipientCount + 1) of argv
    set messageBody to item (recipientCount + 2) of argv
    set attachmentPath to item (recipientCount + 3) of argv

    tell application "Microsoft Outlook"
        set newMessage to make new outgoing message with properties {subject:subjectLine, content:messageBody}
        repeat with recipientEmail in recipientEmails
            make new recipient at newMessage with properties {email address:{address:(recipientEmail as text)}}
        end repeat
        make new attachment at newMessage with properties {file:POSIX file attachmentPath}
        open newMessage
    end tell
end run
""".strip()
    subprocess.run(
        ["osascript", "-e", applescript, *recipients, subject, format_outlook_body(body), str(attachment_path)],
        check=True,
    )


def main() -> None:
    args = parse_args()

    try:
        base_data = generate_invoice.validate_data(generate_invoice.load_data(Path(args.data)))
        reference_date = resolve_reference_date(args.reference_date)
        invoice_number = generate_invoice.next_invoice_number()
        invoice_data, context = build_weekly_invoice_data(
            base_data,
            reference_date=reference_date,
            due_days=args.due_days,
            hours=args.hours,
            description_template=args.description_template,
        )
        result = generate_invoice.generate_invoice_document(
            invoice_data,
            invoice_number=invoice_number,
            dry_run=args.dry_run,
        )
    except FileNotFoundError:
        print(f"Error: Data file not found: {args.data}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    recipient_value = args.recipient or str(invoice_data["client_email"])
    recipients = parse_recipients(recipient_value)
    if not recipients:
        print("Error: no recipient email addresses were provided.", file=sys.stderr)
        sys.exit(1)

    email_context = {
        **context,
        "invoice_number": normalize_invoice_number(result["invoice_number"]),
        "greeting": greeting_for_hour(datetime.now().hour),
    }
    subject = args.email_subject_template.format(**email_context)
    body = args.email_body_template.format(**email_context)

    if args.dry_run:
        print(f"period_start={context['start_date']}")
        print(f"period_end={context['end_date']}")
        print(f"invoice_number={result['invoice_number']:04d}")
        print(f"output_path={result['pdf_path']}")
        print(f"recipients={', '.join(recipients)}")
        print(f"subject={subject}")
        print("body_start")
        print(body.rstrip())
        print("body_end")
        return

    try:
        create_outlook_draft(recipients, subject, body, Path(result["pdf_path"]))
    except subprocess.CalledProcessError as exc:
        print(f"Error: failed to create Outlook draft ({exc}).", file=sys.stderr)
        sys.exit(1)

    print(result["pdf_path"])
    print(f"Draft created in Outlook for {', '.join(recipients)}.")


if __name__ == "__main__":
    main()

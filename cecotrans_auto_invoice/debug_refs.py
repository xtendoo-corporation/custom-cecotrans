# Script to find invoices with CE prefix
env = self.env
invoices = env["account.move"].search(
    [
        ("move_type", "=", "in_invoice"),
        ("state", "!=", "cancel"),
        ("ref", "like", "CE/%"),
    ],
    order="ref desc",
    limit=20,
)

print(f"Found {len(invoices)} invoices:")
for inv in invoices:
    print(f"ID: {inv.id} - Ref: {inv.ref} - Date: {inv.date}")

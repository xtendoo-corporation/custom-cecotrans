# Copyright 2022 Xtendoo

{
    "name": "Cecotrans Auto Invoice",
    "summary": """
        Cecotrans Auto Invoice""",
    "version": "18.0.1.0.0",
    "depends": [
        "base",
        "account",
        "cecotrans_vendor_bill_import",
    ],
    "maintainers": [
        "Daniel Domínguez",
    ],
    "author": "Xtendoo",
    "license": "AGPL-3",
    "data": [
        "views/partner_view.xml",
    ],
    "application": True,
    "installable": True,
    "auto_install": True,
}

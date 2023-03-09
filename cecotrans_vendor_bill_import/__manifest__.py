# Copyright 2022 Xtendoo

{
    "name": "Cecotrans Vendor Bill Import",
    "summary": """
        Cecotrans Vendor Bill Import""",
    "version": "15.0.1.0.0",
    "depends": [
        "account",
        "mass_mailing",
    ],
    "maintainers": [
        "Daniel Domínguez",
    ],
    "author": "Xtendoo",
    "license": "AGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "wizard/vendor_bill_import_wizard.xml",
        "views/vendor_bill_import_view.xml"
    ],
    "application": True,
    "installable": True,
    "auto_install": True,
}

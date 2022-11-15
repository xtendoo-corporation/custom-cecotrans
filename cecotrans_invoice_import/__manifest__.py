# Copyright 2022 Xtendoo

{
    "name": "Cecotrans Invoice Import",
    "summary": """
        Cecotrans Invoice Import""",
    "version": "15.0.1.0.0",
    "depends": [
        "account",
        "mass_mailing",
    ],
    "maintainers": [
        "manuelcalerosolis",
    ],
    "author": "Xtendoo",
    "license": "AGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "wizard/invoice_import_wizard.xml",
        "views/invoice_import_view.xml"
    ],
    "application": True,
    "installable": True,
    "auto_install": True,
}

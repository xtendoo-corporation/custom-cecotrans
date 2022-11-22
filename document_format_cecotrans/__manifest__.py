{
    "name": "Document Format Cecotrans",
    "summary": """Formatos de documentos de Cecotrans""",
    "version": "15.0.1.0.0",
    "description": """Formatos de documentos de Cecotrans""",
    "author": "Daniel Dominguez",
    "company": "Xtendoo",
    "website": "http://xtendoo.es",
    "category": "Extra Tools",
    "license": "AGPL-3",
    "depends": [
        "base",
        "web"
    ],
    "data": [
        "views/layout/external_layout_clean.xml",
        "views/sale/sale_order_views.xml",
        "views/purchase/purchase_order_views.xml",
        "views/purchase/purchase_quotation_views.xml",
        "views/stock/report_picking_views.xml",
        "views/stock/report_delivery_document.xml",
        "views/invoice/report_invoice_document.xml",
    ],
    "installable": True,
    "auto_install": False,
}

from django.core.management.base import BaseCommand
from labels.models import LabelTemplate, LabelField

# ---- helpers ---------------------------------------------------------------

def default_schema_for(name: str):
    """
    Return a simple pixel-based layout (works with 300 DPI and our preview).
    You can tweak these positions/sizes later.
    """
    if "Type 1" in name:
        return {"elements": [
            {"id":"logo","type":"image","x":8,"y":8,"w":80,"h":40,"dataKey":"logo_image"},
            {"id":"pname","type":"text","x":100,"y":10,"w":220,"h":20,"fontSize":14,"dataKey":"product_name"},
            {"id":"sku","type":"text","x":100,"y":32,"w":220,"h":18,"fontSize":12,"dataKey":"sku"},
            {"id":"cat","type":"text","x":100,"y":52,"w":220,"h":16,"fontSize":11,"dataKey":"category"},
            {"id":"ptype","type":"text","x":100,"y":70,"w":220,"h":16,"fontSize":11,"dataKey":"product_type"},
            {"id":"comp","type":"text","x":8,"y":96,"w":220,"h":16,"fontSize":11,"dataKey":"company_name"},
            {"id":"addr","type":"text","x":8,"y":114,"w":240,"h":28,"fontSize":10,"dataKey":"company_address"},
            {"id":"cont","type":"text","x":8,"y":146,"w":240,"h":16,"fontSize":10,"dataKey":"contact_details"},
            {"id":"code","type":"barcode","x":260,"y":96,"w":140,"h":60,"dataKey":"code_value"},
        ]}
    if "Type 2" in name:
        return {"elements": [
            {"id":"pname","type":"text","x":8,"y":10,"w":260,"h":20,"fontSize":14,"dataKey":"product_name"},
            {"id":"sku","type":"text","x":8,"y":34,"w":260,"h":18,"fontSize":12,"dataKey":"sku"},
            {"id":"cat","type":"text","x":8,"y":54,"w":260,"h":16,"fontSize":11,"dataKey":"category"},
            {"id":"ptype","type":"text","x":8,"y":72,"w":260,"h":16,"fontSize":11,"dataKey":"product_type"},
            {"id":"comp","type":"text","x":8,"y":96,"w":220,"h":16,"fontSize":11,"dataKey":"company_name"},
            {"id":"addr","type":"text","x":8,"y":114,"w":240,"h":28,"fontSize":10,"dataKey":"company_address"},
            {"id":"cont","type":"text","x":8,"y":146,"w":240,"h":16,"fontSize":10,"dataKey":"contact_details"},
            {"id":"code","type":"qrcode","x":260,"y":96,"w":60,"h":60,"dataKey":"code_value"},
        ]}
    if "Type 3" in name:
        return {"elements": [
            {"id":"logo","type":"image","x":8,"y":8,"w":80,"h":40,"dataKey":"logo_image"},
            {"id":"pimg","type":"image","x":8,"y":54,"w":100,"h":100,"dataKey":"product_image"},
            {"id":"pname","type":"text","x":120,"y":10,"w":240,"h":22,"fontSize":14,"dataKey":"product_name"},
            {"id":"sku","type":"text","x":120,"y":34,"w":240,"h":18,"fontSize":12,"dataKey":"sku"},
            {"id":"cat","type":"text","x":120,"y":56,"w":240,"h":16,"fontSize":11,"dataKey":"category"},
            {"id":"ptype","type":"text","x":120,"y":74,"w":240,"h":16,"fontSize":11,"dataKey":"product_type"},
            {"id":"comp","type":"text","x":120,"y":100,"w":220,"h":16,"fontSize":11,"dataKey":"company_name"},
            {"id":"addr","type":"text","x":120,"y":120,"w":240,"h":28,"fontSize":10,"dataKey":"company_address"},
            {"id":"cont","type":"text","x":120,"y":152,"w":240,"h":16,"fontSize":10,"dataKey":"contact_details"},
            {"id":"code","type":"barcode","x":300,"y":100,"w":140,"h":60,"dataKey":"code_value"},
        ]}
    return {"elements": []}

PREMADE = [
    {
        "name": "Type 1: Logo + Full Details + Code",
        "size": (50.0, 30.0),
        "fields": [
            {"name": "Logo Image", "key": "logo_image", "type": "IMAGE"},
            {"name": "Product Name", "key": "product_name", "type": "TEXT"},
            {"name": "SKU Number", "key": "sku", "type": "TEXT"},
            {"name": "Category", "key": "category", "type": "TEXT"},
            {"name": "Product Type", "key": "product_type", "type": "TEXT"},
            {"name": "Company Name", "key": "company_name", "type": "TEXT"},
            {"name": "Company Address", "key": "company_address", "type": "TEXT"},
            {"name": "Contact Details", "key": "contact_details", "type": "TEXT"},
            {"name": "Code Value", "key": "code_value", "type": "TEXT", "required": True},
            {"name": "Code Type", "key": "code_type", "type": "TEXT", "required": True},
        ],
    },
    {
        "name": "Type 2: No Logo + Full Details + Code",
        "size": (50.0, 30.0),
        "fields": [
            {"name": "Product Name", "key": "product_name", "type": "TEXT"},
            {"name": "SKU Number", "key": "sku", "type": "TEXT"},
            {"name": "Category", "key": "category", "type": "TEXT"},
            {"name": "Product Type", "key": "product_type", "type": "TEXT"},
            {"name": "Company Name", "key": "company_name", "type": "TEXT"},
            {"name": "Company Address", "key": "company_address", "type": "TEXT"},
            {"name": "Contact Details", "key": "contact_details", "type": "TEXT"},
            {"name": "Code Value", "key": "code_value", "type": "TEXT", "required": True},
            {"name": "Code Type", "key": "code_type", "type": "TEXT", "required": True},
        ],
    },
    {
        "name": "Type 3: Logo + Product Image + Full Details + Code",
        "size": (50.0, 50.0),
        "fields": [
            {"name": "Logo Image", "key": "logo_image", "type": "IMAGE"},
            {"name": "Product Image", "key": "product_image", "type": "IMAGE"},
            {"name": "Product Name", "key": "product_name", "type": "TEXT"},
            {"name": "SKU Number", "key": "sku", "type": "TEXT"},
            {"name": "Category", "key": "category", "type": "TEXT"},
            {"name": "Product Type", "key": "product_type", "type": "TEXT"},
            {"name": "Company Name", "key": "company_name", "type": "TEXT"},
            {"name": "Company Address", "key": "company_address", "type": "TEXT"},
            {"name": "Contact Details", "key": "contact_details", "type": "TEXT"},
            {"name": "Code Value", "key": "code_value", "type": "TEXT", "required": True},
            {"name": "Code Type", "key": "code_type", "type": "TEXT", "required": True},
        ],
    },
]

# ---- command ---------------------------------------------------------------

class Command(BaseCommand):
    help = "Seed global premade label templates (Type 1/2/3)."

    def handle(self, *args, **options):
        created = 0
        updated_schema = 0

        for spec in PREMADE:
            name = spec["name"]
            width_mm, height_mm = spec["size"]

            tmpl, was_created = LabelTemplate.objects.get_or_create(
                workspace=None,
                name=name,
                kind=LabelTemplate.Kind.PREMADE,
                defaults={
                    "width_mm": width_mm,
                    "height_mm": height_mm,
                    "dpi": 300,
                    "schema": {"elements": []},
                },
            )

            # Always ensure the schema exists/updated
            new_schema = default_schema_for(name)
            if tmpl.schema != new_schema:
                tmpl.schema = new_schema
                tmpl.save(update_fields=["schema"])
                updated_schema += 1

            if was_created:
                created += 1
                # Create fields once
                for order, f in enumerate(spec["fields"]):
                    field_type = {"TEXT": "TEXT", "IMAGE": "IMAGE", "CODE": "CODE"}.get(f["type"], "TEXT")
                    LabelField.objects.create(
                        template=tmpl,
                        name=f["name"],
                        key=f["key"],
                        field_type=field_type,
                        code_format=LabelField.CodeFormat.NONE,
                        required=f.get("required", True),
                        sort_order=order,
                    )

        self.stdout.write(self.style.SUCCESS(
            f"Premade templates created={created}, schemas updated={updated_schema}"
        ))

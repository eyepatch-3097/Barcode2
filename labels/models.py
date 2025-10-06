# labels/models.py
from django.db import models
from django.conf import settings
from workspaces.models import Workspace

class LabelTemplate(models.Model):
    class Kind(models.TextChoices):
        PREMADE = "PREMADE", "Premade"
        CUSTOM = "CUSTOM", "Custom"

    # Premade: workspace=NULL; Custom: workspace=<current>
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="label_templates",
        null=True, blank=True
    )
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.CUSTOM)

    width_mm = models.FloatField(default=50.0)
    height_mm = models.FloatField(default=30.0)
    dpi = models.PositiveIntegerField(default=300)

    # Canvas schema for custom editor (premade can be empty)
    schema = models.JSONField(default=dict, blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name}"

class LabelField(models.Model):
    class FieldType(models.TextChoices):
        TEXT = "TEXT", "Text"
        IMAGE = "IMAGE", "Image"
        CODE = "CODE", "Code"

    class CodeFormat(models.TextChoices):
        BARCODE = "BARCODE", "Barcode"
        QRCODE = "QRCODE", "QR Code"
        NONE = "NONE", "None"  # for non-code fields

    template = models.ForeignKey(LabelTemplate, on_delete=models.CASCADE, related_name="fields")
    name = models.CharField(max_length=120)   # UI label, e.g. "Product Name"
    key = models.CharField(max_length=120)    # data key, e.g. "product_name"
    field_type = models.CharField(max_length=8, choices=FieldType.choices, default=FieldType.TEXT)
    code_format = models.CharField(max_length=8, choices=CodeFormat.choices, default=CodeFormat.NONE)
    required = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.template.name} · {self.name}"

class LabelInstance(models.Model):
    # Phase 2 usage — created now so DB is ready
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="generated_labels")
    template = models.ForeignKey(LabelTemplate, on_delete=models.PROTECT, related_name="generated_instances")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    data = models.JSONField()  # actual values used to render this label
    pdf_path = models.CharField(max_length=255, blank=True)
    png_path = models.CharField(max_length=255, blank=True)

    def __str__(self):
        sku = self.data.get("sku") if isinstance(self.data, dict) else None
        return f"{self.template.name} · {sku or 'label'}"

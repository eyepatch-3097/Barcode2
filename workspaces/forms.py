# workspaces/forms.py
from django import forms
from django.utils.text import slugify

class WorkspaceCreateForm(forms.Form):
    name = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Design, Ops, Seasonal Labels"})
    )

    def clean(self):
        cleaned = super().clean()
        name = cleaned.get("name", "").strip()
        if not name:
            self.add_error("name", "Name is required.")
        cleaned["slug"] = slugify(name) or "workspace"
        return cleaned

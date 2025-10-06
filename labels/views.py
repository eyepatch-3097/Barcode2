# labels/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.contrib import messages
import csv, io, json, os, uuid
from django.conf import settings
from workspaces.models import Workspace
from organizations.models import Membership
from .models import LabelTemplate, LabelField, LabelInstance
from .utils import render_label_to_image
from django.db import models

def _current_workspace(request):
    ws_id = request.session.get("current_workspace_id")
    if not ws_id:
        return None
    try:
        return Workspace.objects.select_related("organization").get(id=ws_id)
    except Workspace.DoesNotExist:
        return None

@login_required
def generate_choose_template(request):
    ws = _current_workspace(request)
    if not ws: return redirect("workspaces:choose")
    # show premade + your custom
    templates = LabelTemplate.objects.filter(is_active=True).filter(
        models.Q(workspace__isnull=True) | models.Q(workspace=ws)
    ).order_by("kind","name")
    return render(request, "labels/generate_choose.html", {"workspace": ws, "templates": templates})

@login_required
def generate_single(request, pk: int):
    ws = _current_workspace(request)
    if not ws: return redirect("workspaces:choose")
    tmpl = get_object_or_404(LabelTemplate, id=pk, is_active=True)

    # Build form field list (TEXT + IMAGE from fields or schema)
    field_defs = []
    fields_qs = tmpl.fields.order_by("sort_order")
    if fields_qs.exists():
        for f in fields_qs:
            if f.field_type in ("TEXT","IMAGE"):
                field_defs.append({"key":f.key, "name":f.name, "type":f.field_type})
    else:
        # derive from schema for custom
        for el in (tmpl.schema or {}).get("elements", []):
            if el.get("type") in ("text","image"):
                key = (el.get("dataKey") or "").strip()
                if key:
                    field_defs.append({"key":key, "name":key.replace("_"," ").title(),
                                       "type":"IMAGE" if el.get("type")=="image" else "TEXT"})

    # Sort & dedupe by key
    seen, deduped = set(), []
    for f in field_defs:
        if f["key"] not in seen:
            deduped.append(f); seen.add(f["key"])
    field_defs = deduped

    if request.method == "POST":
        payload = {}
        for f in field_defs:
            payload[f["key"]] = (request.POST.get(f["key"]) or "").strip()

        # Code options
        code_type = (request.POST.get("code_type") or "BARCODE").upper()
        code_value = (request.POST.get("code_value") or "") or payload.get("sku") or "CODE"
        # Make available to renderer with the keys your schema expects
        payload["code_value"] = code_value
        if code_type == "QRCODE":
            # If schema has barcode element but user chose QR, keep value; preview will still show barcode/qr per schema
            pass

        # Render & save
        img = render_label_to_image(tmpl, payload)

        # Persist instance
        instance = LabelInstance.objects.create(
            workspace=ws, template=tmpl, created_by=request.user, data=payload
        )
        out_dir = os.path.join(settings.MEDIA_ROOT, "labels", str(ws.id), "instances")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{instance.id}.png")
        img.save(out_path, "PNG")
        instance.png_path = os.path.relpath(out_path, settings.MEDIA_ROOT).replace("\\","/")
        instance.save(update_fields=["png_path"])

        messages.success(request, "Label generated.")
        return render(request, "labels/generate_result.html", {"instance": instance, "template": tmpl})

    return render(request, "labels/generate_single.html", {
        "template": tmpl,
        "field_defs": field_defs,
    })

@login_required
def design_home(request):
    ws = _current_workspace(request)
    if not ws:
        return redirect("workspaces:choose")

    premade = LabelTemplate.objects.filter(kind=LabelTemplate.Kind.PREMADE, is_active=True).order_by("name")
    yours = LabelTemplate.objects.filter(workspace=ws, kind=LabelTemplate.Kind.CUSTOM, is_active=True).order_by("-updated_at")
    return render(request, "labels/design_home.html", {"workspace": ws, "premade": premade, "yours": yours})

@login_required
def template_list(request):
    ws = _current_workspace(request)
    if not ws:
        return redirect("workspaces:choose")
    templates = LabelTemplate.objects.filter(workspace=ws, kind=LabelTemplate.Kind.CUSTOM, is_active=True).order_by("-updated_at")
    return render(request, "labels/template_list.html", {"workspace": ws, "templates": templates})

@login_required
def template_create(request):
    ws = _current_workspace(request)
    if not ws:
        return redirect("workspaces:choose")
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        width_mm = float(request.POST.get("width_mm") or 50)
        height_mm = float(request.POST.get("height_mm") or 30)
        dpi = int(request.POST.get("dpi") or 300)
        if not name:
            messages.error(request, "Template name is required.")
            return redirect("labels:template_create")
        tmpl = LabelTemplate.objects.create(
            workspace=ws, name=name, kind=LabelTemplate.Kind.CUSTOM,
            width_mm=width_mm, height_mm=height_mm, dpi=dpi,
            schema={"elements": []}, created_by=request.user
        )
        messages.success(request, "Template created. You can now design it.")
        return redirect("labels:template_editor", pk=tmpl.id)
    return render(request, "labels/template_create.html", {"workspace": ws})

@login_required
def template_editor(request, pk: int):
    ws = _current_workspace(request)
    tmpl = get_object_or_404(LabelTemplate, id=pk, is_active=True)
    # ensure workspace ownership for custom templates
    if tmpl.kind == LabelTemplate.Kind.CUSTOM and tmpl.workspace_id != (ws.id if ws else None):
        return redirect("workspaces:choose")
    return render(request, "labels/template_editor.html", {"workspace": ws, "template": tmpl})

@login_required
def template_save_schema(request, pk: int):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    ws = _current_workspace(request)
    tmpl = get_object_or_404(LabelTemplate, id=pk, is_active=True)
    if tmpl.kind == LabelTemplate.Kind.CUSTOM and tmpl.workspace_id != (ws.id if ws else None):
        return JsonResponse({"ok": False, "error": "No access"}, status=403)
    elements = request.POST.get("elements_json")
    if not elements:
        return JsonResponse({"ok": False, "error": "Missing schema"}, status=400)
    try:
        parsed = json.loads(elements)
        if not isinstance(parsed, list):
            return JsonResponse({"ok": False, "error": "Invalid schema"}, status=400)
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"Bad JSON: {e}"}, status=400)
    tmpl.schema = {"elements": parsed}
    tmpl.save(update_fields=["schema", "updated_at"])
    return JsonResponse({"ok": True})

@login_required
def template_preview(request, pk: int):
    # A simple “sample” view: list fields + show size/dpi. (Visual canvas preview for premade is simple here)
    tmpl = get_object_or_404(LabelTemplate, id=pk, is_active=True)
    fields = tmpl.fields.order_by("sort_order")
    return render(request, "labels/template_preview.html", {"template": tmpl, "fields": fields})

@login_required
def template_csv(request, pk: int):
    tmpl = get_object_or_404(LabelTemplate, id=pk, is_active=True)

    headers = []
    fields_qs = tmpl.fields.order_by("sort_order")
    if fields_qs.exists():
        # Premade: use structured fields, exclude CODE
        for f in fields_qs:
            if f.field_type != "CODE":
                headers.append(f.key)
    else:
        # Custom: derive from schema elements (TEXT & IMAGE, with dataKey)
        schema = tmpl.schema or {}
        for el in (schema.get("elements") or []):
            if el.get("type") in ("text","image"):
                key = (el.get("dataKey") or "").strip()
                if key:
                    headers.append(key)

    headers = list(dict.fromkeys(headers))  # dedupe, preserve order
    if not headers:
        headers = ["example_field"]  # fallback so CSV isn't empty

    buff = io.StringIO()
    writer = csv.writer(buff)
    writer.writerow(headers)

    resp = HttpResponse(buff.getvalue(), content_type="text/csv")
    safe_name = tmpl.name.lower().replace(" ", "_")
    resp["Content-Disposition"] = f'attachment; filename="{safe_name}_format.csv"'
    return resp

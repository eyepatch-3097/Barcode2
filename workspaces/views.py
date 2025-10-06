from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from organizations.models import Membership
from .models import Workspace, WorkspaceAccess
from django.contrib import messages
from .forms import WorkspaceCreateForm

@login_required
def choose_workspace(request):
    # all ACTIVE memberships for this user
    memberships = Membership.objects.filter(user=request.user, status=Membership.Status.ACTIVE)\
                                    .select_related("organization")
    # workspaces the user can access (via WorkspaceAccess)
    access_qs = WorkspaceAccess.objects.filter(membership__in=memberships)\
                                       .select_related("workspace", "workspace__organization", "membership")
    # group by org for display
    org_map = {}
    for acc in access_qs:
        org = acc.workspace.organization
        org_map.setdefault(org, []).append(acc.workspace)

    faq = [
        "Choose the workspace you want to work in.",
        "Admins can create more workspaces from the workspace settings (coming soon).",
        "If you don't see a workspace, ask your org admin to grant access.",
    ]
    return render(request, "workspaces/choose.html", {"org_map": org_map, "faq": faq})

@login_required
def select_workspace(request, workspace_id: int):
    ws = get_object_or_404(Workspace, id=workspace_id)
    # ensure user has access
    has_access = WorkspaceAccess.objects.filter(
        membership__user=request.user,
        membership__organization=ws.organization,
        membership__status=Membership.Status.ACTIVE,
        workspace=ws
    ).exists()
    if not has_access:
        return redirect("workspaces:choose")

    request.session["current_workspace_id"] = ws.id
    # after selecting, go to dashboard (for now)
    return redirect("accounts:post_login")

def _current_workspace(request):
    ws_id = request.session.get("current_workspace_id")
    if not ws_id:
        return None
    try:
        return Workspace.objects.select_related("organization").get(id=ws_id)
    except Workspace.DoesNotExist:
        return None

@login_required
def create_workspace(request):
    # Must be ADMIN in the current org
    current_ws = _current_workspace(request)
    if not current_ws:
        return redirect("workspaces:choose")
    org = current_ws.organization

    is_admin = Membership.objects.filter(
        user=request.user, organization=org, role=Membership.Role.ADMIN, status=Membership.Status.ACTIVE
    ).exists()
    if not is_admin:
        messages.error(request, "Only org admins can create workspaces.")
        return redirect("workspaces:choose")

    if request.method == "POST":
        form = WorkspaceCreateForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            slug = form.cleaned_data["slug"]
            # Ensure unique per org
            if Workspace.objects.filter(organization=org, slug=slug).exists():
                form.add_error("name", "A workspace with a similar name already exists.")
            else:
                ws = Workspace.objects.create(
                    organization=org, name=name, slug=slug, created_by=request.user
                )
                # Give all ACTIVE ADMINS access automatically (and the creator for sure)
                admin_memberships = Membership.objects.filter(
                    organization=org, role=Membership.Role.ADMIN, status=Membership.Status.ACTIVE
                )
                for m in admin_memberships:
                    WorkspaceAccess.objects.get_or_create(membership=m, workspace=ws)
                messages.success(request, f'Workspace "{name}" created.')
                return redirect("workspaces:access", workspace_id=ws.id)
    else:
        form = WorkspaceCreateForm()

    return render(request, "workspaces/new.html", {"form": form, "org": org})

@login_required
def manage_access(request, workspace_id: int):
    ws = get_object_or_404(Workspace.objects.select_related("organization"), id=workspace_id)
    org = ws.organization

    # permission: only ADMINs of this org
    is_admin = Membership.objects.filter(
        user=request.user, organization=org, role=Membership.Role.ADMIN, status=Membership.Status.ACTIVE
    ).exists()
    if not is_admin:
        messages.error(request, "Only org admins can manage access.")
        return redirect("workspaces:choose")

    # Grant/revoke via querystring (?grant=<mem_id> or ?revoke=<mem_id>)
    grant_id = request.GET.get("grant")
    revoke_id = request.GET.get("revoke")

    if grant_id:
        try:
            m = Membership.objects.get(id=int(grant_id), organization=org, status=Membership.Status.ACTIVE)
            WorkspaceAccess.objects.get_or_create(membership=m, workspace=ws)
            messages.success(request, f"Granted access to {m.user.email}.")
            return redirect("workspaces:access", workspace_id=ws.id)
        except (Membership.DoesNotExist, ValueError):
            messages.error(request, "Invalid member to grant.")

    if revoke_id:
        try:
            m = Membership.objects.get(id=int(revoke_id), organization=org, status=Membership.Status.ACTIVE)
            WorkspaceAccess.objects.filter(membership=m, workspace=ws).delete()
            messages.success(request, f"Revoked access from {m.user.email}.")
            return redirect("workspaces:access", workspace_id=ws.id)
        except (Membership.DoesNotExist, ValueError):
            messages.error(request, "Invalid member to revoke.")

    # Build lists
    active_members = Membership.objects.filter(organization=org, status=Membership.Status.ACTIVE)\
                                       .select_related("user")
    granted_ids = set(
        WorkspaceAccess.objects.filter(workspace=ws, membership__in=active_members)
        .values_list("membership_id", flat=True)
    )

    return render(
        request, "workspaces/access.html",
        {"workspace": ws, "org": org, "members": active_members, "granted_ids": granted_ids}
    )
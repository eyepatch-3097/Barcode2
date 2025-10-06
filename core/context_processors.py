# core/context_processors.py
from organizations.models import Membership
from workspaces.models import Workspace

def current_context(request):
    org = None
    workspace = None
    role = None
    if request.user.is_authenticated:
        ws_id = request.session.get("current_workspace_id")
        if ws_id:
            try:
                workspace = Workspace.objects.select_related("organization").get(id=ws_id)
                org = workspace.organization
                mem = Membership.objects.filter(
                    user=request.user, organization=org, status=Membership.Status.ACTIVE
                ).first()
                if mem:
                    role = mem.role
            except Workspace.DoesNotExist:
                pass
    return {
        "CURRENT_ORG": org,
        "CURRENT_WORKSPACE": workspace,
        "CURRENT_ROLE": role,
    }

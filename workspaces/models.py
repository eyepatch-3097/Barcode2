from django.db import models
from django.conf import settings
from organizations.models import Organization, Membership

class Workspace(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="workspaces")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "slug")

    def __str__(self):
        return f"{self.name} · {self.organization.domain}"

class WorkspaceAccess(models.Model):
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="workspace_accesses")
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="accesses")
    # Future: granular permissions (design/generate/billing)
    can_design = models.BooleanField(default=True)
    can_generate = models.BooleanField(default=True)

    class Meta:
        unique_together = ("membership", "workspace")

    def __str__(self):
        return f"{self.membership.user.email} -> {self.workspace.name}"

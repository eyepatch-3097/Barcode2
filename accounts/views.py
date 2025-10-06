# accounts/views.py
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import SignUpForm, LoginForm
from django.http import Http404
from .models import User
from django.core.mail import send_mail
from django.conf import settings
from organizations.models import Organization, Membership
from workspaces.models import Workspace, WorkspaceAccess

def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower().strip()
            user = User.objects.create_user(email=email, password=form.cleaned_data["password"])

            domain = email.split("@")[-1].lower()
            is_public = domain in getattr(settings, "PUBLIC_EMAIL_DOMAINS", set())

            if is_public:
                
                # PERSONAL org: one user = one org, immediate access
                org = Organization.objects.create(
                    name=email,           # or f"{email} (Personal)"
                    domain=email,         # store full email to keep uniqueness simple
                    kind=Organization.Kind.PERSONAL,
                    created_by=user
                )

                # Create default workspace
                default_ws = Workspace.objects.create(
                    organization=org, name="Default Workspace", slug="default", created_by=user
                )

                # Create admin membership (only once)
                admin_mem = Membership.objects.create(
                    user=user, organization=org, role=Membership.Role.ADMIN, status=Membership.Status.ACTIVE
                )

                # Give admin access to default workspace
                WorkspaceAccess.objects.create(membership=admin_mem, workspace=default_ws)

                # Activate the user
                user.is_active = True
                user.save(update_fields=["is_active"])

                messages.success(request, "Account created. You can now log in.")
                return redirect("accounts:login")

            # CORPORATE (non-public domain): group by domain
            org = Organization.objects.filter(domain__iexact=domain, kind=Organization.Kind.CORPORATE).first()

            if org is None:
                # First user for this corporate domain → create org, make admin, activate
                org = Organization.objects.create(
                    name=domain, domain=domain, kind=Organization.Kind.CORPORATE, created_by=user
                )

                # Create default workspace
                default_ws = Workspace.objects.create(
                    organization=org, name="Default Workspace", slug="default", created_by=user
                )
                # Create admin membership (already in your code)
                admin_mem = Membership.objects.create(
                    user=user, organization=org, role=Membership.Role.ADMIN, status=Membership.Status.ACTIVE
                )
                # Give admin access to default workspace
                WorkspaceAccess.objects.create(membership=admin_mem, workspace=default_ws)

                user.is_active = True
                user.save(update_fields=["is_active"])
                messages.success(request, "Account created. You can now log in.")
                return redirect("accounts:login")
            else:
                # Existing corporate org → create pending member, require approval
                Membership.objects.create(
                    user=user, organization=org,
                    role=Membership.Role.MEMBER, status=Membership.Status.PENDING
                )
                user.is_active = False
                user.save(update_fields=["is_active"])

                admin_emails = list(
                    User.objects.filter(
                        memberships__organization=org,
                        memberships__role=Membership.Role.ADMIN,
                        memberships__status=Membership.Status.ACTIVE
                    ).values_list("email", flat=True)
                )
                if admin_emails:
                    send_mail(
                        subject=f"[Barcode2.0] Approval needed for {email}",
                        message=(
                            f"User {email} has requested access to organization {org.name} ({org.domain}). "
                            f"Please review and approve in the Admin Approvals screen."
                        ),
                        from_email=None,
                        recipient_list=admin_emails,
                        fail_silently=True,
                    )

                messages.info(request, "Thanks! Your account is pending admin approval. We’ll email you once approved.")
                return redirect("accounts:login")
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:post_login")
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data["user"]
            login(request, user)
            messages.success(request, "Welcome back!")
            return redirect("accounts:post_login")
    else:
        form = LoginForm()
    return render(request, "accounts/login.html", {"form": form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("accounts:login")

@login_required
def post_login_view(request):
    # check if user is an active admin in any organization
    
    # ensure workspace picked
    if not request.session.get("current_workspace_id"):
        return redirect("workspaces:choose")

    is_admin = Membership.objects.filter(
        user=request.user,
        role=Membership.Role.ADMIN,
        status=Membership.Status.ACTIVE
    ).exists()
    return render(request, "accounts/post_login.html", {"is_admin": is_admin})

@login_required
def approvals_view(request):
    # Superusers can see all (optional), or limit to admin orgs only
    admin_org_ids = Membership.objects.filter(
        user=request.user, role=Membership.Role.ADMIN, status=Membership.Status.ACTIVE
    ).values_list("organization_id", flat=True)

    pending = Membership.objects.select_related("user", "organization").filter(
        organization_id__in=admin_org_ids, status=Membership.Status.PENDING
    )

    return render(request, "accounts/approvals.html", {"pending": pending})

@login_required
def approve_member_view(request, membership_id: int):
    try:
        m = Membership.objects.select_related("organization", "user").get(id=membership_id)
    except Membership.DoesNotExist:
        raise Http404("Membership not found")

    is_admin = Membership.objects.filter(
        user=request.user,
        organization=m.organization,
        role=Membership.Role.ADMIN,
        status=Membership.Status.ACTIVE
    ).exists()
    if not is_admin:
        messages.error(request, "You do not have permission to approve this member.")
        return redirect("accounts:approvals")

    m.status = Membership.Status.ACTIVE
    m.save(update_fields=["status"])

    org_workspaces = Workspace.objects.filter(organization=m.organization)
    for ws in org_workspaces:
        WorkspaceAccess.objects.get_or_create(membership=m, workspace=ws)

    if not m.user.is_active:
        m.user.is_active = True
        m.user.save(update_fields=["is_active"])

    send_mail(
        subject="[Barcode2.0] Your account has been approved",
        message=f"Your access to {m.organization.name} has been approved. You can now log in.",
        from_email=None,
        recipient_list=[m.user.email],
        fail_silently=True,
    )
    messages.success(request, f"Approved {m.user.email}.")
    return redirect("accounts:approvals")
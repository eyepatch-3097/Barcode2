# accounts/urls.py
from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("post-login/", views.post_login_view, name="post_login"),  # placeholder page after login
    path("approvals/", views.approvals_view, name="approvals"),
    path("approve/<int:membership_id>/", views.approve_member_view, name="approve_member"),
]

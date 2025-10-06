from django.urls import path
from . import views

app_name = "workspaces"
urlpatterns = [
    path("choose/", views.choose_workspace, name="choose"),
    path("select/<int:workspace_id>/", views.select_workspace, name="select"),
    path("new/", views.create_workspace, name="new"),
    path("<int:workspace_id>/access/", views.manage_access, name="access"),
]

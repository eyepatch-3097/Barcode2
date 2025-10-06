from django.urls import path
from . import views

app_name = "labels"

urlpatterns = [
    path("", views.design_home, name="design_home"),
    path("templates/", views.template_list, name="template_list"),
    path("templates/new/", views.template_create, name="template_create"),
    path("templates/<int:pk>/edit/", views.template_editor, name="template_editor"),
    path("templates/<int:pk>/save/", views.template_save_schema, name="template_save_schema"),
    path("templates/<int:pk>/preview/", views.template_preview, name="template_preview"),
    path("templates/<int:pk>/csv/", views.template_csv, name="template_csv"),
    path("generate/", views.generate_choose_template, name="generate_choose"),
    path("generate/<int:pk>/single/", views.generate_single, name="generate_single"),
]

from django.urls import path
from . import views

urlpatterns = [
    # placeholder — add actual routes later if needed
    path('', views.organization_home, name='organization_home'),
]

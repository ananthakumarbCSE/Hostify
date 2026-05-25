from django.urls import path
from . import views

app_name = "tickets"

urlpatterns = [
    path("validate/", views.validate_discount_view, name="validate_discount"),
]

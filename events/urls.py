from django.urls import path
from . import views

app_name = "events"

urlpatterns = [
    path("",                     views.home_view,        name="home"),
    path("events/",              views.event_list_view,  name="list"),
    path("events/<slug:slug>/",  views.event_detail_view,name="detail"),
]

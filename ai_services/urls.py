from django.urls import path
from . import views

app_name = "ai_services"

urlpatterns = [
    path("chatbot/<int:event_id>/",    views.chatbot_view,              name="chatbot"),
    path("generate-description/",      views.generate_description_view, name="generate_description"),
    path("schedule/<int:event_id>/",   views.schedule_builder_view,     name="schedule_builder"),
    path("recommendations/refresh/",   views.refresh_recommendations_view, name="refresh_recommendations"),
]

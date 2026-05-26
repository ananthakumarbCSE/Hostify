from django.urls import path
from . import views

app_name = "ai_services"

urlpatterns = [
    path("chatbot/<int:event_id>/",    views.chatbot_view,              name="chatbot"),
    path("generate-description/",      views.generate_description_view, name="generate_description"),
    path("generate-email-draft/<int:event_id>/", views.generate_email_draft_view, name="generate_email_draft"),
    path("auto-fill-event/",           views.auto_fill_event_view,      name="auto_fill_event"),
    path("schedule/<int:event_id>/",   views.schedule_builder_view,     name="schedule_builder"),
    path("recommendations/refresh/",   views.refresh_recommendations_view, name="refresh_recommendations"),
]

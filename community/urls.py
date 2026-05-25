from django.urls import path
from . import views

app_name = "community"

urlpatterns = [
    path("review/<int:event_id>/",           views.submit_review_view,    name="submit_review"),
    path("feedback/",                         views.submit_feedback_view,  name="submit_feedback"),
    path("networking/<int:event_id>/",        views.networking_optin_view, name="networking_optin"),
    path("question/<int:event_id>/",          views.submit_question_view,  name="submit_question"),
    path("question/answer/<int:question_id>/",views.answer_question_view,  name="answer_question"),
    path("networking/attendees/<int:event_id>/", views.networking_list_view, name="networking_list"),
]

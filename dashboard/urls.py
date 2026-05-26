from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    #common routes
    path("",                                views.redirect_to_events),
    path("events/",                         views.events_view,          name="events"),
    path("events/<int:event_id>/",          views.event_manage_view,    name="event_manage"),
    path("events/<int:event_id>/send-email/", views.send_event_email_view, name="send_event_email"),
    path("profile/",                        views.profile_view,         name="profile"),
    path("profile/<str:username>/",         views.public_profile_view,  name="public_profile"),
    path("notifications/",                  views.notifications_view,   name="notifications"),
    path("notifications/mark-read/",        views.mark_notifications_read_view, name="mark_notifications_read"),

    #Organizer routes
    path("create-event/",                   views.create_event_view,    name="create_event"),
    path("edit-event/<int:event_id>/",      views.edit_event_view,      name="edit_event"),
    path("delete-event/<int:event_id>/",    views.delete_event_view,    name="delete_event"),
    path("checkin/<int:event_id>/",         views.checkin_panel_view,   name="checkin"),
    path("checkin/scan/",                   views.checkin_scan_view,    name="checkin_scan"),
    path("export/<int:event_id>/csv/",      views.export_attendees_csv, name="export_csv"),

    #Attendee routes
    path("activity/",                       views.activity_view,        name="activity"),
    path("history/",                        views.history_view,         name="history"),
    path("wishlist/toggle/",               views.wishlist_toggle_view,  name="wishlist_toggle"),
]
from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("create-order/",       views.create_order_view,      name="create_order"),
    path("callback/",           views.razorpay_callback_view,  name="callback"),
    path("success/",            views.payment_success_view,    name="success"),
    path("failed/",             views.payment_failed_view,     name="failed"),
    path("refund/request/<int:order_id>/",  views.refund_request_view,  name="refund_request"),
    path("refund/review/<int:refund_id>/",  views.refund_review_view,   name="refund_review"),
    path("payout/simulate/<int:event_id>/", views.payout_simulate_view, name="payout_simulate"),
]

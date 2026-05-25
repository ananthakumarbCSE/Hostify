from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
import json
import razorpay
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from events.models import Event
from tickets.models import TicketTier, DiscountCode, Ticket
from accounts.models import Notification
from .models import Order, OrderItem, Refund, OrganizerPayout
from decimal import Decimal

# Create your views here.

RAZORPAY_CLIENT = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


@login_required
@require_POST
def create_order_view(request):
    data       = json.loads(request.body)
    event      = get_object_or_404(Event, pk=data.get("event_id"), status="published")
    items_data = data.get("items", [])

    if not items_data:
        return JsonResponse({"ok": False, "error": "Please select at least one ticket to purchase."}, status=400)

    order    = Order.objects.create(user=request.user, event=event)
    subtotal = Decimal("0.00")

    for item in items_data:
        tier  = get_object_or_404(TicketTier, pk=item["tier_id"], event=event, is_active=True)
        qty   = max(1, int(item.get("qty", 1)))
        price = tier.current_price()
        remaining = tier.tickets_remaining()
        if remaining is not None and qty > remaining:
            order.delete()
            return JsonResponse({"ok": False, "error": f"Only {remaining} tickets left for {tier.name}."})

        OrderItem.objects.create(order=order, ticket_tier=tier,
                                  quantity=qty, unit_price=price)
        subtotal += price * qty
    discount_amount = 0
    code_str = data.get("discount_code", "").strip().upper()
    if code_str:
        try:
            code = DiscountCode.objects.get(event=event, code=code_str)
            if code.is_valid():
                if code.discount_type == "percentage":
                    discount_amount = subtotal * code.value / 100
                else:
                    discount_amount = min(code.value, subtotal)
                order.discount_code = code
                code.used_count += 1
                code.save(update_fields=["used_count"])
        except DiscountCode.DoesNotExist:
            pass

    total = max(Decimal("0.00"), subtotal - discount_amount)
    order.subtotal        = subtotal
    order.discount_amount = discount_amount
    order.total           = total
    order.save()
    if total == 0:
        order.status  = "paid"
        order.paid_at = timezone.now()
        order.save()
        _issue_tickets(order)
        return JsonResponse({"ok": True, "free": True, "redirect": reverse("dashboard:activity")})

    rz_order = RAZORPAY_CLIENT.order.create({
        "amount":   int(total * Decimal("100")),
        "currency": "INR",
        "receipt":  f"order_{order.pk}",
    })
    order.razorpay_order_id = rz_order["id"]
    order.save(update_fields=["razorpay_order_id"])

    return JsonResponse({
        "ok":                True,
        "free":              False,
        "order_id":          order.pk,
        "razorpay_order_id": order.razorpay_order_id,
        "amount":            int(total * Decimal("100")),
        "key_id":            settings.RAZORPAY_KEY_ID,
        "name":              event.title,
        "email":             request.user.email,
        "callback_url":      reverse("payments:callback"),
    })


@login_required
@require_POST
def confirm_order_view(request):
    event_id = request.POST.get("event_id")
    event = get_object_or_404(Event, pk=event_id, status="published")

    items = []
    subtotal = Decimal("0.00")
    discount_error = ""

    for key, value in request.POST.items():
        if not key.startswith("tier_"):
            continue
        try:
            tier_id = int(key.split("_", 1)[1])
            quantity = int(value)
        except (ValueError, TypeError):
            continue
        if quantity <= 0:
            continue

        tier = get_object_or_404(TicketTier, pk=tier_id, event=event, is_active=True)
        if tier.max_per_order and quantity > tier.max_per_order:
            messages.error(request, f"You can only purchase up to {tier.max_per_order} tickets for {tier.name}.")
            return redirect("events:detail", slug=event.slug)

        remaining = tier.tickets_remaining()
        if remaining is not None and quantity > remaining:
            messages.error(request, f"Only {remaining} tickets left for {tier.name}.")
            return redirect("events:detail", slug=event.slug)

        unit_price = tier.current_price()
        line_total = unit_price * quantity
        subtotal += line_total
        items.append({
            "tier": tier,
            "quantity": quantity,
            "unit_price": unit_price,
            "line_total": line_total,
        })

    if not items:
        messages.error(request, "Please select at least one ticket to purchase.")
        return redirect("events:detail", slug=event.slug)

    discount_code = request.POST.get("discount_code", "").strip().upper()
    discount_amount = Decimal("0.00")
    discount = None
    if discount_code:
        try:
            discount = DiscountCode.objects.get(event=event, code=discount_code)
            if discount.is_valid():
                if discount.discount_type == "percentage":
                    discount_amount = subtotal * discount.value / Decimal("100.00")
                else:
                    discount_amount = min(discount.value, subtotal)
            else:
                discount_error = "Discount code is not valid or has expired."
        except DiscountCode.DoesNotExist:
            discount_error = "Discount code is not valid."

    total = max(Decimal("0.00"), subtotal - discount_amount)

    return render(request, "payments/confirmation.html", {
        "event": event,
        "items": items,
        "subtotal": subtotal,
        "discount": discount,
        "discount_amount": discount_amount,
        "discount_error": discount_error,
        "total": total,
        "discount_code": discount_code,
    })


@csrf_exempt
def razorpay_callback_view(request):
    data = request.POST if request.POST else json.loads(request.body)
    try:
        RAZORPAY_CLIENT.utility.verify_payment_signature({
            "razorpay_order_id":   data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature":  data["razorpay_signature"],
        })
    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({"ok": False, "error": "Signature verification failed."}, status=400)

    order = get_object_or_404(Order, razorpay_order_id=data["razorpay_order_id"])
    if order.status == "paid":
        return JsonResponse({"ok": True, "already_paid": True})

    order.razorpay_payment_id = data["razorpay_payment_id"]
    order.razorpay_signature  = data["razorpay_signature"]
    order.status  = "paid"
    order.paid_at = timezone.now()
    order.save()

    _issue_tickets(order)
    return JsonResponse({"ok": True, "redirect": reverse("payments:success")})


def _issue_tickets(order):
    for item in order.items.select_related("ticket_tier"):
        for _ in range(item.quantity):
            ticket = Ticket.objects.create(
                attendee   = order.user,
                tier       = item.ticket_tier,
                order      = order,
                status     = "confirmed",
                price_paid = item.unit_price,
            )
            ticket.generate_qr()

    Notification.objects.create(
        user       = order.user,
        notif_type = "ticket",
        title      = f"Tickets confirmed — {order.event.title}",
        message    = f"Your {order.items.count()} ticket(s) are ready. Check your dashboard.",
        link       = "/dashboard/activity/",
    )


@login_required
def payment_success_view(request):
    latest_order = (Order.objects
                    .filter(user=request.user, status="paid")
                    .order_by("-paid_at").first())
    return render(request, "payments/success.html", {"order": latest_order})


@login_required
def payment_failed_view(request):
    return render(request, "payments/failed.html")


@login_required
@require_POST
def refund_request_view(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user, status="paid")

    if Refund.objects.filter(order=order, status__in=["requested", "approved"]).exists():
        messages.warning(request, "A refund request already exists for this order.")
        return redirect("dashboard:activity")

    reason = request.POST.get("reason", "").strip()
    if not reason:
        messages.error(request, "Please provide a reason for the refund.")
        return redirect("dashboard:activity")

    Refund.objects.create(
        order        = order,
        requested_by = request.user,
        reason       = reason,
        amount       = order.total,
    )
    Notification.objects.create(
        user       = order.event.organizer,
        notif_type = "refund",
        title      = f"Refund request — {order.event.title}",
        message    = f"{request.user.get_full_name()} has requested a refund of ₹{order.total}.",
        link       = f"/dashboard/events/{order.event.pk}/",
    )
    messages.success(request, "Refund request submitted. The organiser will review it.")
    return redirect("dashboard:activity")


@login_required
@require_POST
def refund_review_view(request, refund_id):
    refund = get_object_or_404(Refund, pk=refund_id,
                                order__event__organizer=request.user)
    action      = request.POST.get("action")
    review_note = request.POST.get("review_note", "")

    if action == "approve":
        refund.status      = "approved"
        refund.review_note = review_note
        refund.reviewed_by = request.user
        refund.reviewed_at = timezone.now()
        refund.save()
        refund.order.status = "refunded"
        refund.order.save(update_fields=["status"])
        refund.order.tickets.all().update(status="refunded")

        Notification.objects.create(
            user       = refund.requested_by,
            notif_type = "refund",
            title      = "Refund approved",
            message    = f"Your refund of ₹{refund.amount} for {refund.order.event.title} has been approved.",
            link       = "/dashboard/history/",
        )
    elif action == "reject":
        refund.status      = "rejected"
        refund.review_note = review_note
        refund.reviewed_by = request.user
        refund.reviewed_at = timezone.now()
        refund.save()

        Notification.objects.create(
            user       = refund.requested_by,
            notif_type = "refund",
            title      = "Refund rejected",
            message    = f"Your refund request for {refund.order.event.title} was rejected. Reason: {review_note}",
            link       = "/dashboard/history/",
        )

    messages.success(request, f"Refund {refund.status}.")
    return redirect("dashboard:event_manage", event_id=refund.order.event.pk)


@login_required
@require_POST
def payout_simulate_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id, organizer=request.user)

    if OrganizerPayout.objects.filter(event=event, status="processed").exists():
        messages.info(request, "Payout already processed.")
        return redirect("dashboard:event_manage", event_id=event.pk)

    gross = sum(
        o.total for o in Order.objects.filter(event=event, status="paid")
    )
    platform_fee = round(gross * 5 / 100, 2)   # 5% platform fee simulation
    net = gross - platform_fee

    OrganizerPayout.objects.update_or_create(
        event    = event,
        organizer= request.user,
        defaults = {
            "gross":        gross,
            "platform_fee": platform_fee,
            "net":          net,
            "status":       "processed",
            "processed_at": timezone.now(),
            "reference_id": f"SIM-{event.pk}-{timezone.now().strftime('%Y%m%d')}",
        },
    )
    messages.success(request, f"Payout of ₹{net} processed (simulated).")
    return redirect("dashboard:event_manage", event_id=event.pk)

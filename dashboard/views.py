from django.shortcuts import render, redirect, get_object_or_404
import csv
import json
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from django.urls import reverse
from django.core.mail import EmailMessage
from events.models import Event, EventWishlist
from events.forms import EventForm, EventSessionFormSet,TicketTierFormSet, DiscountCodeFormSet,EventFAQFormSet, EventSponsorFormSet
from tickets.models import Ticket, CheckIn
from payments.models import Order, Refund, OrganizerPayout
from community.models import PostEventFeedback, AttendeeQuestion
from accounts.models import Notification
from accounts.forms import UserUpdateForm, AttendeeProfileForm, OrganizerProfileForm

# Create your views here.

User = get_user_model()


def redirect_to_events(request):
    return redirect("dashboard:events")

@login_required
def events_view(request):
    user = request.user
    ctx  = {}

    if user.is_organizer:
        org_events = Event.objects.filter(organizer=user).order_by("-created_at")
        total_revenue = org_events.aggregate(
            rev=Sum("orders__total", filter=__import__(
                "django.db.models", fromlist=["Q"]
            ).Q(orders__status="paid"))
        )["rev"] or 0

        ctx.update({
            "org_events":    org_events,
            "total_revenue": total_revenue,
        })

    if user.is_attendee:
        my_tickets = (Ticket.objects
                      .filter(attendee=user, status="confirmed")
                      .select_related("tier__event")
                      .order_by("tier__event__start_datetime"))
        wishlist   = (user.wishlist
                      .select_related("event")
                      .order_by("-added_at"))
        ctx.update({"my_tickets": my_tickets, "wishlist": wishlist})

    return render(request, "dashboard/common/events.html", ctx)


@login_required
def profile_view(request):
    user = request.user

    from accounts.models import AttendeeProfile, OrganizerProfile
    profile,     _ = AttendeeProfile.objects.get_or_create(user=user)
    org_profile, _ = OrganizerProfile.objects.get_or_create(
        user=user,
        defaults={"display_name": user.get_full_name() or user.email}
    )

    if request.method == "POST":
        user_form   = UserUpdateForm(request.POST, request.FILES, instance=user)
        att_form    = AttendeeProfileForm(request.POST, instance=profile)
        org_form    = OrganizerProfileForm(request.POST, request.FILES, instance=org_profile)

        if user_form.is_valid() and att_form.is_valid() and org_form.is_valid():
            user_form.save()
            att_form.save()
            if user.is_organizer:
                org_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("dashboard:profile")
    else:
        user_form = UserUpdateForm(instance=user)
        att_form  = AttendeeProfileForm(instance=profile)
        org_form  = OrganizerProfileForm(instance=org_profile)

    return render(request, "dashboard/common/profile.html", {
        "user_form":   user_form,
        "att_form":    att_form,
        "org_form":    org_form,
        "profile":     profile,
        "org_profile": org_profile,
    })


@login_required
def public_profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)
    past_events  = (Ticket.objects
                    .filter(attendee=profile_user, status="confirmed",
                            tier__event__end_datetime__lt=timezone.now())
                    .select_related("tier__event")
                    .order_by("-tier__event__end_datetime")[:10])
    try:
        att_profile = profile_user.attendee_profile
    except Exception:
        att_profile = None

    return render(request, "dashboard/common/public_profile.html", {
        "profile_user":   profile_user,
        "attendee_profile": att_profile,
        "past_events":    [t.tier.event for t in past_events],
    })


@login_required
def notifications_view(request):
    notifs = request.user.notifications.order_by("-created_at")
    notifs.filter(is_read=False).update(is_read=True)
    return render(request, "dashboard/common/notifications.html",
                  {"notifications": notifs})


@login_required
@require_POST
def mark_notifications_read_view(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({"ok": True})

@login_required
def create_event_view(request):
    if not request.user.is_organizer:
        messages.error(request, "You need an organiser account to create events.")
        return redirect("dashboard:events")

    if request.method == "POST":
        form          = EventForm(request.POST, request.FILES)
        session_forms = EventSessionFormSet(request.POST, prefix="sessions")
        tier_forms    = TicketTierFormSet(request.POST, prefix="tiers")
        discount_forms= DiscountCodeFormSet(request.POST, prefix="discounts")
        faq_forms     = EventFAQFormSet(request.POST, prefix="faqs")
        sponsor_forms = EventSponsorFormSet(request.POST, request.FILES, prefix="sponsors")

        if (form.is_valid() and session_forms.is_valid() and tier_forms.is_valid()
                and discount_forms.is_valid() and faq_forms.is_valid()
                and sponsor_forms.is_valid()):
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()

        
            for formset in [session_forms, tier_forms, discount_forms, faq_forms, sponsor_forms]:
                instances = formset.save(commit=False)
                for obj in instances:
    
                    if any(getattr(obj, field.name, None) for field in obj._meta.get_fields() 
                           if not field.name.startswith('_') and field.name not in ['id', 'event']):
                        obj.event = event
                        obj.save()
                for obj in formset.deleted_objects:
                    obj.delete()

            messages.success(request, "Event created successfully!")
            return redirect("dashboard:event_manage", event_id=event.pk)
        else:
            if not form.is_valid():
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
            if not session_forms.is_valid():
                for form_errors in session_forms.errors:
                    if form_errors:
                        messages.error(request, f"Session error: {form_errors}")
            if not tier_forms.is_valid():
                for form_errors in tier_forms.errors:
                    if form_errors:
                        messages.error(request, f"Ticket Tier error: {form_errors}")
            if not discount_forms.is_valid():
                for form_errors in discount_forms.errors:
                    if form_errors:
                        messages.error(request, f"Discount Code error: {form_errors}")
            if not faq_forms.is_valid():
                for form_errors in faq_forms.errors:
                    if form_errors:
                        messages.error(request, f"FAQ error: {form_errors}")
            if not sponsor_forms.is_valid():
                for form_errors in sponsor_forms.errors:
                    if form_errors:
                        messages.error(request, f"Sponsor error: {form_errors}")
    else:
        form           = EventForm()
        session_forms  = EventSessionFormSet(prefix="sessions")
        tier_forms     = TicketTierFormSet(prefix="tiers")
        discount_forms = DiscountCodeFormSet(prefix="discounts")
        faq_forms      = EventFAQFormSet(prefix="faqs")
        sponsor_forms  = EventSponsorFormSet(prefix="sponsors")

    return render(request, "dashboard/organizer/create_event.html", {
        "form":           form,
        "session_forms":  session_forms,
        "tier_forms":     tier_forms,
        "discount_forms": discount_forms,
        "faq_forms":      faq_forms,
        "sponsor_forms":  sponsor_forms,
    })


@login_required
def edit_event_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id, organizer=request.user)

    if request.method == "POST":
        form           = EventForm(request.POST, request.FILES, instance=event)
        session_forms  = EventSessionFormSet(request.POST, prefix="sessions", instance=event)
        tier_forms     = TicketTierFormSet(request.POST, prefix="tiers",     instance=event)
        discount_forms = DiscountCodeFormSet(request.POST, prefix="discounts",instance=event)
        faq_forms      = EventFAQFormSet(request.POST, prefix="faqs",        instance=event)
        sponsor_forms  = EventSponsorFormSet(request.POST, request.FILES,
                                              prefix="sponsors", instance=event)

        if (form.is_valid() and session_forms.is_valid() and tier_forms.is_valid()
                and discount_forms.is_valid() and faq_forms.is_valid()
                and sponsor_forms.is_valid()):
            form.save()
            for formset in [session_forms, tier_forms, discount_forms, faq_forms, sponsor_forms]:
                instances = formset.save(commit=False)
                for obj in instances:
                    if any(getattr(obj, field.name, None) for field in obj._meta.get_fields() 
                           if not field.name.startswith('_') and field.name not in ['id', 'event']):
                        obj.event = event
                        obj.save()
                for obj in formset.deleted_objects:
                    obj.delete()

            messages.success(request, "Event updated.")
            return redirect("dashboard:event_manage", event_id=event.pk)
        else:
            if not form.is_valid():
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
            if not session_forms.is_valid():
                for form_errors in session_forms.errors:
                    if form_errors:
                        messages.error(request, f"Session error: {form_errors}")
            if not tier_forms.is_valid():
                for form_errors in tier_forms.errors:
                    if form_errors:
                        messages.error(request, f"Ticket Tier error: {form_errors}")
            if not discount_forms.is_valid():
                for form_errors in discount_forms.errors:
                    if form_errors:
                        messages.error(request, f"Discount Code error: {form_errors}")
            if not faq_forms.is_valid():
                for form_errors in faq_forms.errors:
                    if form_errors:
                        messages.error(request, f"FAQ error: {form_errors}")
            if not sponsor_forms.is_valid():
                for form_errors in sponsor_forms.errors:
                    if form_errors:
                        messages.error(request, f"Sponsor error: {form_errors}")
    else:
        form           = EventForm(instance=event)
        session_forms  = EventSessionFormSet(prefix="sessions",  instance=event)
        tier_forms     = TicketTierFormSet(prefix="tiers",       instance=event)
        discount_forms = DiscountCodeFormSet(prefix="discounts", instance=event)
        faq_forms      = EventFAQFormSet(prefix="faqs",          instance=event)
        sponsor_forms  = EventSponsorFormSet(prefix="sponsors",  instance=event)

    return render(request, "dashboard/organizer/edit_event.html", {
        "event": event,
        "form":           form,
        "session_forms":  session_forms,
        "tier_forms":     tier_forms,
        "discount_forms": discount_forms,
        "faq_forms":      faq_forms,
        "sponsor_forms":  sponsor_forms,
    })


@login_required
@require_POST
def delete_event_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id, organizer=request.user)
    title = event.title
    event.delete()
    messages.success(request, f'"{title}" deleted.')
    return redirect("dashboard:events")


@login_required
def event_manage_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id, organizer=request.user)

    tickets     = (Ticket.objects
                   .filter(tier__event=event, status="confirmed")
                   .select_related("attendee", "tier"))
    tiers       = event.ticket_tiers.all()
    sessions    = event.sessions.all()
    questions   = event.attendee_questions.select_related("asked_by").order_by("asked_at")
    refund_reqs = (Refund.objects
                   .filter(order__event=event)
                   .select_related("requested_by", "order")
                   .order_by("-requested_at"))
    feedbacks   = (PostEventFeedback.objects
                   .filter(ticket__tier__event=event, submitted_at__isnull=False)
                   .order_by("-submitted_at"))
    avg_feedback= feedbacks.aggregate(avg=Avg("rating"))["avg"]

    # For fully online events, mark all confirmed tickets as checked in automatically.
    if event.mode == "online":
        auto_checkin = tickets.filter(checked_in=False)
        for ticket in auto_checkin:
            ticket.checked_in = True
            ticket.save(update_fields=["checked_in"])
            try:
                ticket.checkin
            except CheckIn.DoesNotExist:
                CheckIn.objects.create(ticket=ticket, scanned_by=None, method="automatic")

    total_revenue = (Order.objects
                     .filter(event=event, status="paid")
                     .aggregate(t=Sum("total"))["t"] or 0)

    try:
        payout = event.payouts.get()
    except OrganizerPayout.DoesNotExist:
        payout = None

    return render(request, "dashboard/organizer/event_manage.html", {
        "event":          event,
        "tickets":        tickets,
        "tiers":          tiers,
        "sessions":       sessions,
        "questions":      questions,
        "refund_requests":refund_reqs,
        "feedbacks":      feedbacks,
        "avg_feedback_rating": avg_feedback,
        "total_registered":    tickets.count(),
        "total_checked":       tickets.filter(checked_in=True).count(),
        "total_revenue":       total_revenue,
        "payout":         payout,
    })


@login_required
def checkin_panel_view(request, event_id):
    event     = get_object_or_404(Event, pk=event_id, organizer=request.user)
    confirmed = Ticket.objects.filter(tier__event=event, status="confirmed")
    checked   = confirmed.filter(checked_in=True)
    recent    = (checked
                 .select_related("attendee", "tier", "checkin")
                 .order_by("-checkin__scanned_at")[:30])

    return render(request, "dashboard/organizer/checkin.html", {
        "event":             event,
        "total_registered":  confirmed.count(),
        "total_checked":     checked.count(),
        "recent_checkins":   recent,
    })


@login_required
@require_POST
def send_event_email_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id, organizer=request.user)
    subject = request.POST.get("subject", "").strip()
    message = request.POST.get("message", "").strip()

    if not subject or not message:
        messages.error(request, "Please provide both subject and message for the announcement.")
        return redirect("dashboard:event_manage", event_id=event.pk)

    confirmed_tickets = Ticket.objects.filter(tier__event=event, status="confirmed").select_related("attendee")
    recipient_emails = sorted({t.attendee.email for t in confirmed_tickets if t.attendee.email})

    if not recipient_emails:
        messages.error(request, "No confirmed attendees are available to send the email to.")
        return redirect("dashboard:event_manage", event_id=event.pk)

    # Create site notifications for each confirmed attendee.
    notified_users = {}
    for ticket in confirmed_tickets:
        user = ticket.attendee
        if user.pk in notified_users:
            continue
        notified_users[user.pk] = user
        Notification.objects.create(
            user=user,
            notif_type="announcement",
            title=f"Organizer announcement for {event.title}",
            message=message,
            link=reverse("events:detail", args=[event.slug])
        )

    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=request.user.email,
        to=[request.user.email],
        bcc=recipient_emails,
    )
    try:
        email.send(fail_silently=False)
        messages.success(request, "Announcement sent to confirmed attendees and notifications created.")
    except Exception as exc:
        messages.error(request, f"Email delivery failed: {exc}")

    return redirect("dashboard:event_manage", event_id=event.pk)


@login_required
@require_POST
def checkin_scan_view(request):
    data  = json.loads(request.body)
    token = data.get("token", "").strip()

    try:
        ticket = (Ticket.objects
                  .select_related("attendee", "tier__event")
                  .get(qr_token=token, status="confirmed"))
    except Ticket.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Invalid or unknown ticket."})

    if ticket.tier.event.organizer_id != request.user.pk:
        return JsonResponse({"ok": False, "error": "Not authorised for this event."})

    if ticket.checked_in:
        return JsonResponse({
            "ok": False,
            "error": "Already checked in.",
            "attendee": ticket.attendee.get_full_name(),
        })

    ticket.checked_in = True
    ticket.save(update_fields=["checked_in"])
    CheckIn.objects.create(ticket=ticket, scanned_by=request.user, method="manual")

    return JsonResponse({
        "ok":      True,
        "attendee": ticket.attendee.get_full_name(),
        "tier":    ticket.tier.name,
        "event":   ticket.tier.event.title,
    })


@login_required
def export_attendees_csv(request, event_id):
    event = get_object_or_404(Event, pk=event_id, organizer=request.user)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{event.slug}-attendees.csv"'

    writer = csv.writer(response)
    writer.writerow(["Name", "Email", "Ticket Tier", "Price Paid",
                     "Checked In", "Issued At", "Order ID"])

    tickets = (Ticket.objects
               .filter(tier__event=event, status="confirmed")
               .select_related("attendee", "tier", "order"))
    for t in tickets:
        writer.writerow([
            t.attendee.get_full_name(),
            t.attendee.email,
            t.tier.name,
            t.price_paid,
            "Yes" if t.checked_in else "No",
            t.issued_at.strftime("%Y-%m-%d %H:%M"),
            t.order_id or "",
        ])

    return response

@login_required
def activity_view(request):
    now = timezone.now()
    upcoming_tickets = (Ticket.objects
                        .filter(attendee=request.user, status="confirmed",
                                tier__event__end_datetime__gte=now)
                        .select_related("tier__event", "order")
                        .order_by("tier__event__start_datetime"))
    wishlist = (request.user.wishlist
                .select_related("event")
                .order_by("-added_at"))

    return render(request, "dashboard/attendee/activity.html", {
        "upcoming_tickets": upcoming_tickets,
        "wishlist":         wishlist,
    })


@login_required
def history_view(request):
    now = timezone.now()
    past_tickets = (Ticket.objects
                    .filter(attendee=request.user, status="confirmed",
                            tier__event__end_datetime__lt=now)
                    .select_related("tier__event")
                    .order_by("-tier__event__end_datetime"))

    return render(request, "dashboard/attendee/history.html", {
        "past_tickets": past_tickets,
    })


@login_required
@require_POST
def wishlist_toggle_view(request):
    event_id = request.POST.get("event_id")
    event = get_object_or_404(Event, pk=event_id)
    obj, created = EventWishlist.objects.get_or_create(user=request.user, event=event)
    if not created:
        obj.delete()
    return redirect("events:detail", slug=event.slug)

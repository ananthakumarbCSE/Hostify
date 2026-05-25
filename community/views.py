from django.shortcuts import render, get_object_or_404, redirect
import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib import messages
from events.models import Event
from tickets.models import Ticket
from .models import EventReview, PostEventFeedback, NetworkingOptIn, AttendeeQuestion

# Create your views here.

@login_required
@require_POST
def submit_review_view(request, event_id):
    
    event = get_object_or_404(Event, pk=event_id)

    has_ticket = Ticket.objects.filter(
        attendee=request.user, tier__event=event, status="confirmed"
    ).exists()
    if not has_ticket:
        return JsonResponse({"error": "You need a ticket to review this event."}, status=403)

    data = json.loads(request.body)
    EventReview.objects.update_or_create(
        event=event, author=request.user,
        defaults={"rating": data["rating"], "body": data["body"]},
    )
    return JsonResponse({"ok": True})


@login_required
@require_POST
def submit_feedback_view(request):
    data      = json.loads(request.body)
    ticket    = get_object_or_404(Ticket, pk=data.get("ticket_id"), attendee=request.user)
    PostEventFeedback.objects.update_or_create(
        ticket=ticket,
        defaults={
            "rating":       data["rating"],
            "text":         data.get("text", ""),
            "submitted_at": timezone.now(),
        },
    )
    return JsonResponse({"ok": True})


@login_required
@require_POST
def networking_optin_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    data  = json.loads(request.body)
    NetworkingOptIn.objects.update_or_create(
        event=event, user=request.user,
        defaults={
            "show_linkedin": data.get("show_linkedin", False),
            "show_email":    data.get("show_email", False),
        },
    )
    return JsonResponse({"ok": True})


@login_required
@require_POST
def submit_question_view(request, event_id):

    event    = get_object_or_404(Event, pk=event_id)
    question = request.POST.get("question", "").strip()
    if not question:
        messages.error(request, "Question cannot be empty.")
        return redirect("events:detail", slug=event.slug)

    AttendeeQuestion.objects.create(
        event    = event,
        asked_by = request.user,
        question = question,
    )
    messages.success(request, "Question submitted. The organiser will answer it.")
    return redirect("events:detail", slug=event.slug)


@login_required
@require_POST
def answer_question_view(request, question_id):
    qa = get_object_or_404(AttendeeQuestion, pk=question_id,
                            event__organizer=request.user)
    answer = request.POST.get("answer", "").strip()
    if answer:
        qa.answer      = answer
        qa.answered_by = request.user
        qa.answered_at = timezone.now()
        qa.save(update_fields=["answer", "answered_by", "answered_at"])
        messages.success(request, "Answer posted.")
    return redirect("dashboard:event_manage", event_id=qa.event.pk)


@login_required
def networking_list_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    has_ticket = Ticket.objects.filter(
        attendee=request.user, tier__event=event, status="confirmed"
    ).exists()
    if not has_ticket:
        messages.error(request, "You need a ticket to view the networking list.")
        return redirect("events:detail", slug=event.slug)

    optins = (NetworkingOptIn.objects
              .filter(event=event)
              .filter(show_linkedin=True)
              .select_related("user", "user__attendee_profile")
              .exclude(user=request.user))

    return render(request, "community/networking_list.html", {
        "event":  event,
        "optins": optins,
    })

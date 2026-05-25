from django.shortcuts import render,get_object_or_404
import json
import time
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from groq import Groq
from events.models import Event
from .models import EventAIKnowledge, AIConversation, AIGenerationLog, AIRecommendation
from tickets.models import Ticket

# Create your views here.


groq_client = Groq(api_key=settings.GROQ_API_KEY)


def _log(gen_type, prompt, result, tokens, latency, event=None, user=None):
    AIGenerationLog.objects.create(
        gen_type=gen_type, event=event, user=user,
        prompt=prompt, result=result,
        tokens_used=tokens, latency_ms=latency,
    )


@require_POST
def chatbot_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id, status="published")
    data  = json.loads(request.body)
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return JsonResponse({"error": "Empty message."}, status=400)

    try:
        knowledge = event.ai_knowledge_obj.knowledge
    except EventAIKnowledge.DoesNotExist:
        knowledge = event.description

    system_prompt = (
        f'You are a helpful assistant for the event "{event.title}". '
        "Answer questions using only the knowledge provided below. "
        "If the answer isn't there, say so and suggest contacting the organiser.\n\n"
        f"EVENT KNOWLEDGE:\n{knowledge}"
    )

    messages = []
    conv = None
    if request.user.is_authenticated:
        conv, _ = AIConversation.objects.get_or_create(
            event=event, user=request.user, defaults={"messages": []}
        )
        messages = conv.messages[-20:]

    messages.append({"role": "user", "content": user_msg})

    t0 = time.time()
    response = groq_client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "system", "content": system_prompt}] + messages,
        max_tokens=512,
    )
    latency = int((time.time() - t0) * 1000)
    reply   = response.choices[0].message.content

    messages.append({"role": "assistant", "content": reply})
    if conv:
        conv.messages = messages
        conv.save(update_fields=["messages", "updated_at"])

    _log("chatbot", user_msg, reply, response.usage.total_tokens, latency,
         event=event,
         user=request.user if request.user.is_authenticated else None)

    return JsonResponse({"reply": reply})


@login_required
@require_POST
def generate_description_view(request):
    data    = json.loads(request.body)
    bullets = data.get("bullets", "").strip()
    title   = data.get("event_title", "this event")

    if not bullets:
        return JsonResponse({"error": "No bullet points provided."}, status=400)

    prompt = (
        f'You are an expert event copywriter. Convert these bullet points into '
        f'a polished, engaging event description for "{title}". '
        'Write 3-4 paragraphs. Be enthusiastic but professional. '
        'Use second-person ("you\'ll..."). Do not add anything not in the bullets.\n\n'
        f'BULLET POINTS:\n{bullets}'
    )
    t0 = time.time()
    response = groq_client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
    )
    latency = int((time.time() - t0) * 1000)
    result  = response.choices[0].message.content

    _log("description", bullets, result, response.usage.total_tokens, latency,
         user=request.user)

    return JsonResponse({"description": result})


@login_required
@require_POST
def schedule_builder_view(request, event_id):
    event    = get_object_or_404(Event, pk=event_id, organizer=request.user)
    data     = json.loads(request.body)
    sessions = data.get("sessions", [])

    if not sessions:
        return JsonResponse({"error": "No sessions provided."}, status=400)

    prompt = (
        f'You are an expert event programme director. '
        f'Given the sessions below for "{event.title}", suggest the optimal ordering. '
        'Consider: audience energy (keynotes first, workshops later, networking last), '
        'logical content flow, speaker availability, and variety.\n\n'
        'Return ONLY a JSON array like:\n'
        '[{"id": <original_index>, "title": "...", "reason": "one sentence"}]\n\n'
        f'SESSIONS:\n{json.dumps(sessions, indent=2)}'
    )
    t0 = time.time()
    response = groq_client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
    )
    latency = int((time.time() - t0) * 1000)
    raw     = response.choices[0].message.content

    try:
        clean   = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        ordered = json.loads(clean)
    except Exception:
        ordered = []

    _log("schedule", str(sessions), raw, response.usage.total_tokens, latency,
         event=event, user=request.user)

    return JsonResponse({"ordered_sessions": ordered})


@login_required
@require_POST
def refresh_recommendations_view(request):
    

    user = request.user

    attended_cats = list(
        Ticket.objects
        .filter(attendee=user, status="confirmed")
        .values_list("tier__event__category", flat=True)
        .distinct()
    )
    wishlist_cats = list(
        user.wishlist.values_list("event__category", flat=True).distinct()
    )
    all_cats = list(set(attended_cats + wishlist_cats)) or ["technical"]

    attended_ids = Ticket.objects.filter(
        attendee=user, status="confirmed"
    ).values_list("tier__event_id", flat=True)

    candidates = list(
        Event.objects
        .filter(status="published")
        .exclude(pk__in=attended_ids)
        .order_by("start_datetime")[:20]
        .values("id", "title", "category", "mode", "price_type", "venue_city")
    )

    if not candidates:
        return JsonResponse({"ok": True, "count": 0})

    prompt = (
        f"A user enjoys these event categories: {', '.join(all_cats)}.\n"
        "Rank the following upcoming events from most to least relevant for them.\n"
        "Return ONLY a JSON array of event IDs in ranked order, like: [12, 5, 8, ...]\n\n"
        f"EVENTS:\n{json.dumps(candidates, indent=2)}"
    )

    t0 = time.time()
    response = groq_client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
    )
    latency = int((time.time() - t0) * 1000)
    raw     = response.choices[0].message.content

    try:
        clean    = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        ordered_ids = json.loads(clean)
    except Exception:
        ordered_ids = [e["id"] for e in candidates]

    AIRecommendation.objects.update_or_create(
        user=user,
        defaults={"event_ids": ordered_ids},
    )

    _log("recommendation", str(all_cats), raw, response.usage.total_tokens, latency,
         user=user)

    return JsonResponse({"ok": True, "count": len(ordered_ids)})

from django.shortcuts import render,get_object_or_404
from django.db.models import Q,Avg
from .models import Event


# Create your views here.

def home_view(request):
    upcoming = Event.objects.filter(status="published").order_by("start_datetime")[:8]
    recommended = []
    if request.user.is_authenticated:
        try:
            rec = request.user.ai_recommendations
            recommended = list(Event.objects.filter(pk__in=rec.event_ids[:4]))
        except Exception:
            pass
    return render(request, "events/home.html", {
        "upcoming":    upcoming,
        "recommended": recommended,
    })


def event_list_view(request):
    qs = Event.objects.filter(status="published")
    category   = request.GET.get("category")
    mode       = request.GET.get("mode")
    price_type = request.GET.get("price")
    city       = request.GET.get("city")
    search     = request.GET.get("q")

    if category:   qs = qs.filter(category=category)
    if mode:       qs = qs.filter(mode=mode)
    if price_type: qs = qs.filter(price_type=price_type)
    if city:       qs = qs.filter(venue_city__icontains=city)
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

    return render(request, "events/list.html", {
        "events":           qs.order_by("start_datetime"),
        "category_choices": Event.CATEGORY_CHOICES,
        "mode_choices":     Event.MODE_CHOICES,
    })


def event_detail_view(request, slug):
    
    event      = get_object_or_404(Event, slug=slug, status="published")
    sessions   = event.sessions.all()
    faqs       = event.faqs.all()
    reviews    = event.reviews.filter(is_visible=True).select_related("author").order_by("-created_at")
    questions  = event.attendee_questions.filter(is_public=True).order_by("asked_at")
    avg_rating = reviews.aggregate(avg=Avg("rating"))["avg"]
    tiers      = event.ticket_tiers.filter(is_active=True)

    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = event.wishlisted_by.filter(user=request.user).exists()
    
    public_questions = event.attendee_questions.filter(is_public=True)

    return render(request, "events/detail.html", {
        "event":      event,
        "sessions":   sessions,
        "faqs":       faqs,
        "reviews":    reviews,
        "questions":  questions,
        "avg_rating": avg_rating,
        "tiers":      tiers,
        "in_wishlist": in_wishlist,
        "public_questions":public_questions,
    })

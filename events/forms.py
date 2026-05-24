from django import forms
from django.forms import inlineformset_factory
from django.utils.text import slugify
import uuid
from .models import Event, EventSession, EventFAQ, EventSponsor
from tickets.models import TicketTier, DiscountCode


class EventForm(forms.ModelForm):
    class Meta:
        model  = Event
        fields = [
            "title", "category", "mode", "price_type", "status",
            "description", "ai_knowledge",
            "logo", "banner",
            "start_datetime", "end_datetime",
            "venue_name", "venue_address", "venue_city",
            "venue_lat", "venue_lng", "online_link",
            "chief_guest", "total_capacity",
        ]
        widgets = {
            "start_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_datetime":   forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description":    forms.Textarea(attrs={"rows": 5}),
            "ai_knowledge":   forms.Textarea(attrs={"rows": 4}),
        }

    def save(self, commit=True):
        event = super().save(commit=False)
        if not event.slug:
            base = slugify(event.title)
            slug = base
            while Event.objects.filter(slug=slug).exclude(pk=event.pk).exists():
                slug = f"{base}-{uuid.uuid4().hex[:6]}"
            event.slug = slug
        if commit:
            event.save()
        return event


EventSessionFormSet = inlineformset_factory(
    Event,
    EventSession,
    fields=["title", "description", "speaker", "start_time", "end_time", "location", "order"],
    extra=1,
    can_delete=True,
    widgets={
        "start_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        "end_time":   forms.DateTimeInput(attrs={"type": "datetime-local"}),
    },
)

TicketTierFormSet = inlineformset_factory(
    Event,
    TicketTier,
    fields=["name", "tier_type", "description", "price",
            "early_bird_price", "early_bird_expires",
            "capacity", "max_per_order", "sale_start", "sale_end", "is_active"],
    extra=1,
    can_delete=True,
    widgets={
        "early_bird_expires": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        "sale_start":         forms.DateTimeInput(attrs={"type": "datetime-local"}),
        "sale_end":           forms.DateTimeInput(attrs={"type": "datetime-local"}),
    },
)

DiscountCodeFormSet = inlineformset_factory(
    Event,
    DiscountCode,
    fields=["code", "discount_type", "value", "max_uses", "expires_at", "is_active"],
    extra=1,
    can_delete=True,
    widgets={
        "expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
    },
)

EventFAQFormSet = inlineformset_factory(
    Event,
    EventFAQ,
    fields=["question", "answer", "order"],
    extra=1,
    can_delete=True,
)

EventSponsorFormSet = inlineformset_factory(
    Event,
    EventSponsor,
    fields=["name", "logo", "website", "tier", "amount", "description"],
    extra=1,
    can_delete=True,
)

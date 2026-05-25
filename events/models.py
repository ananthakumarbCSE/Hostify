from django.db import models
from django.utils import timezone
from cloudinary.models import CloudinaryField
from accounts.models import User

# Create your models here.



class Event(models.Model):
  
    CATEGORY_CHOICES = [
        ("technical",  "Technical"),
        ("sports",     "Sports"),
        ("cultural",   "Cultural"),
        ("speech",     "Speech"),
        ("workshop",   "Workshop"),
        ("music",      "Music"),
        ("networking", "Networking"),
        ("other",      "Other"),
    ]
    MODE_CHOICES = [
        ("online",  "Online"),
        ("offline", "Offline"),
        ("hybrid",  "Hybrid"),
    ]
    PRICE_CHOICES = [
        ("free", "Free"),
        ("paid", "Paid"),
    ]
    STATUS_CHOICES = [
        ("draft",     "Draft"),
        ("published", "Published"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]

    organizer    = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="organized_events")
    title        = models.CharField(max_length=200)
    slug         = models.SlugField(max_length=220, unique=True)
    description  = models.TextField()
    ai_knowledge = models.TextField(blank=True,help_text="Plain-text knowledge fed to the event chatbot (Groq)")
    logo         = CloudinaryField("logo",   blank=True, null=True) 
    banner       = CloudinaryField("banner", blank=True, null=True)
    category     = models.CharField(max_length=12, choices=CATEGORY_CHOICES)
    mode         = models.CharField(max_length=8,  choices=MODE_CHOICES)
    price_type   = models.CharField(max_length=4,  choices=PRICE_CHOICES, default="free")
    status       = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    
    start_datetime = models.DateTimeField()
    end_datetime   = models.DateTimeField()
    
    venue_name     = models.CharField(max_length=200, blank=True)
    venue_address  = models.TextField(blank=True)
    venue_city     = models.CharField(max_length=100, blank=True)
    venue_lat      = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    venue_lng      = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    online_link    = models.URLField(blank=True)

    chief_guest    = models.CharField(max_length=200, blank=True)

    total_capacity = models.PositiveIntegerField(default=0)

    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_datetime"]

    def __str__(self):
        return self.title

    @property
    def is_upcoming(self):
        return self.start_datetime > timezone.now()

    @property
    def is_past(self):
        return self.end_datetime < timezone.now()

class EventSession(models.Model):
    
    event      = models.ForeignKey(Event, on_delete=models.CASCADE,related_name="sessions")
    title      = models.CharField(max_length=200)
    description= models.TextField(blank=True)
    speaker    = models.CharField(max_length=30,blank=True,default="speaker name")
    start_time = models.DateTimeField()
    end_time   = models.DateTimeField()
    location   = models.CharField(max_length=200, blank=True,help_text="Room / hall / breakout")
    order      = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "start_time"]

    def __str__(self):
        return f"{self.event.title} — {self.title}"

class EventFAQ(models.Model):
    
    event    = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="faqs")
    question = models.CharField(max_length=300)
    answer   = models.TextField()
    order    = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]


class EventWishlist(models.Model):
    
    user            = models.ForeignKey("accounts.User", on_delete=models.CASCADE,related_name="wishlist")
    event           = models.ForeignKey(Event, on_delete=models.CASCADE,related_name="wishlisted_by")
    added_at        = models.DateTimeField(auto_now_add=True)
    reminder_sent   = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "event")


class EventSponsor(models.Model):
    
    TIER_CHOICES = [
        ("platinum", "Platinum"),
        ("gold",     "Gold"),
        ("silver",   "Silver"),
        ("bronze",   "Bronze"),
    ]
    
    event       = models.ForeignKey(Event, on_delete=models.CASCADE,related_name="sponsors")
    name        = models.CharField(max_length=120)
    logo        = CloudinaryField("sponsor_logo", blank=True, null=True)
    website     = models.URLField(blank=True)
    tier        = models.CharField(max_length=10, choices=TIER_CHOICES)
    amount      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.tier}) — {self.event.title}"
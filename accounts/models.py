from django.db import models
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField

# Create your models here.



class User(AbstractUser):
    
    ROLE_CHOICES = [("attendee",   "Attendee"),("organizer",  "Organizer")]
    
    email      = models.EmailField(unique=True)
    first_name = models.CharField(max_length=60)
    last_name  = models.CharField(max_length=60)
    photo      = CloudinaryField("photo", blank=True, null=True)
    role       = models.CharField(max_length=12, choices=ROLE_CHOICES, default="attendee")
    bio        = models.TextField(blank=True)
    
    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]
    
    def __str__(self):
        return f"{self.get_full_name()} <{self.email}>"

    @property
    def is_organizer(self):
        return self.role == "organizer"

    @property
    def is_attendee(self):
        return self.role == "attendee"


class OrganizerProfile(models.Model):
    
    TYPE_CHOICES = [("individual",   "Individual"),("organization", "Organization")]

    user         = models.OneToOneField(User, on_delete=models.CASCADE,related_name="organizer_profile")
    display_name = models.CharField(max_length=120)
    org_type     = models.CharField(max_length=14, choices=TYPE_CHOICES,default="individual")
    description  = models.TextField(blank=True)
    contact_phone= models.CharField(max_length=20, blank=True)
    contact_email= models.EmailField(blank=True)
    website      = models.URLField(blank=True)
    logo         = CloudinaryField("org_logo", blank=True, null=True)
    verified     = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name


class AttendeeProfile(models.Model):
    
    user       = models.OneToOneField(User, on_delete=models.CASCADE,related_name="attendee_profile")
    interests  = models.TextField(blank=True, help_text="Comma-separated interest tags")
    expertise  = models.TextField(blank=True)
    linkedin   = models.URLField(blank=True)
    twitter    = models.URLField(blank=True)
    github     = models.URLField(blank=True)
    website    = models.URLField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AttendeeProfile({self.user.email})"


class Notification(models.Model):
    
    TYPE_CHOICES = [
        ("reminder",      "Event Reminder"),
        ("ticket",        "Ticket Confirmed"),
        ("refund",        "Refund Update"),
        ("feedback",      "Feedback Request"),
        ("announcement",  "Organiser Announcement"),
    ]

    user       = models.ForeignKey(User, on_delete=models.CASCADE,related_name="notifications")
    notif_type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    title      = models.CharField(max_length=200)
    message    = models.TextField()
    link       = models.CharField(max_length=300, blank=True)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.notif_type} → {self.user.email}"


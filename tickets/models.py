from django.db import models
import uuid
import qrcode
import io
from cloudinary.uploader import upload as cloudinary_upload
from django.utils import timezone
from cloudinary.models import CloudinaryField

# Create your models here.

class TicketTier(models.Model):
    
    TIER_TYPE_CHOICES = [
        ("free",        "Free"),
        ("general",     "General"),
        ("vip",         "VIP"),
        ("early_bird",  "Early Bird"),
        ("student",     "Student"),
        ("custom",      "Custom"),
    ]
    event            = models.ForeignKey(
        "events.Event", on_delete=models.CASCADE, related_name="ticket_tiers"
    )
    name             = models.CharField(max_length=100)
    tier_type        = models.CharField(max_length=12, choices=TIER_TYPE_CHOICES)
    description      = models.TextField(blank=True)
    price            = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    early_bird_price = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    early_bird_expires = models.DateTimeField(null=True, blank=True)
    capacity         = models.PositiveIntegerField(default=0,help_text="0 = unlimited")
    max_per_order    = models.PositiveSmallIntegerField(default=10)
    sale_start       = models.DateTimeField(null=True, blank=True)
    sale_end         = models.DateTimeField(null=True, blank=True)
    is_active        = models.BooleanField(default=True)

    def current_price(self):
       
        if (self.early_bird_price and self.early_bird_expires
                and timezone.now() < self.early_bird_expires):
            return self.early_bird_price
        return self.price

    def tickets_sold(self):
        return self.tickets.filter(status="confirmed").count()

    def tickets_remaining(self):
        if self.capacity == 0:
            return None
        return max(0, self.capacity - self.tickets_sold())

    def __str__(self):
        return f"{self.event.title} — {self.name}"


class DiscountCode(models.Model):
    DISCOUNT_TYPE = [
        ("percentage", "Percentage"),
        ("flat",       "Flat Amount"),
    ]

    event        = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="discount_codes")
    code         = models.CharField(max_length=30)
    discount_type= models.CharField(max_length=10, choices=DISCOUNT_TYPE)
    value        = models.DecimalField(max_digits=8, decimal_places=2)
    max_uses     = models.PositiveIntegerField(default=0, help_text="0 = unlimited")
    used_count   = models.PositiveIntegerField(default=0)
    expires_at   = models.DateTimeField(null=True, blank=True)
    is_active    = models.BooleanField(default=True)

    class Meta:
        unique_together = ("event", "code")

    def is_valid(self):
        from django.utils import timezone
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        if self.max_uses > 0 and self.used_count >= self.max_uses:
            return False
        return True

    def __str__(self):
        return f"{self.code} ({self.event.title})"


class Ticket(models.Model):
    STATUS_CHOICES = [
        ("pending",   "Pending Payment"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("refunded",  "Refunded"),
    ]

    uid          = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    attendee     = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="tickets")
    tier         = models.ForeignKey(TicketTier, on_delete=models.CASCADE,related_name="tickets")
    order        = models.ForeignKey("payments.Order", on_delete=models.CASCADE, related_name="tickets",null=True, blank=True)
    status       = models.CharField(max_length=10, choices=STATUS_CHOICES,default="pending")
    qr_code      = CloudinaryField("qr_code", blank=True, null=True)
    qr_token     = models.CharField(max_length=64, blank=True,
                                     help_text="Short token embedded in QR")
    checked_in   = models.BooleanField(default=False)
    issued_at    = models.DateTimeField(auto_now_add=True)
    price_paid   = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def generate_qr(self):
        
        self.qr_token = str(self.uid)
        data = f"EVENTSPHERE:{self.qr_token}"
        img = qrcode.make(data)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        result = cloudinary_upload(buf, public_id=f"qr/{self.uid}",resource_type="image")
        self.qr_code = result["public_id"]
        self.save(update_fields=["qr_code", "qr_token"])

    def __str__(self):
        return f"Ticket {self.uid} — {self.attendee.email}"


class CheckIn(models.Model):
    
    ticket      = models.OneToOneField(Ticket, on_delete=models.CASCADE,related_name="checkin")
    scanned_by  = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="checkins")
    scanned_at  = models.DateTimeField(auto_now_add=True)
    method      = models.CharField(max_length=10, 
                                   choices=[
        ("qr_scan", "QR Scan"), ("manual", "Manual Entry")
    ], default="manual")
    notes       = models.TextField(blank=True)

    def __str__(self):
        return f"CheckIn: {self.ticket.uid} @ {self.scanned_at}"
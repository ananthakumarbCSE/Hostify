from django.db import models

# Create your models here.

class Order(models.Model):
    STATUS_CHOICES = [
        ("pending",   "Pending"),
        ("paid",      "Paid"),
        ("failed",    "Failed"),
        ("refunded",  "Refunded"),
        ("cancelled", "Cancelled"),
    ]
    user             = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="orders")
    event            = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="orders")
    status           = models.CharField(max_length=10, choices=STATUS_CHOICES,default="pending")
    subtotal         = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total            = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency         = models.CharField(max_length=3, default="INR")
    discount_code    = models.ForeignKey("tickets.DiscountCode", on_delete=models.SET_NULL, null=True, blank=True)

    razorpay_order_id  = models.CharField(max_length=100, blank=True)
    razorpay_payment_id= models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order#{self.pk} — {self.user.email} — {self.status}"


class OrderItem(models.Model):
    
    order       = models.ForeignKey(Order, on_delete=models.CASCADE,related_name="items")
    ticket_tier = models.ForeignKey("tickets.TicketTier", on_delete=models.CASCADE, related_name="order_items")
    quantity    = models.PositiveSmallIntegerField(default=1)
    unit_price  = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.quantity} * {self.ticket_tier.name} in Order: {self.order_id}"


class Refund(models.Model):
    
    STATUS_CHOICES = [
        ("requested", "Requested"),
        ("approved",  "Approved"),
        ("rejected",  "Rejected"),
        ("processed", "Processed"),
    ]

    order       = models.ForeignKey(Order, on_delete=models.CASCADE,related_name="refunds")
    requested_by= models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="refund_requests")
    reason      = models.TextField()
    amount      = models.DecimalField(max_digits=12, decimal_places=2)
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES,default="requested")
    reviewed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True,related_name="reviewed_refunds")
    review_note = models.TextField(blank=True)
    requested_at= models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Refund({self.status}) — Order#{self.order_id}"


class OrganizerPayout(models.Model):

    STATUS_CHOICES = [
        ("pending",   "Pending"),
        ("processed", "Processed"),
        ("failed",    "Failed"),
    ]

    event      = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="payouts")
    organizer  = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="payouts")
    gross      = models.DecimalField(max_digits=12, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net        = models.DecimalField(max_digits=12, decimal_places=2)
    status     = models.CharField(max_length=10, choices=STATUS_CHOICES,default="pending")
    processed_at = models.DateTimeField(null=True, blank=True)
    reference_id = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Payout({self.status}) — {self.event.title}"


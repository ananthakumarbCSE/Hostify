from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.





class EventReview(models.Model):
    
    event      = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="reviews")
    author     = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="reviews")
    rating     = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    body       = models.TextField()
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "author")

    def __str__(self):
        return f"Review({self.rating}★) — {self.event.title} by {self.author.email}"


class PostEventFeedback(models.Model):
    ticket     = models.OneToOneField("tickets.Ticket", on_delete=models.CASCADE, related_name="feedback")
    rating     = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    text       = models.TextField(blank=True)
    sent_at    = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Feedback — Ticket {self.ticket.uid}"


class NetworkingOptIn(models.Model):
    
    event          = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="networking_optins")
    user           = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="networking_optins")
    show_linkedin  = models.BooleanField(default=False)
    show_email     = models.BooleanField(default=False)
    opted_in_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "user")

    def __str__(self):
        return f"NetworkingOptIn — {self.user.email} @ {self.event.title}"


class AttendeeQuestion(models.Model):
    event      = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="attendee_questions")
    asked_by   = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="questions_asked")
    question   = models.TextField()
    answer     = models.TextField(blank=True)
    answered_by= models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True,related_name="questions_answered")
    is_public  = models.BooleanField(default=True)
    asked_at   = models.DateTimeField(auto_now_add=True)
    answered_at= models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Q: {self.question[:60]}"

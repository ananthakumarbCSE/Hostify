from django.db import models

# Create your models here.

class EventAIKnowledge(models.Model):
    
    event       = models.OneToOneField("events.Event", on_delete=models.CASCADE, related_name="ai_knowledge_obj")
    knowledge   = models.TextField(help_text="Plain text fed to Groq as system context")
    last_synced = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Knowledge — {self.event.title}"


class AIConversation(models.Model):
    event    = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="ai_conversations")
    user     = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="ai_conversations",null=True, blank=True)
    messages = models.JSONField(default=list)
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("event", "user")

    def __str__(self):
        return f"Chat — {self.event.title} / {self.user}"


class AIRecommendation(models.Model):
    user        = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="ai_recommendations"
    )
    event_ids   = models.JSONField(default=list)
    reason_map  = models.JSONField(default=dict,help_text="event_id → short reason string")
    generated_at= models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Recs — {self.user.email}"


class AIGenerationLog(models.Model):
    GEN_TYPE = [
        ("description",     "Event Description Draft"),
        ("logo_prompt",     "Logo Generation Prompt"),
        ("schedule",        "Schedule Builder"),
        ("recommendation",  "Event Recommendation"),
        ("chatbot",         "Chatbot Response"),
        ("form_autofill",   "Form Autofill"),
    ]

    gen_type    = models.CharField(max_length=16, choices=GEN_TYPE)
    event       = models.ForeignKey("events.Event", on_delete=models.SET_NULL, null=True, blank=True,related_name="ai_logs")
    user        = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True,related_name="ai_logs")
    prompt      = models.TextField()
    result      = models.TextField(blank=True)
    tokens_used = models.PositiveIntegerField(default=0)
    latency_ms  = models.PositiveIntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"AILog({self.gen_type}) — {self.created_at:%Y-%m-%d %H:%M}"
from django.db import models
from django.contrib.auth.models import User
import uuid

# ChatSession: Har ek naye chat thread ke liye alag ID
class ChatSession(models.Model):
    # UUID: Unique ID jo har chat ko alag pehchan degi
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # User: Kis user ki chat hai
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # Title: Chat ka naam (Message ke pehle 25 words)
    title = models.CharField(max_length=255, default="New Chat")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

# ChatMessage: Chat ke andar ke individual messages
class ChatMessage(models.Model):
    # Session: Kis chat thread ka message hai
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages', null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # Role: Kisne message bheja? 'user' (Aap) ya 'ai' (Edith)
    role = models.CharField(max_length=10) 
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

# UserProfile: User ki personal details (jaise naam, preference)
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # JSONField: Flexible storage taaki hum kuch bhi save kar sakein dictionary format me
    personal_facts = models.JSONField(default=dict)

    def __str__(self):
        return f"Profile for {self.user.username}"

# Knowledge: AI ka Global Brain. Jo bhi aap sikhayenge yahan save hoga.
class Knowledge(models.Model):
    # content: Wo sentence jo AI ne seekha hai (Unique taaki duplicate na ho)
    content = models.TextField(unique=True)
    # source_user: Kisne ye sikhaya (Optional)
    source_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.content[:50]

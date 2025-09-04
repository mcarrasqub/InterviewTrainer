from django.contrib import admin
from .models import InterviewSession, ChatMessage, UserProfile

@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'session_type', 'created_at', 'is_active']
    list_filter = ['session_type', 'is_active', 'created_at']
    search_fields = ['title', 'user__username']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'is_user', 'content_preview', 'timestamp']
    list_filter = ['is_user', 'timestamp']
    search_fields = ['content', 'session__title']
    
    def content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Contenido'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'preferred_interview_type', 'total_sessions', 'created_at']
    list_filter = ['preferred_interview_type', 'created_at']
    search_fields = ['user__username', 'user__email']
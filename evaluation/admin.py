from django.contrib import admin
from .models import CompetencyScore, FeedbackReport, UserAnalytics, CompetencyDefinition

@admin.register(CompetencyScore)
class CompetencyScoreAdmin(admin.ModelAdmin):
    list_display = ['session', 'competency_name', 'score']
    list_filter = ['competency_name', 'score']
    search_fields = ['session__user__username', 'competency_name']

@admin.register(FeedbackReport)
class FeedbackReportAdmin(admin.ModelAdmin):
    list_display = ['session', 'average_score', 'performance_level', 'generated_at']
    list_filter = ['performance_level', 'generated_at']
    search_fields = ['session__user__username', 'session__title']
    ordering = ['-generated_at']
    readonly_fields = ['generated_at']

@admin.register(UserAnalytics)
class UserAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_sessions_evaluated', 'average_overall_score', 'last_updated']
    list_filter = ['last_updated']
    search_fields = ['user__username', 'user__email']
    ordering = ['-average_overall_score']
    readonly_fields = ['last_updated']

@admin.register(CompetencyDefinition)
class CompetencyDefinitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'is_active', 'order']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['order', 'name']
    list_editable = ['is_active', 'order']

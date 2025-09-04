"""
URL configuration for lumo_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('interview_trainer.urls')),
    path('api/', include('interview_trainer.api_urls')),
    path('evaluation/', include('evaluation.urls')),
    path('api/evaluation/', include('evaluation.api_urls')),
    path('auth/', include('django.contrib.auth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
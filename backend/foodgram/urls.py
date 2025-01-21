from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

from recipes.views import redirect_to_recipe


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('s/<slug:short_link>/', redirect_to_recipe, name='redirect_to_recipe'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.urls import path
from django.views.static import serve as static_serve

def healthz(_request): 
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tracker.urls')),
]

urlpatterns += [path("healthz", healthz)]

# Serve built MkDocs site at /site (index and assets). For small docs this is fine
# If you host docs elsewhere, remove this mapping.
urlpatterns += [
    path('site/', lambda r: static_serve(r, 'index.html', document_root=settings.MKDOCS_SITE_DIR)),
    re_path(r'^site/(?P<path>.*)$', static_serve, {'document_root': settings.MKDOCS_SITE_DIR}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

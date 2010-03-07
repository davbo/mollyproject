from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin

from molly.conf import applications

admin.autodiscover()

urlpatterns = patterns('',
    (r'adm/(.*)', admin.site.root),

    # These are how we expect all applications to be eventually.
    (r'^contact/', applications.contact.urls),
    (r'^service-status/', applications.service_status.urls),
    (r'^weather/', applications.weather.urls),
    (r'^library/', applications.library.urls),
    (r'^weblearn/', applications.weblearn.urls),
    (r'^auth/', applications.auth.urls),

    # These ones still need work
    (r'^search/', include('molly.googlesearch.urls', 'search', 'search')),
    (r'^maps/', include('molly.maps.urls', 'maps', 'maps')),
    (r'^osm/', include('molly.osm.urls', 'osm', 'osm')),

    (r'', include('molly.core.urls', 'core', 'core')),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^site-media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.SITE_MEDIA_PATH})
    )

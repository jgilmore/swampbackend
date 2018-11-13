"""swampbackend URL Configuration
"""
from django.conf.urls import url, include
from django.contrib import admin
from bog import views
from rest_framework import routers

router = routers.SimpleRouter()
router.register(r'diceset', views.ListCreateDiceSetView)
router.register(r'play', views.CreateUpdatePlayView)
router.register(r'puzzle', views.ListCreatePuzzleView)
router.register(r'player', views.PlayerModelView)
router.register(r'word', views.WordListViewSet, base_name='word')

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^wordlist/(\d+)/$', views.listwords, name="wordlist"),
    url(r'admin/', admin.site.urls, name='admin'),
    url(r'^$', views.api_root, name='api_root'),
    url(r'^auth/', include('rest_auth.urls')),
    url(r'^auth/', include('rest_auth.registration.urls')),
]

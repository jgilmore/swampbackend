"""swampbackend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from bog.views import (ListCreatePuzzleView, CreateUpdatePlayView, ListWordsView,
                       PlayerModelView, ListCreateDiceSetView, api_root, UserModelView)
from rest_framework import routers

router = routers.SimpleRouter()
router.register(r'diceset', ListCreateDiceSetView)
router.register(r'play', CreateUpdatePlayView)
router.register(r'puzzle', ListCreatePuzzleView)
router.register(r'player', PlayerModelView)
router.register(r'user', UserModelView, base_name='user')

router.register(r'wordlist', ListWordsView, base_name='wordlist')
# Replaced by manually adding the url patterns, in order to require an extra "play_id"
# argument in the URL.
urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'admin', admin.site.urls, name='admin'),
    url(r'^$', api_root, name='api_root'),
]

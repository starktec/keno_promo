from django.urls import path

from . import consumers_bilhete

websocket_urlpatterns = [
  path('ws/<str:token_tv>/bilhete/<str:token>/connect/',consumers_bilhete.ConexaoBilheteConsumer.as_asgi())
]
from django.urls import path

from . import consumers_bilhete

websocket_urlpatterns = [
  path('ws/<str:token>/sorteio/<int:sorteio>/bilhete/<str:bilhete>/connect/',consumers_bilhete.ConexaoBilheteConsumer.as_asgi())
]
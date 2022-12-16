from django.urls import path

from . import consumers_bilhete
from . import consumers

websocket_urlpatterns = [
  path('ws/<str:token>/sorteio/<int:sorteio>/bilhete/<str:bilhete>/connect/',consumers_bilhete.ConexaoBilheteConsumer.as_asgi()),
  path('ws/dados/realtime/', consumers.DadosTempoRealConsumer.as_asgi()),
  path('ws/tela/<str:token>/connect/',consumers.ConexaoTelaConsumer.as_asgi()),
]
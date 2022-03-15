from django.urls import path

from . import consumers, consumers_bilhete

websocket_urlpatterns = [
  path('ws/tela/<str:token>/connect/',consumers.ConexaoTelaConsumer.as_asgi()),
  path('ws/dados/realtime/', consumers.DadosTempoRealConsumer.as_asgi()),
  path('ws/<str:token_tv>/bilhete/<str:token>/connect/',consumers_bilhete.ConexaoBilheteConsumer.as_asgi())
]
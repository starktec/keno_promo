from rest_framework.permissions import BasePermission

from jogo.models import Jogador


class EhJogador(BasePermission):
    def has_permission(self, request, view):
        if 'Authorization' in request.headers and "Token" in request.headers['Authorization']:
            token = request.headers['Authorization'].split("Token ")[1]
            return Jogador.objects.filter(usuario_token=token,user__active=True).exists()
        return False
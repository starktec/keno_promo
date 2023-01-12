import random
import string

from django.utils.crypto import get_random_string

from jogo.models import Jogador


def run():
    quantidade = Jogador.objects.filter(codigo__isnull=True).count()
    if quantidade>0:
        jogadores = []
        for jogador in Jogador.objects.filter(codigo__isnull=True):
            codigo = get_random_string(length=6, allowed_chars=string.digits)
            while Jogador.objects.filter(codigo=codigo).exists():
                codigo = get_random_string(length=6, allowed_chars=string.digits)
            jogador.codigo = codigo
            jogadores.append(jogador)
        Jogador.objects.bulk_update(jogadores,["codigo"])
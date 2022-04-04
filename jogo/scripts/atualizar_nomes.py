from jogo.models import Cartela


def run():
    cartelas_update = []
    for c in Cartela.objects.filter(jogador__isnull=False):
        if c.nome != c.jogador.nome:
            c.nome = c.jogador.nome
            cartelas_update.append(c)

    Cartela.objects.bulk_update(cartelas_update,['nome'])

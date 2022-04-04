import datetime

from jogo.models import Cartela, Partida, CartelaVencedora


def run():
    agora = datetime.datetime.now()
    partidas = Partida.objects.filter(data_partida__lt=agora)
    print(Cartela.objects.count())
    for p in partidas:
        vencedores = CartelaVencedora.objects.filter(partida=p)
        codigos = [x.cartela.codigo for x in vencedores]
        if p.cartelas_participantes:
            print(Cartela.objects.filter(
                jogador__isnull=True, partida=p, codigo__in=p.cartelas_participantes.split(",")
            ).exclude(codigo__in=codigos).delete())
        else:
            if codigos:
                vencedores.delete()
                print(Cartela.objects.filter(
                    jogador__isnull=True, partida=p).exclude(codigo__in=codigos).delete())
            else:
                print(Cartela.objects.filter(jogador__isnull=True, partida=p).delete())

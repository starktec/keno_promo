from jogo.consts import StatusJogador
from jogo.models import Jogador


def run():
    jogadores = Jogador.objects.all()
    analisados = [jogadores.first()]
    nomes = [jogadores.first().usuario[:15]]
    cont = 1000
    for j in jogadores:
        if cont == 1000:
            break
        if j not in analisados:
            suspeitos = Jogador.objects.filter(usuario__startswith=j.usuario[:15]).exclude(id=j.id)
            if suspeitos:
                j.status = StatusJogador.SUSPEITO
                update_jogadores = [j]
                for suspeito in suspeitos:
                    suspeito.status = StatusJogador.SUSPEITO
                    update_jogadores.append(suspeito)

                Jogador.objects.bulk_update(update_jogadores, ["status"])

                analisados += update_jogadores
            else:
                analisados.append(j)
            cont += 1
            print(len(suspeitos))

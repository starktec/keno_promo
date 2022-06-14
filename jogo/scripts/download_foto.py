from jogo.models import Jogador
from jogo.utils import download_foto
def run():
    for jogador in Jogador.objects.filter(conta__isnull=False, foto__isnull=True):
        print(f"verficando @{jogador.usuario}")
        conta = jogador.conta
        print(f" - conta {conta.id}")
        jogador.foto = download_foto(conta.pic, conta.instagram_id)
        print(f" - foto {jogador.foto}")
        jogador.save()
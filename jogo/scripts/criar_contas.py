from jogo.consts import StatusJogador
from jogo.models import InstagramAccount, Jogador
from jogo.utils import download_foto


def run():
    print("Começando....")

    arquivo = open("seguidores.csv")
    linha1 = True
    for linha in arquivo.readlines():
        if linha and not linha1:

            campos = linha[:-1].split(";")
            print(campos)
            if len(campos)>2:
                if len(campos) == 4:
                    id,username,fullname,pic = campos
                elif len(campos)==3:
                    id = campos[0]
                    username = campos[1]
                    fullname = campos[2]
                    pic = ""
                else:
                    id = campos[0]
                    username = campos[1]
                    fullname = "".join(campos[2:-2])
                    pic = campos[-1]

                InstagramAccount.objects.get_or_create(
                        instagram_id=id,
                        username = username,
                        full_name = fullname,
                        pic = pic
                    )

        else:
            linha1 = False
    print("Fechando o arquivo e salvando os objetos")
    arquivo.close()

    #InstagramAccount.objects.bulk_create(contas)

    i_contas = InstagramAccount.objects.all()
    jogadores = []
    for conta in i_contas:
        # busca pelo ID
        j = Jogador.objects.filter(usuario_id=conta.instagram_id).first()
        if not j:
            # busca pelo nome de usuario
            j = Jogador.objects.filter(usuario=conta.username)
            if j.count()>1:
                j.update(status=StatusJogador.SUSPENSO)
                print(f"Conta {conta.instagram_id} - {conta.username} - {conta.full_name} tem {j.count()} jogadores")
                continue
            j = j.first()

        # encontrou jogador
        if j:
            update = False
            if not j.usuario_id:
                j.usuario_id = conta.instagram_id
                update = True
            if not j.nome or j.nome != conta.full_name:
                j.nome = conta.full_name
                update = True
            if not j.usuario or j.usuario != conta.username:
                j.usuario = conta.username
                update = True
            if not j.status == StatusJogador.ATIVO:
                j.status = StatusJogador.ATIVO
                update = True
            if not j.foto and conta.pic:
                j.foto = download_foto(conta.pic,conta.instagram_id)
                update = True
            if not j.conta:
                j.conta = conta
                update = True
            if update:
                print(f"Preparando atualização: {j.usuario}")
                jogadores.append(j)

    if jogadores:
        Jogador.objects.bulk_update(jogadores,["nome","usuario","usuario_id","status","conta"])

    num_jogadores_restantes = Jogador.objects.exclude(id__in=[c.id for c in jogadores]).count()
    print(f"Restam {num_jogadores_restantes} jogadores")

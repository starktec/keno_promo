import os

import requests
from django.conf import settings
from instagrapi import Client
from instagrapi.exceptions import ClientNotFoundError, UserNotFound

from jogo.consts import StatusJogador
from jogo.models import Jogador, InstagramAccount
import time

from jogo.utils import download_foto

JOGOSDASORTEBR_ID = "44328406722"

CONTAS = [
    {"username":"teste.user.1","password":"teste123@"},
    {"username":"teste.user.2","password":"teste123@"},
    {"username":"teste.user.3","password":"teste123@"},
    {"username":"teste.user.4","password":"teste123@"},
    {"username":"teste.user.5","password":"teste123@"},
]

TIME_MIN = 15

def run():
    print("Fazendo login")
    clients = []
    for i_conta in CONTAS:
        print(f"Fazendo login na conta {i_conta.get('username')}...")
        time.sleep(15)
        con_client = Client()
        con_client.login(i_conta.get("username"),i_conta.get("password"))
        clients.append(con_client)

    #clients.login("gdsgamesdev","EdsTecBr@123")

    fake = []
    nao_segue = []
    jogadores = Jogador.objects.filter(conta__isnull=True)
    print(f"Quantidade jogadores a analisar: {jogadores.count()}")
    contador = 1
    posicao = 0
    for jogador in jogadores:
        # Proxima conta
        client = clients[posicao%len(CONTAS)]
        posicao += 1
        print(f"Analisando {jogador.usuario} n°{contador}")
        contador += 1
        print(" - Aguardando 15s para a primeira busca...")
        time.sleep(15)
        try:
            usuario = client.user_info_by_username(jogador.usuario)
            if not usuario:
                raise ClientNotFoundError()
        except (ClientNotFoundError,UserNotFound) as cnfe:
            print(" - Conta inexistente")
            # Conta nao existe
            jogador.status = StatusJogador.CANCELADO
            fake.append(jogador.usuario)
            continue

        print(f" - Aguardando mais 15s para a segunda busca...")
        client = clients[posicao % len(CONTAS)]
        posicao += 1
        usuarios = client.search_followers(JOGOSDASORTEBR_ID,jogador.usuario)
        usuarios_dict = {u.username:u for u in usuarios}
        if usuarios and jogador.usuario in usuarios_dict.keys():
            print(" - Usuario encontrado. Criando registro e atualizado jogador...")
            # Passou no teste atualizando
            usuario = usuarios_dict.get(jogador.usuario)
            conta = InstagramAccount.objects.create(
                instagram_id=usuario.pk,
                username=usuario.username,
                full_name=usuario.full_name,
                pic=str(usuario.profile_pic_url)
            )
            jogador.conta = conta
            jogador.usuario_id = conta.instagram_id
            jogador.status=StatusJogador.ATIVO
            jogador.foto = download_foto(conta.pic,conta.instagram_id)
        else:
            # Usuario nao segue a Jogosdasortebr
            jogador.status=StatusJogador.SUSPENSO
            print(" - Usuario existe mas nao segue a Jogosdasortebr")
            nao_segue.append(jogador.usuario)
        jogador.save()

    print(f"Perfis Fake: {len(fake)}")
    print(f"Perfis que não seguem: {len(nao_segue)}")

    arquivo = open("relatorio.txt","w",encoding="utf-8")
    arquivo.write("FAKE:\n")
    arquivo.write(str(fake))
    arquivo.write("\n")
    arquivo.write("NAO SEGUE:\n")
    arquivo.write(str(nao_segue))
    arquivo.close()

import datetime
import json
import random
import pickle

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from instagrapi import Client
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes

from jogo import local_settings
from jogo.choices import AcaoTipoChoices
from jogo.models import Jogador, Partida, Cartela, Regra, Configuracao

CLIENT = None

def setSocialConnection():
    with transaction.atomic():
        global CLIENT
        configuracao = Configuracao.objects.select_for_update().last()
        if configuracao:
            if not configuracao.instagram_connection:
                CLIENT = Client()
                CLIENT.login(local_settings.INSTAGRAM_USER, local_settings.INSTAGRAM_PASSWORD)
                configuracao.instagram_connection = pickle.dumps(CLIENT)
                configuracao.save()
            else:
                CLIENT = pickle.loads(configuracao.instagram_connection)
                if not CLIENT.get_settings():
                    CLIENT = Client()
                    CLIENT.login(local_settings.INSTAGRAM_USER, local_settings.INSTAGRAM_PASSWORD)
                    configuracao.instagram_connection = pickle.dumps(CLIENT)
                    configuracao.save()

setSocialConnection()

@csrf_exempt
@require_http_methods(["GET"])
def index_social(request):
    seguir_url = ""
    seguir = "@"
    agora = datetime.datetime.now()
    partida = Partida.objects.filter(data_partida__gt=agora).order_by('data_partida').first()
    if partida:
        acoes = partida.regra.acao_set.all()
        for acao in acoes:
            if acao.tipo == AcaoTipoChoices.SEGUIR:
                seguir_url = acao.perfil_social.url
                seguir += seguir_url.split("/www.instagram.com/")[1]
                if seguir.endswith("/"):
                    seguir = seguir[:-1]
    return JsonResponse(data={"seguir_url":seguir_url,"seguir":seguir}, status=200)


@api_view(['POST'])
def gerar_bilhete(request):
    mensagem = ""
    if 'Authorization' in request.headers and "Token" in request.headers['Authorization']:
        token = request.headers['Authorization'].split("Token ")[1]
        dados = json.loads(request.body)
        perfil = dados.get("perfil")
        if perfil:
            if perfil.startswith("@"):
                perfil = perfil[1:]
            if "/" in perfil:
                perfil = perfil.split("/www.instagram.com/")[1].split("/")[0]
            try:
                perfil = perfil.lower()
                agora = datetime.datetime.now()
                partida = Partida.objects.filter(data_partida__gt=agora).order_by("data_partida").first()
                if partida:
                    perfil_id = ""
                    for acao in partida.regra.acao_set.all():
                        if acao.tipo == AcaoTipoChoices.SEGUIR:
                            perfil_id = acao.perfil_social.perfil_id
                            break
                    if perfil_id:
                        #jogador_instagram_id = CLIENT.user_id_from_username(perfil)
                        #jogador_seguindo = CLIENT.search_followers(user_id=perfil_id, query=perfil)
                        jogador_seguindo = True
                        if jogador_seguindo:
                            jogador, jogador_criado = Jogador.objects.get_or_create(usuario=perfil)#, usuario_token=token)
                            nome = ""
                            # atualizar o nome do jogador
                            if jogador.nome == jogador.usuario:
                                #nome = CLIENT.user_info_by_username(perfil).full_name
                                if nome:
                                    jogador.nome = nome
                                    jogador.save()
                                else:
                                    nome = jogador.nome

                            cartela = Cartela.objects.filter(jogador=jogador, partida=partida).first()
                            if cartela:
                                mensagem = f"Você já está participando do sorteio {partida.id}"
                            else:
                                cartelas = Cartela.objects.filter(partida=partida, jogador__isnull=True)
                                if cartelas:
                                    cartela = random.choice(cartelas)
                                    cartela.jogador = jogador
                                    if nome:
                                        cartela.nome = nome
                                    cartela.save()
                                else:
                                    mensagem = "Cartelas esgotadas"
                                    return JsonResponse(data={"detail": mensagem}, status=404)
                            return JsonResponse(
                                data={"detail": mensagem, "bilhete": cartela.hash, "sorteio": int(cartela.partida.id)})
                        else:
                            mensagem = "Você ainda não segue o perfil?"
                            return JsonResponse(data={"detail": mensagem}, status=404)
                    else:
                        mensagem = "Não foi encontrado uma regra do tipo 'Seguir um perfil'"
                        return JsonResponse(data={"detail": mensagem}, status=200)
                else:
                    mensagem = "Não há sorteios disponíveis no momento"
                    return JsonResponse(data={"detail": mensagem}, status=404)
            except Exception as e:
                mensagem = "Perfil não encontrado"
                return JsonResponse(data={"detail":mensagem},status=403)
        else:
            mensagem = "Faltam dados de perfil"
            return JsonResponse(data={"detail": mensagem}, status=403)

    return JsonResponse(data={"detail":mensagem},status=403)


import datetime
import json
import random
import pickle
import time

import requests
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from instagrapi import Client
from instagrapi.exceptions import ClientLoginRequired, UserNotFound, LoginRequired, PleaseWaitFewMinutes
from instagrapi.types import User
from requests.adapters import HTTPAdapter
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
#from urllib3 import Retry

from jogo import local_settings
from jogo.choices import AcaoTipoChoices
from jogo.models import Jogador, Partida, Cartela, Regra, Configuracao

import logging

from jogo.utils import get_connection

LOGGER = logging.getLogger(__name__)

CLIENT = None

def setSocialConnection():
    with transaction.atomic():
        global CLIENT
        configuracao = Configuracao.objects.select_for_update().last()
        if configuracao:
            try:
                if not configuracao.instagram_connection:
                    CLIENT = Client()
                    CLIENT.set_proxy(get_connection())
                    CLIENT.login(local_settings.INSTAGRAM_USER, local_settings.INSTAGRAM_PASSWORD)
                    configuracao.instagram_connection = pickle.dumps(CLIENT)
                    configuracao.save()
                else:
                    CLIENT = pickle.loads(configuracao.instagram_connection)
                    if not CLIENT.get_settings():
                        CLIENT = Client()
                        CLIENT.set_proxy(get_connection())
                        CLIENT.login(local_settings.INSTAGRAM_USER, local_settings.INSTAGRAM_PASSWORD)
                        configuracao.instagram_connection = pickle.dumps(CLIENT)
                        configuracao.save()
            except:
                pass

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
    else:
        configuracao = Configuracao.objects.last()
        seguir_url = configuracao.perfil_default
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
                    jogador = Jogador.objects.filter(usuario=perfil).first()
                    nome = ""
                    jogador_seguindo = True
                    if not jogador:
                        try:
                            global CLIENT

                            jogador_instagram = None
                            try:
                                api = Client()
                                api.set_proxy(get_connection())
                                jogador_instagram = api.user_info_by_username(perfil)
                                if jogador_instagram and not isinstance(jogador_instagram,User):
                                    raise LoginRequired
                            except (LoginRequired, PleaseWaitFewMinutes):
                                try:
                                    if CLIENT:
                                        CLIENT.set_proxy(get_connection())
                                        jogador_instagram = CLIENT.user_info_by_username_v1(perfil)
                                        #time.sleep(3)
                                except UserNotFound:
                                    raise UserNotFound
                                except Exception:
                                    pass
                            CLIENT.set_proxy(get_connection())
                            jogador_seguindo = CLIENT.search_followers_v1(user_id=perfil_id, query=perfil) if CLIENT else True
                        except UserNotFound as e:
                            LOGGER.exception(msg=e)
                            mensagem = "Perfil não encontrado, tente novamente mais tarde"
                            return JsonResponse(data={"detail": mensagem}, status=403)
                        except PleaseWaitFewMinutes:
                            pass
                        finally:
                            if jogador_seguindo:
                                nome = jogador_instagram.full_name if jogador_instagram else perfil
                                partida.novos_participantes += 1
                                partida.save()
                                LOGGER.info("Criando Jogador "+perfil)
                                jogador = Jogador.objects.create(usuario=perfil,nome=nome)
                            else:
                                mensagem = "Você ainda não segue o perfil?"
                                LOGGER.info(mensagem)
                                return JsonResponse(data={"detail": mensagem}, status=404)

                    else:
                        CLIENT.set_proxy(get_connection())
                        jogador_seguindo = CLIENT.search_followers_v1(user_id=perfil_id,
                                                                      query=perfil) if CLIENT else True
                        if not jogador_seguindo:
                            mensagem = "Você deixou de seguir o perfil?"
                            LOGGER.info(mensagem)
                            return JsonResponse(data={"detail": mensagem}, status=404)

                    # atualizar o nome do jogador
                    if jogador.nome == jogador.usuario:
                        CLIENT.set_proxy(get_connection())
                        nome = CLIENT.user_info_by_username(perfil).full_name
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
                            LOGGER.info(mensagem)
                            return JsonResponse(data={"detail": mensagem}, status=404)
                    return JsonResponse(
                        data={"detail": mensagem, "bilhete": cartela.hash, "sorteio": int(cartela.partida.id)})

                else:
                    mensagem = "Não foi encontrado uma regra do tipo 'Seguir um perfil'"
                    LOGGER.info(mensagem)
                    return JsonResponse(data={"detail": mensagem}, status=200)
            else:
                mensagem = "Não há sorteios disponíveis no momento"
                LOGGER.info(mensagem)
                return JsonResponse(data={"detail": mensagem}, status=404)

        else:
            mensagem = "Faltam dados de perfil"
            LOGGER.info(mensagem)
            return JsonResponse(data={"detail": mensagem}, status=403)
    LOGGER.info(mensagem)
    return JsonResponse(data={"detail":mensagem},status=403)


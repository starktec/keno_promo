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
from requests.adapters import HTTPAdapter
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from urllib3 import Retry

from jogo import local_settings
from jogo.choices import AcaoTipoChoices
from jogo.models import Jogador, Partida, Cartela, Regra, Configuracao

import logging
LOGGER = logging.getLogger(__name__)

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
                    jogador = Jogador.objects.filter(usuario=perfil, usuario_token=token).first()
                    nome = ""
                    if not jogador:
                        try:
                            """
                            headers_list = [
                                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74',
                                "aplication/json",
                                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36",
                                "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0",
                                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36 OPR/38.0.2220.41",
                                "Mozilla/5.0 (iPhone; CPU iPhone OS 13_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1",
                                "Mozilla/5.0 (compatible; MSIE 9.0; Windows Phone OS 7.5; Trident/5.0; IEMobile/9.0)",
                                "Googlebot/2.1 (+http://www.google.com/bot.html)"
                            ]
                            headers = {
                                'user-agent': random.choice(headers_list)}
                            payload = {'__a': '1'}

                            session = requests.Session()
                            retry = Retry(connect=3, backoff_factor=0.5)
                            adapter = HTTPAdapter(max_retries=retry)
                            session.mount('http://', adapter)
                            session.mount('https://', adapter)

                            
                            r = session.get(
                                f"https://instagram.com/{perfil}/",
                                headers=headers,params=payload,verify=False,
                            )
                            

                            jogador_seguindo = True
                            time.sleep(1)
                            r = request.get(f"https://instagram.com/{perfil}/?__a=1")
                            if r.status_code == 200:
                                if not r.text.startswith("<!DOCTYPE html>"):
                                    jogador_instagram_json = r.json()
                                    if jogador_instagram_json:
                                        nome = jogador_instagram_json["graphql"]["user"]["full_name"]
                                    else:
                                        raise Exception

                                    jogador_seguindo = CLIENT.search_followers_v1(user_id=perfil_id, query=perfil)
                            """

                            #api = Client()
                            #jogador_instagram = api.user_info_by_username(perfil)
                            jogador_instagram = None
                            jogador_seguindo = CLIENT.search_followers_v1(user_id=perfil_id, query=perfil)
                            if jogador_seguindo:
                                nome = jogador_instagram.full_name if jogador_instagram else perfil
                                partida.novos_participantes += 1
                                partida.save()
                                jogador = Jogador.objects.create(usuario=perfil,nome=nome)
                            else:
                                mensagem = "Você ainda não segue o perfil?"
                                return JsonResponse(data={"detail": mensagem}, status=404)

                        except Exception as e:
                            LOGGER.exception(msg=e)
                            mensagem = "Perfil não encontrado, tente novamente mais tarde"
                            return JsonResponse(data={"detail": mensagem}, status=403)

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
                    mensagem = "Não foi encontrado uma regra do tipo 'Seguir um perfil'"
                    return JsonResponse(data={"detail": mensagem}, status=200)
            else:
                mensagem = "Não há sorteios disponíveis no momento"
                return JsonResponse(data={"detail": mensagem}, status=404)

        else:
            mensagem = "Faltam dados de perfil"
            return JsonResponse(data={"detail": mensagem}, status=403)

    return JsonResponse(data={"detail":mensagem},status=403)


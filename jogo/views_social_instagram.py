import base64
import datetime
import json
import random
import pickle

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from instagrapi import Client
from instagrapi.exceptions import UserNotFound, LoginRequired, PleaseWaitFewMinutes, ChallengeRequired
from instagrapi.types import User
from rest_framework.decorators import api_view

from jogo import local_settings
from jogo.choices import AcaoTipoChoices
from jogo.models import Jogador, Partida, Cartela, Regra, Configuracao

import logging

from jogo.utils import get_connection, get_conta

LOGGER = logging.getLogger(__name__)

CLIENT = None


def setSocialConnection(deactivate=False):
    with transaction.atomic():
        global CLIENT
        conta = get_conta(deactivate)
        if conta:
            try:
                if not conta.instagram_connection:
                    CLIENT = Client()
                    proxy = get_connection()
                    CLIENT.set_proxy(proxy)
                    if conta:
                        LOGGER.info(f"CONECTION {conta.username}: {proxy}")
                        CLIENT.login(conta.username,conta.password)
                    else:
                        CLIENT.login(local_settings.username, local_settings.password)
                    conta.instagram_connection = pickle.dumps(CLIENT)
                    conta.save()
                else:
                    CLIENT = pickle.loads(conta.instagram_connection)
                    if not CLIENT:
                        CLIENT = Client()
                        proxy = get_connection()
                        CLIENT.set_proxy(proxy)
                        if conta:
                            LOGGER.info(f"CONECTION {conta.username}: {proxy}")
                            CLIENT.login(conta.username, conta.password)
                        else:
                            CLIENT.login(local_settings.username, local_settings.password)
                        conta.instagram_connection = pickle.dumps(CLIENT)
                        conta.save()
                    else:
                        proxy = get_connection()
                        CLIENT.set_proxy(proxy)
                        LOGGER.info(f"CONECTION {conta.username}: {proxy}")
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
    configuracao = Configuracao.objects.last()
    if partida:
        acoes = partida.regra.acao_set.all()
        for acao in acoes:
            if acao.tipo == AcaoTipoChoices.SEGUIR:
                seguir_url = acao.perfil_social.url
                seguir += seguir_url.split("/www.instagram.com/")[1]
                if seguir.endswith("/"):
                    seguir = seguir[:-1]
    else:
        seguir_url = configuracao.perfil_default
        seguir += seguir_url.split("/www.instagram.com/")[1]
        if seguir.endswith("/"):
            seguir = seguir[:-1]
    url_botao = configuracao.perfil_default or ""
    nome_botao = configuracao.nome_botao or ""

    return JsonResponse(data={"seguir_url":seguir_url,"seguir":seguir,'url_botao':url_botao,'nome_botao':nome_botao}, status=200)


@api_view(['POST'])
def gerar_bilhete(request):
    mensagem = ""
    if 'Authorization' in request.headers and "Token" in request.headers['Authorization']:
        token = request.headers['Authorization'].split("Token ")[1]
        dados = json.loads(request.body)
        perfil = dados.get("perfil")
        # Formatando o dado perfil vindo do front para eliminar a url, @ e /, alem de forçar minusculo
        if perfil:
            if perfil.startswith("@"):
                perfil = perfil[1:]
            if "/" in perfil:
                perfil = perfil.split("/www.instagram.com/")[1].split("/")[0]
            perfil = perfil.lower()

            agora = datetime.datetime.now()

            # Buscando próxima partida
            partida = Partida.objects.filter(data_partida__gt=agora).order_by("data_partida").first()
            if partida:
                perfil_id = ""
                # Buscando a regra de seguir
                for acao in partida.regra.acao_set.all():
                    if acao.tipo == AcaoTipoChoices.SEGUIR:
                        perfil_id = acao.perfil_social.perfil_id
                        break
                if perfil_id:
                    # Encontrar um jogador já cadastrado localmente por perfil
                    jogador = Jogador.objects.filter(usuario=perfil).first()
                    nome = ""
                    jogador_id = 0
                    jogador_seguindo = True

                    # Se não encontrar
                    if not jogador:
                        try:
                            global CLIENT
                            jogador_instagram = None
                            try:
                                # Fazendo a busca de dados do perfil
                                api = Client()
                                proxy = get_connection()
                                api.set_proxy(proxy)
                                LOGGER.info(f"CONECTION: Anonimo {proxy}")
                                jogador_instagram = api.user_info_by_username(perfil)
                                if jogador_instagram and not isinstance(jogador_instagram,User):
                                    # Falha na busca, forçar login
                                    raise LoginRequired
                            except (LoginRequired, PleaseWaitFewMinutes):
                                try:
                                    if CLIENT: # Caso a instancia já esteja montada faz a busca dos dados do perfil
                                        setSocialConnection()
                                        jogador_instagram = CLIENT.user_info_by_username_v1(perfil)
                                        #time.sleep(3)
                                except UserNotFound:
                                    # Redirecionar para Usuario nao encontrado
                                    raise UserNotFound
                                except Exception:
                                    # Qualquer outra falha, despreze
                                    pass

                            # Verificando se o perfil segue o outro
                            setSocialConnection()
                            jogador_seguindo = CLIENT.search_followers_v1(user_id=perfil_id, query=perfil) if CLIENT else True
                        except UserNotFound as e:
                            mensagem = "Perfil não encontrado, tente novamente mais tarde"
                            LOGGER.info(mensagem)
                            return JsonResponse(data={"detail": mensagem}, status=403)
                        except (PleaseWaitFewMinutes, ChallengeRequired):
                            setSocialConnection(deactivate=True)
                        finally:
                            if jogador_seguindo:
                                nome = jogador_instagram.full_name if jogador_instagram else perfil
                                jogador_id = jogador_instagram.pk if jogador_instagram else 0
                                if jogador_id:
                                    jogador = Jogador.objects.filter(usuario_id=jogador_id).first()
                                else:
                                    jogador = Jogador.objects.filter(usuario=perfil).first()

                                try:
                                    # Caso tenha sido encontrado um jogador com o ID jogador_id
                                    if jogador:
                                        if jogador_id:
                                            # Atualiza seus dados caso tenha encontrado o ID do instagram
                                            LOGGER.info("Atualizando Jogador " + perfil)
                                            jogador.usuario=perfil
                                            jogador.usuario_token = base64.b64encode(perfil.encode("ascii")).decode("ascii")
                                            jogador.nome = nome
                                            jogador.save()
                                    else:
                                        # Cria um novo
                                        LOGGER.info("Criando Jogador " + perfil)
                                        jogador = Jogador.objects.create(
                                            usuario=perfil,nome=nome,usuario_id=jogador_id if jogador_id else None
                                        )
                                        partida.novos_participantes += 1
                                        
                                except UnicodeEncodeError:
                                    mensagem = "Perfil não encontrado"
                                    LOGGER.info(mensagem)
                                    return JsonResponse(data={"detail": mensagem}, status=404)
                            else:
                                mensagem = "Você ainda não segue o perfil?"
                                LOGGER.info(mensagem)
                                return JsonResponse(data={"detail": mensagem}, status=404)

                    else:
                        setSocialConnection()
                        jogador_seguindo = CLIENT.search_followers_v1(user_id=perfil_id,
                                                                      query=perfil) if CLIENT else True
                        if not jogador_seguindo:
                            mensagem = "Você deixou de seguir o perfil?"
                            LOGGER.info(mensagem)
                            return JsonResponse(data={"detail": mensagem}, status=404)

                    # atualizar o nome do jogador
                    if jogador.nome == jogador.usuario:
                        setSocialConnection()
                        jogador_instagram = CLIENT.user_info_by_username(perfil)
                        if jogador_instagram:
                            jogador.nome = jogador_instagram.full_name
                            jogador.usuario_id = jogador_instagram.pk
                            jogador.save()

                    cartela = Cartela.objects.filter(jogador=jogador, partida=partida).first()
                    if cartela:
                        mensagem = f"Você já está participando do sorteio {partida.id}"
                    else:
                        cartelas = Cartela.objects.filter(partida=partida, jogador__isnull=True)
                        partida.save()
                        if cartelas:
                            cartela = random.choice(cartelas)
                            cartela.jogador = jogador
                            cartela.nome = jogador.nome
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


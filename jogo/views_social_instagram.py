import base64
import datetime
import json
import random
import pickle

from django.db import transaction
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from instagrapi import Client
from instagrapi.exceptions import UserNotFound, LoginRequired, PleaseWaitFewMinutes, ChallengeRequired
from instagrapi.types import User
from rest_framework.decorators import api_view

from jogo.choices import AcaoTipoChoices
from jogo.consts import StatusJogador
from jogo.models import Jogador, Partida, Cartela, Configuracao, ConfiguracaoInstagram

import logging

from jogo.utils import get_connection, setSocialConnection, CONTA_ATUAL

LOGGER = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET"])
def index_social(request):
    """
    Busca a próxima partida criada e a sua regra
    :param request: HTTPRequest
    :type request: HTTPRequest
    :return: json informando a regra, a url da regra, o nome de botao e a url desse botao
    :rtype: JsonResponse
    """
    seguir_url = ""
    seguir = "@"
    agora = datetime.datetime.now()
    partida = Partida.objects.filter(data_partida__gt=agora).order_by('data_partida').first()
    configuracao = Configuracao.objects.last()
    configuracao_instagram = ConfiguracaoInstagram.objects.last()
    if partida:
        acoes = partida.regra.acao_set.all()
        for acao in acoes:
            if acao.tipo == AcaoTipoChoices.SEGUIR:
                seguir_url = acao.perfil_social.url
                seguir += seguir_url.split("/www.instagram.com/")[1]
                if seguir.endswith("/"):
                    seguir = seguir[:-1]
    else:
        seguir_url = configuracao_instagram.perfil_default if configuracao_instagram else ""
        seguir = ""
        if seguir_url:
            seguir += seguir_url.split("/www.instagram.com/")[1]
        if seguir.endswith("/"):
            seguir = seguir[:-1]
    url_botao = configuracao.url_botao or ""
    nome_botao = configuracao.nome_botao or ""

    return JsonResponse(data={"seguir_url":seguir_url,"seguir":seguir,'url_botao':url_botao,'nome_botao':nome_botao}, status=200)


@api_view(['POST'])
def gerar_bilhete(request):
    """
    Dado o perfil, validar (ou nao) o perfil, criar um jogador caso precise, associar o jogador a uma cartela
    :param request: HTTPRequest
    :type request: HTTPRequest
    :return: Json, com o codigo do bilhete e o codigo do sorteio, ou mensagens de erro
    :rtype: JsonResponse
    """
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

            configuracao = Configuracao.objects.last()
            configuracao_instagram = ConfiguracaoInstagram.objects.last()
            # Buscando próxima partida
            partidas = Partida.objects.filter(data_partida__gt=agora).order_by("data_partida")
            if partidas:
                partida = partidas.first()

                if not configuracao.reter_jogadores:
                    for p in partidas:
                        inicial = p.numero_cartelas_iniciais
                        atual = Cartela.objects.filter(partida=p, jogador__isnull=False, cancelado=False).count()
                        if inicial > atual:
                            partida = p
                            LOGGER.info(f" Sorteio ESCOLHIDO: {partida.id}")
                            break

                perfil_id = ""
                # Buscando a regra de seguir
                for acao in partida.regra.acao_set.all():
                    if acao.tipo == AcaoTipoChoices.SEGUIR:
                        perfil_id = acao.perfil_social.perfil_id
                        break
                if perfil_id:
                    # Encontrar um jogador já cadastrado localmente por perfil
                    jogador = None
                    nome = ""
                    jogador_id = dados.get("instagram_id")
                    if jogador_id:
                        jogador = Jogador.objects.filter(usuario_id=jogador_id).first()
                    if not jogador:
                        jogador = Jogador.objects.filter(usuario=perfil).first()

                    jogador_seguindo = True
                    # Se não encontrar Jogador
                    if not jogador:
                        # Cria um novo
                        LOGGER.info("Criando Jogador " + perfil)
                        jogador = Jogador.objects.create(
                            usuario=perfil, nome=nome, usuario_id=jogador_id if jogador_id else None
                        )
                        partida.novos_participantes += 1

                    else:
                        if jogador.status == StatusJogador.CANCELADO:
                            mensagem = configuracao_instagram.mensagem_nao_existe
                            LOGGER.info(mensagem)
                            return JsonResponse(data={"detail": mensagem}, status=404)
                        if jogador.status == StatusJogador.SUSPENSO:
                            mensagem = configuracao_instagram.mensagem_nao_segue
                            LOGGER.info(mensagem)
                            return JsonResponse(data={"detail": mensagem}, status=404)


                    cartela = Cartela.objects.filter(jogador=jogador, partida=partida).first()
                    if cartela:
                        mensagem = f"{configuracao_instagram.mensagem_ja_participa_sorteio} {partida.id}"
                    else:
                        cartelas = Cartela.objects.filter(partida=partida, jogador__isnull=True)
                        partida.save()
                        if cartelas:
                            cartela = random.choice(cartelas)
                            cartela.jogador = jogador
                            cartela.nome = jogador.nome
                            cartela.save()
                        else:
                            mensagem = configuracao_instagram.mensagem_cartelas_esgotadas
                            LOGGER.info(mensagem)
                            return JsonResponse(data={"detail": mensagem}, status=404)
                    return JsonResponse(
                        data={"detail": mensagem, "bilhete": cartela.hash, "sorteio": int(cartela.partida.id)})

                else:
                    mensagem = "Não foi encontrado uma regra do tipo 'Seguir um perfil'"
                    LOGGER.info(mensagem)
                    return JsonResponse(data={"detail": mensagem}, status=200)
            else:
                mensagem = configuracao_instagram.mensagem_nao_ha_sorteios
                LOGGER.info(mensagem)
                return JsonResponse(data={"detail": mensagem}, status=404)

        else:
            mensagem = "Faltam dados de perfil"
            LOGGER.info(mensagem)
            return JsonResponse(data={"detail": mensagem}, status=403)
    LOGGER.info(mensagem)
    return JsonResponse(data={"detail":mensagem},status=403)


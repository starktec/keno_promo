# Views para cadastro e login do jogador
import datetime
import random
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from jogo.models import Cartela, Partida, Configuracao, CreditoBonus, Jogador, ConfiguracaoAplicacao
from jogo.permissions import EhJogador
from jogo.serializers import JogadorSerializer, LoginJogadorSerializer, CadastroJogadorSerializer, \
    ConfiguracoesAplicacaoSerializer, ConfiguracaoAplicacaoSerializer, RequisicaoPremioAplicacaoSerializer
from jogo.utils import format_serializer_message

import logging
LOGGER = logging.getLogger(__name__)

class CadastroJogador(APIView):
    def post(self,request):
        #LOGGER.info(request.data)
        serializer = CadastroJogadorSerializer(data=request.data)
        if serializer.is_valid():
            jogador = serializer.save()
            return Response(data=JogadorSerializer(jogador).data, status=status.HTTP_201_CREATED)
        LOGGER.info(format_serializer_message(serializer.errors))
        raise serializers.ValidationError(detail=format_serializer_message(serializer.errors))

class LoginJogador(APIView):
    def post(self,request):
        #LOGGER.info(f"LOGIN: {request.data}")
        serializer = LoginJogadorSerializer(data=request.data)
        if serializer.is_valid():
            usuario = request.data.get("usuario")
            jogador = Jogador.objects.filter(usuario=usuario).first()
            return Response(data=JogadorSerializer(jogador).data,status=status.HTTP_200_OK)

        raise serializers.ValidationError(detail=format_serializer_message(serializer.errors))

class PegarCartela(APIView):
    permission_classes = [EhJogador,]
    def post(self,request):
        dados = request.data
        #LOGGER.info(f"PEGAR CARTELA: {dados}")
        #perfil = dados.get("perfil")

        # Encontrar um jogador já cadastrado localmente por perfil
        token = request.headers['Authorization'].split("Token ")[1]

        with transaction.atomic():

            jogador = Jogador.objects.select_for_update().filter(usuario_token=token).first()
            nome = ""


            agora = datetime.datetime.now()

            configuracao = Configuracao.objects.last()
            # Buscando próxima partida
            partidas = Partida.objects.filter(data_partida__gt=agora).order_by("data_partida")
            if partidas:
                partida = partidas.first()
                LOGGER.info(f" Sorteio ESCOLHIDO: {partida.id}")
                if not configuracao.reter_jogadores:
                    for p in partidas:
                        inicial = p.numero_cartelas_iniciais
                        atual = Cartela.objects.filter(partida=p, jogador__isnull=False, cancelado=False).count()
                        if inicial > atual:
                            partida = p
                            LOGGER.info(f" Sorteio MUDADO: {partida.id}")
                            break

                # atualizar o nome do jogador
                if not jogador.nome or jogador.nome != jogador.usuario:
                    jogador.nome = jogador.usuario
                    jogador.save()

                # Gerando a cartela
                cartela_existente = True

                cartelas = Cartela.objects.filter(jogador=jogador, partida=partida)
                if not cartelas:
                    cartela_existente = False
                    # Para o caso de não ter cartela desse jogador no próximo sorteio

                    # Verificar se é o primeiro sorteio desse jogador
                    if not Cartela.objects.filter(jogador=jogador).exists():
                        partida.novos_participantes += 1
                        partida.save()

                    # Verificando se o jogador tem crédito de bonus para descontar
                    credito_bonus = 0
                    bonus = CreditoBonus.objects.filter(jogador=jogador,resgatado_em__isnull=False).order_by("id").first()
                    if bonus:
                        credito_bonus = bonus.valor
                    if partida.chance_vitoria == Decimal(100.0):
                        cartelas_quantidade = Cartela.objects.filter(partida=partida).count()
                        if cartelas_quantidade>partida.numero_cartelas_iniciais:
                            mensagem = "Cartelas esgotadas"
                            LOGGER.info(mensagem)
                            return Response(data={"detail": mensagem}, status=404)
                        else:
                            nome = jogador.usuario
                            if not nome:
                                nome = jogador.nome
                            cartelas_partida = Cartela.objects.select_for_update().filter(partida=partida)
                            with transaction.atomic():
                                codigos_possiveis = range(1,partida.numero_cartelas_iniciais)
                                codigos_cartelas = [x.codigo for x in cartelas_partida]
                                codigos_a_sortear = [str(x) for x in codigos_possiveis if str(x) not in codigos_cartelas]

                                if Cartela.objects.filter(jogador=jogador, partida=partida).exists():
                                    cartela_existente = True
                                else:
                                    cartela_nova = Cartela.objects.create(partida=partida,
                                                                 codigo=random.choice(codigos_a_sortear),
                                                                 jogador=jogador, nome=nome)

                    if cartela_existente:
                        cartelas_livres = Cartela.objects.filter(partida=partida, jogador__isnull=True)

                        if cartelas_livres:

                            cartela = random.choice(cartelas_livres)
                            cartela.jogador = jogador
                            cartela.nome = jogador.nome
                            cartela.save()
                            cartelas = [cartela]
                        else:
                            mensagem = "Cartelas esgotadas"
                            LOGGER.info(mensagem)
                            return Response(data={"detail": mensagem}, status=404)
                    else:
                        cartelas = Cartela.objects.filter(jogador=jogador, partida=partida)

                return Response(
                    data={"cartela":[int(c.id) for c in cartelas], "bilhete": cartelas[0].hash, "sorteio": int(cartelas[0].partida.id)})

            else:
                mensagem = "Não há sorteios disponíveis no momento"
                LOGGER.info(mensagem)
                return Response(data={"detail": mensagem}, status=404)

class ConfiguracaoAplicacaoView(APIView):
    def get(self, request):
        configuracao_serializer = ConfiguracoesAplicacaoSerializer(data={})
        if configuracao_serializer.is_valid():
            return Response(data=configuracao_serializer.validated_data,status=status.HTTP_200_OK)
        return Response(data=configuracao_serializer.errors)

class RequisicaoPremioAplicacaoView(APIView):
    def get(self, request):
        requisicao_premio_serializer = RequisicaoPremioAplicacaoSerializer(read_only=True)
        return Response(data=requisicao_premio_serializer.data,status=status.HTTP_200_OK)

# Views para cadastro e login do jogador
import datetime
import random
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from jogo.models import Cartela, Partida, Configuracao, CreditoBonus, Jogador, ConfiguracaoAplicacao, CartelaVencedora
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
        token = request.headers['Authorization'].split("Token ")[1]

        with transaction.atomic():
            # Obtendo o Jogador pelo header
            jogador = Jogador.objects.select_for_update().filter(usuario_token=token).first()
            nome = ""
            if jogador:

                agora = datetime.datetime.now()
                configuracao = Configuracao.objects.last()

                # Verificando se o jogador tem crédito de bonus para descontar e definindo o numero de cartelas a pegar
                gerar_cartelas = 1 # Padrão

                # Buscando próxima partida
                partidas = Partida.objects.select_for_update().filter(data_partida__gt=agora).order_by("data_partida")
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


                    cartela_existente = True
                    # buscando cartelas do jogador para a partida atual
                    cartelas = Cartela.objects.filter(jogador=jogador, partida=partida)
                    if not cartelas:
                        # Para o caso de não ter cartela desse jogador no próximo sorteio
                        # verificando bonus disponiveis
                        bonus = CreditoBonus.objects.filter(jogador=jogador,
                                                            resgatado_em__isnull=True).order_by("id")
                        desconta = 0  # sem descontos de creditos

                        if configuracao.max_vitorias_jogador > 0:  # Limite de vitorias é positivo
                            # conta quantas vitorias o jogador já teve
                            vitorias = CartelaVencedora.objects.filter(cartela__jogador=jogador).count()
                            if vitorias >= configuracao.max_vitorias_jogador:
                                # caso o numero de vitorias do jogador tenha ultrapassado o limite
                                if bonus:
                                    # se tem crédito bonus fazer a contagem
                                    credito_bonus = bonus.aggregate(Sum("valor"))['valor__sum']
                                    if credito_bonus >= configuracao.numero_cadastro_libera_jogador:
                                        # se tem credito para desbloquear anota o valor a descontar
                                        desconta = configuracao.numero_cadastro_libera_jogador
                                    else:
                                        raise serializers.ValidationError(
                                            detail={
                                                "detail": "Limite de vitórias atingido e você não possui bonus suficiente"})
                                else:
                                    raise serializers.ValidationError(detail={
                                        "detail": "Limite de vitórias atingido e você não possui bonus disponível"})


                        if bonus and not desconta:  # tem bonus e não atingiu o limite de vitorias
                            # Verifica o valor do primeiro credito e soma com o valor da quantidade de cartelas
                            gerar_cartelas += bonus.first().valor
                            # registra o quanto deve descontar de credito
                            desconta = bonus.first().valor

                        # Verificar se é o primeiro sorteio desse jogador
                        if not Cartela.objects.filter(jogador=jogador).exists():
                            partida.novos_participantes += 1
                            partida.save()

                        # avaliar a regra da chance de vitoria da partida
                        if partida.chance_vitoria == Decimal(100.0):
                            # trabalhando com cartelas geradas dinamicamente
                            cartela_existente = False

                            # verificando se a quantidade de cartelas para o sorteio atual ja ultrapassou o limite
                            cartelas_quantidade = Cartela.objects.filter(partida=partida).count()
                            if cartelas_quantidade>partida.numero_cartelas_iniciais:
                                mensagem = "Cartelas esgotadas"
                                LOGGER.info(mensagem)
                                return Response(data={"detail": mensagem}, status=404)
                            else:
                                nome = jogador.usuario
                                if not nome:
                                    nome = jogador.nome

                                with transaction.atomic():
                                    # listando os codigos possiveis para cartelas: de 1 a numero de cartelas iniciais
                                    codigos_possiveis = range(1,partida.numero_cartelas_iniciais)
                                    # listando os codigos já escolhidos para a partida atual
                                    codigos_cartelas = partida.codigos_escolhidos
                                    # listando os codigos disponiveis para sortear
                                    codigos_a_sortear = [x for x in codigos_possiveis if x not in codigos_cartelas]

                                    # checando mais uma vez se o jogador não pegou cartela para o sorteio atual
                                    if not Cartela.objects.filter(jogador=jogador, partida=partida).exists():
                                        # fazendo o sorteio dos codigos na quantidade de cartelas que serão geradas
                                        codigos_sorteados = random.choices(codigos_a_sortear,k=gerar_cartelas)

                                        # atualizando a lista de codigos já escolhidos para a partida atual
                                        partida.codigos_escolhidos += codigos_sorteados
                                        partida.save()

                                        # gerando as cartelas
                                        # TODO: HASH
                                        hash = ""
                                        for i in range(gerar_cartelas):
                                            Cartela.objects.create(partida=partida,codigo=str(codigos_sorteados[i]),
                                                               jogador=jogador, nome=nome)
                                        # decontando o bonus
                                        if bonus:
                                            contador = 0
                                            agora = datetime.datetime.now()
                                            for bonus_obj in bonus:
                                                contador += bonus_obj.valor
                                                if contador > desconta:
                                                    break
                                                bonus_obj.resgatado_em = agora # registrando o resgate do bonus
                                                bonus_obj.save()

                        if cartela_existente: # regra da partida que gera cartelas antecipadamente
                            # buscando cartelas que não foram pegues
                            cartelas_livres = Cartela.objects.select_for_update().filter(partida=partida, jogador__isnull=True)
                            with transaction.atomic():
                                if cartelas_livres:
                                    # sorteando a quantidade de cartelas já definidas
                                    cartelas_sorteadas = random.choices(cartelas_livres,k=gerar_cartelas)
                                    cartelas = []
                                    # TODO: HASH
                                    for cartela_sorteada in cartelas_sorteadas:
                                        # atualizando as cartelas escolhidas com os dados do jogador
                                        cartela_sorteada.jogador = jogador
                                        cartela_sorteada.nome = jogador.nome
                                        cartela_sorteada.save()
                                        cartelas.append(cartela_sorteada)
                                else:
                                    mensagem = "Cartelas esgotadas"
                                    LOGGER.info(mensagem)
                                    return Response(data={"detail": mensagem}, status=404)
                        else:
                            # buscando todas as cartelas do jogador para a partida atual
                            cartelas = Cartela.objects.filter(jogador=jogador, partida=partida)

                    return Response(
                        #data={"cartelas":[int(c.id) for c in cartelas], "bilhete": cartelas[0].hash, "sorteio": int(cartelas[0].partida.id)})
                        data={"cartelas":[{"id":int(c.id),"hash":c.hash} for c in cartelas], "sorteio": int(cartelas[0].partida.id)})

                else:
                    mensagem = "Não há sorteios disponíveis no momento"
                    LOGGER.info(mensagem)
                    return Response(data={"detail": mensagem}, status=404)
            else:
                raise PermissionDenied()

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

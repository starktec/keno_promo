import datetime
import json
import logging

# Get an instance of a logger
import time

from django.shortcuts import redirect

logger = logging.getLogger(__name__)
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from django.http import HttpResponse, JsonResponse

# Create your views here.
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
#from easyaudit.models import CRUDEvent

from jogo.models import Partida, CartelaVencedora, \
    Configuracao, Jogador, Cartela
from jogo.serializers import PartidaSerializer, PartidaProximaSerializer, PartidaHistoricoSerializer, \
    PartidaProximaEspecialSerializer

SORTEIOS = {}

@csrf_exempt
@require_http_methods(["GET","OPTIONS"])
def resultado_sorteio(request, local_id, sorteio_id):
    logger.info(f"{request.META.get('PATH_INFO')} - {request.META.get('HTTP_X_FORWARDED_FOR')}")
    if 'Authorization' in request.headers and "Token" in request.headers['Authorization']:
        token = request.headers['Authorization'].split("Token ")[1]
        jogador = Jogador.objects.filter(usuario_token=token).first()
        if jogador and Cartela.objects.filter(
                partida=Partida.objects.filter(id=sorteio_id).first(),jogador=jogador):
            logger.info(f" - Jogador {jogador}")

            if request.method == 'GET':
                partida:Partida = Partida.objects.filter(id=sorteio_id).first()
                if partida:
                    cartela = Cartela.objects.filter(partida=partida, jogador=jogador).first()
                    if cartela:
                        partida.cartelas_receberam_sorteio.add(cartela)
                        partida.save()
                        serializer = PartidaSerializer(instance=Partida.objects.filter(id=sorteio_id).first())
                        logger.info(f" - {jogador} Enviando sorteio {partida.id}")
                        return JsonResponse(serializer.data, safe=False)
                logger.warning(f" - {jogador} - Partida {sorteio_id} não existe ou o jogador {jogador.nome} não tem cartela para esse sorteio")
                return HttpResponse(status=403)

        else:
            logger.warning(f" - Jogador Não cadastrado")
            return JsonResponse(data={'details':'Jogador Não cadastrado'},safe=True,status=401)
    else:
        logger.warning(" - Não autorizado")
        return HttpResponse(status=401)

@csrf_exempt
@require_http_methods(["GET","OPTIONS"])
def proximos(request):
    logger.info(f"{request.META.get('PATH_INFO')} - {request.META.get('HTTP_X_FORWARDED_FOR')}")
    if 'Authorization' in request.headers and "Token" in request.headers['Authorization']:
        token = request.headers['Authorization'].split("Token ")[1]
        jogador = Jogador.objects.filter(usuario_token=token).first()
        if jogador and Cartela.objects.filter(jogador=jogador):
            logger.info(f" - Jogador {jogador}")
            if request.method == 'GET':
                conf:Configuracao = Configuracao.objects.last()
                agora = datetime.datetime.now()
                proximos = Partida.objects.filter(
                    Q(data_partida__gt=agora,
                      em_sorteio=False, bolas_sorteadas__isnull=True)|
                    Q(data_partida__gt=agora - datetime.timedelta(minutes=conf.tempo_max_espera_sorteio),
                      data_partida__lte=agora,em_sorteio=False, bolas_sorteadas__isnull=False)
                ).order_by('data_partida')[:5]
                serializer = PartidaProximaSerializer(instance=proximos, many=True)
                logger.info(f" - {jogador} Enviando próximos sorteios")
                return JsonResponse({"sorteios":serializer.data,'datahora':datetime.datetime.now()}, safe=False)

            return HttpResponse(status=403)
        else:
            logger.warning(" - Jogador não cadastrado")
            return JsonResponse(data={'details':'Jogador não cadastrado'},safe=True,status=401)
    else:
        logger.warning(" - Não autorizado")
        return HttpResponse(status=401)

@csrf_exempt
@require_http_methods(["GET","OPTIONS"])
def proximos_especiais(request):
    logger.info(f"{request.META.get('PATH_INFO')} - {request.META.get('HTTP_X_FORWARDED_FOR')}")
    if 'Authorization' in request.headers and "Token" in request.headers['Authorization']:
        token = request.headers['Authorization'].split("Token ")[1]
        jogador = Jogador.objects.filter(usuario=token).first()
        if jogador and Cartela.objects.filter(jogador=jogador):
            logger.info(f" - Jogador {jogador}")
            proximos = Partida.objects.filter(
                data_partida__gt=datetime.datetime.now(), em_sorteio=False, bolas_sorteadas__isnull=True,
                tipo_rodada__gt=1
            ).order_by('data_partida')[:5]
            serializer = PartidaProximaEspecialSerializer(instance=proximos, many=True)
            logger.info(f" - {jogador} Enviando próximos sorteios especiais")
            return JsonResponse({"sorteios":serializer.data,'datahora':datetime.datetime.now()}, safe=False)
        else:
            logger.warning(" - Jogador não cadastrado ou inativo")
            return JsonResponse(data={'details':'Jogador não cadastrado'},safe=True,status=401)
    else:
        logger.warning(" - Não autorizada")
        return HttpResponse(status=401)

@csrf_exempt
@require_http_methods(["GET","OPTIONS"])
def historico(request):
    logger.info(f"{request.META.get('PATH_INFO')} - {request.META.get('HTTP_X_FORWARDED_FOR')}")
    if 'Authorization' in request.headers and "Token" in request.headers['Authorization']:
        token = request.headers['Authorization'].split("Token ")[1]
        jogador = Jogador.objects.filter(usuario=token).first()
        if jogador and Cartela.objects.filter(jogador=jogador):
            logger.info(f" - Jogador {jogador}")
            proximos = Partida.objects.filter(data_partida__gt=datetime.datetime.now(),)
            if len(proximos)>3:
                proximos = proximos[:3]
            sorteados = Partida.objects.filter(data_partida__lte=datetime.datetime.now()).order_by('-id')[:3]
            if len(sorteados)>3:
                sorteados = sorteados[:3]
            serializer = PartidaHistoricoSerializer(instance=list(sorteados) + list(proximos), many=True)
            logger.info(f" - {jogador} Enviando histórico: 3 antes e 3 próximos")
            return JsonResponse({"sorteios":serializer.data,'datahora':datetime.datetime.now()}, safe=False)

        else:
            logger.warning(" - Jogador não cadastrado ou inativo")
            return JsonResponse(data={'details':'TV não cadastrado'},safe=True,status=401)
    else:
        logger.warning(" - Não autorizada")
        return HttpResponse(status=401)

@csrf_exempt
@require_http_methods(["GET","OPTIONS"])
def status(request, partida_id):
    logger.info(f"{request.META.get('PATH_INFO')} - {request.META.get('HTTP_X_FORWARDED_FOR')}")
    partida_id = int(partida_id)
    
    if 'Authorization' in request.headers and "Token" in request.headers['Authorization']:
        token = request.headers['Authorization'].split("Token ")[1]
        jogador = Jogador.objects.filter(usuario=token).first()
        if jogador and Cartela.objects.filter(jogador=jogador):
            logger.info(f" - Jogador {jogador}")
            partida = Partida.objects.filter(id=partida_id,).first()
            d = {}
            previsao = -1
            if partida_id < 0:
                d = {
                    'id':partida_id,
                    'status': 0,
                    'tempo': -1,
                    'datahora': datetime.datetime.now()
                }
                return JsonResponse(data=d,status=200,safe=False)
            if partida:
                agora = datetime.datetime.now()
                status = None
                configuracao = Configuracao.objects.last()
                data_inicio_sorteio = (partida.data_partida+datetime.timedelta(seconds=configuracao.iniciar_sorteio_em))

                if data_inicio_sorteio<agora:

                    if partida not in SORTEIOS.keys():
                        SORTEIOS[partida] = partida.num_cartelas_atual()

                    if partida.bolas_sorteadas:
                        status = 2 # SORTEADO
                        previsao = 0
                    else:
                        if partida.em_sorteio:
                            status = 1 # EM SORTEIO
                            previsao = round(SORTEIOS[partida]/1000) - (agora - data_inicio_sorteio).seconds
                        else:
                            if SORTEIOS[partida]:
                                status = 0
                            else:
                                status = -1 # NAO SORTEADO
                else:
                    if partida not in SORTEIOS.keys():
                        SORTEIOS[partida] = partida.doacoesP()
                    previsao = (data_inicio_sorteio - agora).seconds + round(SORTEIOS[partida]/1000)
                    status = 0 # Esperando o sorteio

                logger.info(f" - {jogador} - sorteio {partida_id}: {status}")

                d = {
                    'id':int(partida.id),
                    'status': status,
                    "tempo":previsao,
                    'datahora': datetime.datetime.now()
                }

                if partida.data_partida<agora:
                    if not partida.bolas_sorteadas:
                        if partida.em_sorteio:
                            d['details'] = "Realizando sorteio nesse momento"
                        elif not partida.doacoes:
                            d['details'] = "Sorteio ainda não realizado por falta de cartelas vendidas"
                        else:
                            d['details'] = "Sorteio não realizado"
                else:
                    d['details'] = "Sorteio futuro"
                logger.info(f" - {d}")
                return JsonResponse(data=d,status=200,safe=False)
            else:
                logger.warning(f" - Sorteio {partida_id} não encontrado ou pertencente a outra rota")
                return JsonResponse(data={'details':'Sorteio não encontrado ou pertencente a outra rota'}, safe=False,status=401)
        else:
            logger.warning(" - Jogador não cadastrado")
            return JsonResponse(data={'details':'Jogador não cadastrado'},safe=False,status=401)
    else:
        logger.warning(" - Não autorizado")
        return HttpResponse(status=401)

@csrf_exempt
@require_http_methods(["GET","OPTIONS"])
def ultimos_ganhadores(request):
    logger.info(f"{request.META.get('PATH_INFO')} - {request.META.get('HTTP_X_FORWARDED_FOR')}")
    if 'Authorization' in request.headers and "Token" in request.headers['Authorization']:
        token = request.headers['Authorization'].split("Token ")[1]
        jogador = Jogador.objects.filter(usuario=token).first()
        if jogador and Cartela.objects.filter(jogador=jogador):
            logger.info(f" - Jogador {jogador}")
            vencedores= []
            configuracao = Configuracao.objects.last()
            data_liberacao = datetime.datetime.now() - datetime.timedelta(
                minutes=configuracao.tempo_sorteio_online)
            for v in CartelaVencedora.objects.filter(partida__data_partida__lte=data_liberacao).order_by('-id')[:6]:
                d = {
                    'sorteio':int(v.partida.id),
                    'cartela':int(v.cartela.codigo),
                    'nome':str(v.cartela.jogador),
                    'premio':float(v.valor_premio),
                    'tipo':int(v.premio)
                }
                vencedores.append(d)
            logger.info(f" - {jogador} Enviando lista de ganhadores")
            return JsonResponse({'vencedores':vencedores,'datahora':datetime.datetime.now()},safe=False,status=200)

        else:
            logger.warning(" - Jogador não cadastrado")
            return JsonResponse(data={'details':'TV não cadastrada'},safe=False,status=401)
    else:
        logger.warning(" - Não autorizada")
        return HttpResponse(status=401)

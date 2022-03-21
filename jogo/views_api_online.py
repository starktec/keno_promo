import json
import logging
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from jogo.models import Cartela, Configuracao, Partida, Jogador
import datetime
from django.http import HttpResponse, JsonResponse

logger = logging.getLogger(__name__)

from jogo.serializers import PartidaProximaSerializer,  UltimosGanhadoresSerializer

@require_http_methods(["GET"])
def dados_bilhete(request,hash):
    if 'Authorization' in request.headers and "Token" in request.headers['Authorization']:
        token = request.headers['Authorization'].split("Token ")[1]
        jogador = Jogador.objects.filter(usuario=token).first()
        if jogador and Cartela.objects.filter(jogador=jogador,hash=hash, cancelado=False):
            logger.info(f" - Jogador {jogador}")
            cartela = Cartela.objects.filter(jogador=jogador,hash=hash, cancelado=False).first()
            cartelas = []
            dado = {
                "codigo":cartela.codigo,
                "estabelecimento":cartela.jogador.nome,
                "linha1_lista":cartela.linha1_lista(),
                "linha2_lista":cartela.linha2_lista(),
                "linha3_lista":cartela.linha3_lista(),
            }
            cartelas.append(dado)
            cartela:Cartela = cartela
            dados = {
                "hash":cartela.hash,
                "sorteio":PartidaProximaSerializer(cartela.partida).data,
                "data_hora_sorteio":datetime.date.strftime(cartela.partida.data_partida,'%Y-%m-%dT%H:%M:%S'),
                "comprado_em":cartela.comprado_em,
                "cartelas":cartelas,
            }
            return JsonResponse(data=dados, status=200, safe=False)
        else:
            return JsonResponse(data={}, status=404)
    else:
        return JsonResponse(data={}, status=403)


@csrf_exempt
@require_http_methods(["GET","OPTIONS"])
def proximos_kol(request):
    logger.info(f"{request.META.get('PATH_INFO')} - {request.META.get('HTTP_X_FORWARDED_FOR')}")
    if 'Authorization' in request.headers and "Token" in request.headers['Authorization']:
        token = request.headers['Authorization'].split("Token ")[1]
        jogador = Jogador.objects.filter(usuario=token).first()
        if jogador and Cartela.objects.filter(jogador=jogador, cancelado=False):
            logger.info(f" - Jogador {jogador}")
            if request.method == 'GET':
                conf = Configuracao.objects.last()
                agora = datetime.datetime.now()
                proximos = Partida.objects.filter(
                    Q(data_partida__gt=agora,
                      em_sorteio=False, bolas_sorteadas__isnull=True)|
                    Q(data_partida__gt=agora - datetime.timedelta(minutes=conf.tempo_max_espera_sorteio),
                      data_partida__lte=agora,em_sorteio=False, bolas_sorteadas__isnull=False)
                ).order_by('data_partida')
                serializer = PartidaProximaSerializer(instance=proximos, many=True)
                logger.info(f" - Enviando próximos sorteios")
                return JsonResponse({"sorteios":serializer.data,'datahora':datetime.datetime.now()}, safe=False)

        else:
            logger.warning(" - Jogador não cadastrado ou inativo")
            return JsonResponse(data={'details':'Jogador não cadastrado'},safe=True,status=401)
    else:
        logger.warning(" - Não autorizada")
        return HttpResponse(status=401)



@api_view(['GET'])
@require_http_methods(["GET","OPTIONS"])
def data_hora_servidor(request):
    if 'Authorization' in request.headers and "Token" in request.headers['Authorization']:
        token = request.headers['Authorization'].split("Token ")[1]
        jogador = Jogador.objects.filter(usuario=token).first()
        if jogador:
            return JsonResponse(data={'data_hora':datetime.datetime.now()},safe=True,status=200)
        return JsonResponse(data={'details':'Token Inválido'},safe=True,status=401)
    else:
        return HttpResponse(status=401)


@require_http_methods(["GET"])
def dados_bilhete_v2(request,hash):
    if 'Authorization' in request.headers and "Token" in request.headers['Authorization']:
        token = request.headers['Authorization'].split("Token ")[1]
        jogador = Jogador.objects.filter(usuario=token).first()
        if jogador and Cartela.objects.filter(jogador=jogador, hash=hash, cancelado=False):
            logger.info(f" - Jogador {jogador}")
            cartela = Cartela.objects.filter(jogador=jogador, hash=hash, cancelado=False)
            cartelas  = []

            dado = {
                "codigo":cartela.codigo,
                "estabelecimento":cartela.jogador.nome,
                "linha1_lista":cartela.linha1_lista(),
                "linha2_lista":cartela.linha2_lista(),
                "linha3_lista":cartela.linha3_lista(),
            }
            cartelas.append(dado)
            dados = {
                "hash":cartela.hash,
                "sorteio":PartidaProximaSerializer(Partida.objects.get(id = cartela.partida.id)).data,
                "data_hora_sorteio":datetime.date.strftime(cartela.partida.data_partida,'%Y-%m-%dT%H:%M:%S'),
                "comprado_em":cartela.comprado_em,
                "cartelas":cartelas,
            }
            return JsonResponse(data=dados, status=200, safe=False)
        return JsonResponse(data={'details':'Token Inválido'},safe=True,status=401)
    return JsonResponse(data={'details':'Token Inválido'},safe=True,status=401)

@require_http_methods(["GET"])
def ultimos_ganhadores_kol(request,sorteio_id = None):
    if 'Authorization' in request.headers and "Token" in request.headers['Authorization']:
        token = request.headers['Authorization'].split("Token ")[1]
        jogador = Jogador.objects.filter(usuario=token).first()
        if jogador and Cartela.objects.filter(jogador=jogador, cancelado=False):
            logger.info(f" - Jogador {jogador}")
            if sorteio_id:
                ultimas_partidas = Partida.objects.filter(id = sorteio_id)
            else:
                ultimas_partidas = Partida.objects.filter(bolas_sorteadas__isnull=False,data_partida__lt=datetime.datetime.now()).order_by('-data_partida')[0:5]
            dados = UltimosGanhadoresSerializer(ultimas_partidas,many=True).data
            return JsonResponse(data={"sorteios":dados}, status=200, safe=False)
        return JsonResponse(data={'details':'Token Inválido'},safe=True,status=401)
    return JsonResponse(data={'details':'Token Inválido'},safe=True,status=401)

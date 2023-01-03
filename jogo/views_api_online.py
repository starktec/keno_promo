import json
import logging
import urllib

from django.db.models import Q
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from jogo.models import Cartela, CartelaVencedora, Configuracao, Partida, Jogador
import datetime
from django.http import HttpResponse, JsonResponse

logger = logging.getLogger(__name__)

from jogo.serializers import PartidaProximaSerializer,  UltimosGanhadoresSerializer

@require_http_methods(["GET"])
def dados_bilhete(request,hash):
    if 'Authorization' in request.headers and "Token" in request.headers['Authorization']:
        token = request.headers['Authorization'].split("Token ")[1]
        jogador = Jogador.objects.filter(usuario_token=token).first()
        if jogador and Cartela.objects.filter(jogador=jogador,hash=hash, cancelado=False):
            logger.info(f" - Jogador {jogador}")
            configuracao = Configuracao.objects.last()
            data_liberacao = datetime.datetime.now() + datetime.timedelta(configuracao.liberar_resultado_sorteio_em)
            cartela = Cartela.objects.filter(
                jogador=jogador,hash=hash, cancelado=False,
            ).first()
            cartelas = []
            dado = {
                "nome":cartela.nome,
                "perfil":cartela.jogador.usuario,
                "codigo":cartela.codigo,
                "linha1_lista":cartela.linha1_lista(),
                "linha2_lista":cartela.linha2_lista(),
                "linha3_lista":cartela.linha3_lista(),
                "posicao":int(cartela.posicao),
            }
            cartelas.append(dado)
            cartela:Cartela = cartela

            link_vencedor = ""
            vencedora = CartelaVencedora.objects.filter(
                cartela=cartela,
                cartela__partida__data_partida__lte=data_liberacao
            ).first()
            if vencedora:
                if configuracao.contato_cartela:
                    #msg = "Oi.%20Acabei%20de%20ganhar%20um%20sorteio%20no%20Recebabonus.%20"
                    msg = "Ol%C3%A1!%20Sou%20o%20(a)%20mais%20novo%20(a)%20ganhador%20(a)%20do%20Receba%20B%C3%B4nus!%20%0A%0A"
                    sorteio_text = "-%20N%C3%BAmero%20do%20sorteio%20premiado:%20"
                    codigo_text = "-%20C%C3%B3digo:%20"
                    apelido_text = "-%20Apelido:%20"
                    valor_text = "-%20Valor%20do%20pr%C3%AAmio:%20R$"
                    final_text = "%0A%0AComo%20fa%C3%A7o%20para%20receber%20o%20meu%20b%C3%B4nus?"
                    if configuracao.mensagem_whatsapp:
                        final_text = urllib.parse.quote(configuracao.mensagem_whatsapp)
                    link_vencedor = f"https://api.whatsapp.com/send/?phone={configuracao.contato_cartela}&text={msg}"
                    complemento = []
                    if configuracao.incluir_sorteio:
                        complemento.append(f"{sorteio_text}{cartela.partida.id}%0A")
                    if configuracao.incluir_codigo:
                        complemento.append(f"{codigo_text}{cartela.codigo}%0A")
                    if configuracao.incluir_apelido:
                        complemento.append(f"{apelido_text}{cartela.jogador.usuario}%0A")
                    if configuracao.incluir_valor:
                        complemento.append(f"{valor_text}{vencedora.valor_premio}%0A")

                    if complemento:
                        link_vencedor += "".join(complemento)

                    link_vencedor += final_text

            dados = {
                "hash":cartela.hash,
                "sorteio":PartidaProximaSerializer(cartela.partida).data,
                "data_hora_sorteio":datetime.date.strftime(cartela.partida.data_partida,'%Y-%m-%dT%H:%M:%S'),
                "comprado_em":cartela.comprado_em,
                "ganhou":CartelaVencedora.objects.filter(cartela=cartela).exists(),
                "cartelas":cartelas,
                "link_vencedor":link_vencedor,
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
    ultimas_partidas = Partida.objects.none()
    configuracao = Configuracao.objects.last()
    data_liberacao = datetime.datetime.now() - datetime.timedelta(
        minutes=configuracao.tempo_sorteio_online)
    if sorteio_id:
        ultimas_partidas = Partida.objects.filter(id = sorteio_id, data_partida__lte=data_liberacao)
    else:
        ultimas_partidas = Partida.objects.filter(bolas_sorteadas__isnull=False,
                                                  data_partida__lte=data_liberacao).order_by('-data_partida')[:5]
    dados = UltimosGanhadoresSerializer(ultimas_partidas,many=True).data
    return JsonResponse(data={"sorteios":dados}, status=200, safe=False)


@require_http_methods(["GET"])
def get_regras_kol(request):
    configuracao = Configuracao.objects.last()
    return JsonResponse(data={"detail":configuracao.regras})


@require_http_methods(["GET"])   
def get_politicas_de_privacidade_kol(request):
    configuracao = Configuracao.objects.last()
    return JsonResponse(data={"detail":configuracao.politicas_de_privacidade})
import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from jogo.models import Jogador, CartelaVencedora, VencedorStatus, Partida, AccountSMS


@csrf_exempt
@require_http_methods(["POST"])
def requisitar_pagamento(request):
    if 'Authorization' in request.headers and "Token" in request.headers['Authorization']:
        token = request.headers['Authorization'].split("Token ")[1]
        dados = json.loads(request.body)
        perfil = dados.get("perfil")
        sorteio = dados.get("sorteio")
        # Formatando o dado perfil vindo do front para eliminar a url, @ e /, alem de forçar minusculo
        if perfil:
            sorteio = Partida.objects.filter(id=sorteio).first()
            if not sorteio:
                # TODO: error nao tem sorteio
                pass
            jogador = Jogador.objects.filter(usuario=perfil.lower()).first()
            if not jogador:
                # TODO: error nao tem jogador
                pass
            cartelas = CartelaVencedora.objects.filter(cartela__jogador=jogador,status=VencedorStatus.AGUARDANDO_VALIDACAO)
            if cartelas.exists():
                sms = AccountSMS.objects.filter(credits__gt=0).first()
                if sms:
                    sms.send_sms(jogador)
            else:
                # TODO: nao tem cartela a pagar
                pass

@csrf_exempt
@require_http_methods(["POST"])
def confirmar_telefone(request):
    pass
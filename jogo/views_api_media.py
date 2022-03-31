from PIL import Image
from django.http import HttpResponse,JsonResponse
from jogo.models import Configuracao

def media_logo(request):
    configuracao = Configuracao.objects.last()
    if configuracao.logo_dash:
        img = Image.open('.'+ configuracao.logo_dash.url, mode='r')
    else:
        img = Image.open('./static/images-logo/mr-keno-dash.png')

    response = HttpResponse(content_type='image/png')
    img.save(response, 'png')
    return response
       

def media_favicon(request):
    configuracao = Configuracao.objects.last()
    if configuracao.favicon:
        img = Image.open('.'+ configuracao.favicon.url, mode='r')
    else:
        img = Image.open('./static/images-logo/favicon.png')

    response = HttpResponse(content_type='image/png')
    img.save(response, 'png')
    return response


def media_login(request):
    configuracao = Configuracao.objects.last()
    if configuracao.logo_login:
        img = Image.open('.'+ configuracao.logo_login.url, mode='r')
    else:
        img = Image.open('./static/images-logo/mr-keno-login.png')

    response = HttpResponse(content_type='image/png')
    img.save(response, 'png')
    return response

def nome_server(request):
    configuracao = Configuracao.objects.last()
    if configuracao.nome_server:
        return JsonResponse(data={'nome_server':configuracao.nome_server}, status=200, safe=False)
    else:
        return JsonResponse(data={'nome_server':None}, status=200, safe=False)

def logo_promo(request):
    configuracao = Configuracao.objects.last()
    if configuracao.logo_promo:
        img = Image.open('.'+ configuracao.logo_promo.url, mode='r')
    else:
        img = Image.open('./static/images-logo/mr-keno-login.png')
    response = HttpResponse(content_type='image/png')
    img.save(response, 'png')
    return response
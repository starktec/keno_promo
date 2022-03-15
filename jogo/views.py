import datetime
import json
from datetime import date, timedelta
import random
from decimal import Decimal
import csv
import math
import logging

from jogo.utils import testa_horario
from keno_promo.settings import BASE_DIR
from jogo.constantes import VALORES_VOZES
from jogo.frontend_objects import FrontEndFranquia, FrontEndPartida, FrontEndADSCriar

from jogo.websocket_triggers import event_doacoes, event_tela_partidas
from jogo.websocket_triggers_bilhete import event_bilhete_partida

from jogo.agendamento import Agenda
from jogo.forms import NovaPartidaAutomatizada, PartidaEditForm, GanhadoresForm, NovaPartidaForm, UsuarioAddForm, \
    ConfiguracaoForm, TemplateEditForm
from jogo.models import Partida, Automato, Cartela, Usuario, Configuracao, CartelaVencedora, TemplatePartida

logger = logging.getLogger(__name__)

import itertools
from django import forms
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import HttpResponse
from django.shortcuts import render, redirect
# Create your views here.
from rest_framework.authtoken.models import Token

agenda = Agenda()

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


def login_page(request):
    error = []
    configuracao = Configuracao.objects.last()
    if not configuracao:
        configuracao = Configuracao.objects.create()
    if request.method == "POST":
        username = request.POST['user']
        senha = request.POST['password']
        user = authenticate(username=username, password=senha)
        if user is not None:
            login(request, user)
            usuario = Usuario.objects.filter(usuario=user).first()
            if usuario:
                if configuracao.favicon:
                    request.session['favicon'] = configuracao.favicon.url
                if configuracao.logo_dash:
                    request.session['logo_dash'] = configuracao.logo_dash.url
                if configuracao.nome_server:
                    request.session['nome_server'] = configuracao.nome_server
                if configuracao.logo_login:
                    request.session['logo_login'] = configuracao.logo_login.url
                if configuracao.usar_realtime:
                    request.session['real_time'] = configuracao.usar_realtime

                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('/partidas/')

        else:
            logger.error(error)
            error = "Usuário ou senha inválidos"
    titulo = ""
    favicon = ""
    imagem = ""
    versao = ""
    if configuracao:
        titulo = configuracao.nome_server
        favicon = configuracao.favicon
        imagem = configuracao.logo_login
        versao = configuracao.versao

    return render(request, 'login.html', {'error': error, 'titulo': titulo, "versao": versao,
                                          'favicon': favicon, 'imagem': imagem})


@login_required(login_url="/login/")
def logout_page(request):
    logout(request)
    if "perfil_max" in request.session:
        del request.session['perfil_max']
    return redirect('/')


@login_required(login_url="/login/")
def cancelar_partida(request, partida_id):
    p = Partida.objects.filter(id=partida_id, doacoes=0.00)
    if not Cartela.objects.filter(partida=p,jogador__isnull=False).exists():
        p.delete()
        event_doacoes()
    # TODO: WEBSOCKET
    ##event_tela_partidas(franquias)  ## informa aos websockets de tela que houve modificação na tela
    return redirect("/")



@login_required(login_url="/login/")
def index(request):
    return redirect('/partidas/')


@login_required(login_url="/login/")
def partida_automatica(request):
    usuario = Usuario.objects.filter(usuario=request.user).first()
    form = NovaPartidaAutomatizada()
    if request.session['automato']:
        if request.method == 'POST':
            form = NovaPartidaAutomatizada(request.POST)
            if form.is_valid():
                dia_partida_inicial = form.cleaned_data['dia_partida_inicial']
                hora_partida_inicial = form.cleaned_data['hora_partida_inicial']
                data_partida = datetime.datetime.strptime(
                    dia_partida_inicial + " " + hora_partida_inicial, "%d/%m/%Y %H:%M")
                if data_partida < datetime.datetime.now():
                    form.add_error('dia_partida_inicial', 'data/hora inválido(a)')
                valor_kuadra_inicial = form.cleaned_data['valor_kuadra_inicial']
                valor_kina_inicial = form.cleaned_data['valor_kina_inicial']
                valor_keno_inicial = form.cleaned_data['valor_keno_inicial']
                tempo_partidas = form.cleaned_data['tempo_partidas']
                limite_partidas = form.cleaned_data['limite_partidas']
                cartelas_iniciais = form.cleaned_data['cartelas_iniciais']

                tipo_crescimento = form.cleaned_data['tipo_crescimento']

                tipo_rodada = form.cleaned_data['tipo_rodada']

                if form.errors:
                    return render(request, "partida_automatizada.html", {'form': form})
                with transaction.atomic():
                    if int(tipo_crescimento) == 1:
                        automato = Automato.objects.create(
                            usuario=usuario,
                            tempo=tempo_partidas,
                            quantidade_sorteios=limite_partidas,
                            cartelas_minimas=cartelas_iniciais,
                            tipo_crescimento=int(tipo_crescimento),
                        )
                    

                    partida_inicial = Partida.objects.create(
                        valor_kuadra=valor_kuadra_inicial,
                        valor_kina=valor_kina_inicial,
                        valor_keno=valor_keno_inicial,
                        data_partida=data_partida,
                        usuario=usuario,
                        id_automato=automato.id,
                        partida_automatizada=True,
                        tipo_rodada=tipo_rodada,
                    )
                    partida_inicial.save()
                    agenda.agendar(partida_inicial)
                    for numero in range(cartelas_iniciais):
                        Cartela.objects.create(partida=partida_inicial)
                #event_tela_partidas(franquias)
                return redirect('/partidas/')
        return render(request, "partida_automatizada.html", {'form': form})
    else:
        return HttpResponse(status=401)


@login_required(login_url="/login/")
def partidas(request):

    pagina = 0
    ultima_pagina = 0
    itens_pagina = 10
    usuario = request.user.usuario
    partidas = []
    data_final = None
    data_inicial = datetime.date.today()
    if request.method == "POST":
        data_inicial = request.POST.get(
            'outlined-initial-date-picker', datetime.date.today().strftime("%d/%m/%Y"))
        data_final = request.POST['outlined-final-date-picker']
        if data_final:
            data_final = datetime.datetime.strptime(
                data_final + " 23:59:59", "%d/%m/%Y %H:%M:%S")
        if data_inicial:
            data_inicial = datetime.datetime.strptime(data_inicial, "%d/%m/%Y")
        else:
            data_inicial = datetime.date.today()
        if not data_final:
            partidas = Partida.objects.filter(data_partida__gte=data_inicial,)
        else:
            partidas = Partida.objects.filter(data_partida__gte=data_inicial,
                                              data_partida__lte=data_final,)
    else:
        if not partidas:
            partidas = Partida.objects.filter(data_partida__gte=data_inicial,)


    total_dados = partidas.count()
    if (total_dados != 0 and itens_pagina != 0):
        ultima_pagina = int(math.ceil(total_dados / itens_pagina))
    partidas = partidas.order_by('-data_partida')
    if request.GET.get("pagina"):
        pagina = int(request.GET["pagina"])
        numeroF = int(int(pagina) * itens_pagina)
        numeroI = numeroF - itens_pagina
        partidas = partidas[numeroI:numeroF]

    else:
        pagina = 1
        partidas = partidas[0:itens_pagina]
    proxima_pagina = int(pagina) + 1
    pagina_anterior = int(pagina) - 1

    if ultima_pagina == 0:
        ultima_pagina = 1

    total_participantes = 0
    total_online = 0
    total_offline = 0
    agora = datetime.datetime.now()
    if partidas:
        proxima_partida = partidas[len(partidas)-1]
        for p in partidas:
            if p < agora:
                break
            else:
                proxima_partida = p

        total_participantes = Cartela.objects.filter(partida=proxima_partida, jogador__isnull=False).count()

    return render(request, 'partidas.html', {'data_inicial': data_inicial.strftime("%d/%m/%Y"),
                                             'data_final': data_final.strftime("%d/%m/%Y") if data_final else None,
                                             'partidas': partidas, 'agora': agora, 'pagina_atual': pagina,
                                             'ultima_pagina': ultima_pagina, 'proxima_pagina': proxima_pagina,
                                             'pagina_anterior': pagina_anterior, "participantes":total_participantes,
                                             'online':total_online,'offline':total_offline
                                             })


@login_required(login_url="/login/")
def ganhadores(request):
    hoje = datetime.date.today()
    data_inicio = datetime.datetime.combine(hoje, datetime.time.min)
    data_fim = datetime.datetime.combine(hoje, datetime.time.max)
    usuario = Usuario.objects.get(usuario=request.user)
    perfil = request.session['perfil_max']
    itens_pagina = 10
    configuracao = Configuracao.objects.last()
    data_liberacao = datetime.datetime.now() - datetime.timedelta(minutes=configuracao.liberar_resultado_sorteio_em)
    vencedores = CartelaVencedora.objects.filter(partida__data_partida__lte=data_liberacao).order_by('-id')
    vencedores = vencedores.filter(partida__data_partida__gte=data_inicio, partida__data_partida__lte=data_fim)
    ultima_pagina = 0
    post = False
    form = GanhadoresForm(
        data={'user': request.user, 'perfil': request.session['perfil_max']})
    if request.method == "POST":
        post = True
        data_form = request.POST.dict()
        data_form['perfil'] = request.session['perfil_max']
        data_form['user'] = request.user
        form = GanhadoresForm(data_form)
        vencedores = CartelaVencedora.objects.filter(partida__data_partida__lte=data_liberacao,).order_by('-id')
        if form.is_valid():

            if 'data_inicio' in form.cleaned_data and form.cleaned_data['data_inicio']:
                data_inicio = datetime.datetime.combine(
                    datetime.datetime.strptime(form.cleaned_data['data_inicio'], "%d/%m/%Y"),
                    datetime.time.min
                )
                if 'data_fim' not in form.cleaned_data or not form.cleaned_data['data_fim']:
                    data_fim = datetime.datetime.combine(
                        data_inicio, datetime.time.max
                    )

            if 'data_fim' in form.cleaned_data and form.cleaned_data['data_fim']:
                data_fim = datetime.datetime.combine(
                    datetime.datetime.strptime(form.cleaned_data['data_fim'], "%d/%m/%Y"),
                    datetime.time.max
                )
                if 'data_inicio' not in form.cleaned_data or not form.cleaned_data['data_inicio']:
                    data_inicio = datetime.datetime.combine(
                        data_fim, datetime.time.min
                    )

            vencedores = vencedores.filter(partida__data_partida__gte=data_inicio, partida__data_partida__lte=data_fim)
            if 'partida' in form.cleaned_data and form.cleaned_data['partida']:
                vencedores = CartelaVencedora.objects.filter(
                    partida__id=form.cleaned_data['partida'], partida__data_partida__lte=data_liberacao)
            if 'pdv' in form.cleaned_data and form.cleaned_data['pdv']:
                pdv = form.cleaned_data['pdv']
                vencedores = CartelaVencedora.objects.filter(partida__data_partida__lte=data_liberacao,
                                                             cartela__pdv=pdv)


    partidas_vencedores = {}


    kuadra, kina, keno, acumulado = (0, 0, 0, 0)
    partidas = []
    for v in vencedores:
        if v.partida not in partidas:
            partidas.append(v.partida)
            kuadra += v.partida.valor_kuadra
            kina += v.partida.valor_kina
            keno += v.partida.valor_keno
        if v.ganhou_acumulado:
            acumulado += v.partida.valor_acumulado
        if v.partida in partidas_vencedores:
            partidas_vencedores[v.partida].append(v)
        else:
            partidas_vencedores[v.partida] = [v]

    total = kuadra + kina + keno + acumulado

    total_dados = len(partidas_vencedores)
    if (total_dados != 0 and itens_pagina != 0):
        ultima_pagina = int(math.ceil(total_dados / itens_pagina))
    if request.GET.get("pagina"):
        pagina = int(request.GET["pagina"])
        numeroF = int(int(pagina) * itens_pagina)
        numeroI = numeroF - itens_pagina
        partidas_vencedores = dict(itertools.islice(partidas_vencedores.items(), numeroI, numeroF))

    else:
        pagina = 1
        partidas_vencedores = dict(itertools.islice(partidas_vencedores.items(), itens_pagina))

    proxima_pagina = int(pagina) + 1
    pagina_anterior = int(pagina) - 1

    if ultima_pagina == 0:
        ultima_pagina = 1
    return render(request, 'ganhadores.html',
                  {'partidas': partidas_vencedores, 'pagina_atual': pagina, 'proxima_pagina': proxima_pagina,
                   'pagina_anterior': pagina_anterior, 'ultima_pagina': ultima_pagina, 'flag': post, 'form': form,
                   'kuadra': kuadra, 'kina': kina,
                   'keno': keno, 'acumulado': acumulado, 'total': total,
                   # 'pago':pago,
                   # 'apagar':apagar
                   })


class UsuarioBuscaForm(forms.Form):
    nome = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': "form-control form-control-lg form-control-outlined"}))
    login = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': "form-control form-control-lg form-control-outlined"}))


@login_required(login_url="/login/")
def criarpartida(request):
    usuario = Usuario.objects.filter(usuario=request.user).first()
    hoje = date.today()
    form = NovaPartidaForm(initial={'dia_partida': hoje},
                           data={'user': request.user})
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    partidas = Partida.objects.filter(data_partida__gte=yesterday).distinct()


    if request.method == "POST":
        form = NovaPartidaForm(request.POST, data={'perfil': request.session["perfil_max"], 'user': request.user})

        if form.is_valid():
            dia_partida = form.cleaned_data['dia_partida']
            hora_partida = form.cleaned_data['hora_partida']
            partida = form.save(commit=False)
            partida.data_partida = datetime.datetime.strptime(
                dia_partida + " " + hora_partida, "%d/%m/%Y %H:%M")
            partida.usuario = usuario
            partida.save()
            form.save_m2m()
            agenda.agendar(partida)
            # TODO: abaixo
            """
            event_tela_partidas(
                partida.franquias.all())  ## informa aos websockets de tela que houve modificação na tela
            """
            return redirect("/partidas/")

    valores_disponiveis = VALORES_VOZES

    return render(request, 'criarpartida.html',
                  {'form': form, 'partidas': partidas,

                   'configuracao': Configuracao.objects.last(),
                   })


@login_required(login_url="/login/")
def cartela(request, cartela_id):
    cartela = Cartela.objects.filter(cancelado=False, id=cartela_id).first()

    return render(request, 'cartelas.html', {'cartela': cartela})


@login_required(login_url="/login/")
def partida_edit(request, partida_id):
    partida = Partida.objects.filter(id=partida_id).first()
    configuracao = Configuracao.objects.last()
    if partida:
        agora = datetime.datetime.now()
        if partida.data_partida > agora:
            form = PartidaEditForm(instance=partida, initial={
                'dia_partida': partida.data_partida.date,
                'hora_partida': partida.data_partida.strftime("%H:%M"),
                'tipo_rodada': partida.tipo_rodada,
                'nome_sorteio': partida.nome_sorteio,
                'valor_kuadra': partida.valor_kuadra,
                'valor_kina': partida.valor_kina,
                'valor_keno': partida.valor_keno,
            })
            if request.method == "POST":
                form = PartidaEditForm(request.POST, instance=partida)
                if form.is_valid():
                    data_partida = form.cleaned_data['dia_partida'] + " " + form.cleaned_data['hora_partida']
                    novadata = datetime.datetime.strptime(data_partida, "%d/%m/%Y %H:%M")
                    antigadata = partida.data_partida
                    partida.data_partida = novadata
                    if form.instance.doacoes and configuracao.edit_tipo:
                        partida.tipo_rodada = form.cleaned_data['tipo_rodada']
                    partida.nome_sorteio = form.cleaned_data['nome_sorteio']
                    partida.valor_kuadra = form.cleaned_data['valor_kuadra']
                    partida.valor_kina = form.cleaned_data['valor_kina']
                    partida.valor_keno = form.cleaned_data['valor_keno']
                    partida.save()

                    # NOVO AGENDAMENTO
                    if not antigadata == novadata:
                        agenda.agendar(partida)

                    # TODO: #event_tela_partidas(franquias)
                    event_bilhete_partida(partida.id)
                    return redirect("/partidas/")

            yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
            partidas = Partida.objects.filter(data_partida__gte=yesterday)
            # TODO: #event_tela_partidas(franquias)
            return render(request, 'partida_edit.html',
                          {'form': form, 'partidas': partidas, 'configuracao': Configuracao.objects.last()})


class CartelasLoteForm(object):
    pass


@login_required(login_url="/login/")
def cartelas(request):
    ultima_pagina = 0
    page_number = 0
    ordenacao = False
    cartelas_total = False
    perfil = request.session['perfil_max']
    usuario = Usuario.objects.filter(usuario=request.user).first()

    cartelas = Cartela.objects.all().order_by('-id')

    if request.method == "POST":
        data_form = request.POST.dict()
        data_form['user'] = request.user
        form = CartelasLoteForm(data_form)
        if form.is_valid():
            if 'data_inicio' in form.cleaned_data and form.cleaned_data['data_inicio']:
                inicio = datetime.datetime.combine(
                    datetime.datetime.strptime(form.cleaned_data['data_inicio'], "%d/%m/%Y"), datetime.time.min)
                cartelas = cartelas.filter(comprado_em__gte=inicio)

            if 'data_fim' in form.cleaned_data and form.cleaned_data['data_fim']:
                fim = datetime.datetime.combine(datetime.datetime.strptime(form.cleaned_data['data_fim'], "%d/%m/%Y"),
                                                datetime.time.max)
                cartelas = cartelas.filter(comprado_em__lte=fim)

            if 'partida' in form.cleaned_data and form.cleaned_data['partida']:
                cartelas = cartelas.filter(
                    partida=form.cleaned_data['partida'])
            if 'pdv' in form.cleaned_data and form.cleaned_data['pdv']:
                pdv = form.cleaned_data['pdv']
                cartelas = cartelas.filter(pdv=pdv)
            if 'hash' in form.cleaned_data and form.cleaned_data['hash']:
                hash = form.cleaned_data['hash']
                cartelas = cartelas.filter(hash=hash)
        cartelas_total = cartelas
    else:
        hoje = datetime.date.today()
        hora_inicio_padrao = datetime.datetime.strptime("00:00:01", '%H:%M:%S').time()
        data_inicio = datetime.datetime.combine(hoje, hora_inicio_padrao)
        hora_fim_padrao = datetime.datetime.strptime("23:59:59", '%H:%M:%S').time()
        data_fim = datetime.datetime.combine(hoje, hora_fim_padrao)
        ordenacao = True
        # cartelas = CartelasLote.objects.filter(comprado_em__gte = data_inicio , comprado_em__lte=data_fim)
        cartelas_total = Cartela.objects.filter(comprado_em__gte=data_inicio, comprado_em__lte=data_fim)
        form = CartelasLoteForm(
            data={'user': request.user, 'perfil': request.session['perfil_max']})
        page_number = request.GET.get('pagina')
        if not page_number:
            page_number = 1

    itens_pagina = 10
    total_dados = cartelas.count()
    ultima_pagina = math.ceil(total_dados / itens_pagina)
    flag = False
    if not page_number:
        page_number = request.GET["pagina"]
        if page_number:
            numeroF = int(int(page_number) * itens_pagina)
            numeroI = numeroF - itens_pagina
            cartelas = cartelas.all().order_by('-id')[numeroI:numeroF]
        else:
            cartelas = cartelas.all().order_by('-id')[0:30]
    else:
        if page_number:
            flag = True
            numeroF = int(int(page_number) * itens_pagina)
            numeroI = numeroF - itens_pagina
            cartelas = cartelas.all().order_by('-id')[numeroI:numeroF]
        else:
            cartelas = cartelas.all().order_by('-id')[0:30]

    doacoes = 0
    cartelas_num = 0
    sorteios_obj = 0
    doacoes_sorteio = 0
    cartelas_sorteio = 0
    hoje = datetime.datetime.now()
    if cartelas_total:
        doacoes = cartelas_total.filter(cancelado=False).aggregate(Sum('valor_da_compra'))[
                      'valor_da_compra__sum'] or 0.00
        cartelas_num = cartelas_total.filter(cancelado=False).aggregate(Sum('quantidade'))['quantidade__sum'] or 0.00
        sorteios_obj = Partida.objects.filter(partidas_lote__in=cartelas_total).distinct().count()
    if doacoes:
        doacoes_sorteio = doacoes / sorteios_obj
    if cartelas_num:
        cartelas_sorteio = cartelas_num / sorteios_obj

    canceladas = cartelas_total.filter(cancelado=True).count()
    if ultima_pagina == 0:
        ultima_pagina = 1
    return render(request, 'cartelas_lote.html', {'cartelas': cartelas, 'form': form, "flag": flag,
                                                  'sorteios': sorteios_obj, 'doacoes': doacoes,
                                                  'doacoes_sorteio': round(doacoes_sorteio, 2),
                                                  'canceladas': canceladas,
                                                  'cartelas_num': cartelas_num,
                                                  'cartelas_sorteio': round(cartelas_sorteio, 2),
                                                  "pagina_atual": int(page_number),
                                                  "proxima_pagina": int(page_number) + 1,
                                                  "pagina_anterior": int(page_number) - 1,
                                                  "ultima_pagina": ultima_pagina, "ordenacao": ordenacao, "hoje": hoje,
                                                  # "data_inicio": data_inicio,"data_fim": data_fim,
                                                  })


class TrocarSenhaForm(forms.Form):
    senha = forms.CharField(widget=forms.PasswordInput(
        attrs={'class': "form-control form-control-lg form-control-outlined"}
    ))
    repetir_senha = forms.CharField(widget=forms.PasswordInput(
        attrs={'class': "form-control form-control-lg form-control-outlined"}
    ))

    def clean(self):
        dados = super().clean()
        if not dados['senha'] == dados['repetir_senha']:
            raise ValidationError(
                "O campo 'senha' e o campo 'confirmar senha' devem ser iguais")



def usuario_dict(usuario):
    # print(usuario.id)
    result = {
        'usuario_id': usuario.id,
        'nome': usuario.usuario.first_name,
        'sobrenome': usuario.usuario.last_name,
        'login': usuario.usuario.username,
        'cpf': usuario.cpf,
        'rg': usuario.rg,
        'endereco': usuario.endereco,
        'endereco_num': usuario.endereco_num,
        'endereco_complemento': usuario.endereco_complemento,
        'endereco_bairro': usuario.endereco_bairro,
        'endereco_cidade': usuario.endereco_cidade,
        'endereco_estado': usuario.endereco_estado,
        'endereco_cep': usuario.endereco_cep,
        'fone': usuario.fone,
        'email': usuario.email,
        'perfis': usuario.perfis.all(),
        'franquias': usuario.franquias.all(),
        'limite_caixa': usuario.limite_caixa
    }
    return result


@login_required(login_url="/login/")
def usuarios(request):
    form = UsuarioBuscaForm()

    usuario = Usuario.objects.filter(usuario=request.user).first()
    usuarios = Usuario.objects.all()

    if request.method == "POST":
        form = UsuarioBuscaForm(request.POST)

        if form.is_valid() and usuarios:
            if 'nome' in form.cleaned_data and form.cleaned_data['nome']:
                nome = form.cleaned_data['nome']
                usuarios = usuarios.filter(Q(usuario__first_name__icontains=nome) | Q(
                    usuario__last_name__icontains=nome))
            if 'login' in form.cleaned_data and form.cleaned_data['login']:
                usuarios = usuarios.filter(
                    usuario__username=form.cleaned_data['login'])

            form = UsuarioBuscaForm()


        if usuarios:
            usuarios = usuarios.order_by('-id')

        return render(request, 'usuarios.html', {'usuarios': usuarios, 'form': form, })
    else:
        return HttpResponse(status=403)


@login_required(login_url="/login/")
def usuarios_add_or_edit(request, usuario_id=None):
    form = None
    usuario_obj = None
    if usuario_id:
        perfil = request.session['perfil_max']
        usuario_obj = Usuario.objects.filter(id=usuario_id, perfis__tipo__gt=perfil).first()
        if usuario_obj:
            form = UsuarioAddForm(initial=usuario_dict(usuario_obj),
                                  data={'user': request.user, 'perfil': request.session['perfil_max']})
    else:
        form = UsuarioAddForm(
            data={'user': request.user, 'perfil': request.session['perfil_max']})

    if request.method == "POST":
        form = UsuarioAddForm(request.POST, data={'user': request.user, 'perfil': request.session['perfil_max']})
        if form.is_valid():
            login = form.cleaned_data['login']
            senha = ""
            if "senha" in form.cleaned_data and form.cleaned_data['senha']:
                senha = form.cleaned_data['senha']
            nome = form.cleaned_data['nome']
            sobrenome = form.cleaned_data['sobrenome']
            cpf = form.cleaned_data['cpf']
            rg = form.cleaned_data['rg']
            endereco = form.cleaned_data['endereco']
            endereco_num = form.cleaned_data['endereco_num'] if form.cleaned_data['endereco_num'] else 0
            endereco_complemento = ""
            if "endereco_complemento" in form.cleaned_data and form.cleaned_data['endereco_complemento']:
                endereco_complemento = form.cleaned_data['endereco_complemento']
            endereco_bairro = form.cleaned_data['endereco_bairro']
            endereco_cidade = form.cleaned_data['endereco_cidade']
            endereco_estado = form.cleaned_data['endereco_estado']
            endereco_cep = form.cleaned_data['endereco_cep']
            fone = form.cleaned_data['fone']
            email = form.cleaned_data['email']
            perfis = form.cleaned_data['perfis']
            franquias = form.cleaned_data['franquias']
            limite_caixa = form.cleaned_data.get('limite_caixa')

            with transaction.atomic():
                if not usuario_id and senha:

                    usuario = User.objects.filter(username=login).first()
                    if not usuario:
                        usuario = User.objects.create(username=login, password=make_password(senha),
                                                      first_name=nome, last_name=sobrenome, email=email)
                        usuario.save()

                    u = Usuario.objects.filter(usuario=usuario).first()

                    if not u:
                        u = Usuario.objects.create(usuario=usuario, fone=fone, cpf=cpf, rg=rg,
                                                   endereco=endereco, endereco_num=endereco_num,
                                                   endereco_complemento=endereco_complemento,
                                                   endereco_bairro=endereco_bairro, endereco_cidade=endereco_cidade,
                                                   endereco_estado=endereco_estado, endereco_cep=endereco_cep,
                                                   email=email, limite_caixa=limite_caixa if limite_caixa else 0)


                    u.save()
                    return redirect("/usuario/details/" + str(u.id) + "/")
                else:
                    usuario_obj = Usuario.objects.filter(id=usuario_id).first()
                    usuario = usuario_obj.usuario

                    # print(usuario_obj)
                    if usuario:
                        # print(usuario)
                        usuario.first_name = nome
                        usuario.username = login
                        usuario.last_name = sobrenome
                        usuario.email = email
                        if senha:
                            usuario.set_password(senha)
                        usuario.save()
                        usuario_obj.fone = fone
                        usuario_obj.cpf = cpf
                        usuario_obj.rg = rg
                        usuario_obj.endereco = endereco
                        usuario_obj.endereco_num = endereco_num
                        usuario_obj.endereco_complemento = endereco_complemento
                        usuario_obj.endereco_bairro = endereco_bairro
                        usuario_obj.endereco_cidade = endereco_cidade
                        usuario_obj.endereco_estado = endereco_estado
                        usuario_obj.endereco_cep = endereco_cep
                        usuario_obj.email = email
                        usuario_obj.perfis.set(perfis)
                        usuario_obj.franquias.set(franquias)
                        usuario_obj.limite_caixa = limite_caixa if limite_caixa != None else usuario_obj.limite_caixa
                        usuario_obj.save()
                    return redirect("/usuario/details/" + str(usuario_obj.id) + "/")

    return render(request, 'usuario_edit_add.html', {'form': form, 'edit': True if usuario_id else False})


@login_required(login_url="/login/")
def usuario_details(request, usuario_id=None):
    if usuario_id:
        usuario = Usuario.objects.filter(id=usuario_id).first()
        return render(request, 'usuario_details.html', {'usuario_obj': usuario, 'usuario': usuario.usuario})
    else:
        return redirect("/usuarios/")


@login_required(login_url="/login/")
def configuracao(request):
    c = Configuracao.objects.last()
    if request.method == "POST":
        form = ConfiguracaoForm(request.POST, request.FILES, instance=c)
        if form.is_valid():
            request.session['aviso'] = c.notificacao_server
            form.save()
    else:
        form = ConfiguracaoForm(instance=c)
    return render(request, 'configuracao.html', {'form': form, 'configuracao': c})


@login_required(login_url="/login/")
def cancelar_bilhete(request, hash):
    if "perfil_max" in request.session and request.session['perfil_max'] < 3 and request.session['cancelar_bilhete']:
        usuario = Usuario.objects.filter(usuario=request.user, ativo=True, perfis__lte=2).first()
        if usuario:
            c = Cartela.objects.filter(cancelado=False, hash=hash).first()
            if c:
                agora = datetime.datetime.now()
                if agora < c.partida.data_partida:
                    c.cancelar(usuario)
                else:
                    return HttpResponse(status=403)
            else:
                return HttpResponse(status=403)
        else:
            return HttpResponse(status=401)
    else:
        return HttpResponse(status=403)


@login_required(login_url="/login/")
def automatos(request, codigo=0):
    info = False
    if request.session['automato'] and request.session['perfil_max'] < 3:
        if codigo:
            if codigo == 1:
                info = True
        partidas = TemplatePartida.objects.filter(play=False, cancelado=False,
                                                  data_partida__gte=datetime.datetime.now()).order_by('-data_partida')
        agora = datetime.datetime.now()
        return render(request, 'template_p_automatos.html', {'partidas': partidas, 'agora': agora, 'info': info})
    else:
        return HttpResponse(status=401)


@login_required(login_url="/login/")
def editar_template(request, template_id):
    usuario = Usuario.objects.filter(usuario=request.user).first()
    template = TemplatePartida.objects.get(id=template_id)
    form = TemplateEditForm(instance=template, initial={
        'dia_partida': template.data_partida.date,
        'hora_partida': template.data_partida.strftime("%H:%M"),
        'valor_cartela': template.valor_cartela,
        'valor_antecipado': template.valor_antecipado,
        'valor_kuadra': template.valor_kuadra,
        'valor_kina': template.valor_kina,
        'valor_keno': template.valor_keno,
        'franquias': template.franquias.all()
    })
    if request.method == "POST":
        form = PartidaEditForm(request.POST, instance=template)
        if form.is_valid():
            data_partida = form.cleaned_data['dia_partida'] + " " + form.cleaned_data['hora_partida']
            novadata = datetime.datetime.strptime(data_partida, "%d/%m/%Y %H:%M")
            template.data_partida = novadata
            template.valor_kuadra = form.cleaned_data['valor_kuadra']
            template.valor_kina = form.cleaned_data['valor_kina']
            template.valor_keno = form.cleaned_data['valor_keno']
            template.play = False
            template.cancelado = False
            template.save()
            return redirect('/automatos/')
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    partidas = Partida.objects.filter(data_partida__gte=yesterday, )
    return render(request, 'template_edit.html',
                  {'form': form, 'partidas': partidas, 'configuracao': Configuracao.objects.last()})


@login_required(login_url="/login/")
def parar_automato(request, partida_id):
    partida = Partida.objects.filter(id=partida_id).first()
    if partida.id_automato:
        partida.id_automato = False
        partida.save()
    return redirect('/partidas/')


@login_required(login_url="/login/")
def sortear_template(request, template_id):
    template = TemplatePartida.objects.get(id=template_id)
    configuracao = Configuracao.objects.first()
    if template.data_partida > datetime.datetime.now() + datetime.timedelta(minutes=(
            round(configuracao.tempo_min_entre_sorteios) * (0.4))) and not template.play and not template.cancelado:
        template.data_partida = testa_horario(template.data_partida, False,
                                              Automato.objects.get(id=template.id_automato).tempo)
        usuario = Usuario.objects.filter(usuario=request.user).first()
        p = Partida.objects.create(
            valor_keno=template.valor_keno,
            valor_kina=template.valor_kina,
            valor_kuadra=template.valor_kuadra,
            data_partida=template.data_partida,
            id_automato=template.id_automato,
            tipo_rodada=template.tipo_rodada,
            partida_automatizada=True,
            hora_virada=template.hora_virada,
            usuario=usuario
        )
        p.save()
        agenda.agendar(p)
        template.play = True
        template.save()

    return redirect('/automatos/')


@login_required(login_url="/login/")
def cancelar_template(request, template_id):
    template = TemplatePartida.objects.get(id=template_id)
    template.cancelado = True
    template.save()
    return redirect('/automatos/')


def webview(request):
    return render(request, "webview.html")


@login_required
def templates(request):
    if request.method == "POST":
        for x in request.POST:
            if request.POST[x] and x != 'csrfmiddlewaretoken':
                if x[0] == 'd':
                    dia = request.POST[x]
                elif x[0] == 'h':
                    hora = request.POST[x]
                    dia = datetime.datetime.strptime(dia, "%d/%m/%Y")
                    hora = datetime.datetime.strptime(hora, "%H:%M").time()
                    data_hora = datetime.datetime.combine(dia, hora)
                    dia = ''
                    hora = ''
    templates = TemplatePartida.objects.filter(id_automato__isnull=True)
    agora = datetime.datetime.now()
    return render(request, 'template_partidas.html', {'partidas': templates, 'agora': agora})


@login_required
def realtime_data(request):
    if request.session.get('real_time'):
        return render(request, 'realtime_data.html')
    else:
        return HttpResponse(status=401)






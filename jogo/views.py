import datetime
import json
from datetime import date, timedelta
import random
from decimal import Decimal
import csv
import math
import logging

from jogo.choices import AcaoTipoChoices
from jogo.utils import testa_horario, comprar_cartelas
from jogo.constantes import VALORES_VOZES

from jogo.agendamento import Agenda
from jogo.forms import CartelasFilterForm, JogadoresForm, NovaPartidaAutomatizada, PartidaEditForm, GanhadoresForm, NovaPartidaForm, UsuarioAddForm, \
    ConfiguracaoForm, TemplateEditForm
from jogo.models import Jogador, Partida, Automato, Cartela, Usuario, Configuracao, CartelaVencedora, TemplatePartida, Regra, \
    Acao, PerfilSocial
from jogo.views_social_instagram import CLIENT
from jogo.websocket_triggers_bilhete import event_bilhete_partida

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
    return redirect('/')


@login_required(login_url="/login/")
def cancelar_partida(request, partida_id):
    p = Partida.objects.get(id=partida_id)
    if not Cartela.objects.filter(partida=p,jogador__isnull=False).exists():
        p.delete()
        #event_doacoes()
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

            tipo_rodada = form.cleaned_data['tipo_rodada']

            if form.errors:
                return render(request, "partida_automatizada.html", {'form': form})
            with transaction.atomic():
                automato = Automato.objects.create(
                    usuario=usuario,
                    tempo=tempo_partidas,
                    quantidade_sorteios=limite_partidas)

                partida_inicial = Partida.objects.create(
                    regra = Regra.objects.get_or_create(nome="PROMO")[0],
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
                # comprando cartelas
                configuracao = Configuracao.objects.last()
                comprar_cartelas(partida_inicial,configuracao.quantidade_cartelas_compradas)

                agenda.agendar(partida_inicial)
            return redirect('/partidas/')
    return render(request, "partida_automatizada.html", {'form': form})



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
    total_sorteios = len(partidas)
    total_premios = 0
    agora = datetime.datetime.now()
    if partidas:
        for partida in partidas:
            total_participantes += Cartela.objects.filter(partida=partida, jogador__isnull=False).count()
            if partida.bolas_sorteadas:
                total_premios += partida.premios()

    return render(request, 'partidas.html', {'data_inicial': data_inicial.strftime("%d/%m/%Y"),
                                             'data_final': data_final.strftime("%d/%m/%Y") if data_final else None,
                                             'partidas': partidas, 'agora': agora, 'pagina_atual': pagina,
                                             'ultima_pagina': ultima_pagina, 'proxima_pagina': proxima_pagina,
                                             'pagina_anterior': pagina_anterior, "total_participantes":total_participantes,
                                             'total_sorteios':total_sorteios,'total_premios':total_premios
                                             })


@login_required(login_url="/login/")
def ganhadores(request):
    hoje = datetime.date.today()
    data_inicio = datetime.datetime.combine(hoje, datetime.time.min)
    data_fim = datetime.datetime.combine(hoje, datetime.time.max)
    itens_pagina = 10
    data_liberacao = datetime.datetime.now()
    vencedores = CartelaVencedora.objects.filter(partida__data_partida__lte=data_liberacao).order_by('-id')
    vencedores = vencedores.filter(partida__data_partida__gte=data_inicio, partida__data_partida__lte=data_fim)
    ultima_pagina = 0
    post = False
    form = GanhadoresForm()
    if request.method == "POST":
        post = True
        data_form = request.POST.dict()
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

    partidas_vencedores = {}

    kuadra, kina, keno, acumulado = (0, 0, 0, 0)
    partidas = []
    for v in vencedores:
        v:CartelaVencedora
        if v.partida not in partidas:
            partidas.append(v.partida)
            kuadra += v.partida.valor_kuadra
            kina += v.partida.valor_kina
            keno += v.partida.valor_keno
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
                   })


@login_required(login_url="/login/")
def jogadores(request):
    form = JogadoresForm()
    jogadores = Jogador.objects.all()
    itens_pagina = 10
    if request.method == "POST":
        form = JogadoresForm(request.POST)
        if form.is_valid():
            if 'data_inicio' in form.cleaned_data and form.cleaned_data['data_inicio']:
                data_inicio = datetime.datetime.combine(
                    datetime.datetime.strptime(form.cleaned_data['data_inicio'], "%d/%m/%Y"),
                    datetime.time.min
                )
                jogadores = jogadores.filter(cadastrado_em__gte=data_inicio)
                if 'data_fim' not in form.cleaned_data or not form.cleaned_data['data_fim']:
                    data_fim = datetime.datetime.combine(
                        data_inicio, datetime.time.max
                    )
                    jogadores = jogadores.filter(cadastrado_em__lte=data_fim)

            if 'data_fim' in form.cleaned_data and form.cleaned_data['data_fim']:
                data_fim = datetime.datetime.combine(
                    datetime.datetime.strptime(form.cleaned_data['data_fim'], "%d/%m/%Y"),
                    datetime.time.max
                )
                jogadores = jogadores.filter(cadastrado_em__lte=data_fim)
                if 'data_inicio' not in form.cleaned_data or not form.cleaned_data['data_inicio']:
                    data_inicio = datetime.datetime.combine(
                        data_fim, datetime.time.min
                    )
                    jogadores.filter(cadastrado_em_gte=data_inicio)
            if 'partida' in form.cleaned_data and form.cleaned_data['partida']:
                cartelas = Cartela.objects.filter(partida__id=form.cleaned_data['partida'])
                jogadores = jogadores.filter(cartela__in=cartelas).order_by('id').distinct('id')
            if 'nome_jogador' in form.cleaned_data and form.cleaned_data['nome_jogador']:
                jogadores = jogadores.filter(nome__icontains=form.cleaned_data['nome_jogador'])
        else:
            print(form.errors)  
    total_dados = jogadores.count()
    ultima_pagina = 1
    if (total_dados != 0 and itens_pagina != 0):
        ultima_pagina = int(math.ceil(total_dados / itens_pagina))
    if request.GET.get("pagina"):
        pagina = int(request.GET["pagina"])
        numeroF = int(int(pagina) * itens_pagina)
        numeroI = numeroF - itens_pagina
        jogadores = jogadores[numeroI:numeroF]

    else:
        pagina = 1
        jogadores = jogadores[0:itens_pagina]

   

    return render(request,'jogadores.html',{'jogadores':jogadores,'form':form,'pagina_atual': pagina,'ultima_pagina':ultima_pagina,})

@login_required(login_url="/login/")
def criarpartida(request):
    usuario = Usuario.objects.filter(usuario=request.user).first()
    hoje = date.today()
    form = NovaPartidaForm(initial={'dia_partida': hoje})
    ontem = datetime.datetime.now() - datetime.timedelta(days=1)
    partidas = Partida.objects.filter(data_partida__gte=ontem)
    configuracao = Configuracao.objects.last()
    if request.method == "POST":
        form = NovaPartidaForm(request.POST)

        if form.is_valid():
            # Definição de Ações
            regra, regra_criado = Regra.objects.get_or_create(nome="PROMO")
            acoes_select = request.POST.getlist("acoes_select")
            acoes_url = request.POST.getlist("acoes_url")

            if len(acoes_url) == len([x for x in acoes_url if x.startswith("https://www.instagram.com/")]):

                dados = list(zip(acoes_select,acoes_url))

                for dado in dados:
                    url_social = dado[1]

                    perfil_social = PerfilSocial.objects.filter(url = url_social).first()
                    if not perfil_social:
                        try:
                            perfil = url_social.split("www.instagram.com/")[1]
                            if perfil.endswith("/"):
                                perfil = perfil[:-1]
                            perfil_id = CLIENT.user_id_from_username(perfil)
                            perfil_social = PerfilSocial.objects.create(
                                url = url_social, perfil_id = perfil_id
                            )
                        except:
                            raise ValidationError("Perfil não existe")

                    acao, acao_criado = Acao.objects.get_or_create(
                        tipo = dado[0],perfil_social=perfil_social, regra = regra
                    )

                dia_partida = form.cleaned_data['dia_partida']
                hora_partida = form.cleaned_data['hora_partida']
                numero_cartelas_iniciais = form.cleaned_data['numero_cartelas_iniciais']
                partida = form.save(commit=False)
                partida.regra = regra
                partida.data_partida = datetime.datetime.strptime(
                    dia_partida + " " + hora_partida, "%d/%m/%Y %H:%M")
                partida.usuario = usuario
                partida.save()

                # comprando cartelas

                comprar_cartelas(partida,numero_cartelas_iniciais)

                # Agendando sorteio
                agenda.agendar(partida)

                return redirect("/partidas/")
            else:
                form.add_error(None,"Um ou mais urls não está escrito corretamente")

    valores_disponiveis = VALORES_VOZES
    acoes_tipo = AcaoTipoChoices.choices
    perfil_default = configuracao.perfil_default
    return render(request, 'criarpartida.html',
                  {'form': form, 'partidas': partidas,"perfil_default":perfil_default,
                    'valores_disponiveis':valores_disponiveis,
                   'configuracao': Configuracao.objects.last(),"acoes_tipo":acoes_tipo,
                   })


@login_required(login_url="/login/")
def cartela(request, cartela_id):
    cartela = Cartela.objects.filter(cancelado=False, id=cartela_id).first()

    return render(request, 'cartelas.html', {'cartela': cartela})


@login_required(login_url="/login/")
def partida_edit(request, partida_id):
    partida:Partida = Partida.objects.filter(id=partida_id).first()
    configuracao:Configuracao = Configuracao.objects.last()
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
                    partida.tipo_rodada = form.cleaned_data['tipo_rodada']
                    partida.nome_sorteio = form.cleaned_data['nome_sorteio']
                    partida.valor_kuadra = form.cleaned_data['valor_kuadra']
                    partida.valor_kina = form.cleaned_data['valor_kina']
                    partida.valor_keno = form.cleaned_data['valor_keno']
                    partida.save()

                    # NOVO AGENDAMENTO
                    if not antigadata == novadata:
                        agenda.agendar(partida)

                    event_bilhete_partida(partida.id)
                    return redirect("/partidas/")

            yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
            partidas = Partida.objects.filter(data_partida__gte=yesterday)
            # TODO: #event_tela_partidas(franquias)
            return render(request, 'partida_edit.html',
                          {'form': form, 'partidas': partidas, 'configuracao': Configuracao.objects.last()})



@login_required(login_url="/login/")
def cartelas(request):
    ultima_pagina = 0
    page_number = 0
    ordenacao = False
    cartelas = Cartela.objects.filter(jogador__isnull=True).order_by('-id')
    if request.method == "POST":
        form = CartelasFilterForm(request.POST)
        if form.is_valid():
            if 'partida' in form.cleaned_data and form.cleaned_data['partida']:
                cartelas = cartelas.filter(
                    partida=form.cleaned_data['partida'])
            if 'hash' in form.cleaned_data and form.cleaned_data['hash']:
                hash = form.cleaned_data['hash']
                cartelas = cartelas.filter(hash=hash)
    else:
        hoje = datetime.date.today()
        ordenacao = True
        form = CartelasFilterForm()
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

    sorteios_count = Partida.objects.filter(cartelas__in = cartelas).order_by('-id').distinct('id').count()
    hoje = datetime.datetime.now()
    if ultima_pagina == 0:
        ultima_pagina = 1
    return render(request, 'cartelas_lote.html', {'cartelas': cartelas, 'form': form, "flag": flag,
                                                  'sorteios': sorteios_count,
                                                  'cartelas_num': total_dados,
                                                  "pagina_atual": int(page_number),
                                                  "proxima_pagina": int(page_number) + 1,
                                                  "pagina_anterior": int(page_number) - 1,
                                                  "ultima_pagina": ultima_pagina, "ordenacao": ordenacao, "hoje": hoje,
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



@login_required(login_url="/login/")
def configuracao(request):
    c = Configuracao.objects.last()
    if request.method == "POST":
        form = ConfiguracaoForm(request.POST, request.FILES, instance=c)
        if form.is_valid():
            form.save()
    else:
        form = ConfiguracaoForm(instance=c)
    return render(request, 'configuracao.html', {'form': form, 'configuracao': c})


@login_required(login_url="/login/")
def cancelar_bilhete(request, hash):
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



@login_required(login_url="/login/")
def automatos(request, codigo=0):
    info = False
    if codigo:
        if codigo == 1:
            info = True
    partidas = TemplatePartida.objects.filter(play=False, cancelado=False,
                                              data_partida__gte=datetime.datetime.now()).order_by('-data_partida')
    agora = datetime.datetime.now()
    return render(request, 'template_p_automatos.html', {'partidas': partidas, 'agora': agora, 'info': info})


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
    template:TemplatePartida = TemplatePartida.objects.get(id=template_id)
    configuracao = Configuracao.objects.first()
    if template.data_partida > datetime.datetime.now() + datetime.timedelta(minutes=(
            round(configuracao.tempo_min_entre_sorteios) * (0.4))) and not template.play and not template.cancelado:
        template.data_partida = testa_horario(template.data_partida, False,
                                              Automato.objects.get(id=template.id_automato).tempo)
        usuario = Usuario.objects.filter(usuario=request.user).first()
        p = Partida.objects.create(
            regra = template.regra,
            valor_keno=template.valor_keno,
            valor_kina=template.valor_kina,
            valor_kuadra=template.valor_kuadra,
            data_partida=template.data_partida,
            id_automato=template.id_automato,
            tipo_rodada=template.tipo_rodada,
            partida_automatizada=True,
            usuario=usuario
        )
        p.save()
        # comprando cartelas
        configuracao = Configuracao.objects.last()
        comprar_cartelas(p,configuracao.quantidade_cartelas_compradas)
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






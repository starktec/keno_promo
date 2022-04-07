import pickle
import random

from asgiref.sync import sync_to_async
from django.conf import settings
from instagrapi import Client

from jogo.models import Regra, Partida, Configuracao, TemplatePartida, Cartela, IPTabela, Conta, Publicacao, Automato, \
    Galeria, TextoPublicacao
from datetime import date, datetime, timedelta

import datetime
from django.db import connection, transaction
import subprocess

import logging
LOGGER = logging.getLogger(__name__)

def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def convert_float(number):
    return str(round(number,2)).replace('.',',')

        
def convert_float_list(lst):
    lista = list(lst)
    for x, res in enumerate(lista): 
        if x != 0:
            if type(res) != str:
                res = convert_float(res)
            lista[x]= res
    return tuple(lista)

def convert_float_list_partida(lst):
    lista = list(lst)
    for x, res in enumerate(lista): 
        if x > 2:
            if type(res) != str:
                res = convert_float(res)
            lista[x]= res
    return tuple(lista)


def totalCartelas_sql(data_inicio,data_fim):
    with connection.cursor() as cursor: 
        cursor.execute("""
        SELECT 	SUM(quantidade),
		COUNT(*)
		FROM jogo_cartelas
		WHERE 
		  jogo_cartelas.comprado_em >='""" + str(data_inicio) + """'::timestamp AND
		  jogo_cartelas.comprado_em <= '""" +str(data_fim) + """'::timestamp AND
          jogo_cartelas.cancelado = false
        """
        )
        data = dictfetchall(cursor)
        return data





def testa_horario(horario,find=False,tempo_entre_sorteios = None):
    if find:
        return horario
    t = Configuracao.objects.last().tempo_min_entre_sorteios
    te = Configuracao.objects.last().tempo_min_entre_sorteios_E
    tse = Configuracao.objects.last().tempo_min_entre_sorteios_SE
    if tempo_entre_sorteios:
        tes = tempo_entre_sorteios
    else:
        tes = t
    horario_plus = horario + datetime.timedelta(minutes=t)
    horario_less = horario - datetime.timedelta(minutes=t)
    horario_plus_e = horario + datetime.timedelta(minutes=te)
    horario_less_e = horario - datetime.timedelta(minutes=t)
    horario_plus_se = horario + datetime.timedelta(minutes=tse)
    horario_less_se = horario - datetime.timedelta(minutes=t)
    partidas = Partida.objects.filter(data_partida__lt = horario_plus,data_partida__gt=horario_less,bolas_sorteadas__isnull=True,tipo_rodada=1)
    partidas_e = Partida.objects.filter(data_partida__lt = horario_plus_e,data_partida__gt=horario_less_e,bolas_sorteadas__isnull=True,tipo_rodada=2)
    partidas_se = Partida.objects.filter(data_partida__lt = horario_plus_se,data_partida__gt=horario_less_se,bolas_sorteadas__isnull=True,tipo_rodada=3)
    novo_horario = []
    if partidas:
        partida = partidas.order_by('data_partida').first()
        #novo_horario_n = partida.data_partida + datetime.timedelta(minutes=tes)
        novo_horario.append(partida.data_partida + datetime.timedelta(minutes=tes))
    else:
        if partidas_e:
            partida = partidas_e.order_by('data_partida').first()
            #novo_horario_e = partida.data_partida + datetime.timedelta(minutes=tes)
            novo_horario.append(partida.data_partida + datetime.timedelta(minutes=tes))
            #return testa_horario(novo_horario,False,tes)
        elif partidas_se:
            partida = partidas_se.order_by('data_partida').first()
            #novo_horario_se = partida.data_partida + datetime.timedelta(minutes=tes)
            novo_horario.append(partida.data_partida + datetime.timedelta(minutes=tes))
            #return testa_horario(novo_horario,False,tes)
        else:
            find = True
            return horario
    if novo_horario:
        return testa_horario(max(novo_horario),False,tes)
   

def arredondamento(x, base=5):   #
    return base * round(x/base)

# TODO: Estudar adaptação do automato
def partida_automatizada(partida:Partida,agenda):
    configuracao = Configuracao.objects.last()
    with transaction.atomic():
        if partida.id_automato:
            automato:Automato = Automato.objects.filter(id=partida.id_automato).first()
            automato.partidas.add(partida)
            data_prox = testa_horario(partida.data_partida + datetime.timedelta(minutes=automato.tempo),False,automato.tempo)
            if automato.quantidade_sorteios > 0:
                template:TemplatePartida = TemplatePartida.objects.create(
                    regra = Regra.objects.get_or_create(nome="PROMO")[0],
                    valor_keno = partida.valor_keno,
                    valor_kina= partida.valor_kina,
                    valor_kuadra=partida.valor_kuadra,
                    usuario = automato.usuario,
                    data_partida = data_prox,
                    data_introducao = datetime.datetime.now(),
                    id_automato = automato.id,
                    tipo_rodada = partida.tipo_rodada,
                )
                template.save() 
                automato.quantidade_sorteios = automato.quantidade_sorteios - 1
                automato.save()
                agenda.agendar_template(template)

@sync_to_async
def update_configuracao(dado):
    configuracao = Configuracao.objects.exclude(versao=dado).first()
    if configuracao:
        configuracao.versao = dado
        configuracao.save()


async def git_branch_name():
    cmd = "git status"
    status, output = subprocess.getstatusoutput(cmd)
    if status==0:
        dado = output.split("\n")[0].split()[2]
        if dado:
            await update_configuracao(dado)


def comprar_cartelas(partida,quantidade):
    numeros = random.sample(range(1000,10000),k=quantidade)
    for i in range(quantidade):
        Cartela.objects.create(partida=partida, codigo=numeros[i])


# Lidando com proxy
def get_connection():
    connection = ""
    with transaction.atomic():
        dados = IPTabela.objects.select_for_update().last()
        if dados:
            connection = dados.ip_proxy+":"
            faixa = dados.ip_faixa
            ultima_posicao = dados.ip_ultima_posicao
            if not ultima_posicao or ultima_posicao==faixa[1]:
                ultima_posicao=faixa[0]
            else:
                ultima_posicao+=1
            dados.ip_ultima_posicao = ultima_posicao
            dados.save()
            connection += str(ultima_posicao)
    return connection

# Lidando com as contas

def desativar_conta(conta, atualizado=False):
    with transaction.atomic():
        conta_desativar = Conta.objects.select_for_update().filter(id=conta.id).first()
        if not atualizado:
            conta_desativar.ativo = False

        conta_atualizar = Conta.objects.select_for_update().filter(proximo_id=conta.id).first()
        if conta_atualizar:
            conta_atualizar.proximo = conta_desativar.proximo
            conta_desativar.proximo = None
            conta_atualizar.save()

        conta_desativar.save()


def ativar_conta(conta, atualizado=False):
    with transaction.atomic():
        conta_ativar = Conta.objects.select_for_update().filter(id=conta.id).first()
        if not atualizado:
            conta_ativar.ativo = True

        conta_proximo = Conta.objects.filter(ativo=True).exclude(id=conta.id).last()
        conta_anterior = Conta.objects.select_for_update().filter(ativo=True).exclude(id=conta.id).first()

        if conta_proximo and conta_anterior:
            conta_ativar.proximo = conta_proximo
            conta_anterior.proximo = conta_ativar
            conta_anterior.save()

        conta_ativar.save()

def get_conta():
    result = Conta.objects.none()

    contas = Conta.objects.filter(ativo=True)
    if contas:
        conta = contas.order_by("-ultimo_acesso").first()
        result = conta
        if conta.proximo:
            with transaction.atomic():
                proximo = Conta.objects.select_for_update().filter(id=conta.proximo.id)
                if proximo:
                    proximo = proximo.first()
                    proximo.ultimo_acesso = datetime.datetime.now()
                    proximo.save()
                    result = proximo

    return result


def manter_contas():

    contas = Conta.objects.filter(ativo=True)
    configuracao = Configuracao.objects.last()

    hoje = date.today()
    for conta in contas:
        publicacao = Publicacao.objects.filter(conta=conta).order_by("-data_publicacao").first()

        if not publicacao or (publicacao and not configuracao.publicacao_uma_vez_dia) or \
                (publicacao and configuracao.publicacao_uma_vez_dia and publicacao.data_publicacao.date()<hoje):
            # Publicar na conta
            connection = get_connection()
            try:
                if not conta.instagram_connection:
                    acesso = Client()
                    if connection:
                        acesso.set_proxy(connection)
                    LOGGER.info(f"CONTAS -> atualizar: CONECTION (N) {conta.username}: {connection}")
                    acesso.login(conta.username, conta.password)  # Faz o login

                    # Atualizando a conexao no banco
                    conta.instagram_connection = pickle.dumps(acesso)
                    conta.save()

                else:  # Caso tenha a instancia da conexao
                    acesso = pickle.loads(conta.instagram_connection)  # Recuperar a instancia do banco e ativar
                    if connection:
                        acesso.set_proxy(connection)
                    LOGGER.info(f"CONTAS -> atualizar: CONECTION (R) {conta.username}: {connection}")

                # Montando a publicacao
                LOGGER.info(f"CONTAS -> atualizar: Montando a publicacao")
                fotos = []
                galerias = Galeria.objects.filter(ativo=True)
                if galerias:
                    fotos = [(x.id,settings.BASE_DIR + x.arquivo.url) for x in galerias]
                else:
                    fotos.append((0,settings.MEDIA_ROOT + "galeria/universo.jpeg"))


                textos = TextoPublicacao.objects.filter(ativo=True)
                if not textos:
                    # Texto padrão
                    texto = TextoPublicacao.objects.create(
                        texto="Na astronomia, o Universo corresponde ao conjunto de toda a matéria e energia existente.\n"
                        "Ele reúne os astros: planetas, cometas, estrelas, galáxias, nebulosas, satélites, dentre outros.\n"
                        "É um local imenso e para muitos, infinito. Note que do latim, a palavra universum significa "
                              "'todo inteiro' ou 'tudo em um só'."
                    )
                    textos=[texto]
                foto_escolhida = random.choice(fotos)
                texto_escolhido = random.choice(textos)
                # Publicando
                LOGGER.info(f"CONTAS -> atualizar: publicando.....")
                acesso.photo_upload(foto_escolhida[1],texto_escolhido.texto,)
                LOGGER.info(f"CONTAS -> atualizar: pronto")
                if foto_escolhida[0] == 0:
                    Publicacao.objects.create(conta=conta, texto=texto_escolhido)
                else:
                    Publicacao.objects.create(conta=conta, texto=texto_escolhido, imagem_id=foto_escolhida[0])

            except Exception as e:
                if e.message == "login_required" or e.message['message'] == "login_required":
                    LOGGER.error(f"Deu Login Required na conta {conta}... resolvendo")
                    acesso = Client()
                    if connection:
                        acesso.set_proxy(connection)
                    LOGGER.info(f"CONTAS -> atualizar: CONECTION (N) {conta.username}: {connection}")
                    acesso.login(conta.username, conta.password)  # Faz o login

                    # Atualizando a conexao no banco
                    conta.instagram_connection = pickle.dumps(acesso)
                    conta.save()

                    LOGGER.info(f"CONTAS -> atualizar: publicando.....")
                    acesso.photo_upload(foto_escolhida[1], texto_escolhido.texto, )
                    LOGGER.info(f"CONTAS -> atualizar: pronto")
                    if foto_escolhida[0] == 0:
                        Publicacao.objects.create(conta=conta, texto=texto_escolhido)
                    else:
                        Publicacao.objects.create(conta=conta, texto=texto_escolhido, imagem_id=foto_escolhida[0])
                    pass
                else:
                    LOGGER.exception(e)
                    pass


def manter_contas_thread():
    print(f"func: {datetime.datetime.now()}")
    cont = 0
    for i in range(100000):
        cont += 1
        if cont%10000==0:
            print(f"contando {cont}.....")
    print(f"func: {datetime.datetime.now()}")





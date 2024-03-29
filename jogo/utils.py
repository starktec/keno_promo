import random

from asgiref.sync import sync_to_async

from jogo.models import Automato, Regra, Usuario, Partida, Configuracao, TemplatePartida, Cartela
from datetime import date, datetime, timedelta

import datetime
from django.db import connection, transaction
import subprocess


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
import random

from asgiref.sync import sync_to_async

from jogo.models import Automato, Usuario, Partida, Configuracao, TemplatePartida, Cartela
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





def testa_horario(horario,franquias,find=False,tempo_entre_sorteios = None):
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
        return testa_horario(max(novo_horario),franquias,False,tes)
   

def arredondamento(x, base=5):   #
    return base * round(x/base)

# TODO: Estudar adaptação do automato
def partida_automatizada(partida,agenda):
    configuracao = Configuracao.objects.last()
    if configuracao.automato:
        with transaction.atomic():
            resultado = float(partida.resultado())
            if partida.id_automato:
                automato = Automato.objects.filter(id=partida.id_automato).first()
                automato.partidas.add(partida)
                data_prox = testa_horario(partida.data_partida + datetime.timedelta(minutes=automato.tempo),partida.franquias.all(),False,automato.tempo)
                prox = False
                if automato.tipo_crescimento == 2:
                    if resultado > 0:
                        automato.lucro_total = float(float(automato.lucro_total)+resultado/2)
                        automato.quantidade_negativos = automato.quantidade_inicial_negativo
                        soma_premio = float((100-automato.porcentagem)/100) * resultado
                        soma_keno = float(automato.percentual_keno/100) * soma_premio
                        soma_kina = float(automato.percentual_kina/100) * soma_premio
                        soma_kuadra = float(automato.percentual_kuadra/100) * soma_premio
                        if (float(partida.valor_keno) + float(soma_keno)) <= float(automato.valor_maximo_keno):    
                            keno = arredondamento(float(partida.valor_keno)+float(soma_keno))
                            #keno = round(float(float(partida.valor_keno) + float(soma_keno)))
                        else:
                            resto = float(float(partida.valor_keno) + float(soma_keno)) - float(automato.valor_maximo_keno)
                            keno = automato.valor_maximo_keno
                            automato.lucro_total = float(automato.lucro_total)+float(resto) 
                        if (float(partida.valor_kina) + float(soma_kina)) <= float(automato.valor_maximo_kina):
                            kina = arredondamento(float(partida.valor_kina)+float(soma_kina))
                            #kina = round(float(float(partida.valor_kina) + float(soma_kina)))
                        else:
                            resto = float(float(partida.valor_kina) + float(soma_kina)) - float(automato.valor_maximo_kina)
                            kina = automato.valor_maximo_kina
                            automato.lucro_total = float(automato.lucro_total)+float(resto) 
                        if (float(partida.valor_kuadra) + float(soma_kuadra)) <= float(automato.valor_maximo_kuadra):
                            kuadra = arredondamento(float(partida.valor_kuadra)+float(soma_kuadra))
                            #kuadra = round(float(float(partida.valor_kuadra) + float(soma_kuadra)))
                        else:
                            resto = float(float(partida.valor_kuadra) + float(soma_kuadra)) - float(automato.valor_maximo_kuadra)
                            kuadra = automato.valor_maximo_kuadra
                            automato.lucro_total = float(automato.lucro_total)+float(resto)     
                        prox=True
                    else:
                        automato.lucro_total = float(float(automato.lucro_total)+resultado)
                        if resultado <= automato.valor_minimo: 
                            if resultado <= automato.valor_minimo_maximo:
                                prox=False
                                automato.quantidade_negativos=0
                                automato.quantidade_sorteios=0
                            else:
                                automato.quantidade_negativos = automato.quantidade_negativos - 1
                        if automato.quantidade_negativos > 0 and automato.quantidade_sorteios > 0:
                            partida = automato.partidas.last()
                            keno = partida.valor_keno
                            kina = partida.valor_kina
                            kuadra = partida.valor_kuadra
                            prox = True
                        else:
                            prox = False
                    
                    if prox:
                        template = TemplatePartida.objects.create(
                            valor_keno = keno,
                            valor_kina= kina,
                            valor_kuadra=kuadra,
                            usuario = automato.usuario,
                            valor_cartela = partida.valor_cartela,
                            valor_antecipado = partida.valor_antecipado,
                            data_partida = data_prox,
                            data_introducao = datetime.datetime.now(),
                            id_automato = automato.id,
                            tipo_rodada = partida.tipo_rodada,
                            hora_virada = partida.hora_virada
                        )
                        template.franquias.set(partida.franquias.all())
                        template.save() 
                        agenda.agendar_template(template)
                        automato.save()
                else:
                    if resultado <= 0 :
                        automato.quantidade_negativos = automato.quantidade_negativos - 1
                    else:
                        automato.lucro_total = float(automato.lucro_total) + float(resultado)
                    if automato.quantidade_negativos > 0  and automato.quantidade_sorteios > 0 and resultado > automato.valor_minimo_maximo:
                        automato.quantidade_sorteios = automato.quantidade_sorteios - 1
                        template = TemplatePartida.objects.create(
                            valor_keno = partida.valor_keno,
                            valor_kina= partida.valor_kina,
                            valor_kuadra=partida.valor_kuadra,
                            usuario = automato.usuario,
                            valor_cartela = partida.valor_cartela,
                            valor_antecipado = partida.valor_antecipado,
                            data_partida = data_prox,
                            data_introducao = datetime.datetime.now(),
                            id_automato = automato.id,
                            tipo_rodada = partida.tipo_rodada,
                            hora_virada = partida.hora_virada
                        )
                        template.franquias.set(partida.franquias.all())
                        template.save() 
                        agenda.agendar_template(template)
                        automato.save()

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
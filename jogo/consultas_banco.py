from datetime import datetime, timedelta,time

from jogo.models import Partida,  Configuracao
from django.db.models import Sum
from django.db import connection, transaction

def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def cartelas_sql_teste(partida_id):
    with connection.cursor() as cursor: 
        cursor.execute(f"""
            select jogo_cartela.id,codigo,linha1,linha2,linha3,vencedor_kuadra,vencedor_kina,vencedor_keno,jogo_jogador.nome 
            from jogo_cartela left join jogo_jogador on jogo_cartela.jogador_id = jogo_jogador.id             
            where partida_id = {partida_id} and cancelado = false
            """
        )
        return dictfetchall(cursor)

def cartelas_sql_linhas(partida_id):
    with connection.cursor() as cursor:
        cursor.execute(f"""            
            select codigo
             , split_part(linha1, ',', 1) AS linha1_0
             , split_part(linha1, ',', 2) AS linha1_1
             , split_part(linha1, ',', 3) AS linha1_2
             , split_part(linha1, ',', 4) AS linha1_3
             , split_part(linha1, ',', 5) AS linha1_4
             , split_part(linha2, ',', 1) AS linha2_0
             , split_part(linha2, ',', 2) AS linha2_1
             , split_part(linha2, ',', 3) AS linha2_2
             , split_part(linha2, ',', 4) AS linha2_3
             , split_part(linha2, ',', 5) AS linha2_4
             , split_part(linha3, ',', 1) AS linha3_0
             , split_part(linha3, ',', 2) AS linha3_1
             , split_part(linha3, ',', 3) AS linha3_2
             , split_part(linha3, ',', 4) AS linha3_3
             , split_part(linha3, ',', 5) AS linha3_4 
            
            from jogo_cartela 
            where partida_id = {partida_id} and cancelado = false
            """
        )

        dados = {}
        for row in cursor.fetchall():
            numeros = row[1:]
            dados[row[0]] = [
                [int(numero) for numero in numeros[:5]],
                [int(numero) for numero in numeros[5:10]],
                [int(numero) for numero in numeros[10:15]],
            ]

        return dados

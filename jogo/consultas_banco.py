from datetime import datetime, timedelta,time

from jogo.consts import NumeroVitorias
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
            select id,codigo,linha1,linha2,linha3,vencedor_kuadra,vencedor_kina,vencedor_keno,nome,jogador_id 
            FROM jogo_cartela  
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


def estatisticas_jogadores(filtro, vitorias=-1):
    jogadores_geral = []
    jogadores_vitorias = []
    jogadores_partidas = {}
    with connection.cursor() as cursor:
        sql = """
            select j.id,j.nome,j.instagram,j.whatsapp,
            count(c.id) as cartelas, count(distinct p.id) as sorteios
            from jogo_jogador as j
            inner join jogo_cartela as c
            on c.jogador_id=j.id
            inner join jogo_partida as p
            on p.id=c.partida_id 
        """
        if filtro:
            sql+=f"WHERE {' AND '.join(filtro)}"
        sql += " group by j.id"

        cursor.execute(sql)
        jogadores_geral = cursor.fetchall()

    with connection.cursor() as cursor:
        sql = """
            select j.id, p.id  
            from jogo_jogador as j
            inner join jogo_cartela as c
            on c.jogador_id=j.id
            inner join jogo_partida as p on p.id=c.partida_id 
        """
        if filtro:
            sql+=f"WHERE {' AND '.join(filtro)}"

        sql += " order by j.id"
        cursor.execute(sql)
        jogadores_partidas_sql = cursor.fetchall()
        for j in jogadores_partidas_sql:
            if j[0] in jogadores_partidas.keys():
                jogadores_partidas[j[0]].append(j[1])
            else:
                jogadores_partidas[j[0]]=[j[1]]

    with connection.cursor() as cursor:
        sql = """
            select j.id,count(distinct cv.id) as vitorias 
            from jogo_jogador as j
            inner join jogo_cartela as c
            on c.jogador_id=j.id
            left join jogo_cartelavencedora as cv
            on c.id=cv.cartela_id
            inner join jogo_partida as p
            on p.id=c.partida_id 
        """
        if filtro:
            sql+=f"WHERE {' AND '.join(filtro)}"

        sql += " group by j.id "

        if vitorias == NumeroVitorias.NENHUMA:
            sql += " HAVING count(distinct cv.id)=0 "
        elif vitorias == NumeroVitorias.MINIMO_1:
            sql += " HAVING count(distinct cv.id)>0 "
        elif vitorias == NumeroVitorias.ATE_5:
            sql += " HAVING count(distinct cv.id)>0 and count(distinct cv.id)<6 "
        elif vitorias == NumeroVitorias.ATE_20:
            sql += " HAVING count(distinct cv.id)>0 and count(distinct cv.id)<21 "
        elif vitorias == NumeroVitorias.MAIS_20:
            sql += " HAVING count(distinct cv.id)>20 "

        sql += "order by vitorias desc,count(c.id) desc"
        cursor.execute(sql)
        jogadores_vitorias = cursor.fetchall()

    jogadores = {}
    for row in jogadores_vitorias:
        if row[0] in jogadores.keys():
            jogadores[row[0]].append(row[1])
        else:
            jogadores[row[0]] = [row[1]]


    for row in jogadores_geral:
        if row[0] in jogadores.keys():
            jogadores[row[0]]+=[row[1],row[2],row[3],row[4],row[5]]
        else:
            if vitorias==-1:
                jogadores[row[0]] = [0,row[1],row[2],row[3],row[4],row[5]]

    for k,v in jogadores_partidas.items():
        if k in jogadores.keys():
            jogadores[k]+=[v]
        else:
            if vitorias == -1:
                jogadores[k] = [v]

    return jogadores

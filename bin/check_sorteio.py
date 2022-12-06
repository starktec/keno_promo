import psycopg2
import datetime

conn = psycopg2.connect(
    host="130.185.238.250",
    database="keno",
    user="postgres",
    password="keno@123"
)
#print(conn)
partida_id = 0
try:
    # create a cursor
    cur = conn.cursor()

    # execute a statement
    agora = datetime.datetime.now()
    date_range = [agora-datetime.timedelta(minutes=1),agora]
    #print(date_range)
    cur.execute(f"SELECT * from jogo_partida where data_partida between '{date_range[0]}' and '{date_range[1]}'")

    for linha in cur.fetchall():
        #print(linha)
        if linha:
            partida_id = linha[0]
            break

    # close the communication with the PostgreSQL
    cur.close()
except (Exception, psycopg2.DatabaseError) as error:
    print(error)
finally:
    if conn is not None:
        conn.close()
        #print('Database connection closed.')
        if partida_id:
            print(partida_id)
        else:
            print(0)

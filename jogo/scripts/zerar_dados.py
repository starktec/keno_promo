from django.db import connection

from jogo.models import Automato, GrupoCanal, Partida, TemplatePartida, Cartela, CartelaVencedora, ReciboPagamento
from easyaudit.models import CRUDEvent,LoginEvent


def idseq(model_class):
    return '{}_id_seq'.format(model_class._meta.db_table)

def reset_sequence(model_class, value=1):
    cursor = connection.cursor()
    sequence = idseq(model_class)
    print(sequence)
    print(model_class)
    cursor.execute(f"ALTER SEQUENCE {sequence} RESTART WITH {value};")#.format(sequence, value))



def run(*args, **kwargs):
    with connection.cursor() as cursor:
        GrupoCanal.objects.all().delete()
        ReciboPagamento.objects.all().delete()
        cursor.execute("delete from jogo_cartelavencedora")
        cursor.execute("delete from jogo_cartela")
        Partida.objects.all().delete()
        Automato.objects.all().delete()
        TemplatePartida.objects.all().delete()


        cursor.execute("delete from easyaudit_crudevent")
        cursor.execute("delete from easyaudit_requestevent")
        cursor.execute("delete from easyaudit_loginevent")

    reset_sequence(ReciboPagamento)
    reset_sequence(Partida)
    reset_sequence(Cartela)
    reset_sequence(CartelaVencedora)
    reset_sequence(CRUDEvent)
    reset_sequence(LoginEvent)
    reset_sequence(Automato)
    reset_sequence(TemplatePartida)
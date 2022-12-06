from jogo.models import Partida, Agendamento
from jogo.agendamento import Agenda

def run(*args, **kwargs):
    for id in args:
        p = Partida.objects.filter(id=id).first()
        if p:
            #a = Agendamento.objects.filter(partida=p).first()
            #if a:
            #    a.delete()
            Agenda().sortear_agendado(partida=p,reload=False)

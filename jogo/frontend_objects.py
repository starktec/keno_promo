class FrontEndFranquia(object):
    franquia = None
    partidas = []

class FrontEndPartida(object):
    id = None
    efetividade_partida = None
    total_pdvs = None
    efetividade_percentual = None
    telas_partida = None
    total_telas = None
    subiu = None

class FrontEndADSCriar(object):
    partida = None
    datas_disponiveis = []

    def __init__(self, **kwargs):
        self.partida = kwargs['partida']
        self.datas_disponiveis = sorted(kwargs['datas_disponiveis'])
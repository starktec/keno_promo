from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def event_tela():
    '''
    Caso a tela venha a ter um save no banco, essa função é chamada para atualizar o total de telas
    no websocket

    '''
    layer = get_channel_layer()
    async_to_sync(layer.group_send)('real-time-data', {
        'type': 'events.tela',
    })

def event_pos():
    '''
    pos online/offline

    '''
    layer = get_channel_layer()
    async_to_sync(layer.group_send)('real-time-data', {
        'type': 'events.pos',
    })

def event_doacoes():
    '''
    caso alguma cartela for comprada atualiza os dados dos websockets
    '''
    layer = get_channel_layer()
    async_to_sync(layer.group_send)('real-time-data', {
        'type': 'events.doacoes',
    })

def event_tela_partidas(franquias):
    '''
    caso salve algum novo sorteio ou atualize algo manda para todas as rotas de franquias
    '''
    for f in franquias:
        layer = get_channel_layer()
        async_to_sync(layer.group_send)('tela-connect-franquia-'+str(f.id), {
            'type': 'events.tela.partidas'
        })

def event_tela_sorteio(id_sorteio,franquias):
    '''
    termino do sorteio
    '''
    layer = get_channel_layer()
    for f in franquias:
        async_to_sync(layer.group_send)('tela-connect-franquia-'+str(f.id), {
            'type': 'events.tela.sorteio',
            'id_sorteio':id_sorteio
        })
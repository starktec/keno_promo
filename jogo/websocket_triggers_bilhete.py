from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime
from jogo.models import GrupoWebSocket, Partida


def event_bilhete_sorteio(id_sorteio):
    '''
    termino do sorteio
    '''
    layer = get_channel_layer()
    if layer:
        async_to_sync(layer.group_send)('sorteio-'+str(id_sorteio), {
            'type': 'events.bilhete.sorteio',
            'id_sorteio':id_sorteio
        })


def event_fechar_grupo_sorteio(id_sorteio):
    '''
    termino do sorteio
    '''
    layer = get_channel_layer()
    if layer:
        grupo = GrupoWebSocket.objects.filter(partida__id=id_sorteio).first()
        if grupo:

            canais = grupo.grupocanal_set.all()
            for canal in canais:
                async_to_sync(layer.group_discard)(grupo.nome, canal.nome)

            async_to_sync(layer.group_send)(grupo.nome, {"type":"websocket_disconnect"})
            grupo.delete()


def event_bilhete_partida(id_sorteio):
    '''
        termino do sorteio
        '''
    layer = get_channel_layer()
    if layer:
        agora = datetime.now()
        sorteio_ids = [partida.id for partida in Partida.objects.filter(data_partida__gt=agora)]
        if not sorteio_ids:
            sorteio_ids = [id_sorteio]
        for id in sorteio_ids:
            async_to_sync(layer.group_send)('sorteio-' + str(id), {
                'type': 'events.bilhete.partida',
                'id_sorteio': id_sorteio
            })


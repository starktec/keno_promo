from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def event_doacoes():
    '''
    caso alguma cartela for comprada atualiza os dados dos websockets
    '''
    layer = get_channel_layer()
    async_to_sync(layer.group_send)('real-time-data', {
        'type': 'events.doacoes',
    })
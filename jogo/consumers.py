import datetime
from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import logging
import json
from django.db.models.aggregates import Sum

from jogo.models import Cartela, Jogador, Partida
logger = logging.getLogger(__name__)

GROUPS = []

class DadosTempoRealConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            logger.info(f"WS Connection {self.channel_name} - DADOS TEMPO REAL")
            self.user = self.scope["user"]
            await self.accept()
            partidas,novos_jogadores_min = await self.doacoes()
            await self.channel_layer.group_add( # criando um layer group
                "real-time-data",
                self.channel_name
            )
            await self.send(json.dumps({'partidas':partidas, "novos_jogadores_min":novos_jogadores_min}))
        except Exception as e:
            logger.exception(e)
            raise e

    @sync_to_async
    def doacoes(self):
        try:
            dados = []
            novos_jogadores_min = Jogador.objects.filter(cadastrado_em__gt =(datetime.datetime.now() - datetime.timedelta(minutes=1)),
                                        cadastrado_em__lt = datetime.datetime.now()).count()
            for p in Partida.objects.filter(data_partida__gt=datetime.datetime.now(),bolas_sorteadas__isnull = True):
                cartelas_count = Cartela.objects.filter(jogador__isnull=False,partida=p).count()
                
                partida = {
                    "partida":p.id,
                    "data_partida":datetime.datetime.strftime(p.data_partida,"%d-%m-%Y %H:%M"),
                    "tipo":p.get_tipo_rodada_display(),
                    "cartelas_count":cartelas_count,
                    "novos_participantes":p.novos_participantes,
                    "limite":p.numero_cartelas_iniciais,
                }
                dados.append(partida)
    
            return {'partidas':dados},novos_jogadores_min
        except Exception as e:
            logger.exception(e)
            raise e
    
    async def events_doacoes(self,event):
        try:
            partidas,novos_jogadores_min = await self.doacoes()
            await self.send(json.dumps({'partidas':partidas,'novos_jogadores_min':novos_jogadores_min}))
        except Exception as e:
            logger.exception(e)
            raise e
import datetime
import json
import logging
from enum import Enum

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from asgiref.sync import sync_to_async
from django.db.models import TextChoices

from jogo.serializers import PartidaProximaEspecialSerializer, PartidaProximaSerializer
from .models import Configuracao, GrupoWebSocket, GrupoCanal, \
    DispositivosConectados, Partida, Cartela

logger = logging.getLogger(__name__)

class MessageType(Enum):
    SORTEIO_ID = "sorteio_ids"

class ConexaoBilheteConsumer(AsyncJsonWebsocketConsumer):

    @sync_to_async
    def proximos_sorteios(self, sorteio_id, hash):
        try:
            proximos = [Partida.objects.get(id=sorteio_id),]
            bilhetes = [{"sorteio_id":sorteio_id,"bilhete":hash}]
            serializer = PartidaProximaSerializer(instance=proximos, many=True)
            return {"type":"proximos_sorteios","sorteios":serializer.data,"bilhetes":bilhetes,
                    'datahora':datetime.datetime.strftime(datetime.datetime.now(),'%Y-%m-%dT%H:%M:%S')}
        except Exception as e:
            logger.exception(e)
            raise e

    @sync_to_async
    def cartela_jogador_exists(self,token,sorteio):
        return Cartela.objects.filter(jogador__usuario_token=token,partida_id=sorteio).exists()
    

    async def connect(self):
        logger.info(f"WS Connect {self.channel_name} - TOKEN {self.scope['url_route']['kwargs']['token']}")
        token = self.scope['url_route']['kwargs']['token']
        sorteio = self.scope['url_route']['kwargs']['sorteio']
        hash = self.scope['url_route']['kwargs']['bilhete']

        if await self.cartela_jogador_exists(token,sorteio):
            logger.info(f"Encontrou cartela {hash}")
            partida_id = sorteio
            await self.accept()
            if partida_id:
                if partida_id>0:
                    self.nome_sala = 'sorteio-'+str(partida_id)

                    await self.channel_layer.group_add( # criando um layer group
                        self.nome_sala,
                        self.channel_name
                    )

                    await self.aumentar_quantidade_conexoes_sala()

                await self.send_json({'code': 200, 'message': 'Conexao estabelecida!', 'error_message': '', 'data': {}})
                proximos_sorteios = await self.proximos_sorteios(sorteio, hash)
                await self.send_json(proximos_sorteios)
                logger.info(f" - Conexão Estabelecida ")

            else:
                logger.info(f" - Não encontrado próximos sorteios ")
                await self.send_json({'code': 404, 'message': 'Bilhetes não encontrados ou token inválido',
                                'error_message': 'Não existe', 'data': {}})
                self.websocket_disconnect(message={"code":1000})



    async def events_bilhete_sorteio(self,event):
        sorteio = event.get('id_sorteio')
        logger.info(f"WS {self.channel_name} - evento sorteio {sorteio}")
        await self.send_json({"type":"sorteio","id_sorteio":sorteio})
        #await self.channel_layer.group_discard('sorteio-'+str(sorteio), self.channel_name)

    @sync_to_async
    def aumentar_quantidade_conexoes_sala(self):
        try:
            d, created = DispositivosConectados.objects.get_or_create(nome_sala= self.nome_sala)
            d.quantidade += 1
            d.save()
        except Exception as e:
            logger.exception(e)
            raise e

    @sync_to_async
    def diminuir_quantidade_conexoes_sala(self):
        try:
            d = DispositivosConectados.objects.filter(nome_sala= self.nome_sala).first()
            if d:
                d.quantidade -= 1
                d.save()
        except Exception as e:
            logger.exception(e)
            raise e


    async def disconnect(self,code):
        logger.info(f"WS Disconnect {self.channel_name}")
        try:
            if self.nome_sala:
                await self.diminuir_quantidade_conexoes_sala()
        except Exception as e:
            pass
        finally:
            return await super().disconnect(code)

    @sync_to_async
    def get_serializer_data(self,serializer):
        return serializer.data

    @sync_to_async
    def send_proximos_sorteios(self,ids):
        proximos = Partida.objects.filter(id__in=ids)
        if proximos:
            serializer = PartidaProximaSerializer(instance=proximos, many=True)
            return {"type": "proximos_sorteios", "sorteios": serializer.data,
                     'datahora': datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%dT%H:%M:%S')}

        else:
            return {"messagem": "Sorteios não encontrados"}

    async def receive_json(self, content, **kwargs):
        data = content
        if data["type"] == MessageType.SORTEIO_ID.value:
            ids = [int(d) for d in data['values'].split(",") if d.isdigit()]
            if ids:
                dados = await self.send_proximos_sorteios(ids)
                await self.send_json(dados)
            else:
                await self.send_json({"messagem": "Formatação incorreta"})
        else:
            await self.send_json({"messagem":"Não há o que responder"})

    @sync_to_async
    def sorteio_atualizado(self, sorteio_id):
        partida = Partida.objects.get(id=sorteio_id)
        serializer = PartidaProximaSerializer(instance=partida,read_only=True)
        return {"type": "update_sorteio", "sorteio": serializer.data,
                'datahora': datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%dT%H:%M:%S')}

    async def events_bilhete_partida(self, event):
        try:
            proximo = await self.sorteio_atualizado(event['id_sorteio'])
            await self.send_json(proximo)

        except Exception as e:
            logger.exception(e)
            raise e


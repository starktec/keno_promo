import datetime
from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import logging
import json
from django.db.models.aggregates import Sum
from jogo.serializers import PartidaProximaSerializer, PartidaProximaEspecialSerializer

from jogo.models import Cartela, Jogador, Partida, Configuracao, CartelaVencedora

logger = logging.getLogger(__name__)

GROUPS = []


class ConexaoTelaConsumer(AsyncJsonWebsocketConsumer):
    @sync_to_async
    def proximos_sorteios(self):
        proximos = Partida.objects.filter(
            data_partida__gt=datetime.datetime.now(), em_sorteio=False, bolas_sorteadas__isnull=True, tipo_rodada=1
        ).order_by('data_partida')[:5]
        serializer = PartidaProximaSerializer(instance=proximos, many=True)
        logger.info(f" - Próximos: {[str(proximo.id) for proximo in proximos]}")
        return {"type": "proximos_sorteios", "sorteios": serializer.data, 'datahora': datetime.datetime.strftime(
            datetime.datetime.now(), '%Y-%m-%dT%H:%M:%S')}

    @sync_to_async
    def proximos_especiais(self):
        proximos = Partida.objects.filter(
            data_partida__gt=datetime.datetime.now(), em_sorteio=False, bolas_sorteadas__isnull=True,
            tipo_rodada=2
        ).order_by('data_partida')[:5]
        serializer = PartidaProximaEspecialSerializer(instance=proximos, many=True)
        logger.info(f" - Próximos: {[str(proximo.id) for proximo in proximos]}")
        return {"type": "proximos_especiais", "sorteios": serializer.data, 'datahora': str(datetime.datetime.now())}

    @sync_to_async
    def proximos_s_especiais(self):

        proximos = Partida.objects.filter(
            data_partida__gt=datetime.datetime.now(), em_sorteio=False, bolas_sorteadas__isnull=True,
            tipo_rodada=3
        ).order_by('data_partida')[:5]
        serializer = PartidaProximaEspecialSerializer(instance=proximos, many=True)
        logger.info(f" - Próximos: {[str(proximo.id) for proximo in proximos]}")
        return {"type": "proximos_s_especiais", "sorteios": serializer.data, 'datahora': str(datetime.datetime.now())}

    @sync_to_async
    def ultimos_ganhadores(self):
        try:
            vencedores = []
            configuracao = Configuracao.objects.last()
            data_liberacao = datetime.datetime.now() - datetime.timedelta(
                minutes=configuracao.liberar_resultado_sorteio_em)
            for v in CartelaVencedora.objects.filter(
                    partida__data_partida__lte=data_liberacao
            ).order_by('-id')[:6]:
                d = {
                    'sorteio': int(v.partida.id),
                    'cartela': int(v.cartela.codigo),
                    'nome': str(v.cartela.nome),
                    'premio': float(v.valor_premio),
                    'tipo': int(v.premio)
                }
                vencedores.append(d)
            return {'type': 'vencedores', 'vencedores': vencedores}
        except Exception as e:
            logger.exception(e)


    async def connect(self):
        logger.info(f"WS Connect {self.channel_name} - TOKEN {self.scope['url_route']['kwargs']['token']}")
        self.user = self.scope["user"]
        self.token = self.scope['url_route']['kwargs']['token']
        self.nome_sala = 'tela-connect'
        if self.nome_sala not in GROUPS:
            GROUPS.append(self.nome_sala)

        await self.accept()
        await self.channel_layer.group_add(  # criando um layer group
            self.nome_sala,
            self.channel_name
        )

        await self.send_json({'code': 200, 'message': 'Conexao estabelecida!', 'error_message': '', 'data': {}})
        proximos_sorteios = await self.proximos_sorteios()
        logger.info(f" - {proximos_sorteios}")
        proximos_especiais = await self.proximos_especiais()
        logger.info(f" - {proximos_especiais}")
        proximos_se_especiais = await self.proximos_s_especiais()
        logger.info(f" - {proximos_se_especiais}")
        ultimos_ganhadores = await self.ultimos_ganhadores()
        logger.info(f" - {ultimos_ganhadores}")
        await self.send_json(proximos_sorteios)
        await self.send_json(proximos_especiais)
        await self.send_json(proximos_se_especiais)
        await self.send_json(ultimos_ganhadores)

    async def disconnect(self, code):
        logger.info(f"WS Disconnect {self.channel_name}")
        await self.desconectar_tela()
        return await super().disconnect(code)

    async def events_tela_partidas(self, event):
        try:
            proximos_sorteios = await self.proximos_sorteios()
            proximos_especiais = await self.proximos_especiais()
            proximos_s_especiais = await self.proximos_s_especiais()
            await self.send_json(proximos_sorteios)
            await self.send_json(proximos_especiais)
            await self.send_json(proximos_s_especiais)
        except Exception as e:
            logger.exception(e)
            raise e

    async def events_tela_sorteio(self, event):
        sorteio = event.get('id_sorteio')
        logger.info(f"WS Notificando sorteio {sorteio}")
        await self.send_json({"type": "sorteio", "id_sorteio": sorteio})

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
            agora = datetime.datetime.now()

            novos_jogadores_min = Cartela.objects.filter(
                comprado_em__gt =(agora - datetime.timedelta(minutes=1)),
                comprado_em__lt = agora
            ).count()

            for p in Partida.objects.filter(
                    data_partida__gt=agora,bolas_sorteadas__isnull = True
            ).order_by("data_partida"):
                cartelas_count = Cartela.objects.filter(jogador__isnull=False,partida=p).count()
                if not cartelas_count:
                    break
                
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
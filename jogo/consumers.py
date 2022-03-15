import datetime
import json
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer # The class we're using
from asgiref.sync import sync_to_async
from django.db.models.aggregates import Sum
from jogo.serializers import PartidaProximaEspecialSerializer, PartidaProximaSerializer
from .models import Cartela, Configuracao, Partida, DispositivosConectados, CartelaVencedora

logger = logging.getLogger(__name__)

GROUPS = []

class ConexaoTelaConsumer(AsyncJsonWebsocketConsumer):

    @sync_to_async
    def conectar_tela(self):
        try:
            tv = TV.objects.get(senha_numerica=self.token)
            self.tv = tv
            tv.online = True
            tv.save()
            logger.info(f" - TELA {tv} - ONLINE {tv.online}")
            return tv.estabelecimento.franquia.id
        except Exception as e:
            logger.exception(e)
            raise e
    @sync_to_async
    def desconectar_tela(self):
        try:
            tv = TV.objects.get(senha_numerica=self.token)
            tv.online = False
            tv.save()
            logger.info(f" - TELA {tv} - ONLINE {tv.online}")
        except Exception as e:
            logger.exception(e)
            raise e

    @sync_to_async
    def proximos_sorteios(self):
        tv = self.tv
        franquia = tv.estabelecimento.franquia or None
        agora = datetime.datetime.now()
        proximos = Partida.objects.filter(franquias=franquia).filter(
            data_partida__gt=agora,em_sorteio=False, bolas_sorteadas__isnull=True,tipo_rodada = 1
        ).order_by('data_partida')[:5]
        serializer = PartidaProximaSerializer(instance=proximos, many=True)
        logger.info(f" - Próximos: {[str(proximo.id) for proximo in proximos]}")
        return {"type":"proximos_sorteios","sorteios":serializer.data,'datahora':datetime.datetime.strftime(
                datetime.datetime.now(),'%Y-%m-%dT%H:%M:%S')}
    
    @sync_to_async
    def proximos_especiais(self):
        tv = self.tv
        franquia = tv.estabelecimento.franquia or None
        proximos = Partida.objects.filter(franquias=franquia).filter(
            data_partida__gt=datetime.datetime.now(), em_sorteio=False, bolas_sorteadas__isnull=True,
            tipo_rodada=2
        ).order_by('data_partida')[:5]
        serializer = PartidaProximaEspecialSerializer(instance=proximos, many=True)
        logger.info(f" - Próximos: {[str(proximo.id) for proximo in proximos]}")
        return {"type":"proximos_especiais","sorteios":serializer.data,'datahora':str(datetime.datetime.now())}
    
    @sync_to_async
    def proximos_s_especiais(self):
        tv = self.tv
        franquia = tv.estabelecimento.franquia or None
        proximos = Partida.objects.filter(franquias=franquia).filter(
            data_partida__gt=datetime.datetime.now(), em_sorteio=False, bolas_sorteadas__isnull=True,
            tipo_rodada=3
        ).order_by('data_partida')[:5]
        serializer = PartidaProximaEspecialSerializer(instance=proximos, many=True)
        logger.info(f" - Próximos: {[str(proximo.id) for proximo in proximos]}")
        return {"type":"proximos_s_especiais","sorteios":serializer.data,'datahora':str(datetime.datetime.now())}

    @sync_to_async
    def ultimos_ganhadores(self):
        tv = self.tv
        franquia = tv.estabelecimento.franquia or None

        vencedores = []
        configuracao = Configuracao.objects.last()
        data_liberacao = datetime.datetime.now() - datetime.timedelta(
            minutes=configuracao.liberar_resultado_sorteio_em)
        for v in CartelaVencedora.objects.filter(
                partida__franquias=franquia,
                partida__data_partida__lte=data_liberacao
        ).order_by('-id')[:6]:
            d = {
                'sorteio': int(v.partida.id),
                'cartela': int(v.cartela.codigo),
                'nome': str(v.cartela.pdv.estabelecimento),
                'premio': float(v.valor_premio),
                'tipo': int(v.premio) if not v.ganhou_acumulado else 4
            }
            vencedores.append(d)
        return {'type':'vencedores','vencedores': vencedores}

    
    @sync_to_async
    def conectar_sala(self):
        try:
            if not DispositivosConectados.objects.filter(nome_sala= self.nome_sala):
                d = DispositivosConectados.objects.create(nome_sala= self.nome_sala)
            else:
                d = DispositivosConectados.objects.get(nome_sala= self.nome_sala)
                d.quantidade += 1
                d.save()
        except Exception as e:
            logger.exception(e)
            raise e

    @sync_to_async
    def desconectar_sala(self):
        try:
            d = DispositivosConectados.objects.get(nome_sala= self.nome_sala)
            d.quantidade -= 1
            d.save()
        except Exception as e:
            logger.exception(e)
            raise e

    async def connect(self):
        logger.info(f"WS Connect {self.channel_name} - TOKEN {self.scope['url_route']['kwargs']['token']}")
        self.user = self.scope["user"]
        self.token = self.scope['url_route']['kwargs']['token']
        franquia_id = await self.conectar_tela()
        self.nome_sala = 'tela-connect-franquia-'+str(franquia_id)
        if self.nome_sala not in GROUPS:
            GROUPS.append(self.nome_sala)

        await self.accept() 
        await self.channel_layer.group_add( # criando um layer group
            self.nome_sala,
            self.channel_name
        )

        await self.send_json({'code':200, 'message': 'Conexao estabelecida!', 'error_message': '', 'data':{}})
        proximos_sorteios = await self.proximos_sorteios()
        proximos_especiais = await self.proximos_especiais()
        proximos_se_especiais = await self.proximos_s_especiais()
        ultimos_ganhadores = await self.ultimos_ganhadores()
        await self.send_json(proximos_sorteios)
        await self.send_json(proximos_especiais)
        await self.send_json(proximos_se_especiais)
        await self.send_json(ultimos_ganhadores)

    async def disconnect(self,code):
        logger.info(f"WS Disconnect {self.channel_name}")
        await self.desconectar_tela()
        return await super().disconnect(code)

    async def events_tela_partidas(self,event):
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
        
    
    async def events_tela_sorteio(self,event):
        sorteio = event.get('id_sorteio')
        logger.info(f"WS Notificando sorteio {sorteio}")
        await self.send_json({"type":"sorteio","id_sorteio":sorteio})

class DadosTempoRealConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            logger.info(f"WS Connection {self.channel_name} - DADOS TEMPO REAL")
            self.user = self.scope["user"]
            await self.accept()
            partidas,total_doacoes,doacoes_min = await self.doacoes()
            tvs_online,total_telas = await self.telas_online()
            pos_online,pos_total = await self.pos_online()
            await self.channel_layer.group_add( # criando um layer group
                "real-time-data",
                self.channel_name
            )
            await self.send(json.dumps({'partidas':partidas, "total_doacoes":total_doacoes, "tvs_online":tvs_online,
                                            'total_telas':total_telas, 'doacoes_min':doacoes_min, 'pos_online':pos_online, 'pos_total':pos_total}))
        except Exception as e:
            logger.exception(e)
            raise e

    @sync_to_async
    def doacoes(self):
        try:
            doacoes_total = 0
            dados = []
            doacoes_min = 0.00
            valor_premio = 0
            for p in Partida.objects.filter(data_partida__gt=datetime.datetime.now(),bolas_sorteadas__isnull = True):
                doacoes_partida = p.doacoesP()
                rtp_percentual = 0
                cartelas = Cartela.objects.filter(gerado_em__gt =(datetime.datetime.now() - datetime.timedelta(minutes=1)),
                                        gerado_em__lt = datetime.datetime.now())
                if cartelas.count():
                    doacoes_min = (float(cartelas.aggregate(Sum('valor'))['valor__sum']) or 0.00)
                if doacoes_partida:
                    valor_premio = float(p.valor_keno + p.valor_kina + p.valor_keno)
                    numerador = float(doacoes_partida)-valor_premio   
                    denominador = float(doacoes_partida)
                    rtp_percentual = numerador/denominador * 100
                partida = {
                    "partida":p.id,
                    "data_partida":datetime.datetime.strftime(p.data_partida,"%d-%m-%Y %H:%M"),
                    "doacoes":doacoes_partida,
                    "tipo":p.get_tipo_rodada_display(),
                    "premios":valor_premio,
                    "franquias":",".join(franquia.referencia for franquia in p.franquias.all()),
                    "resultado":p.resultado_parcial(),
                    "rtp":rtp_percentual       
                }
                dados.append(partida)
                doacoes_total += float(doacoes_partida)
            return {'partidas':dados},doacoes_total,doacoes_min
        except Exception as e:
            logger.exception(e)
            raise e

    @sync_to_async
    def telas_online(self):
        try:
            tvs_online = TV.objects.filter(ativo=True,online=True).count()
            total_telas = TV.objects.filter(ativo=True).count()
            return tvs_online,total_telas
        except Exception as e:
            logger.exception(e)
            raise e

    @sync_to_async
    def pos_online(self):
        try:
            pos_online = PDV.objects.filter(ativo=True,online=True).count()
            pos_total = PDV.objects.filter(ativo=True).count()
            return pos_online,pos_total
        except Exception as e:
            logger.exception(e)
            raise e
    
    async def events_pos(self,event):
        try:
            pos_online,pos_total = await self.pos_online()
            await self.send(json.dumps({'pos_online':pos_online,'pos_total':pos_total}))
        except Exception as e:
            logger.exception(e)
            raise e


    async def events_tela(self,event):
        try:
            tvs_online,total_telas = await self.telas_online()
            await self.send(json.dumps({'tvs_online':tvs_online,'total_telas':total_telas}))
        except Exception as e:
            logger.exception(e)
            raise e
    
    async def events_doacoes(self,event):
        try:
            partidas,total_doacoes,doacoes_min = await self.doacoes()
            await self.send(json.dumps({'partidas':partidas,"total_doacoes":total_doacoes,'doacoes_min':doacoes_min}))
        except Exception as e:
            logger.exception(e)
            raise e
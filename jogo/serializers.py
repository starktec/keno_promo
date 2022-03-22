from datetime import datetime, timedelta
from rest_framework import serializers

from jogo.models import CartelaVencedora, Partida, Cartela, Configuracao

class CartelaSerializer(serializers.ModelSerializer):
    codigo = serializers.IntegerField(source='id')
    class Meta:
        model = Cartela
        fields = ['codigo', 'nome','linha1_lista','linha2_lista','linha3_lista']


class PartidaSerializer(serializers.ModelSerializer):
    #cartelas = CartelaSerializer(many=True,read_only=True)
    bola_kuadra = serializers.IntegerField()
    bola_kina = serializers.IntegerField()
    bola_keno = serializers.IntegerField()
    valor_kuadra = serializers.FloatField()
    valor_kina = serializers.FloatField()
    valor_keno = serializers.FloatField()
    codigo = serializers.IntegerField(source='id')
    bolas_sorteadas = serializers.JSONField(source="sorteadas_list")
    vencedores_kuadra = serializers.JSONField(source="cartelas_vencedoras_kuadra_json")
    vencedores_kina = serializers.JSONField(source="cartelas_vencedoras_kina_json")
    vencedores_keno = serializers.JSONField(source="cartelas_vencedoras_keno_json")
    cartelas = serializers.JSONField(source="cartelas_obj")
    turnos = serializers.JSONField(source="turnos_sorteio")
    datahora = serializers.DateTimeField(default=datetime.now())
    cartelas_compradas = serializers.JSONField()
    sorteio_nome = serializers.JSONField(source='nome_sorteio_text')
    linhas_vencedoras_kuadra = serializers.JSONField(source="linhas_vencedoras_kuadra_json")
    linhas_vencedoras_kina = serializers.JSONField(source="linhas_vencedoras_kina_json")
    linhas_vencedoras_keno = serializers.JSONField(source="linhas_vencedoras_keno_json")
    status = serializers.SerializerMethodField()

    def get_status(self,partida:Partida):
        agora = datetime.now()
        if agora < partida.data_partida:
            return 'aguardando'
        elif agora >= partida.data_partida and  agora <= partida.data_partida + timedelta(minutes=4):
            return 'agora'
        elif agora > partida.data_partida + timedelta(minutes=4):
            return 'replay'
    class Meta:
        model = Partida
        fields = ['codigo', 'tipo_rodada','data_partida','bolas_sorteadas','cartelas_compradas',
                  'bola_kuadra','bola_kina','bola_keno',
                  "vencedores_kuadra","vencedores_kina","vencedores_keno",
                  'valor_kuadra','valor_kina','valor_keno',
                  "cartelas", 'turnos', 'datahora', 'sorteio_nome', 'linhas_vencedoras_kuadra',
                  "linhas_vencedoras_kina","linhas_vencedoras_keno","status"]


class PartidaProximaSerializer(serializers.ModelSerializer):
    codigo = serializers.IntegerField(source='id')
    sorteio_nome = serializers.CharField(source='nome_sorteio')
    status = serializers.SerializerMethodField()

    def get_hora_antecipado(self,partida):
        return partida.horario_limite_antecipado()


    def get_status(self,partida):
        agora = datetime.now()
        if agora < partida.data_partida:
            return 'aguardando'
        elif agora >= partida.data_partida and  agora <= partida.data_partida + timedelta(minutes=4):
            return 'agora'
        elif agora > partida.data_partida + timedelta(minutes=4):
            return 'replay'
        
    class Meta:
        model = Partida
        fields = ['codigo', 'data_partida','tipo_rodada',
                  'valor_kuadra','valor_kina','valor_keno',
                   'sorteio_nome','status']



class PartidaProximaEspecialSerializer(PartidaProximaSerializer):
    codigo = serializers.IntegerField(source='id')
    sorteio_nome = serializers.CharField(source='nome_sorteio')
    class Meta:
        model = Partida
        fields = ['codigo', 'data_partida','tipo_rodada',
                  'valor_kuadra','valor_kina','valor_keno',
                  'sorteio_nome']

class PartidaHistoricoSerializer(serializers.ModelSerializer):
    codigo = serializers.IntegerField(source='id')
    vencedores_kuadra = serializers.JSONField(source="cartelas_vencedoras_kuadra_json")
    vencedores_kina = serializers.JSONField(source="cartelas_vencedoras_kina_json")
    vencedores_keno = serializers.JSONField(source="cartelas_vencedoras_keno_json")
    sorteio_nome = serializers.CharField(source='nome_sorteio')
    class Meta:
        model = Partida
        fields = ['codigo', 'data_partida', 'valor_kuadra','valor_kina','valor_keno',
                  "vencedores_kuadra","vencedores_kina","vencedores_keno",'sorteio_nome']


class CartelaDetalhesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cartela
        fields = ['partida','jogador__nome','codigo','linha1_lista','linha2_lista','linha3_lista']

class UltimosGanhadoresSerializer(serializers.ModelSerializer):
    sorteio = serializers.IntegerField(source='id')
    bilhetes_kuadra = serializers.SerializerMethodField()
    bilhetes_kina = serializers.SerializerMethodField()
    bilhetes_keno = serializers.SerializerMethodField()

    def get_bilhetes_kuadra(self,partida):
        cartelas = CartelaVencedora.objects.filter(partida=partida,premio=1)
        return CartelasVencedorasSerializer(cartelas,many=True).data
    def get_bilhetes_kina(self,partida):
        cartelas = CartelaVencedora.objects.filter(partida=partida,premio=2)
        return CartelasVencedorasSerializer(cartelas,many=True).data
    def get_bilhetes_keno(self,partida):
        cartelas = CartelaVencedora.objects.filter(partida=partida,premio=3)
        return CartelasVencedorasSerializer(cartelas,many=True).data

    class Meta:
        model = Partida
        fields = ['sorteio','bilhetes_kuadra','bilhetes_kina','bilhetes_keno']


class CartelasVencedorasSerializer(serializers.ModelSerializer):
    numero_cartela = serializers.SerializerMethodField()
    premio = serializers.SerializerMethodField()
    def get_numero_cartela(self,vencedora)->str:
        return vencedora.cartela.codigo
    def get_premio(self,vencedora)->str:
        return vencedora.valor_premio
    class Meta:
        model = CartelaVencedora
        fields = ['numero_cartela','premio']

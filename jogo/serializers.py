from datetime import datetime, timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers

from jogo.models import CartelaVencedora, Partida, Cartela, Configuracao, Jogador
import re

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
    tipo_sorteio = serializers.SerializerMethodField()
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
    def get_tipo_sorteio(self,partida):
        return partida.get_tipo_rodada_display()

    class Meta:
        model = Partida
        fields = ['sorteio','bilhetes_kuadra','bilhetes_kina','bilhetes_keno', "tipo_sorteio"]


class CartelasVencedorasSerializer(serializers.ModelSerializer):
    numero_cartela = serializers.SerializerMethodField()
    premio = serializers.SerializerMethodField()
    nome = serializers.SerializerMethodField()
    def get_numero_cartela(self,vencedora)->str:
        return vencedora.cartela.codigo
    def get_premio(self,vencedora)->str:
        return vencedora.valor_premio
    def get_nome(self, vencedora):
        return vencedora.cartela.nome

    class Meta:
        model = CartelaVencedora
        fields = ['numero_cartela','premio',"nome"]

NONO_DIGITO = [81, 82, 83, 84, 85, 86, 87, 88, 89, 31, 32, 33, 34, 35, 37, 38, 71, 73, 74, 75, 77, 79]
class CadastroJogadorSerializer(serializers.Serializer):
    usuario = serializers.CharField(max_length=100)
    email = serializers.EmailField(required=False)
    whatsapp = serializers.CharField(max_length=20,required=False, allow_blank=True)
    instagram = serializers.CharField(max_length=50,required=False, allow_blank=True)
    senha = serializers.CharField(max_length=20)
    confirmar_senha = serializers.CharField(max_length=20)

    def validate(self, attrs):
        usuario = attrs.get("usuario")
        email = attrs.get("email")
        whatsapp = attrs.get("whatsapp")
        senha = attrs.get("senha")
        confirmar_senha = attrs.get("confirmar_senha")
        instagram = attrs.get("instagram")
        usuario = usuario.lower()
        if Jogador.objects.filter(usuario__iexact=usuario).exists() or User.objects.filter(username__iexact=usuario).exists():
            raise serializers.ValidationError(detail="Login já cadastrado")
        usuario_avaliado = re.findall("[a-z0-9\.\_]+",usuario)
        if usuario_avaliado and len(usuario_avaliado) == 1:
            if len(usuario_avaliado[0]) != len(usuario):
                raise serializers.ValidationError(
                    detail="Apelido Inválido. Use apenas letras minúsuculas, números, pontos ou sublinhados"
                )
        else:
            raise serializers.ValidationError(
                detail="Apelido Inválido. Use apenas letras minúsuculas, números, pontos ou sublinhados"
            )
        if email and Jogador.objects.filter(user__email=email).exists():
            raise serializers.ValidationError(detail="E-mail já cadastrado")
        if whatsapp:
            if not whatsapp.isdigit() or len(whatsapp)>11:
                raise serializers.ValidationError(detail="Insira um número válido")
            if len(whatsapp)<10:
                raise serializers.ValidationError(detail="Insira um número completo com DDD")
            if Jogador.objects.filter(whatsapp=whatsapp).exists():
                raise serializers.ValidationError(detail="Número de Whatsapp já usado")
            ddd = int(whatsapp[:2])
            onze_digitos = ddd in NONO_DIGITO
            if onze_digitos and len(whatsapp)<11:
                raise serializers.ValidationError(detail="Insira um número válido")
            if Jogador.objects.filter(whatsapp=whatsapp).exists():
                raise serializers.ValidationError(detail="Número de Whatsapp já usado")
        if senha!=confirmar_senha:
            raise serializers.ValidationError(detail="'Senha' está diferente de 'Confirmar Senha'")
        if instagram:
            if instagram.startswith("@"):
                instagram = instagram[1:]
            if "/" in instagram:
                instagram = instagram.split("/www.instagram.com/")[1].split("/")[0]
            instagram = instagram.lower()

            instagram_avaliado = re.findall("[a-z0-9\.\_]+",instagram)
            if not instagram_avaliado or instagram_avaliado[0]!=instagram:
                raise serializers.ValidationError(
                    detail="Instagram inválido"
                )

            if Jogador.objects.filter(instagram=instagram).exists():
                raise serializers.ValidationError(detail="Perfil do instagram já cadastrado")

            attrs['instagram'] = instagram

        return attrs

    def create(self, validated_data):
        usuario = validated_data.get("usuario")
        email = validated_data.get("email")
        whatsapp = validated_data.get("whatsapp")
        instagram = validated_data.get("instagram")
        senha = validated_data.get("senha")
        user = User.objects.create_user(username=usuario,email=email,password=senha)
        jogador = Jogador.objects.create(
            usuario=usuario,whatsapp=whatsapp,user=user,instagram=instagram
        )
        return jogador

class JogadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Jogador
        fields = ["id","usuario","instagram"]

class LoginJogadorSerializer(serializers.Serializer):
    usuario = serializers.CharField(max_length=100)
    senha = serializers.CharField(max_length=20)

    def validate(self, attrs):
        usuario = attrs.get("usuario")
        senha = attrs.get("senha")
        jogador = Jogador.objects.filter(usuario__iexact=usuario).first()
        if not jogador:
            raise serializers.ValidationError(detail="apelido ou senha inválidos")
        if jogador.usuario != usuario:
            raise serializers.ValidationError(detail=f"Jogador não encontrado. Você quis dizer '{jogador.usuario}'?")
        user = authenticate(username=usuario, password=senha)
        if not user or not user.is_active:
            raise serializers.ValidationError(detail="apelido ou senha inválidos")

        return attrs

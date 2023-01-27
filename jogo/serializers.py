from datetime import datetime, timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count
from rest_framework import serializers

from jogo.choices import AcaoBonus
from jogo.consts import SOCIAL_MEDIA_IMAGES, LocalBotaoChoices
from jogo.models import CartelaVencedora, Partida, Cartela, Configuracao, Jogador, CreditoBonus, RegraBonus, \
    ConfiguracaoAplicacao, BotaoAplicacao, BotaoMidiaSocial, Parceiro, RequisicaoPremioAplicacao, UserAfiliadoTeste, \
    CampoCadastro
import re

import logging
logger = logging.getLogger(__name__)

from jogo.utils import cpf_isvalid


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
    velocidade_sorteio = serializers.SerializerMethodField()
    velocidade_sorteio_online = serializers.SerializerMethodField()

    def get_velocidade_sorteio(self, obj):
        configuracao = Configuracao.objects.last()
        return int(configuracao.velocidade_sorteio)

    def get_velocidade_sorteio_online(self, obj):
        configuracao = Configuracao.objects.last()
        return int(configuracao.velocidade_sorteio_online)

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
                  "linhas_vencedoras_kina","linhas_vencedoras_keno","status","velocidade_sorteio","velocidade_sorteio_online"]


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
    cpf = serializers.CharField(max_length=11,required=False, allow_blank=True)
    codigo = serializers.CharField(max_length=6, min_length=6,required=False, allow_blank=True)

    def validate(self, attrs):
        usuario = attrs.get("usuario")
        email = attrs.get("email")
        whatsapp = attrs.get("whatsapp")
        senha = attrs.get("senha")
        confirmar_senha = attrs.get("confirmar_senha")
        instagram = attrs.get("instagram")
        codigo = attrs.get("codigo")
        cpf = attrs.get("cpf")

        campos_obrigatorios = CampoCadastro.objects.filter(ativo=True,obrigatorio=True)
        for obrigatorio in campos_obrigatorios:
            if not attrs.get(obrigatorio.nome):
                raise serializers.ValidationError(detail=f"{obrigatorio.nome.upper()}: Campo Obrigatório")


        if cpf:
            if not cpf.isdigit():
                raise serializers.ValidationError(detail="CPF apenas dígitos")
            if not len(cpf)==11 or len(set(cpf)) == 1 or not cpf_isvalid(cpf):
                raise serializers.ValidationError(detail="CPF inválido")
            if Jogador.objects.filter(cpf=cpf).exists():
                raise serializers.ValidationError(detail="CPF inválido")


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

        force_affiliate = UserAfiliadoTeste.objects.last()
        if force_affiliate and force_affiliate.jogador:
            afiliado = force_affiliate.jogador
            attrs['codigo'] = afiliado.codigo
        else:
            if codigo:
                if not codigo.isdigit():
                    raise serializers.ValidationError(detail="Código inválido")
                if not Jogador.objects.filter(codigo=codigo).exists():
                    raise serializers.ValidationError(detail="Código não existe")

        return attrs

    def create(self, validated_data):
        usuario = validated_data.get("usuario")
        email = validated_data.get("email")
        whatsapp = validated_data.get("whatsapp")
        instagram = validated_data.get("instagram")
        senha = validated_data.get("senha")
        codigo = validated_data.get("codigo")
        cpf = validated_data.get("cpf")
        user = User.objects.create_user(username=usuario,email=email,password=senha)
        with transaction.atomic():
            jogador = Jogador.objects.create(
                usuario=usuario,whatsapp=whatsapp,user=user,instagram=instagram,cpf=cpf
            )
            logger.info(f"CREATE: código {codigo}")
            if codigo:

                indicador = Jogador.objects.get(codigo=codigo)
                jogador.indicado_por = indicador
                jogador.save()

                regra = RegraBonus.objects.filter(acao=AcaoBonus.CADASTRO).first()
                if not regra:
                    regra = RegraBonus.objects.create(acao=AcaoBonus.CADASTRO, valor=1)
                CreditoBonus.objects.create(
                    regra=regra, valor=regra.valor,
                    jogador=indicador,indicado=jogador
                )

        return jogador

class JogadorSerializer(serializers.ModelSerializer):
    travado = serializers.SerializerMethodField()
    desconto_credito_bonus = serializers.SerializerMethodField()

    def get_travado(self,obj):
        num_vitorias = CartelaVencedora.objects.filter(cartela__jogador=obj).count()
        configuracao = Configuracao.objects.last()
        if configuracao.max_vitorias_jogador>0:
            return num_vitorias>=configuracao.max_vitorias_jogador
        return False

    def get_desconto_credito_bonus(self, obj):
        configuracao = Configuracao.objects.last()
        if configuracao:
            return int(configuracao.creditos_bonus_gera_bilhete)
        return 1

    class Meta:
        model = Jogador
        fields = ["id","usuario","instagram","creditos","travado","desconto_credito_bonus","indicado_por"]

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


class ConfiguracaoAplicacaoSerializer(serializers.ModelSerializer):
    footerImage = serializers.SerializerMethodField()

    def get_footerImage(self,configuracao):
        if configuracao.footerImage:
            return configuracao.footerImage.url
        else:
            return ""

    class Meta:
        model = ConfiguracaoAplicacao
        exclude = ["id"]

class BotaoAplicacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotaoAplicacao
        exclude = ["id", "order","local"]

class BotaoMidiaSocialSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()

    def get_logo(self, botao):
        if botao.logo:
            return botao.logo.url
        else:
            return SOCIAL_MEDIA_IMAGES[botao.tipo]
    class Meta:
        model = BotaoMidiaSocial
        exclude = ["id","ativo"]

class ParceiroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parceiro
        exclude = ["id","ativo"]

class CamposCadastroSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampoCadastro
        fields = ["id","nome","obrigatorio"]

class ConfiguracoesAplicacaoSerializer(serializers.Serializer):
    configuracao_aplicacao = ConfiguracaoAplicacaoSerializer(read_only=True)
    botoes_login = BotaoAplicacaoSerializer(read_only=True,many=True)
    botoes_logado = BotaoAplicacaoSerializer(read_only=True,many=True)
    midias_sociais = BotaoMidiaSocialSerializer(read_only=True,many=True)
    patrocinadores = ParceiroSerializer(read_only=True,many=True)
    campos_cadastro = CamposCadastroSerializer(read_only=True,many=True)


    def validate(self, attrs):
        attrs["configuracao_aplicacao"] = ConfiguracaoAplicacaoSerializer(instance=ConfiguracaoAplicacao.objects.last(),read_only=True).data
        attrs["botoes_login"] = BotaoAplicacaoSerializer(BotaoAplicacao.objects.filter(local=LocalBotaoChoices.LOGIN),many=True).data
        attrs["botoes_logado"] = BotaoAplicacaoSerializer(BotaoAplicacao.objects.filter(local=LocalBotaoChoices.LOGADO),many=True).data
        attrs["midias_sociais"] = BotaoMidiaSocialSerializer(BotaoMidiaSocial.objects.filter(ativo=True),many=True).data
        attrs["patrocinadores"] = ParceiroSerializer(Parceiro.objects.filter(ativo=True),many=True).data
        attrs["campos_cadastro"] = CamposCadastroSerializer(CampoCadastro.objects.filter(ativo=True),many=True).data

        return attrs

class RequisicaoPremioAplicacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequisicaoPremioAplicacao
        exclude = ["id"]

class AfiliadoSerializer(serializers.ModelSerializer):
    travado = serializers.SerializerMethodField()
    link_afiliado = serializers.SerializerMethodField()
    link_formatado = serializers.SerializerMethodField()
    saldo = serializers.SerializerMethodField()
    libera_bilhete = serializers.SerializerMethodField()
    falta_liberar = serializers.SerializerMethodField()
    top5 = serializers.SerializerMethodField()

    def get_travado(self, obj):
        num_vitorias = CartelaVencedora.objects.filter(cartela__jogador=obj).count()
        configuracao = Configuracao.objects.last()
        return num_vitorias >= configuracao.max_vitorias_jogador

    def get_link_afiliado(self, obj):
        configuracao = RegraBonus.objects.filter(acao=AcaoBonus.CADASTRO).last()
        codigo = obj.codigo
        if configuracao and configuracao.url and codigo:
            return f"{configuracao.url}?codigo={codigo}"
        return ""

    def get_link_formatado(self, obj):
        configuracao = RegraBonus.objects.filter(acao=AcaoBonus.CADASTRO).last()
        codigo = obj.codigo
        if configuracao and configuracao.link_formatado and configuracao.url and codigo:
            return f"{configuracao.link_formatado}\n\n{configuracao.url}?codigo={codigo}"
        return ""

    def get_saldo(self, obj):
        bonus = CreditoBonus.objects.filter(jogador=obj)
        if not bonus:
            return {"total":0,"usado":0,"restante":0}
        total = bonus.count()
        usado = bonus.filter(resgatado_em__isnull=False).count()
        restante = total - usado
        return {"total":total,"usado":usado,"restante":restante}

    def get_libera_bilhete(self, obj):
        configuracao = Configuracao.objects.last()
        return configuracao.numero_cadastro_libera_jogador

    def get_falta_liberar(self, obj):
        configuracao = Configuracao.objects.last()
        num_vitorias = CartelaVencedora.objects.filter(cartela__jogador=obj).count()
        if num_vitorias >= configuracao.max_vitorias_jogador:
            libera = configuracao.numero_cadastro_libera_jogador
            bonus = CreditoBonus.objects.filter(jogador=obj,resgatado_em__isnull=True).count()
            if libera>0 and libera >= bonus:
                return libera-bonus
        return 0

    def get_top5(self,obj):
        results = Jogador.objects.filter(
            jogador__isnull=False
        ).annotate(quantidade=Count("id")).order_by("-quantidade").values("nome","quantidade")
        if results.count()>5:
            posicao = 5
            for i in range(1,results.count()+1):
                if results[posicao+i]['quantidade']==results[posicao]['quantidade']:
                    posicao += 1
                else:
                    results = results[:posicao]
                    break
        return results

    class Meta:
        model = Jogador
        fields = ["id", "usuario", "instagram", "travado", "link_afiliado","link_formatado","saldo","libera_bilhete",
                  "falta_liberar","top5"]


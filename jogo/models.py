import base64
import pickle

from django.contrib.postgres.fields import ArrayField
from django.db import models

# Create your models here.
import decimal
import json
import random
import secrets

from datetime import timedelta, datetime, date, time
from django.db.models import Sum, Q

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User

import threading

# Create your models here.
from django_resized import ResizedImageField

from jogo import local_settings
from jogo.choices import AcaoTipoChoices
from jogo.constantes import NOME_PESSOAS
from jogo.websocket_triggers import event_doacoes


def configuracao_images_path(instance, filename):
    return 'configuracao/{0}'.format(filename)


def configuracao_biuld_path(instance, filename):
    return 'build/{0}'.format(filename)


class ContadorCartelaPartida(models.Model):
    data = models.DateField(unique=True)
    numeracao = models.IntegerField()

    def __str__(self):
        return f"Dia: {self.data}: {self.numeracao}"

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            lista = local_settings.INICIO_CONTAGEM_CARTELAS
            self.numeracao = random.choice(lista)
        super().save(force_insert, force_update, using, update_fields)

    def atualizar(self, quantidade):
        self.numeracao += quantidade
        self.save()


class Configuracao(models.Model):
    tempo_min_entre_sorteios = models.PositiveSmallIntegerField(default=1)
    tempo_min_entre_sorteios_E = models.PositiveSmallIntegerField(default=30)
    tempo_min_entre_sorteios_SE = models.PositiveSmallIntegerField(default=30)
    iniciar_sorteio_em = models.PositiveSmallIntegerField(default=15)
    logo_login = models.ImageField(upload_to=configuracao_images_path, blank=True, null=True)
    logo_dash = models.ImageField(upload_to=configuracao_images_path, blank=True, null=True)
    favicon = models.FileField(upload_to=configuracao_images_path, blank=True, null=True)
    logo_promo = models.FileField(upload_to=configuracao_images_path, blank=True, null=True)
    nome_server = models.CharField(max_length=100, blank=True, null=True)
    token_server = models.CharField(max_length=100, blank=True, null=True)

    # COM VENDAS DE CARTELAS
    edit_data_antecipar = models.BooleanField(default=False)
    edit_data_adiar = models.BooleanField(default=False)
    edit_horario_antecipar = models.BooleanField(default=False)
    edit_horario_adiar = models.BooleanField(default=False)
    edit_nome = models.BooleanField(default=False)
    edit_kuadra = models.BooleanField(default=False)
    edit_kina = models.BooleanField(default=False)
    edit_keno = models.BooleanField(default=False)

    cancelar_bilhete = models.BooleanField(default=False)
    tempo_expirar_template = models.PositiveSmallIntegerField(default=2)

    # PARA WEBGL
    tempo_sorteio_online = models.PositiveSmallIntegerField(default=10)
    imprimir_qrcode = models.BooleanField(default=False)

    # Usar realtime data
    usar_realtime = models.BooleanField(default=False)

    # Automato
    quantidade_cartelas_compradas = models.PositiveIntegerField(default=1000)

    # Modo de pagar premio
    pagamento_automatico = models.BooleanField(default=True)

    # Versao da branch
    versao = models.CharField(max_length=100, blank=True, null=True)

    # Link para jogos reais
    nome_botao = models.CharField(max_length=200,blank=True,null=True)
    url_botao = models.URLField(blank=True,null=True)

    # link para grupo telegram
    nome_grupo_telegram =  models.CharField(max_length=200,blank=True,null=True)
    url_grupo_telegram = models.URLField(blank=True,null=True)

    # instagram compatibilidade
    instagram_connection = models.BinaryField(blank=True, null=True)
    perfil_default = models.URLField(blank=True, null=True)
    validacao_ativa = models.BooleanField(default=False)
    publicacao_uma_vez_dia = models.BooleanField(default=True)

    reter_jogadores = models.BooleanField(default=True)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            self.token_server = secrets.token_hex(20)
        super().save(force_insert, force_update, using, update_fields)

class ConfiguracaoInstagram(models.Model):
    # Conexao com o instagram
    instagram_connection = models.BinaryField(blank=True, null=True)
    perfil_default = models.URLField(blank=True, null=True)
    validacao_ativa = models.BooleanField(default=False)
    publicacao_uma_vez_dia = models.BooleanField(default=True)
    perfil_id = models.CharField(max_length=50, blank=True, null=True)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            conf = Configuracao.objects.last()
            if conf and conf.instagram_connection:
                conexao = pickle.loads(conf.instagram_connection)
                self.instagram_connection = pickle.dumps(conexao)
        super().save(force_insert,force_update,using,update_fields)


class Usuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    cpf = models.CharField(max_length=20, verbose_name="CPF", blank=True, null=True)
    fone = models.CharField(max_length=50)
    email = models.EmailField(blank=True, null=True)
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    token = models.CharField(max_length=200, unique=True, blank=True)
    sessao_atual = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{str(self.id).zfill(3)} - {self.usuario.first_name.title()}"

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            self.token = secrets.token_hex(20)
            creating = True

        super().save(force_insert, force_update, using, update_fields)



class Regiao(models.Model):
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome

TEMPO_MINIMO_ANTECIPADO = {
    (timedelta(minutes = 30), "30 Min"), (timedelta(minutes = 45), "45 Min"), (timedelta(minutes = 60), "60 Min"),
    (timedelta(minutes = 90), "90 Min"), (timedelta(minutes = 120), "120 Min")
}

TEMPO_CHOICES = (
    (1, "1 Minuto"),(2,'2 Minutos'),(3, "3 Minutos"), (4, "4 Minutos"), (5, "5 Minutos")
)
TEMPO_LIBERAR_CHOICES = (
    (5, "5 Minutos"),(6,'6 Minutos'),(7, "7 Minutos"), (8, "8 Minutos"), (9, "9 Minutos"), (10, "10 Minutos")
)

PARTIDA_TIPOS_CHOICES = (
    (1,"NORMAL"),(2,"ESPECIAL"),(3,"SUPER ESPECIAL")
)

# NOVA CLASSE
class Regra(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome

# NOVA CLASSE
class PerfilSocial(models.Model):
    url = models.CharField(max_length=255, unique=True)
    perfil_id = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.url

# NOVA CLASSE
class Acao(models.Model):
    regra = models.ForeignKey(Regra, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=20, choices=AcaoTipoChoices.choices)
    perfil_social = models.ForeignKey(PerfilSocial, on_delete=models.PROTECT)

    def __str__(self):
        return self.get_tipo_display() + " " + str(self.perfil_social)


class Partida(models.Model):
    # NOVO CAMPO
    regra = models.ForeignKey(Regra, on_delete=models.PROTECT)

    valor_kuadra = models.DecimalField(default=20.00, decimal_places=2, max_digits=6)
    valor_kina = models.DecimalField(default=20.00, decimal_places=2, max_digits=6)
    valor_keno = models.DecimalField(default=100.00, decimal_places=2, max_digits=8)
    tipo_rodada = models.PositiveSmallIntegerField(default=1, choices=PARTIDA_TIPOS_CHOICES)
    data_partida = models.DateTimeField()
    data_inicio = models.DateTimeField(blank=True, null=True)
    data_fim = models.DateTimeField(blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    bolas_sorteadas = models.CharField(max_length=255, null=True, blank=True)

    # NOVO CAMPO
    cartelas_receberam_sorteio = models.ManyToManyField('Cartela', blank=True, related_name="cartelas_receberam_sorteio")

    bola_kuadra = models.PositiveSmallIntegerField(null=True, blank=True)
    bola_kina = models.PositiveSmallIntegerField(null=True, blank=True)
    bola_keno = models.PositiveSmallIntegerField(null=True, blank=True)
    num_cartelas = models.IntegerField(default=0)
    em_sorteio = models.BooleanField(default=False)
    cartelas_participantes = models.TextField(blank=True, null=True)
    sorteio = models.TextField(blank=True, null=True)
    cancelado = models.BooleanField(default=False)
    nome_sorteio = models.CharField(max_length=200, blank=True, null=True)
    partida_automatizada = models.BooleanField(default=False, null=True)
    id_automato = models.BigIntegerField(blank=True, null=True)
    premios_set = models.DecimalField(decimal_places=2, max_digits=10, default=0.00)

    novos_participantes = models.PositiveIntegerField(default=0)
    # NOVOS CAMPOS
    chance_vitoria = models.DecimalField(default=100.0, decimal_places=2,max_digits=5)
    numero_cartelas_iniciais = models.PositiveSmallIntegerField(default=500)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            pass
            """
            from jogo.utils import manter_contas
            t = threading.Thread(target=manter_contas)
            t.start()
            """
        super().save(force_insert, force_update, using, update_fields)
        # notificar?
        event_doacoes()


    def cartelas_compradas(self):
        return self.num_cartelas

    def __str__(self):
        data = self.data_partida
        datahora = data.strftime("%d/%m/%Y %H:%M:%S")

        return "Sorteio: " + str(self.id).zfill(5) + " as " + datahora

    def linhas_vencedoras_kuadra_json(self):
        return [x.linha_vencedora for x in CartelaVencedora.objects.filter(partida=self, premio=1).order_by('id')]

    def linhas_vencedoras_kina_json(self):
        return [x.linha_vencedora for x in CartelaVencedora.objects.filter(partida=self, premio=2).order_by('id')]

    def linhas_vencedoras_keno_json(self):
        return [x.linha_vencedora for x in CartelaVencedora.objects.filter(partida=self, premio=3).order_by('id')]

    def nome_sorteio_text(self):
        return self.nome_sorteio if self.nome_sorteio else ""

    def num_participantes(self):
        return Cartela.objects.filter(partida=self,jogador__isnull=False).count()

    def sorteadas_list(self):
        if self.bolas_sorteadas:
            return [int(x) for x in self.bolas_sorteadas.split(',')]

    def cartelas_obj(self):
        if self.cartelas_participantes:
            codigos = self.cartelas_participantes.split(",")
            vencedoras = CartelaVencedora.objects.filter(partida=self)
            for v in vencedoras:
                if v.cartela.codigo not in codigos:
                    codigos.append(v.cartela.codigo)
            cartelas = Cartela.objects.filter(codigo__in=list(set(codigos)), partida=self)
            result = []
            for c in cartelas:
                d = {
                    'codigo': int(c.codigo),
                    "nome": c.nome,
                    'linha1_lista': [int(x) for x in c.linha1.split(",")],
                    'linha2_lista': [int(x) for x in c.linha2.split(",")],
                    'linha3_lista': [int(x) for x in c.linha3.split(",")]
                }
                result.append(d)
            return result

    def turnos_sorteio(self):
        if self.sorteio:
            return json.loads(self.sorteio)

    def resumo(self):
        return str(self.id) + " - " + self.data_partida.strftime("%d/%m/%Y %H:%M")

    def codigo(self):
        return str(id).zfill(5)

    def horario_sorteio(self):
        return self.data_partida

    def cartelas_vencedoras(self):
        kuadra = Cartela.objects.filter(partida=self, vencedor_kuadra=True)
        kina = Cartela.objects.filter(partida=self, vencedor_kina=True)
        keno = Cartela.objects.filter(partida=self, vencedor_keno=True)
        if kuadra or kina or keno:
            result = []
            lista = []
            for k1 in kuadra:
                lista.append({"codigo": k1.id, "nome": str(k1.nome)})
            result.append(lista)
            lista = []
            for k2 in kina:
                lista.append({"codigo": k2.id, "nome": str(k2.nome)})
            result.append(lista)
            lista = []
            for k3 in keno:
                lista.append({"codigo": k3.id, "nome": str(k3.nome)})
            result.append(lista)

            return result
        else:
            return []

    def cartelas_vencedoras_obj(self):
        kuadra = Cartela.objects.filter(partida=self, vencedor_kuadra=True).order_by('id')
        kina = Cartela.objects.filter(partida=self, vencedor_kina=True).order_by('id')
        keno = Cartela.objects.filter(partida=self, vencedor_keno=True).order_by('id')
        if kuadra or kina or keno:
            return (kuadra, kina, keno)

        return None

    def cartelas_vencedoras_kuadra_json(self):
        kuadra = [int(x.cartela.codigo) for x in CartelaVencedora.objects.filter(partida=self, premio=1).order_by('id')]
        return kuadra

    def cartelas_vencedoras_kina_json(self):
        kina = [int(x.cartela.codigo) for x in CartelaVencedora.objects.filter(partida=self, premio=2).order_by('id')]
        return kina

    def cartelas_vencedoras_keno_json(self):
        keno = [int(x.cartela.codigo) for x in CartelaVencedora.objects.filter(partida=self, premio=3).order_by('id')]
        return keno

    def premios(self):
        return self.valor_kina + self.valor_keno + self.valor_kuadra

    def bolas_array(self):
        return self.bolas_sorteadas.split(",") if self.bolas_sorteadas else ""

    class Meta:
        ordering = ['-data_partida']

    def num_cartelas_atual(self):
        if self.num_cartelas:
            return self.num_cartelas
        else:
            return Cartela.objects.filter(partida=self, cancelado=False).count()

    def verifica_force(self):
        agora = datetime.now()
        if agora > self.data_partida + timedelta(seconds=15):
            return True
        else:
            return False

    def total_cartelas(self):
        cartelas = Cartela.objects.filter(partida=self).count()
        if cartelas>self.numero_cartelas_iniciais:
            return cartelas
        return self.numero_cartelas_iniciais


TEMPLATE_STATUS_CHOICES = ((0, "APLICADO"), (1, "CANCELADO"))

class TemplatePartida(models.Model):
    valor_kuadra = models.DecimalField(default=20.00, decimal_places=2, max_digits=6)
    valor_kina = models.DecimalField(default=20.00, decimal_places=2, max_digits=6)
    valor_keno = models.DecimalField(default=100.00, decimal_places=2, max_digits=8)
    data_partida = models.DateTimeField()
    data_introducao = models.DateTimeField(auto_now_add=True)
    play = models.BooleanField(default=False)
    cancelado = models.BooleanField(default=False)
    id_automato = models.BigIntegerField(blank=True, null=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    status = models.PositiveSmallIntegerField(choices=TEMPLATE_STATUS_CHOICES, blank=True, null=True)
    tipo_rodada = models.PositiveSmallIntegerField(default=1, choices=PARTIDA_TIPOS_CHOICES)
    
     # NOVO CAMPO
    regra = models.ForeignKey(Regra, on_delete=models.PROTECT)

    def __str__(self):
        data = self.data_partida
        datahora = data.strftime("%d/%m/%Y %H:%M:%S")
        if self.id_automato:
            return "Template Sorteio: " + str(self.id).zfill(5) + " as " + datahora + " automato:" + str(
                self.id_automato)
        else:
            return "Template Sorteio: " + str(self.id).zfill(5)

    def inicio(self):
        configuracao = Configuracao.objects.last()
        data = self.data_introducao + timedelta(minutes=configuracao.tempo_expirar_template)
        return "Partida iniciará automaticamente as: " + data.strftime("%H:%M")

# NOVA CLASSE
class Jogador(models.Model):
    nome = models.CharField(max_length=255, blank=True, null=True)
    usuario = models.CharField(max_length=255)
    usuario_id = models.CharField(max_length=100,blank=True,null=True)
    usuario_token = models.CharField(max_length=255)
    seguidores = models.BigIntegerField(default=0)
    cadastrado_em = models.DateTimeField(auto_now_add=True)
    user = models.OneToOneField(User,on_delete=models.PROTECT)
    whatsapp = models.CharField(max_length=20,blank=True,null=True)
    instagram = models.CharField(max_length=50,blank=True,null=True)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            jogador = Jogador.objects.filter(usuario_id__isnull=False,usuario_id=self.usuario_id).first()
            if jogador:
                return jogador
            self.usuario_token = base64.b64encode(self.usuario.encode("ascii")).decode("ascii")
        if not self.nome:
            self.nome = self.usuario
        super().save(force_insert,force_update,using,update_fields)

    def sorteios_participou(self):
        from jogo.models import Cartela,Partida
        cartelas = Cartela.objects.filter(jogador=self)
        partidas = Partida.objects.filter(cartelas__in = cartelas).order_by('id').distinct('id')
        return partidas

    def sorteios_participou_count(self):
        return self.sorteios_participou().count()
         

class Cartela(models.Model):
    # NOVO CAMPO
    jogador = models.ForeignKey(Jogador, on_delete=models.PROTECT, blank=True,null=True)
    nome = models.CharField(max_length=50, blank=True,null=True)

    codigo = models.CharField(max_length=10)
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, related_name='cartelas')
    gerado_em = models.DateTimeField(auto_now_add=True)
    linha1 = models.CharField(max_length=20, blank=True, null=True)
    linha2 = models.CharField(max_length=20, blank=True, null=True)
    linha3 = models.CharField(max_length=20, blank=True, null=True)
    bolas_marcadas_linha1 = models.CharField(max_length=20, blank=True, null=True)
    bolas_marcadas_linha2 = models.CharField(max_length=20, blank=True, null=True)
    bolas_marcadas_linha3 = models.CharField(max_length=20, blank=True, null=True)
    vencedor_kuadra = models.BooleanField(default=False)
    vencedor_kina = models.BooleanField(default=False)
    vencedor_keno = models.BooleanField(default=False)
    bolas_marcadas = models.CharField(max_length=255, blank=True, null=True)
    valor = models.DecimalField(decimal_places=2, default=1.00, max_digits=4)
    comprado_em = models.DateTimeField(auto_now_add=True)
    hash = models.CharField(max_length=30)
    cancelado = models.BooleanField(default=False)


    def linha_restante(self, num_linha):
        if num_linha == 1:
            if not self.bolas_marcadas_linha1:
                return self.linha1.split(',')
            else:
                return [x for x in self.linha1.split(',') if x not in self.bolas_marcadas_linha1.split(',')]
        elif num_linha == 2:
            if not self.bolas_marcadas_linha2:
                return self.linha2.split(',')
            else:
                return [x for x in self.linha2.split(',') if x not in self.bolas_marcadas_linha2.split(',')]
        elif num_linha == 3:
            if not self.bolas_marcadas_linha3:
                return self.linha3.split(',')
            else:
                return [x for x in self.linha3.split(',') if x not in self.bolas_marcadas_linha3.split(',')]
        elif num_linha == 4:
            numeros = self.linha1.split(',') + self.linha2.split(',') + self.linha3.split(',')
            bolas_marcadas = []
            if self.bolas_marcadas_linha1:
                bolas_marcadas += self.bolas_marcadas_linha1.split(',')
            if self.bolas_marcadas_linha2:
                bolas_marcadas += self.bolas_marcadas_linha2.split(',')
            if self.bolas_marcadas_linha3:
                bolas_marcadas += self.bolas_marcadas_linha3.split(',')
            return [x for x in numeros if x not in bolas_marcadas]
        else:
            return []

    def num_max_bolas_marcadas(self):
        result = len(self.bolas_marcadas_linha1.split(","))
        return result

    def linha1_lista(self):
        return self.linha1.split(',')

    def linha2_lista(self):
        return self.linha2.split(',')

    def linha3_lista(self):
        return self.linha3.split(',')

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        numeros = []
        if not self.id:
            self.hash = secrets.token_hex(15)
            if not self.nome:
                self.nome = random.choice(NOME_PESSOAS)

                # Não utilizando a validação pelo instagram segue a regra abaixo
                self.nome = self.nome.lower()
                if " " in self.nome:
                    self.nome = self.nome.replace(" ","_")

            numeros = []
            grupo_de = int(settings.NUMERO_BOLAS / settings.NUMERO_COLUNAS_CARTELA)
            for colunas in range(settings.NUMERO_COLUNAS_CARTELA):
                faixa = range((colunas * grupo_de) + 1, ((colunas + 1) * grupo_de) + 1)
                numeros.append(sorted(random.sample(faixa, k=3)))

            linhas = list(zip(*numeros))

            self.linha1 = ",".join([str(x) for x in linhas[0]])
            self.linha2 = ",".join([str(x) for x in linhas[1]])
            self.linha3 = ",".join([str(x) for x in linhas[2]])

            if not self.codigo:
                self.codigo = str(self.gerar_codigo())

        super().save(force_insert, force_update, using, update_fields)
        event_doacoes()

    def __str__(self):
        if self.codigo:
            return "CARTELA " + str(self.codigo)
        return "CARTELA #" + str(self.id)


PREMIO_CHOICES = (
    (1, 'KUADRA'), (2, "KINA"), (3, "KENO")
)
LINHA_CHOICES = (
    (-1, "Não Informado"), (0, "Linha Superior"), (1, "Linha do Meio"), (2, "Linha Inferior"), (3, "Todas as Linhas")
)


class CartelaVencedora(models.Model):
    partida = models.ForeignKey(Partida, on_delete=models.PROTECT)
    cartela = models.ForeignKey(Cartela, on_delete=models.PROTECT)
    premio = models.PositiveSmallIntegerField(choices=PREMIO_CHOICES)
    linha_vencedora = models.SmallIntegerField(default=-1)
    valor_premio = models.FloatField(default=0.0)

    def __str__(self):
        return str(self.cartela)


class Agendamento(models.Model):
    partida = models.OneToOneField(Partida, on_delete=models.CASCADE)
    data = models.DateTimeField(auto_now_add=True)


# FILHO DE JUAN PABLO
class Automato(models.Model):
    tempo = models.PositiveSmallIntegerField()
    quantidade_sorteios = models.PositiveSmallIntegerField(default=100)
    partidas = models.ManyToManyField(Partida, blank=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    tipo_rodada = models.PositiveSmallIntegerField(default=1, choices=PARTIDA_TIPOS_CHOICES)

    def sorteios_gerados(self):
        return self.partidas.count()


class DispositivosConectados(models.Model):
    quantidade = models.IntegerField(default=1)
    nome_sala = models.CharField(max_length=255)

class GrupoWebSocket(models.Model):
    nome = models.CharField(max_length=200)
    partida = models.OneToOneField(Partida, on_delete=models.CASCADE)
    criado_em = models.DateTimeField(auto_now_add=True)
    ultima_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome


class GrupoCanal(models.Model):
    grupo = models.ForeignKey(GrupoWebSocket, on_delete=models.CASCADE)
    nome = models.CharField(max_length=255)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome

class Conta(models.Model):
    username = models.CharField(max_length=200)
    password = models.CharField(max_length=200)
    instagram_connection = models.BinaryField(blank=True, null=True)
    instagram_id = models.CharField(max_length=50, blank=True, null=True)
    ultimo_acesso = models.DateTimeField()
    proximo = models.ForeignKey('self', on_delete=models.PROTECT, blank=True,null=True)
    ativo = models.BooleanField(default=True)
    atencao = models.BooleanField(default=False)

    def __str__(self):
        return self.username

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        created = False
        desativar = False
        ativar = False
        if not self.id:
            created = True
            if not self.ultimo_acesso:
                self.ultimo_acesso = datetime.now()
        else:
            conta_antes = Conta.objects.get(id=self.id)
            if conta_antes.ativo and not self.ativo:
                desativar = True
            if not conta_antes.ativo and self.ativo:
                ativar = True

        super().save(force_insert,force_update,using,update_fields)

        if created:
            self.proximo = self
            # Listar todas as contas ativas por ID:Conta (excluindo a recem criada)
            ids = {x.id:x for x in Conta.objects.filter(ativo=True).exclude(id=self.id).order_by("id")}
            if ids: # tem outra conta
                # Obtem a conta próxima e atualiza esta conta recem criada para apontar para esse próximo
                conta_id = max(ids.keys())
                conta_proximo = ids[conta_id]
                self.proximo = conta_proximo
                self.save()

                # Obtem a primeira conta ativa por id e aponta o próximo dela para essa conta recem criada
                conta_primeira_id = min(ids.keys())
                conta_primeira = ids[conta_primeira_id]
                conta_primeira.proximo = self
                conta_primeira.save()

        else:
            from jogo.utils import ativar_conta,desativar_conta
            if desativar:
                desativar_conta(self,atualizado=True)
            if ativar:
                ativar_conta(self,atualizado=True)


class IPTabela(models.Model):
    ip_faixa = ArrayField(models.PositiveIntegerField(), size=2)
    ip_proxy = models.CharField(max_length=200, )
    ip_ultima_posicao = models.PositiveIntegerField()

def galeria_path(instance, filename):
    return 'galeria/{0}'.format(filename)
class Galeria(models.Model):
    arquivo = ResizedImageField(upload_to=galeria_path,
                                size=[1080,1080],
                                crop=['middle', 'center'],
                                quality=100,
                                force_format='JPEG')
    ativo = models.BooleanField(default=True)
    uploaded_em = models.DateTimeField(auto_now_add=True)

class TextoPublicacao(models.Model):
    texto = models.TextField()
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.texto

class Publicacao(models.Model):
    conta = models.ForeignKey(Conta, on_delete=models.CASCADE)
    texto = models.ForeignKey(TextoPublicacao, on_delete=models.PROTECT)
    imagem = models.ForeignKey(Galeria,on_delete=models.PROTECT, blank=True,null=True)
    data_publicacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Publicação {self.id} da conta {self.conta.username}"

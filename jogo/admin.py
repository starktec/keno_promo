from django.contrib import admin, messages
from django.db import models
# Register your models here.
from django.utils.html import format_html
from tinymce.widgets import TinyMCE

from jogo.models import Usuario, Configuracao, Jogador, CartelaVencedora, Cartela, Partida, Acao, Regra, Conta, \
    IPTabela, Publicacao, Galeria, TextoPublicacao, ConfiguracaoInstagram, PerfilSocial, CreditoBonus, RegraBonus, \
    ConfiguracaoAplicacao, BotaoAplicacao, BotaoMidiaSocial, Parceiro, RequisicaoPremioAplicacao, UserAfiliadoTeste, \
    CampoCadastro, ContatoCartelaVencedora, DebitoBonus

admin.site.register(PerfilSocial)
admin.site.register(Usuario)
class ConfiguracaoAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {"widget": TinyMCE},
    }
admin.site.register(Configuracao,ConfiguracaoAdmin)
admin.site.register(ConfiguracaoInstagram)
admin.site.register(ConfiguracaoAplicacao)
admin.site.register(BotaoAplicacao)
admin.site.register(BotaoMidiaSocial)
admin.site.register(Parceiro)
admin.site.register(RequisicaoPremioAplicacao)
admin.site.register(Partida)
admin.site.register(Cartela)
admin.site.register(CartelaVencedora)

class JogadorAdmin(admin.ModelAdmin):
    exclude = ["seguidores","usuario","usuario_id"]
    readonly_fields = ['nome', "usuario_token","user","whatsapp","instagram",
                       "indicado_por","codigo","cpf"]
    list_filter = ["nome","instagram","whatsapp","cpf"]
admin.site.register(Jogador,JogadorAdmin)
admin.site.register(Acao)
admin.site.register(Regra)
admin.site.register(IPTabela)

class PublicacaoAdmin(admin.ModelAdmin):
    fields = ["id","conta","texto","resumo","foto","data_publicacao"]
    readonly_fields = fields
    list_display = ["id","conta","resumo","foto","data_publicacao"]

    def resumo(self,obj):
        return obj.texto.texto[:50]+"..."

    def foto(self,obj):
        if obj.imagem:
            return format_html(f"<img src='{obj.imagem.arquivo.url}' width='100px'>")
        return ""
admin.site.register(Publicacao,PublicacaoAdmin)
admin.site.register(Galeria)
admin.site.register(TextoPublicacao)

class ContaAdmin(admin.ModelAdmin):
    fields = ['username','password','ultimo_acesso','proximo','ativo', 'instagram_id']
    readonly_fields = ['ultimo_acesso',"proximo"]


admin.site.register(Conta, ContaAdmin)

class CreditoBonusAdmin(admin.ModelAdmin):
    exclude = ["id"]
    change_list_template = "bonus_change_list.html"
    list_display = ['__str__','jogador','indicado','debito','ativo']
    list_filter = ['ativo']

    def resgatado(self, obj):
        if obj.resgatado_em:
            return obj.resgatado_em.strftime("%d/%m/%Y %H:%M:%S")
        return "Não"


admin.site.register(CreditoBonus,CreditoBonusAdmin)
admin.site.register(DebitoBonus)
admin.site.register(RegraBonus)
admin.site.register(UserAfiliadoTeste)
admin.site.register(CampoCadastro)
admin.site.register(ContatoCartelaVencedora)
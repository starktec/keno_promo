from django.contrib import admin
from django.db import models
# Register your models here.
from django.utils.html import format_html
from tinymce.widgets import TinyMCE

from jogo.models import Usuario, Configuracao, Jogador, CartelaVencedora, Cartela, Partida, Acao, Regra, Conta, \
    IPTabela, Publicacao, Galeria, TextoPublicacao, ConfiguracaoInstagram, PerfilSocial, CreditoBonus, RegraBonus, \
    ConfiguracaoAplicacao, BotaoAplicacao, BotaoMidiaSocial, Parceiro, RequisicaoPremioAplicacao, UserAfiliadoTeste

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
admin.site.register(Jogador)
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
admin.site.register(CreditoBonus)
admin.site.register(RegraBonus)
admin.site.register(UserAfiliadoTeste)

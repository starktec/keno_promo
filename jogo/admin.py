from django.contrib import admin

# Register your models here.
from jogo.models import Usuario, Configuracao, Jogador, CartelaVencedora, Cartela, Partida, Acao, Regra, Conta, IPTabela

admin.site.register(Usuario)
admin.site.register(Configuracao)
admin.site.register(Partida)
admin.site.register(Cartela)
admin.site.register(CartelaVencedora)
admin.site.register(Jogador)
admin.site.register(Acao)
admin.site.register(Regra)
admin.site.register(IPTabela)

class ContaAdmin(admin.ModelAdmin):
    fields = ['username','password','ultimo_acesso','proximo','ativo']
    readonly_fields = ['ultimo_acesso',"proximo"]


admin.site.register(Conta, ContaAdmin)
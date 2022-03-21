from django.contrib import admin

# Register your models here.
from jogo.models import Usuario, Configuracao, Jogador, CartelaVencedora, Cartela, Partida

admin.site.register(Usuario)
admin.site.register(Configuracao)
admin.site.register(Partida)
admin.site.register(Cartela)
admin.site.register(CartelaVencedora)
admin.site.register(Jogador)

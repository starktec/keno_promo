from django.contrib import admin

# Register your models here.
from jogo.models import Usuario, Configuracao

admin.site.register(Usuario)
admin.site.register(Configuracao)
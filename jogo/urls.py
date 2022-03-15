
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from jogo.views import cancelar_template, criar_ads, ads_edit, deletar_ads, index, ads, \
    partidas, ganhadores, cartela, login_page, logout_page, criarpartida, user_change_status, usuarios, \
    usuarios_add_or_edit, usuario_details, cartelas, configuracao, cancelar_partida, cancelar_bilhete, partida_edit, \
    partida_automatica, automatos, parar_automato, sortear_template, editar_template

from .views import realtime_data, status_ads

urlpatterns = [
    path('', index),
    path('logout/',logout_page, name='logout'),
    path('login/',login_page),
    path('partidas/', partidas),
    path('ads/', ads),
    path('ads/<int:id_ads>/status/', status_ads),
    path('criar_ads/',criar_ads),
    path('ads/<int:id_partida>/edit/', ads_edit),
    path('ads/<int:id>/delete',deletar_ads),
    path('criar_partida/', criarpartida),

    path('ganhadores/', ganhadores),

    path('user/<int:user_id>/status/', user_change_status),
    path('usuarios/',usuarios),
    path('usuario/add/',usuarios_add_or_edit),
    path('usuario/<usuario_id>/',usuarios_add_or_edit),
    path('usuario/details/<usuario_id>/',usuario_details),

    path('cartelas/', cartelas),
    path('configuracao/', configuracao),

    path('cancelar_partida/<int:partida_id>/',cancelar_partida),
    path('cancelar_bilhete/<str:hash>/',cancelar_bilhete),
    path('usuario_details/', usuario_details),
    path('partida_edit/<int:partida_id>/', partida_edit),

    path('partidas/criar_automatica/', partida_automatica),
    path('automatos/', automatos),
    path('automatos/<int:codigo>/',automatos),
    path('partida/<int:partida_id>/parar/', parar_automato),
    path('sortear_template/<int:template_id>/',sortear_template),
    path('template/<int:template_id>/cancelar/',cancelar_template),
    path('template/<int:template_id>/edit/',editar_template),
    #path('templates/',templates),

    path('realtime_data/',realtime_data),

]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
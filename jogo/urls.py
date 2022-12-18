
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from jogo.views import cancelar_template, index, \
    partidas, ganhadores, cartela, login_page, logout_page, criarpartida, \
    cartelas, configuracao, cancelar_partida, cancelar_bilhete, partida_edit, \
    partida_automatica, automatos, parar_automato, sortear_template, editar_template, manter_contas_view, \
    aumentar_cartelas, forcar_sorteio, CadastroJogador, LoginJogador, PegarCartela, status_jogador, mudar_senha_jogador

from .views import jogadores, realtime_data
from .views_api_media import logo_promo, media_login, nome_server, media_logo, media_favicon, media_fundo
from .views_api_online import dados_bilhete, get_politicas_de_privacidade_kol, get_regras_kol, proximos_kol, data_hora_servidor, ultimos_ganhadores_kol
from .views_api_tela import resultado_sorteio, proximos, proximos_especiais, historico, status, ultimos_ganhadores
from .views_social_instagram import index_social, gerar_bilhete

urlpatterns = [
    path('', index),
    path('logout/',logout_page, name='logout'),
    path('login/',login_page),
    path('partidas/', partidas),
    path('criar_partida/', criarpartida),

    path('ganhadores/', ganhadores),
    path('jogadores/', jogadores),
    path('cartelas/', cartelas),
    path('configuracao/', configuracao),

    path('cancelar_partida/<int:partida_id>/',cancelar_partida),
    path('cancelar_bilhete/<str:hash>/',cancelar_bilhete),
    path('partida_edit/<int:partida_id>/', partida_edit),

    path("partidas/<int:partida_id>/aumentar/<str:quantidade>/",aumentar_cartelas),
    path("partidas/<int:partida_id>/force/",forcar_sorteio),

    path('realtime_data/',realtime_data),

    path("jogador/<int:jogador_id>/status/<int:status>/", status_jogador),
    path("jogador/<int:jogador_id>/senha/", mudar_senha_jogador),

    path('api/v1/', include(
        [
            path('sorteio/<int:local_id>/<int:sorteio_id>/', resultado_sorteio),
            path('proximossorteios/', proximos),
            path('proximos_especiais/', proximos_especiais),
            path('historico/', historico),
            path('status/<str:partida_id>/',status),
            path('ultimos_ganhadores/',ultimos_ganhadores),
        ]
    )),

    path('api/kol/', include(
        [
            path('bilhete/<str:hash>/', dados_bilhete),
            path('proximossorteios/', proximos_kol),
            path('data_hora/', data_hora_servidor),
            path('ultimos_ganhadores/', ultimos_ganhadores_kol),
            path('ultimos_ganhadores/<int:sorteio_id>/', ultimos_ganhadores_kol),
            path('regras/',get_regras_kol),
            path('politicas_de_privacidade/',get_politicas_de_privacidade_kol)
        ]

    )),

    path('api/media/', include(
        [
            path('logo/', media_logo),
            path('favicon/',media_favicon),
            path('login/',media_login),
            path('nome/',nome_server),
            path('logo_promo/',logo_promo),
            path('fundo/',media_fundo)
        ]
    )),

    path("api/social/", include(
        [
            path("",index_social),
            path("gerar_bilhete/", gerar_bilhete)
        ]
    )),

    path("api/cadastro/", CadastroJogador.as_view()),
    path("api/login/",LoginJogador.as_view()),
    path("api/gerar_bilhete/",PegarCartela.as_view()),

    path("manter_contas/", manter_contas_view),

]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

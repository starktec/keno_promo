"""
urls = [
   # URLS DA API COM O UNITY
   path('api/v1/', include(
       [
           path('sorteio/<int:local_id>/<int:sorteio_id>/', resultado_sorteio),
           #path('informacoes/<int:local_id>/', informacoes),
           path('proximosorteio/', proximo),
           path('ads/',ads_tela),
           path('proximossorteios/', proximos),
           path('proximos_especiais/', proximos_especiais),
           path('historico/', historico),
           path('comprar_cartela/', comprar_cartela),
           path('cartela/<int:cartela_id>/', cartela),
           path('cartelalote/<int:lote_id>/', cartela_lote),
           path('status/<str:partida_id>/',status),
           path('ultimos_ganhadores/',ultimos_ganhadores),
           path('ongs/',ongs),
           path('autenticar/',autenticar),
           path('replay/',replay_tela),
           path('oferecimento_texto/',oferecimento_texto),
           path('oferecimento_imagem/',oferecimento_imagem),
           path('checkpoint/<str:codigo>/', check_tv),
       ]
   )),

   path('api/media/', include(
       [
           path('logo/', media_logo),
           path('favicon/',media_favicon),
           path('login/',media_login),
           path('nome/',nome_server)
       ]
   )),

   path('api/web/<str:mac_address>', autenticar_web),

   path('api/kol/',include(
       [
           path('bilhete/<str:hash>/',dados_bilhete),
           path('bilhete_v2/<str:hash>/',dados_bilhete_v2),
           path('pre_compra/',pre_compra),
           path('proximossorteios/',proximos_kol),
           path('data_hora/',data_hora_servidor),
           path('ultimos_ganhadores/',ultimos_ganhadores_kol),
           path('ultimos_ganhadores/<int:sorteio_id>/',ultimos_ganhadores_kol),
           path('sorteios/',dados_sorteios)
       ]

   )),
]"""

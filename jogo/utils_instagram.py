def estah_seguindo(api, perfil_id, perfil):
    try:
        jogador_seguindo = api.search_followers_v1(user_id=perfil_id, query=perfil) if api else True
        return jogador_seguindo
    except:
        pass
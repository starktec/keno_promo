import pickle
import time
from datetime import date,datetime

from django.conf import settings
from instagrapi import Client
from instagrapi.exceptions import ClientNotFoundError, UserNotFound

from jogo.consts import StatusJogador
from jogo.models import InstagramAccount, Jogador, RelatorioAtualizacao, Conta, IPTabela
from jogo.utils import download_foto

JOGOSDASORTEBR_ID = "44328406722"
PERFIL = "@jogosdasortebr"
"""
CONTAS = [
    {"username":"teste.user.1","password":"teste123@"},
    {"username":"teste.user.2","password":"teste123@."},
    {"username":"teste.user.3","password":"teste123@."},
    {"username":"teste.user.4","password":"teste123@"},
    {"username":"teste.user.5","password":"teste123@."},
]
"""
TIME_MIN = 15

FILE = settings.BASE_DIR + "/logs/log_atualizacao.txt"
def log(msg):
    arquivo = open(FILE, 'a+')
    try:
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S.%f")
        arquivo.write(agora + " - " + msg + "\n")
    except:
        pass
    finally:
        arquivo.close()

class Seguidor:
    def __init__(self,pk,username,full_name,pic):
        self.pk = pk
        self.username = username
        self.full_name = full_name
        self.pic = pic

def update_jogador(j,conta,status=None):
    update = False
    if not j.usuario_id:
        j.usuario_id = conta.instagram_id
        update = True
    if status and j.status != status:
        j.status = status
        update = True
    if not j.nome or j.nome != conta.full_name:
        j.nome = conta.full_name
        update = True
    if not j.usuario or j.usuario != conta.username:
        j.usuario = conta.username
        update = True
    if not j.foto and conta.pic:
        j.foto = download_foto(conta.pic, conta.instagram_id)
        update = True
    if not j.conta:
        j.conta = conta
        update = True
    if update:
        return j
    return None

def run():
    # Obtenção dos dados e salvar em CSV
    log("Fase1: Geração de CSV")
    log("Fazendo login")
    num_jogadores_ativo_novos = 0
    num_jogadores_cancelado_novos = 0
    num_jogadores_suspenso_novos = 0

    clients = []
    fake = []
    nao_segue = []
    posicao = 0
    save = False
    try:
        CONTAS = Conta.objects.filter(ativo=True, atencao=False)
        if not CONTAS:
            log("NENHUMA CONTA ENCONTRADA")
        else:
            log(f"{len(CONTAS)} Contas encontradas")
            proxies = IPTabela.objects.last()
            proxy_list = []
            if proxies:
                proxy_list = [p.ip_proxy+":"+p.ip_faixa for p in proxies]
            contador = 0
            log(f"{len(proxy_list)} IPs encontrados")
            for i_conta in CONTAS:
                log(f"Fazendo login na conta {i_conta.username}...")
                time.sleep(15)
                con_client = Client()
                if proxy_list:
                    con_client.set_proxy(proxy_list[contador])
                con_client.login(i_conta.username, i_conta.password)
                clients.append((con_client,i_conta.username))
                i_conta.instagram_connection = pickle.dumps(con_client)
                i_conta.ultimo_acesso = datetime.now()
                i_conta.save()

                contador += 1

            client, connection = clients[posicao%len(CONTAS)]
            log(f"({connection}) Buscando seguidores")
            posicao += 1
            antes = datetime.now()
            seguidores = client.user_followers(JOGOSDASORTEBR_ID)
            if isinstance(seguidores,str):
                log("FALHA: seguidores em str")
                raise Exception
            agora = datetime.now()
            log(f" - {len(seguidores)} Seguidores encontrados em {int((agora-antes).seconds/60)} minutos")

            log(" - Registrando csv...")
            hoje = date.today()
            nome_arquivo = f"{hoje.year}{hoje.month}{hoje.day}_seguidores.csv"
            arquivo = open(settings.BASE_DIR + "/logs/"+nome_arquivo,"w",encoding="utf-8")

            lista_seguidores = []

            for seguidor in seguidores.values():
                pic_url = ""
                if seguidor.profile_pic_url:
                    pic_url = str(seguidor.profile_pic_url)
                lista = (seguidor.pk,seguidor.username,seguidor.full_name,pic_url)
                lista_seguidores.append(Seguidor(seguidor.pk,seguidor.username,seguidor.full_name,pic_url))
                arquivo.write("|".join(lista)+"\n")
            arquivo.close()

            log(" - Processado. Entrando na Fase 2: atualizando o banco de dados")
            contas = InstagramAccount.objects.all()
            jogadores = Jogador.objects.all()

            seguidores_por_id = {x.pk: x for x in seguidores}
            seguidores_por_username = {x.username: x for x in seguidores}
            update_jogadores = []

            for jogador in jogadores:
                log(f"START {jogador.usuario}")
                seguidor = None
                if jogador.usuario_id in seguidores_por_id.keys():
                    seguidor = seguidores_por_id[jogador.usuario_id]
                else:
                    if jogador.usuario in seguidores_por_username.keys():
                        seguidor = seguidores_por_username[jogador.usuario]
                if seguidor:
                    log(f"{jogador.usuario} veio na lista de seguidores")
                    conta = contas.filter(instagram_id=seguidor.pk).first()
                    if conta:
                        log(f"{jogador.usuario} possui um registro local")
                        if conta.recente:
                            log(f"{jogador.usuario} deixa de ser um registro recente")
                            conta.recente = False
                            conta.save()
                    else:
                        log(f"{jogador.usuario} NÃO possui um registro local... criando um novo")
                        conta = InstagramAccount.objects.create(
                            instagram_id=seguidor.pk,username=seguidor.username,full_name=seguidor.full_name,
                            pic=seguidor.pic
                        )
                    log(f"{jogador.usuario} sendo atualizado e forçando seu status para ATIVO")
                    j_update = update_jogador(jogador,conta,StatusJogador.ATIVO)
                    if j_update:
                        num_jogadores_ativo_novos += 1
                        j_update.save()
                else:
                    log(f"{jogador.usuario} NÃO veio na lista de seguidores")
                    conta = InstagramAccount.objects.none()
                    if jogador.usuario_id:
                        conta = contas.filter(instagram_id=jogador.usuario_id).first()
                    else:
                        conta = contas.filter(username=jogador.usuario).first()

                    if conta:
                        log(f"{jogador.usuario} possui um registro local")
                        j_update = None
                        if not conta.recente:
                            log(f"{jogador.usuario} suspendendo conta antiga (não participa de jogos)")
                            j_update = update_jogador(jogador, conta, StatusJogador.SUSPENSO)
                            num_jogadores_suspenso_novos += 1
                            nao_segue.append(jogador.usuario)
                        else:
                            tempo_em_dias = (agora - conta.data_cadastro).days
                            if tempo_em_dias>1:
                                log(f"{jogador.usuario} suspendendo conta antiga (acima de 1 dia não participa de jogos)")
                                j_update = update_jogador(jogador, conta, StatusJogador.SUSPENSO)
                                num_jogadores_suspenso_novos += 1
                                nao_segue.append(jogador.usuario)
                            else:
                                log(f"{jogador.usuario} é uma conta recente... aguardando mais 1 dia para vir na lista diária")

                        if j_update:
                            j_update.save()
                    else:
                        log(f"{jogador.usuario} Nem tem um registro local nem veio na lista de seguidores...")
                        time.sleep(int(TIME_MIN/len(CONTAS))+1)
                        client, connection = clients[posicao % len(CONTAS)]
                        log(f"({connection}) Buscando dados do perfil @{jogador.usuario} no instagram")
                        posicao += 1
                        try:
                            usuario = client.user_info_by_username(jogador.usuario)
                            if not usuario:
                                raise ClientNotFoundError()
                        except (ClientNotFoundError, UserNotFound) as cnfe:
                            log(f"@{jogador.usuario} é uma conta inexistente... cancelando jogador")
                            # Conta nao existe
                            jogador.status = StatusJogador.CANCELADO
                            num_jogadores_cancelado_novos += 1
                            jogador.save()
                            fake.append(jogador.usuario)
                            continue

                        time.sleep(int(TIME_MIN / len(CONTAS)) + 1)
                        client, connection = clients[posicao % len(CONTAS)]
                        log(f"({connection}) Confirmando se @{jogador.usuario} segue o {PERFIL} no instagram")
                        posicao += 1
                        usuarios = client.search_followers(user_id=JOGOSDASORTEBR_ID,query=jogador.usuario)
                        #seguidor_instagram = [x for x in seguidores_instagram if x.username == jogador.usuario]

                        usuarios_dict = {u.username: u for u in usuarios}
                        if usuarios and jogador.usuario in usuarios_dict.keys():
                            log(f"@{jogador.usuario} encontrado. Criando registro e atualizado jogador...")
                            # Passou no teste atualizando
                            usuario = usuarios_dict.get(jogador.usuario)
                            conta = InstagramAccount.objects.create(
                                instagram_id=usuario.pk,
                                username=usuario.username,
                                full_name=usuario.full_name,
                                pic=str(usuario.profile_pic_url)
                            )
                            jogador.conta = conta
                            jogador.usuario_id = conta.instagram_id
                            jogador.status = StatusJogador.ATIVO
                            num_jogadores_ativo_novos += 1
                            jogador.foto = download_foto(conta.pic, conta.instagram_id)
                        else:
                            # Usuario nao segue a Jogosdasortebr
                            jogador.status = StatusJogador.SUSPENSO
                            num_jogadores_suspenso_novos += 1
                            log(f"@{jogador.usuario} Usuario existe mas nao segue o {PERFIL}")
                            nao_segue.append(jogador.usuario)
                        jogador.save()
            save = True
    except Exception as e:
        log(str(e))
        save = False
    finally:
        if save:
            RelatorioAtualizacao.objects.create(
                num_jogadores = Jogador.objects.count(),
                num_jogadores_ativo_total = Jogador.objects.filter(status=1).count(),
                num_jogadores_ativo_novos = num_jogadores_ativo_novos,
                num_jogadores_cancelado_total = Jogador.objects.filter(status=3).count(),
                num_jogadores_cancelado_novos = num_jogadores_cancelado_novos,
                num_jogadores_suspenso_total = Jogador.objects.filter(status=2).count(),
                num_jogadores_suspenso_novos = num_jogadores_suspenso_novos,
                num_jogadores_nao_analisados = Jogador.objects.filter(conta__isnull=True,status=1).count(),
            )
        log(f"Relatorio 1 (FAKE): {', '.join(fake)}")
        log(f"Relatorio 2 (NAO SEGUE): {', '.join(nao_segue)}")
        log("************************************************************")
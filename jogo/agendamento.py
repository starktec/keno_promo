import datetime
import json
import random

import traceback
from decimal import Decimal

from backports import zoneinfo

from jogo.constantes import NOME_PESSOAS
from jogo.consultas_banco import cartelas_sql_teste

from jogo.websocket_triggers_bilhete import event_bilhete_sorteio

from django.conf import settings

from apscheduler.schedulers.background import BackgroundScheduler
from django.db import transaction

from jogo.models import Automato, Cartela, Partida, Configuracao, CartelaVencedora, Agendamento, \
    TemplatePartida, DispositivosConectados
from jogo.utils import partida_automatizada, testa_horario, comprar_cartelas

FILE = settings.BASE_DIR + "/logs/log_agendamento.txt"

RECIFE = zoneinfo.ZoneInfo("America/Recife")


class Agenda():
    agendas = {}
    agendas_template = {}

    def log(self,msg):
        arquivo = open(FILE,'a+')
        try:
            agora = datetime.datetime.now(tz=RECIFE).strftime("%d/%m/%Y %H:%M:%S.%f")
            arquivo.write(agora + " - "+ msg+"\n")
        except:
            pass
        finally:
            arquivo.close()


    def limpar_conexoes_websocket(self):
        DispositivosConectados.objects.all().delete()

    def atualizar_conexoes_websocket(self,partida):
        relatorio = DispositivosConectados.objects.filter(nome_sala=f"sorteio-{partida.id}").delete()
        self.log(f"WS exclusao DB: {relatorio}")

    def __init__(self):
        self.log("Remontando o agendamento de partidas")
        
    # AGENDADOR PARA SORTEIOS
    def agendar(self, partida):
        try:
            agenda = BackgroundScheduler(daemon=True,timezone="America/Recife")
            configuracao = Configuracao.objects.last()
            data = partida.data_partida + datetime.timedelta(seconds=configuracao.iniciar_sorteio_em)
            self.log("Agendamento sendo feito para a partida "+str(partida.id)+" horario + " + str(partida.data_partida))
            job = agenda.add_job(self.sortear_agendado, 'date', run_date=data, args=[partida,agenda])
            self.log("Agendado")
            if not partida.id in self.agendas.keys():
                self.agendas[partida.id]=(agenda,False, job.id)
            #self.log(str(self.agendas))
            agenda.start()
        except Exception as e:
            self.log(str(traceback.extract_stack()))


    def sortear_agendado(self, partida, reload=True, agenda=None):
        self.log("TENTATIVA: SORTEIO " + str(partida.id) + " reload: " + str(reload) + " agenda: " + str(agenda))
        modo_sorteio = False
        # if (agenda and partida.id in self.agendas.keys()) or not agenda:
        try:
            c = Agendamento.objects.create(partida=partida)
            if c:

                # self.agendas[partida.id][1] = True
                self.log("SORTEAR AGENDADO INICIOU")

                if reload:
                    self.log("SORTEIO PRE AGENDADO")
                    data_partida = partida.data_partida
                    partida = Partida.objects.filter(id=partida.id, em_sorteio=False,
                                                     bolas_sorteadas__isnull=True).first()
                    if not partida.data_partida == data_partida:
                        self.log("SORTEIO COM HORARIO DIFERENTE DO BANCO")
                        a = Agendamento.objects.filter(partida=partida).first()
                        if a:
                            a.delete()
                        partida = None
                cartelas = Cartela.objects.filter(
                    partida=partida, cancelado=False
                ).values("id","codigo","jogador","linha1","linha2","linha3","nome",
                         "vencedor_kuadra","vencedor_kina","vencedor_keno")
                if partida and cartelas and not partida.em_sorteio and not partida.bolas_sorteadas:

                    partida.data_inicio = datetime.datetime.now(tz=RECIFE)
                    partida.em_sorteio = True
                    partida.save()

                    chance_vitoria = partida.chance_vitoria
                    numero_cartelas_jogadores = cartelas.filter(jogador__isnull=False).count()
                    numero_cartelas_sortear = len(cartelas)

                    if numero_cartelas_jogadores:
                        # Calculo de quantas cartelas devem participar do sorteio
                        numero_cartelas_definido = round(numero_cartelas_jogadores / (float(chance_vitoria)/100.0))

                        """                        
                        if numero_cartelas_definido < 15:
                            numero_cartelas_definido = 15
                        """
                        numero_cartelas_preencher = numero_cartelas_definido - numero_cartelas_jogadores

                        # Montando a lista de Cartelas

                        cartelas_sorteio = list(cartelas.filter(jogador__isnull=False))
                        if numero_cartelas_preencher > len(cartelas) - numero_cartelas_jogadores:
                            cartelas_sorteio += list(cartelas.filter(jogador__isnull=True))
                        else:
                            cartelas_sorteio += list(cartelas.filter(jogador__isnull=True)[:numero_cartelas_preencher])

                        cartelas = cartelas_sorteio


                    cartelas_ordenadas = []
                    bolas_sorteadas = []
                    self.log("RODANDO SORTEIO " + str(partida.id))
                    # FLAGS PARA DEFINIR SE HOUVE GANHADORES DE KUADRA, KINA E KENO
                    kuadra = False
                    kina = False
                    keno = False
                    dados = []

                    # RODAR O SORTEIO PARA ATÉ 90 BOLAS OU ALGUEM GANHAR O KENO
                    with transaction.atomic():
                        modo_sorteio = True

                        cartelas_save = {}
                        vencedores_kuadra = []
                        vencedores_kina = []
                        vencedores_keno = []

                        cartelas_numeros_restantes = {}
                        codigo_cartela_nome = {}
                        for c in cartelas:
                            numeros1 = [int(numero) for numero in c['linha1'].split(",")]
                            numeros2 = [int(numero) for numero in c['linha2'].split(",")]
                            numeros3 = [int(numero) for numero in c['linha3'].split(",")]
                            cartelas_numeros_restantes[c['codigo']] = [
                                numeros1, numeros2, numeros3
                            ]
                            nome = c.get("nome")
                            codigo_cartela_nome[c['codigo']] = (nome,
                                c['id']
                            )


                        sorteio_todas_bolas = random.sample(range(1, 91), k=90)  # Bolas sorteadas
                        for bola in sorteio_todas_bolas:

                            # logger.info("BOLA DE NUMERO " + str(bola).zfill(2))

                            # GUARDA A BOLA SORTEADA
                            bolas_sorteadas.append(str(bola))

                            rodada_kuadra = False
                            rodada_kina = False
                            rodada_keno = False

                            # AVALIAR CADA CARTELA
                            for c in cartelas:
                                # ENCONTROU A BOLA NA LINHA 1
                                if bola in cartelas_numeros_restantes[c['codigo']][0]:
                                    cartelas_numeros_restantes[c['codigo']][0].remove(bola)

                                    # VERIFICAR SE MARCOU A KUADRA
                                    if not kuadra and len(
                                            cartelas_numeros_restantes[c['codigo']][0]) == 1 and not c['vencedor_kuadra']:
                                        c['vencedor_kuadra'] = True
                                        vencedores_kuadra.append((c['codigo'], 0))
                                        rodada_kuadra = True

                                    # VERIFICAR SE MARCOU A KINA
                                    if not kina and len(cartelas_numeros_restantes[c['codigo']][0]) == 0 and not c['vencedor_kina']:
                                        c['vencedor_kina'] = True
                                        vencedores_kina.append((c['codigo'], 0))
                                        rodada_kina = True


                                elif bola in cartelas_numeros_restantes[c['codigo']][1]:
                                    cartelas_numeros_restantes[c['codigo']][1].remove(bola)

                                    # VERIFICAR SE MARCOU A KUADRA
                                    if not kuadra and len(
                                            cartelas_numeros_restantes[c['codigo']][1]) == 1 and not c['vencedor_kuadra']:
                                        c['vencedor_kuadra'] = True
                                        vencedores_kuadra.append((c['codigo'], 1))
                                        rodada_kuadra = True

                                    # VERIFICAR SE MARCOU A KINA
                                    if not kina and len(cartelas_numeros_restantes[c['codigo']][1]) == 0 and not c['vencedor_kina']:
                                        c['vencedor_kina'] = True
                                        vencedores_kina.append((c['codigo'], 1))
                                        rodada_kina = True

                                elif bola in cartelas_numeros_restantes[c['codigo']][2]:
                                    cartelas_numeros_restantes[c['codigo']][2].remove(bola)

                                    # VERIFICAR SE MARCOU A KUADRA
                                    if not kuadra and len(
                                            cartelas_numeros_restantes[c['codigo']][2]) == 1 and not c['vencedor_kuadra']:
                                        c['vencedor_kuadra'] = True
                                        vencedores_kuadra.append((c['codigo'], 2))
                                        rodada_kuadra = True

                                    # VERIFICAR SE MARCOU A KINA
                                    if not kina and len(cartelas_numeros_restantes[c['codigo']][2]) == 0 and not c['vencedor_kina']:
                                        c['vencedor_kina'] = True
                                        vencedores_kina.append((c['codigo'], 2))
                                        rodada_kina = True

                                if kuadra and kina:
                                    # VERIFICAR SE MARCOU A KENO
                                    soma_restante = len(cartelas_numeros_restantes[c['codigo']][0]) + len(
                                        cartelas_numeros_restantes[c['codigo']][1]) + len(
                                        cartelas_numeros_restantes[c['codigo']][2])
                                    if soma_restante == 0 and not c['vencedor_keno']:
                                        c['vencedor_keno'] = True
                                        vencedores_keno.append((c['codigo'], 3))
                                        keno = True
                                        rodada_keno = True

                            premio_keno = kuadra and kina

                            cartelas_estrutura = []

                            if premio_keno:

                                for codigo_cartela, numeros_restantes in cartelas_numeros_restantes.items():
                                    cartela_restante = codigo_cartela
                                    numeros = numeros_restantes
                                    cartelas_estrutura.append(
                                        (cartela_restante, numeros[0].copy() + numeros[1].copy() + numeros[2].copy(), 3)
                                    )

                            else:
                                for codigo_cartela, numeros_restantes in cartelas_numeros_restantes.items():
                                    cartela_restante = codigo_cartela
                                    numeros = numeros_restantes
                                    cartelas_estrutura += [(cartela_restante, numeros[0].copy(), 0),
                                                           (cartela_restante, numeros[1].copy(), 1),
                                                           (cartela_restante, numeros[2].copy(), 2)
                                                           ]

                            cartelas_ordenadas_bola = sorted(cartelas_estrutura, key=lambda x: len(x[1]))[:15]
                            cartelas_ordenadas.append(cartelas_ordenadas_bola)

                            if rodada_kuadra:
                                ##print("KUADRA")
                                partida.bola_kuadra = bola
                                # partida.save()
                                kuadra = True
                            if rodada_kina:
                                ##print("KINA")
                                partida.bola_kina = bola
                                # partida.save()
                                kina = True
                            if rodada_keno:
                                ##print("KENO")
                                partida.bola_keno = bola
                                # partida.save()
                                keno = True

                            rodada_kuadra = False
                            rodada_kina = False
                            rodada_keno = False

                            if keno:
                                break

                        # FINALIZANDO A PARTIDA
                        self.log("finalizando a partida e salvando os dados/relatorios")

                        turnos = []
                        valores_list = []
                        for item in cartelas_ordenadas:
                            for top15 in item:
                                d = {
                                    'codigo': int(top15[0]),
                                    'nome': codigo_cartela_nome[top15[0]][0],
                                    "posicao": int(top15[2]),
                                    "numeros": top15[1]
                                }
                                turnos.append(d)
                                valores_list.append(top15[0])

                        valores_list += [x[0] for x in vencedores_kina + vencedores_kuadra + vencedores_keno]
                        cartelas_participantes = list(set(valores_list))

                        self.log("Setando os valores de Numero de cartelas")
                        partida.bolas_sorteadas = ",".join(bolas_sorteadas)
                        partida.em_sorteio = False
                        partida.data_fim = datetime.datetime.now(tz=RECIFE)
                        partida.cartelas_participantes = ",".join([str(x) for x in cartelas_participantes])

                        partida.num_cartelas = len(cartelas)
                        partida.sorteio = json.dumps(turnos)

                        # REGISTRANDO AS CARTELAS VENCEDORAS
                        self.log("Registrando no banco as cartelas vencedoras e seus valores")
                        premio = partida.valor_kuadra + partida.valor_kina + partida.valor_keno
                        msg = "kuadra:["
                        for v_kuadra in list(set(vencedores_kuadra)):
                            valor = partida.valor_kuadra / len(vencedores_kuadra)
                            CartelaVencedora.objects.create(
                                partida=partida, cartela_id=codigo_cartela_nome[v_kuadra[0]][1], premio=1, valor_premio=valor,
                                linha_vencedora=v_kuadra[1]
                            )
                            msg += str(v_kuadra[0]) + "," + str(valor)
                            msg += "],"
                        msg += "kina:["
                        for v_kina in list(set(vencedores_kina)):
                            valor = partida.valor_kina / len(vencedores_kina)
                            CartelaVencedora.objects.create(
                                partida=partida, cartela_id=codigo_cartela_nome[v_kina[0]][1], premio=2, valor_premio=valor,
                                linha_vencedora=v_kina[1]
                            )
                            msg += str(v_kina[0]) + "," + str(valor)
                            msg += "],"
                        msg += "keno:["
                        for v_keno in list(set(vencedores_keno)):
                            valor = partida.valor_keno / len(vencedores_keno)
                            CartelaVencedora.objects.create(partida=partida, cartela_id=codigo_cartela_nome[v_keno[0]][1], premio=3,
                                                            valor_premio=valor,linha_vencedora=3)
                            msg += str(v_keno[0]) + "," + str(valor)
                            msg += "],"

                        self.log(msg)

                        partida.premios_set = premio
                        partida.data_fim = datetime.datetime.now(tz=RECIFE)

                    self.log("Sorteio Finalizado")

                else:
                    self.log("Sorteio em andamento")
            else:
                self.log("Agendamento não existente")

        except Exception as e:
            self.log(str(e))
            self.log(str(traceback.extract_stack()))
        finally:
            if modo_sorteio:
                self.log("************Finalizando a rotina de agendamento***************")
                if partida:
                    partida.em_sorteio = False
                    partida.save()

                    self.log("Disparando eventos WebSocket")

                    event_bilhete_sorteio(partida.id)

                    if partida.partida_automatizada and partida.id_automato:
                        self.log("Sorteio Automatizado Iniciando Script")
                        self.log("id do automato" + str(partida.id_automato))
                        partida_automatizada(partida, self)

                    self.log("Sorteio Finalizado (finally)")

                    self.atualizando_conexoes_websocket(partida)

                    # Eliminando cartelas nao utilizadas
                    codigos_participantes = partida.cartelas_participantes.split(",")
                    Cartela.objects.filter(
                        partida=partida,jogador__isnull=True
                    ).exclude(codigo__in=codigos_participantes).delete()
                if agenda:
                    agenda.shutdown(wait=False)

            else:
                self.log("************MODO SORTEIO FALSE***************")

    # AGENDADOR PARA TEMPLATE DE PARTIDA
    def agendar_template(self, template, agora=False):
        try:
            agenda_template = BackgroundScheduler(daemon=True,timezone="America/Recife")
            configuracao = Configuracao.objects.all().last()
            if agora:
                self.sortear_template(template=template,agenda_t=None, restart=False)
            else:
                data = template.data_introducao + datetime.timedelta(minutes=configuracao.tempo_expirar_template)
                self.log(f"Agendamento template sendo feito para o template {template.id} horario + {template.data_partida}")
                job = agenda_template.add_job(self.sortear_template, 'date', run_date=data, args=[template,agenda_template])
                self.log("Agendado template")
                if not template.id in self.agendas.keys():
                    self.agendas_template[template.id]=(agenda_template,False, job.id)
                agenda_template.start()
        except Exception as e:
            self.log(str(traceback.extract_stack()))
            self.log(str(e))

    def sortear_template(self,template:TemplatePartida,agenda_t, restart=True):
        self.log(f"Sorteando template: {template.id} horario + {template.data_partida}")
        template = TemplatePartida.objects.get(id = template.id)
        try:
            with transaction.atomic():
                if template.data_partida.replace(tzinfo=RECIFE) >= datetime.datetime.now(tz=RECIFE) + datetime.timedelta(minutes=5) and not template.play and not template.cancelado:
                    self.log(f"Rodando o template agendado: {template.id} horario + {template.data_partida}")
                    tempo = Automato.objects.get(id=template.id_automato).tempo
                    template.data_partida = testa_horario(template.data_partida,False,tempo)
                    p:Partida = Partida.objects.create(
                        valor_keno = template.valor_keno,
                        valor_kina = template.valor_kina,
                        valor_kuadra = template.valor_kuadra,
                        data_partida = template.data_partida,
                        id_automato = template.id_automato,
                        partida_automatizada=True,
                        usuario=template.usuario,
                        tipo_rodada = template.tipo_rodada,
                        regra = template.regra
                    )
                    self.agendar(p)
                    template.play =True
                    template.save()
                    # comprando cartelas
                    configuracao = Configuracao.objects.last()
                    comprar_cartelas(p,configuracao.quantidade_cartelas_compradas)
        except Exception as e:
            self.log(str(traceback.extract_stack()))
            self.log(str(e))
        finally:
            agenda_t.shutdown(wait=False)

    def atualizando_conexoes_websocket(self, partida):
        relatorio = DispositivosConectados.objects.filter(nome_sala=f"sorteio-{partida.id}").delete()
        self.log(f"WS exclusao DB: {relatorio}")

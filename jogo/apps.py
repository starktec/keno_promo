import subprocess
from datetime import datetime

from django.apps import AppConfig
from django.db import transaction, connections

import logging
logger = logging.getLogger(__name__)

class JogoConfig(AppConfig):
    name = 'jogo'
    processou = False


    def ready(self):
        if set(
                ['jogo_partida','jogo_templatepartida','jogo_configuracao']
        ).issubset(connections['default'].introspection.table_names()) and not self.processou:
            logger.info("READY")
            self.processou = True
            cmd = "git status"
            status, output = subprocess.getstatusoutput(cmd)
            if status == 0:
                dado = output.split("\n")[0].split()[2]
                if dado:
                    from jogo.models import Configuracao
                    if not Configuracao.objects.count():
                        Configuracao.objects.create()
                    configuracao = Configuracao.objects.exclude(versao=dado).first()
                    if configuracao:
                        configuracao.versao = dado
                        configuracao.save()

            from jogo.models import Partida, TemplatePartida
            from jogo.views import agenda
            partidas = Partida.objects.filter(data_partida__gt=datetime.now())
            for p in partidas:
                if not p.id in agenda.agendas.keys():
                    agenda.agendar(p)
                    agenda.log("agendado partida " + str(p.id))

            agora = datetime.now()
            with transaction.atomic():
                templates = TemplatePartida.objects.select_for_update().filter(play=False, data_partida__gt=agora)
                if templates:
                    agenda.log("Remontando os templates")
                    for template in templates:
                        agenda.agendar_template(template, agora=True)

            agenda.log("Organizando os grupos websocket")
            agenda.limpar_conexoes_websocket()
    

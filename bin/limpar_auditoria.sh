#!/bin/bash
source /home/project/bingo/env/bin/activate
python /home/project/bingo/manage.py runscript limpar_auditoria
sync && sudo sysctl -w vm.drop_caches=3
systemctl restart redis
systemctl restart postgresql
systemctl restart gunicorn

  
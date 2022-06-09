#!/bin/bash
source /home/project/keno_promo/env/bin/activate
python /home/project/keno_promo/manage.py runscript atualizacaodiaria
sync && sudo sysctl -w vm.drop_caches=3
systemctl restart redis
systemctl restart postgresql
systemctl restart gunicorn

  
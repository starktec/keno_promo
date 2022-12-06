#!/bin/bash
source /home/project/keno_promo/env/bin/activate
RESULT=`python /home/project/keno_promo/bin/check_sorteio.py`
echo $RESULT
if [ "$RESULT" -ge 1 ]; then
  echo "entrou"
  python /home/project/keno_promo/manage.py runscript sortear --script-args $RESULT
else
  echo "saiu"
fi

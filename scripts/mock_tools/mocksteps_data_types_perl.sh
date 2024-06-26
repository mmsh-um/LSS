#!/bin/bash

source /global/common/software/desi/desi_environment.sh main
PYTHONPATH=$PYTHONPATH:$HOME/LSS/py

python mkCat_mock.py --tracer LRG --mockmin $1 --mockmax $2 --survey Y1 --fulld y --fullr y --apply_veto y --mkclusran y --mkclusdat y --mkclusran_allpot y --mkclusdat_allpot y --nz y

python mkCat_mock.py --tracer ELG --mockmin $1 --mockmax $2 --survey Y1 --fulld y --fullr y --apply_veto y --mkclusran y --mkclusdat y --mkclusran_allpot y --mkclusdat_allpot y --nz y

python mkCat_mock.py --tracer QSO --mockmin $1 --mockmax $2 --survey Y1 --fulld y --fullr y --apply_veto y --mkclusran y --mkclusdat y --mkclusran_allpot y --mkclusdat_allpot y --nz y
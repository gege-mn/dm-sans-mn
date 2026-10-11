#!/bin/sh
# sheet.sh OUT SIZE "masters"  -> full Cyrillic set from the generated source
cd "$(dirname "$0")/.." && .venv/bin/python tools/show.py sources/DMSansMN.glyphs "$1" "$2" "$3" \
 "A-cy Be-cy Ve-cy Ge-cy De-cy Ie-cy Io-cy Zhe-cy Ze-cy Ii-cy Iishort-cy Ka-cy El-cy Em-cy En-cy O-cy Obarred-cy Pe-cy" \
 "Er-cy Es-cy Te-cy U-cy Ustraight-cy Ef-cy Ha-cy Tse-cy Che-cy Sha-cy Shcha-cy Hardsign-cy Yeru-cy Softsign-cy Ereversed-cy Iu-cy Ia-cy tugrik numero" \
 "a-cy be-cy ve-cy ge-cy de-cy ie-cy io-cy zhe-cy ze-cy ii-cy iishort-cy ka-cy el-cy em-cy en-cy o-cy obarred-cy pe-cy er-cy es-cy te-cy u-cy ustraight-cy" \
 "ef-cy ha-cy tse-cy che-cy sha-cy shcha-cy hardsign-cy yeru-cy softsign-cy ereversed-cy iu-cy ia-cy n o h a e s"

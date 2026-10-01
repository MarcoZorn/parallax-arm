#!/bin/bash
# Verifica collisioni su una griglia di pose (th2 x e, phi = th2 - e entro [-70, 70]), pinza alternata 0/59 mm.
# th2 = 17 copre il cedimento sotto carico della spalla (sim/dynamics: fino a 17.5° con 50 g).
# Per ogni posa con collisioni ripete il controllo coppia per coppia e stampa chi tocca chi.
# Uso: cad/check_grid.sh   (~2 min per posa con OpenSCAD 2021)
cd "$(dirname "$0")"
out=$(mktemp -d)
names=(turret arm crank drive_rod lev_rod forearm link rod2 wrist hw)
k=0; bad=0; n=0
for th in 17 20 40 60 90 120 140 160; do for e in 20 50 80 110 150; do
  ph=$((th - e)); [ $ph -lt -70 -o $ph -gt 70 ] && continue
  gg=$(( k % 2 == 0 ? 0 : 59 )); k=$((k+1)); n=$((n+1))
  r=$(openscad -D check=1 -D th2=$th -D phi=$ph -D g=$gg -o "$out/p.stl" assembly.scad 2>&1 | grep -Eio "empty|Volumes: *[0-9]+")
  if [ "$r" = "empty" ]; then echo "ok   th2=$th phi=$ph g=$gg"; else
    bad=$((bad+1))
    for i in $(seq 0 8); do for j in $(seq $((i+1)) 9); do
      rr=$(openscad -D check=2 -D pi=$i -D pj=$j -D th2=$th -D phi=$ph -D g=$gg -o "$out/q.stl" assembly.scad 2>&1 | grep -Eio "empty|Volumes: *[0-9]+")
      [ "$rr" != "empty" ] && echo "HIT  th2=$th phi=$ph g=$gg ${names[$i]} x ${names[$j]}"
    done; done
  fi
done; done
# controllo negativo: il braccio dentro il pavimento DEVE collidere, altrimenti la verifica non vale
neg=$(openscad -D check=1 -D th2=-80 -D phi=0 -D g=30 -o "$out/n.stl" assembly.scad 2>&1 | grep -Eio "empty|Volumes: *[0-9]+")
echo "controllo negativo (deve collidere): $neg"
rm -rf "$out"
echo "FINE: $n pose, $bad con collisioni"
[ $bad -eq 0 ] && [ "$neg" != "empty" ]

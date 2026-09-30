#!/bin/bash
# Rigenera tutto dopo una modifica a params.scad:
#   stl/      -> file da stampare, già orientati sul piatto (1 file = 1 pezzo, "xN" = quante copie)
#   ../web/public/models/ -> modelli binari leggeri per il digital twin + rig.json
set -e
cd "$(dirname "$0")"
mkdir -p stl ../web/public/models
rm -f stl/*.stl

p() {  # p <file.scad> <part> <nome_out>
  openscad -D "part=\"$2\"" -o "stl/$3.stl" "$1" 2>&1 | grep -Ei "warn|error" || true
  echo "stl/$3.stl"
}
p test/tolerance_coupon.scad all      00_tolerance_coupon
p base.scad        tray               01_base_tray
p base.scad        lid                02_base_lid
openscad -o stl/03_turret.stl turret.scad 2>&1 | grep -Ei "warn|error" || true; echo stl/03_turret.stl
p upper_arm.scad   arm                04_upper_arm
p upper_arm.scad   lid                05_upper_arm_lid
p crank.scad       crank              06_crank
p crank.scad       lid                07_crank_lid
p crank.scad       spacer             08_crank_spacer
p linkage.scad     drive_rod          09_drive_rod
p linkage.scad     lev_rod            10_lev_rod
p linkage.scad     lev_rod2           11_lev_rod2
p linkage.scad     lev_link           12_lev_link
p linkage.scad     print_forearm      13_forearm
p linkage.scad     spacers            14_elbow_wrist_spacers
p wrist.scad       bracket            15_wrist_bracket
p wrist.scad       housing            16_gripper_housing
p wrist.scad       base_plate         17_gripper_base_plate
p wrist.scad       pinion             18_gripper_pinion
p wrist.scad       jaw                19_gripper_jaw_x2
p wrist.scad       cam_cradle         20_esp32cam_cradle

for w in base turret upper_arm crank drive_rod lev_rod lev_rod2 lev_link forearm wrist jaw_l jaw_r; do
  openscad --export-format binstl -D '$fn=24' -D "which=\"$w\"" -o "../web/public/models/$w.stl" twin.scad 2>&1 | grep -Ei "warn|error" || true
done

# rig.json dai parametri reali (echo di OpenSCAD)
v() { printf 'include <params.scad>\necho(v=%s);\n' "$1" > _v.scad; openscad -o _v.echo _v.scad >/dev/null 2>&1; sed -n 's/^ECHO: v = //p' _v.echo; rm -f _v.scad _v.echo; }
read L3 TCPDZ < <(openscad -D 'part="none"' -o _t.echo wrist.scad >/dev/null 2>&1; sed -n 's/.*L3 = \([-0-9.]*\)  tcp_dz = \([-0-9.]*\).*/\1 \2/p' _t.echo; rm -f _t.echo)
cat > ../web/public/models/rig.json <<EOF
{
  "params": { "base_h": $(v base_h), "sh_h": $(v sh_h), "L1": $(v L1), "L2": $(v L2), "L3": $L3, "tcp_dz": $TCPDZ,
              "crank_r": $(v crank_r), "lev_r": $(v lev_r), "lev2_r": $(v lev2_r) },
  "parts": [
    { "name": "base",      "file": "base.stl",      "y": 0,               "color": "#3a3f45" },
    { "name": "turret",    "file": "turret.stl",    "y": 0,               "color": "#5b6168" },
    { "name": "upper_arm", "file": "upper_arm.stl", "y": $(v y_arm),      "color": "#e6e7e8" },
    { "name": "crank",     "file": "crank.stl",     "y": $(v y_crank_in), "color": "#ff7a1a" },
    { "name": "drive_rod", "file": "drive_rod.stl", "y": $(v y_rod[0]),   "color": "#9aa1a8" },
    { "name": "lev_rod",   "file": "lev_rod.stl",   "y": $(v y_lev[0]),   "color": "#80878e" },
    { "name": "forearm",   "file": "forearm.stl",   "y": $(v y_fore_l[0]),"color": "#e6e7e8" },
    { "name": "lev_link",  "file": "lev_link.stl",  "y": $(v y_link[0]),  "color": "#80878e" },
    { "name": "lev_rod2",  "file": "lev_rod2.stl",  "y": $(v y_rod2[0]),  "color": "#9aa1a8" },
    { "name": "wrist",     "file": "wrist.stl",     "y": 0,               "color": "#5b6168" },
    { "name": "jaw_l",     "file": "jaw_l.stl",     "y": 0,               "color": "#ff7a1a" },
    { "name": "jaw_r",     "file": "jaw_r.stl",     "y": 0,               "color": "#ff7a1a" }
  ]
}
EOF
du -ch ../web/public/models/*.stl | tail -1

// Modelli per il digital twin (web/public/models): ogni parte nel frame del contratto (docs/03-protocollo.md §2).
// Uso: openscad --export-format binstl -D 'which="turret"' -o ../web/public/models/turret.stl twin.scad
include <params.scad>
use <lib/parts.scad>
use <base.scad>
use <turret.scad>
use <upper_arm.scad>
use <crank.scad>
use <linkage.scad>
use <wrist.scad>

which = "turret";
xp = 42; zd = 12;   // come wrist.scad (per il servo della pinza)

module cheek_servo(side) {   // SG90 fuori dalla guancia, albero verso l'interno sull'asse spalla
    y_tab = -(y_wall + cheek_t);
    m = [[0, 1, 0, 0], [0, 0, 1, y_tab - (sg_tab_z + sg_tab_t)], [1, 0, 0, sh_h], [0, 0, 0, 1]];
    if (side < 0) multmatrix(m) sg90_model(); else mirror([0, 1, 0]) multmatrix(m) sg90_model();
}

if (which == "base") { tray(); lid(); translate([0, 0, base_h - sg_horn_face]) sg90_model(); }
if (which == "turret") { turret(); cheek_servo(-1); cheek_servo(1); }
if (which == "upper_arm") { upper_arm(); translate([0, 0, cw_t]) arm_lid(); }
if (which == "crank") crank_assembly();
if (which == "drive_rod") drive_rod();
if (which == "lev_rod") lev_rod();
if (which == "lev_rod2") lev_rod2();
if (which == "lev_link") lev_link();
if (which == "forearm") forearm();
// polso e dita: frame G (Z su) -> frame P locale = Rx(90) (y del piano = 0)
if (which == "wrist") rotate([90, 0, 0]) { bracket(); housing(); base_plate(); cam_cradle(); wrist_servo(); }
if (which == "jaw_l") rotate([90, 0, 0]) rack_pose(1, 0) jaw();
if (which == "jaw_r") rotate([90, 0, 0]) rack_pose(-1, 0) jaw();

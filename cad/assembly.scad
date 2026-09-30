// Assieme torretta + braccio + manovella + bielle (segnaposto) + SG90, per anteprima e verifica collisioni.
// Pose: th2 = angolo assoluto braccio, phi = angolo assoluto avambraccio (gradi, 0 = orizzontale avanti).
// Vincolo parallelogramma: 20 <= th2 - phi <= 160.
// Verifica: openscad -D 'check=1' -D th2=.. -D phi=.. -o out.stl assembly.scad -> deve risultare VUOTO.
include <params.scad>
use <turret.scad>
use <upper_arm.scad>
use <crank.scad>

th2 = 60;
phi = 0;
check = 0;
psi = phi + 180;  // la manovella punta opposta all'avambraccio

function u(a) = [cos(a), 0, sin(a)];
O = [0, 0, sh_h];
G = [-lev_r, 0, sh_h];

module at_shoulder(y, a) translate([0, y, sh_h]) rotate([0, -a, 0]) rotate([-90, 0, 0]) children();

module arm() at_shoulder(y_arm, th2) {
    upper_arm();
    translate([0, 0, cw_t]) arm_lid();
    for (x = [-cw_shoulder_r - lead_pocket[0] / 2 - 4.5], y = [-1, 1] * (lead_pocket[1] + 2) / 2)
        translate([x, y, cw_t + lid_t]) cylinder(d = m3_head_d, h = 3);  // teste viti
}
module crk() at_shoulder(y_crank_in, psi) crank_assembly();

// bielle segnaposto (sezione 8 x rod_t) nei loro piani, lunghe L1 e parallele al braccio
module bar(p, a, ys) translate([p.x, ys[0], p.z]) rotate([0, -a, 0]) translate([0, 0, -4]) cube([L1, ys[1] - ys[0], 8]);
module rods() {
    bar(O + crank_r * u(psi), th2, y_rod);  // motrice: da A, parallela al braccio
    bar(G, th2, y_lev);                     // livellamento: da G
}

// SG90 fuori dalle guance (corpo + linguette), albero sull'asse spalla
module sg90_at(side) {
    y_out = side * (y_wall + cheek_t);
    z0 = sh_h - (sg_body.x - sg_shaft_x);
    translate([-sg_body.y / 2, side > 0 ? y_out : y_out - (sg_tab_z + sg_tab_t), z0]) {
        cube([sg_body.y, sg_tab_z + sg_tab_t, sg_body.x]);
    }
}

if (check == 0) {
    color("SteelBlue") turret();
    color("Orange") arm();
    color("Gold") crk();
    color("Gray", 0.6) rods();
    color("DimGray") { sg90_at(-1); sg90_at(1); }
} else {
    // ogni coppia che NON deve toccarsi
    intersection() { turret(); arm(); }
    intersection() { turret(); crk(); }
    intersection() { arm(); crk(); }
    intersection() { turret(); rods(); }
    intersection() { arm(); rods(); }
    intersection() { crk(); bar(G, th2, y_lev); }
}

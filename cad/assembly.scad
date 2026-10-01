// Assieme completo nel frame torretta (yaw = 0) per anteprima e verifica collisioni.
// Pose: th2 = angolo assoluto braccio, phi = angolo assoluto avambraccio (0 = orizzontale avanti), g = apertura pinza.
// Limiti: 20 <= th2 <= 160, -70 <= phi <= 70, 20 <= th2 - phi <= 150 (docs/03-protocollo.md).
// Verifica: openscad -D check=1 -D th2=.. -D phi=.. -D g=.. -o out.stl assembly.scad -> deve risultare VUOTO.
// Controlla ogni coppia di parti più la ferramenta (teste viti, dadi autobloccanti, distanziali).
include <params.scad>
use <turret.scad>
use <upper_arm.scad>
use <crank.scad>
use <linkage.scad>
use <wrist.scad>
use <base.scad>
use <twin.scad>
use <cables.scad>

th2 = 60;
phi = 0;
g = 30;
check = 0;
pi = 0;
pj = 1;
show_cables = false;
psi = phi + 180;  // la manovella punta opposta all'avambraccio

function u(a) = [cos(a), 0, sin(a)];
function Y(p, y) = [p.x, y, p.z];
O = [0, 0, sh_h];
E = O + L1 * u(th2);
W = E + L2 * u(phi);
A = O + crank_r * u(psi);
B = E + crank_r * u(psi);
G = O + lev_r * u(180);
P1 = E + lev_r * u(180);
U = E + lev2_r * u(90);
V = W + lev2_r * u(90);

// frame del contratto: P(p, a) = T(p) Ry(-a) Rx(-90)
module P(p, a) translate(p) rotate([0, -a, 0]) rotate([-90, 0, 0]) children();

module arm() P(Y(O, y_arm), th2) {
    upper_arm();
    translate([0, 0, cw_t]) arm_lid();
    for (x = [-cw_shoulder_r - lead_pocket[0] / 2 - 4.5], y = [-1, 1] * (lead_pocket[1] + 2) / 2)
        translate([x, y, cw_t + lid_t]) cylinder(d = m3_head_d, h = 3);  // teste viti coperchio
}

module part(i) {
    if (i == 0) turret();
    if (i == 1) arm();
    if (i == 2) P(Y(O, y_crank_in), psi) crank_assembly();
    if (i == 3) P(Y(A, y_rod[0]), th2) drive_rod();
    if (i == 4) P(Y(G, y_lev[0]), th2) lev_rod();
    if (i == 5) P(Y(E, y_fore_l[0]), phi) forearm();
    if (i == 6) P(Y(E, y_link[0]), 0) lev_link();
    if (i == 7) P(Y(U, y_rod2[0]), phi) lev_rod2();
    if (i == 8) translate(W) wrist_assembly(g, lite = check > 0);
    if (i == 9) hardware();
}
N = 10;

// Ferramenta: cilindro lungo Y in p da y0 a y1.
module pin(p, y0, y1, d) translate([p.x, y0, p.z]) rotate([-90, 0, 0]) cylinder(d = d, h = y1 - y0);
module head(p, y, dir) pin(p, dir > 0 ? y + 0.1 : y - 3.1, dir > 0 ? y + 3.1 : y - 0.1, m3_head_d);
module nylock(p, y, dir) pin(p, dir > 0 ? y + 0.1 : y - 4.1, dir > 0 ? y + 4.1 : y - 0.1, 6.4);
module hardware() {
    head(E, y_arm, -1);             nylock(E, y_fore_r[1], 1);
    pin(E, y_fore_l[1] + 0.1, y_link[0] - 0.1, 6);  pin(E, y_link[1] + 0.1, y_fore_r[0] - 0.1, 5);
    head(W, y_fore_l[0], -1);       nylock(W, y_fore_r[1], 1);
    pin(W, y_fore_l[1] + 0.1, y_bracket[0] - 0.1, 6);
    head(A, y_crank_in + crank_t, 1);                       // dado incassato nella biella motrice
    head(B, y_rod[1], 1);                                   // dado incassato nella piastra R
    head(G, y_lev[0], -1);          nylock(G, y_post[1], 1);
    head(P1, y_lev[1], 1);                                  // dado incassato nel triangolo
    head(U, y_rod2[0], -1);                                 // dado incassato nel triangolo
    head(V, y_rod2[0], -1);         nylock(V, y_link[1], 1);
}

if (check == 0) {
    colors = ["SteelBlue", "Orange", "Gold", "Gray", "Gray", "Orange", "Silver", "Gray", "White", "Black"];
    for (i = [0:N - 1]) color(colors[i]) part(i);
    color("DimGray") translate([0, 0, -base_h]) { tray(); lid(); }   // base (solo anteprima)
    cheek_servo(-1); cheek_servo(1);
    translate(W) wrist_servo();
    if (show_cables) cables(th2, phi);
} else if (check == 2) {
    intersection() { part(pi); part(pj); }   // una coppia, per isolare una collisione
} else {
    for (i = [0:N - 2], j = [i + 1:N - 1]) intersection() { part(i); part(j); }
}

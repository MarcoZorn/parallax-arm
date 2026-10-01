// Torretta: gira sulla base (servo J1 sotto il pavimento), porta i servo spalla (guancia sinistra, y<0)
// e gomito (guancia destra), alberi rivolti verso l'interno, più il montante fisso G del livellamento.
// Frame: z=0 = faccia inferiore del pavimento = faccia della squadretta del servo base. Asse spalla lungo Y a z=sh_h.
// Stampa: così com'è, pavimento sul piatto, nessun supporto (le finestre servo sono ponti da 12.8 mm).
//
// Montaggio:
//  1. SG90 spalla e gomito da FUORI: corpo nella finestra, linguette sulla faccia esterna, viti autofilettanti;
//  2. squadretta del servo base nella tasca sotto il pavimento, vite centrale dall'alto;
//  3. cavo pinza/camera: dalla canalina del braccio (lato servo), ansa nello spazio tra squadretta e guancia
//     sinistra, entra di lato nell'asola della guancia, scende fuori e passa nell'asola del pavimento (docs/02).
include <params.scad>
use <lib/parts.scad>

G = [-lev_r, sh_h];                        // perno fisso livellamento (x, z)
groove = [base_lip[0] - clr_pivot / 2, base_lip[1] + clr_pivot / 2, 1.8];  // gola sotto il pavimento: labbro della base
cable_holes = [[-8, 42], [-8, -42]];       // r 43: dentro l'apertura della base per tutta la rotazione
sg_z = [sh_h - (sg_body.x - sg_shaft_x), sh_h + sg_shaft_x];  // corpo SG90 in verticale, albero in alto

module cheek_outline() hull() {
    translate([-32, 0]) square([64, floor_t + 1]);
    translate([0, sh_h]) circle(r = 16);
    translate([-22, sh_h]) circle(r = 7);
}

module cheek(side) {
    y0 = side > 0 ? y_wall : -y_wall - cheek_t;
    difference() {
        translate([0, y0 + cheek_t, 0]) rotate([90, 0, 0]) linear_extrude(cheek_t) cheek_outline();
        // finestra corpo servo + fori pilota per le viti delle linguette
        translate([-(sg_body.y / 2 + clr_servo), y0 - 1, sg_z[0] - clr_servo])
            cube([sg_body.y + 2 * clr_servo, cheek_t + 2, sg_z[1] - sg_z[0] + 2 * clr_servo + 0.3]);  // +0.3 in alto
        for (s = [-1, 1]) translate([0, y0 - 1, (sg_z[0] + sg_z[1]) / 2 + s * sg_screw_pitch / 2])
            rotate([-90, 0, 0]) cylinder(d = sg_screw_d - 0.4, h = cheek_t + 2, $fn = 16);
        // passaggio cavi pinza/camera: foro + asola aperta sul bordo, il cavo entra di lato (il connettore non passa)
        if (side < 0) {
            translate([-22, y0 - 1, sh_h]) rotate([-90, 0, 0]) cylinder(d = 6, h = cheek_t + 2);
            translate([-33, y0 - 1, sh_h - 1.2]) cube([11, cheek_t + 2, 2.4]);
        }
    }
    // fazzoletti esterni (lato servo): dentro la torretta non c'è spazio, lì ruota tutto
    for (x = [-24, 24]) translate([x - 1.5, side > 0 ? y0 + cheek_t : y0, floor_t])
        rotate([90, 0, 90]) linear_extrude(3)
            polygon(side > 0 ? [[0, 0], [14, 0], [0, 50]] : [[0, 0], [-14, 0], [0, 50]]);   // alti 50: guance più rigide fuori piano
}

module post() {
    difference() {
        translate([0, y_post[1], 0]) rotate([90, 0, 0]) linear_extrude(y_post[1] - y_post[0]) hull() {
            translate([G.x - 8, 0]) square([16, floor_t + 1]);
            translate(G) circle(r = 4);
        }
        translate([G.x, y_post[0] - 1, G.y]) rotate([-90, 0, 0]) cylinder(d = m3_d + clr_hole, h = 10);
    }
}

module turret() {
    difference() {
        cylinder(r = floor_r, h = floor_t, $fn = 128);
        horn_pocket(clr_pocket, floor_t + 1);
        translate([0, 0, -1]) difference() {
            cylinder(r = groove[1], h = groove[2] + 1, $fn = 128);
            cylinder(r = groove[0], h = groove[2] + 3, $fn = 128);
        }
        for (p = cable_holes) translate([p.x, p.y, -1]) {   // foro + asola radiale fino al bordo: cavi infilati di lato
            cylinder(d = 8, h = floor_t + 2);
            translate([-1.3, p.y > 0 ? 0 : -(floor_r - abs(p.y) + 1), 0]) cube([2.6, floor_r - abs(p.y) + 1, floor_t + 2]);
        }
        // 4 finestre di alleggerimento: fuori da montante G, guance, gola della corona e squadretta
        for (sx = [-1, 1], sy = [-1, 1]) translate([sx * 32, sy * 16, -1]) cylinder(d = 18, h = floor_t + 2);
    }
    cheek(-1);
    cheek(1);
    post();
}

turret();

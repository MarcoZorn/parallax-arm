// Provino tolleranze: stampalo PRIMA di tutto, con lo stesso materiale e profilo slicer delle parti.
// Per ogni prova annota il valore che calza e riportalo in params.scad:
//   fori M3: diametro in cui la vite passa senza gioco visibile  -> clr_hole = diam - 3.0
//   sedi dado, finestre SG90 (S0.x), squadretta, sedi piombo    -> clr_pocket
//     (entra a mano senza forzare, non balla). Sedi passanti: conta il contorno, non la profondità.
//   cursori coda di rondine 1..4 = 0.1..0.4 per lato            -> clr_slide (scorre senza gioco)
//   colonnine a scatto 0.3/0.45/0.6: la scheda entra con un clic
//     e non si sfila da sola                                    -> snap_hook
// part = "all" | "plate" | "rail" | "sliders" | "snap" | "board"
// ponytail: piastrine collegate da barrette invece di una lastra piena (-70% filamento).
include <../params.scad>
use <../lib/parts.scad>

part = "all";
T = 2.4;   // = altezza dado M3: il dado va a filo
BAR = [3, 1.2];  // barrette di collegamento: larghezza, altezza
clrs = [0.1, 0.2, 0.3];

module tile(c, size) translate([c.x, c.y, 0]) linear_extrude(T) offset(r = 1) square([size.x - 2, size.y - 2], center = true);
module bar(a, b) hull() for (p = [a, b]) translate([p.x, p.y, 0]) cylinder(d = BAR[0], h = BAR[1], $fn = 12);

module plate() {
    difference() {
        union() {
            for (i = [0:4]) tile([12 + i * 20, 76], [13, 20]);                   // fori M3
            for (i = [0:3]) tile([112 + (i % 2) * 24 + 4.5, 80 - floor(i / 2) * 18], [20, 12]);  // dadi
            for (i = [0:2]) tile([18 + i * 37, 41.5], [sg_body.x + 5, 24]);      // finestre SG90
            for (i = [0:2]) tile([116 + i * 15, 20.5], [12, 44]);                // squadrette
            for (i = [0:2]) tile([18 + i * 37, 6], [lead_l + 8, lead_d + 13]);  // piombi a oliva
            bar([12, 76], [150, 76]);
            bar([18, 41.5], [116, 41.5]);
            bar([18, 10], [146, 10]);
            for (x = [18, 92]) bar([x, 10], [x, 76]);
            bar([146, 10], [146, 80]);
        }

        for (i = [0:4]) {
            d = 3.0 + i * 0.1;
            translate([12 + i * 20, 80, -1]) cylinder(d = d, h = T + 2);
            engrave([12 + i * 20, 71], T, str(d), 2.8);
        }
        for (i = [0:3]) {
            p = [112 + (i % 2) * 24, 80 - floor(i / 2) * 18];
            translate([p.x, p.y, -1]) hex_pocket(h = T + 2, c = i * 0.1);
            engrave([p.x + 9.5, p.y], T, str(i * 0.1), 2.5);
        }
        for (i = [0:2]) {
            translate([18 + i * 37, 45, T / 2])
                cube([sg_body.x + 2 * clrs[i], sg_body.y + 2 * clrs[i], T + 2], center = true);
            engrave([18 + i * 37, 34], T, str("S", clrs[i]), 2.8);
        }
        for (i = [0:2]) {
            translate([116 + i * 15, 24, -1]) rotate(90) linear_extrude(T + 2) horn_outline(clrs[i]);
            engrave([116 + i * 15, 3], T, str(clrs[i]), 2.5);
        }
        // sede piombo passante: gioco per lato 0.1/0.2/0.3 (in lunghezza +0.3 in più, come nelle parti)
        for (i = [0:2]) {
            translate([18 + i * 37, 9, -1]) linear_extrude(T + 2) hull() for (s = [-1, 1])
                translate([s * (lead_l + 0.3 - lead_d) / 2, 0]) circle(d = lead_d + 2 * clrs[i]);
            engrave([18 + i * 37, -3], T, str(clrs[i]), 2.5);
        }
    }
}

// Coda di rondine 60°: la stessa guida delle cremagliere della pinza.
dt_top = 8;
dt_h = 4;
dt_bot = dt_top + 2 * dt_h / tan(60);
module dt_profile() polygon([[-dt_bot / 2, 0], [dt_bot / 2, 0], [dt_top / 2, dt_h], [-dt_top / 2, dt_h]]);

RAIL_L = 30;
module rail() {
    difference() {
        cube([dt_bot + 5, RAIL_L, dt_h + 1.2]);
        // scanalatura larga in basso, stretta in alto: sbalzo 30° dalla verticale, stampabile
        translate([(dt_bot + 5) / 2, RAIL_L + 1, 1.2]) rotate([90, 0, 0]) linear_extrude(RAIL_L + 2) {
            dt_profile();
            translate([-dt_top / 2, dt_h - 0.01]) square([dt_top, 1]);
        }
    }
}

// Cursori stampati con la faccia larga sul piatto; il numero inciso = gioco per lato x 0.1
module sliders() {
    for (i = [1:4]) {
        s = i * 0.1;
        translate([(i - 1) * 17, 0, 0]) difference() {
            translate([0, 12, 0]) rotate([90, 0, 0]) linear_extrude(12) {
                offset(delta = -s) dt_profile();
                translate([-(dt_top / 2 - s), dt_h - s - 0.01]) square([dt_top - 2 * s, 3 + s]);
            }
            engrave([0, 6], dt_h + 3, str(i), 3.5);
        }
    }
}

// Colonnine a scatto per schede spesse 1.6 mm (come i PCB).
// Lamella 1.6 x 5, luce ~9 mm -> deformazione 1.5*t*h/L^2 <= 1.8% a h=0.6: sicura per il PLA.
board = [30, 12, 1.6];
standoff = 6;
module latch(h) {
    lip_z = standoff + board.z + 0.1;
    cube([1.6, 5, lip_z + 2.5]);
    // dente con rampa d'invito verso l'interno (+x)
    translate([1.6, 5, lip_z]) rotate([90, 0, 0]) linear_extrude(5) polygon([[0, 0], [h, 0], [0, 2.5]]);
}
module snap() {
    hs = [0.3, 0.45, 0.6];
    difference() {
        cube([board.x + 12, 54, 1.2]);
        for (i = [0:2]) engrave([(board.x + 12) / 2, 3.5 + i * 18, 0], 1.2, str(hs[i]), 2.5);
    }
    for (i = [0:2]) translate([6, 6 + i * 18, 1.2]) {
        // appoggi agli angoli della scheda
        for (x = [2, board.x - 2], y = [2, board.y - 2]) translate([x, y, 0]) cylinder(d = 3, h = standoff);
        // colonnine sui lati corti, faccia interna a board.x/2 + gioco
        translate([-clr_pocket - 1.6, board.y / 2 - 2.5, 0]) latch(hs[i]);
        translate([board.x + clr_pocket + 1.6, board.y / 2 - 2.5, 0]) mirror([1, 0, 0]) latch(hs[i]);
    }
}

if (part == "all" || part == "plate") plate();
if (part == "all" || part == "rail") translate([0, 95, 0]) rail();
if (part == "all" || part == "sliders") translate([35, 100, 0]) sliders();
if (part == "all" || part == "snap") translate([108, 95, 0]) snap();
if (part == "all" || part == "board") translate([35, 120, 0]) cube(board);

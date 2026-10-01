// Base: vassoio con vano elettronica + coperchio con corona di scorrimento della torretta.
// Frame mondo: z=0 = tavolo, asse di yaw in (0,0). La faccia superiore del coperchio è a z=base_h:
// lì appoggia la torretta (e lì cade la faccia della squadretta del servo base).
//
// Vassoio: torre del servo base al centro, culla ESP32 DevKit V1 (38 pin, pin in basso per i Dupont femmina)
// con ganci a scatto, sede della breadboard mezza misura, zona WAGO con asole per fascette, uscite USB.
// Coperchio: apertura centrale (i cavi scendono dai fori della torretta), labbro che guida la torretta, 4 viti M3x8.
// Stampa: vassoio e coperchio così come sono, nessun supporto (le aperture nelle pareti sono ponti corti).
// Consiglio: incolla 4 piedini in gomma o fissa la base al tavolo, il braccio sbilancia in avanti.
include <params.scad>
use <lib/parts.scad>

part = "all";  // all | tray | lid

size = [170, 150];          // ingombro esterno
r_corner = 10;
floor_h = 2;
wall = 2;
lid_t = 2.4;
tray_h = base_h - lid_t;    // altezza pareti
posts = [for (sx = [-1, 1], sy = [-1, 1]) [sx * (size.x / 2 - 7), sy * (size.y / 2 - 7)]];

// servo base: verticale, albero in (0,0), faccia squadretta a z = base_h
sg_bot = base_h - sg_horn_face;
tower_top = sg_bot + sg_tab_z;   // le linguette appoggiano qui
body_x = [-(sg_body.x - sg_shaft_x), sg_shaft_x];   // corpo lungo X, verso il retro

// ESP32 DevKit V1 38 pin: PCB 55.3 x 28.3, pin verso il basso, USB verso -X
esp = [55.3, 28.3, 1.6];
esp_at = [-size.x / 2 + wall + 3, -size.y / 2 + wall + 11.6]; // angolo -x,-y del PCB (fuori dalla colonnina)
esp_z = 30;                  // faccia inferiore del PCB: sotto restano ~6 mm per piegare i fili dei Dupont femmina
bb = [82.5, 54.5];           // breadboard mezza misura
bb_at = [-12, 10];

module rrect(s, r) offset(r = r) square([s.x - 2 * r, s.y - 2 * r], center = true);

module latch(h) {            // come nel provino: lamella 2 x 5, dente con rampa verso +x
    lip_z = esp_z + esp.z + 0.1;
    cube([2, 5, lip_z + 2.5 - floor_h]);
    translate([2, 5, lip_z - floor_h]) rotate([90, 0, 0]) linear_extrude(5) polygon([[0, 0], [h, 0], [0, 2.5]]);
}

module tray() {
    difference() {
        union() {
            difference() {
                linear_extrude(tray_h) rrect(size, r_corner);
                translate([0, 0, floor_h]) linear_extrude(tray_h) rrect(size - [2 * wall, 2 * wall], r_corner - wall);
            }
            for (p = posts) translate([p.x, p.y, 0]) cylinder(d = 9, h = tray_h);
            // torre servo: scatola aperta, il corpo pende dalle linguette
            translate([body_x[0] - 4.6, -sg_body.y / 2 - 3, 0]) cube([sg_body.x + 9.2, sg_body.y + 6, tower_top]);
            // appoggi ESP32 sui lati corti (sotto il PCB lì non ci sono pin)
            for (x = [3, esp.x - 3]) translate([esp_at.x + x, esp_at.y + esp.y / 2, 0]) cylinder(d = 6, h = esp_z);
            // ganci sui lati lunghi, a metà (tra bordo e fila di pin)
            // (rotate(90): lamella verso +y dal punto di ancoraggio -> ancoraggio fuori dal bordo del PCB)
            translate([esp_at.x + esp.x / 2 + 2.5, esp_at.y - clr_pocket - 2, floor_h]) rotate(90) latch(snap_hook);
            translate([esp_at.x + esp.x / 2 - 2.5, esp_at.y + esp.y + clr_pocket + 2, floor_h]) rotate(-90) latch(snap_hook);
            // cornice breadboard (fondo adesivo)
            translate([bb_at.x, bb_at.y, 0]) difference() {
                cube([bb.x + 2 * clr_pocket + 2.4, bb.y + 2 * clr_pocket + 2.4, floor_h + 2]);
                translate([1.2, 1.2, floor_h]) cube([bb.x + 2 * clr_pocket, bb.y + 2 * clr_pocket, 3]);
            }
        }
        // cavità della torre e asola per il cavo del servo
        translate([body_x[0] - clr_pocket, -sg_body.y / 2 - clr_pocket, floor_h]) cube([sg_body.x + 2 * clr_pocket, sg_body.y + 2 * clr_pocket, tower_top]);
        translate([body_x[0] - 6, -3, floor_h]) cube([8, 6, 8]);
        for (x = [(body_x[0] + body_x[1]) / 2 - sg_screw_pitch / 2, (body_x[0] + body_x[1]) / 2 + sg_screw_pitch / 2])
            translate([x, 0, tower_top - 8]) cylinder(d = sg_screw_d - 0.4, h = 9, $fn = 16);
        // fori autofilettanti per il coperchio
        for (p = posts) translate([p.x, p.y, floor_h]) cylinder(d = 2.5, h = tray_h);
        // USB dell'ESP32 (parete -X) e ingresso cavo alimentazione servo
        translate([-size.x / 2 - 1, esp_at.y + esp.y / 2 - 6, esp_z - 4]) cube([wall + 2, 12, 10]);
        translate([-size.x / 2 - 1, 30, 14]) rotate([0, 90, 0]) cylinder(d = 9, h = wall + 2);
        for (dy = [-6, 6]) translate([-size.x / 2 + wall + 4, 30 + dy - 1, -1]) cube([4, 2, floor_h + 2]);  // fascetta antistrappo
        // ancoraggio del fascio cavi che scende dalla torretta (la rotazione della base si fa nell'ansa sopra)
        for (y = [7, 19]) translate([-37, y, -1]) cube([4, 2, floor_h + 2]);
        // zona WAGO: 3 coppie di asole per fascette
        for (x = [25, 45, 65], dy = [-12, 12]) translate([x - 2, -45 + dy - 1, -1]) cube([4, 2, floor_h + 2]);
        // feritoie di aerazione nel fondo (zone libere: davanti alla torre e sotto la culla ESP32)
        for (x0 = [30, -74], i = [0:6]) translate([x0 + i * 6.5, -28, -1]) hull() for (y = [0, 24]) translate([0, y]) cylinder(d = 3, h = floor_h + 2, $fn = 16);
        // nome sul fronte (+X)
        translate([size.x / 2 - 0.8, 0, tray_h / 2]) rotate([90, 0, 90]) linear_extrude(2)
            text("PARALLAX", size = 9, halign = "center", valign = "center", font = "Liberation Sans:style=Bold", spacing = 1.15);
        // fori di fissaggio al tavolo
        for (p = posts) translate([p.x * 0.8, p.y * 0.62, -1]) cylinder(d = 4.2, h = floor_h + 2);
    }
}

module lid() {
    translate([0, 0, tray_h]) difference() {
        union() {
            hull() {   // smusso di 0.8 sul bordo superiore
                linear_extrude(lid_t - 0.8) rrect(size, r_corner);
                linear_extrude(lid_t) rrect(size - [1.6, 1.6], r_corner - 0.8);
            }
            // labbro di guida: entra nella gola sotto la torretta
            translate([0, 0, lid_t]) difference() {
                cylinder(r = base_lip[1], h = 1.5, $fn = 128);
                translate([0, 0, -1]) cylinder(r = base_lip[0], h = 4, $fn = 128);
            }
        }
        translate([0, 0, -1]) cylinder(r = base_hole_r, h = lid_t + 4, $fn = 128);
        for (p = posts) translate([p.x, p.y, -1]) cylinder(d = m3_d + clr_hole, h = lid_t + 2);
        // feritoie davanti e dietro, fuori dal disco della torretta (r 55)
        for (sx = [-1, 1], i = [0:3]) translate([sx * (61 + i * 4.5), 0, -1]) hull() for (y = [-30, 30]) translate([0, y]) cylinder(d = 2.4, h = lid_t + 2, $fn = 16);
    }
}

// Componenti solo visivi per le immagini di montaggio
module esp32_model() translate([esp_at.x, esp_at.y, esp_z]) {
    color("#1d5f3a") cube(esp);                                                      // PCB
    color("Silver") translate([16, 4, esp.z]) cube([25.5, 18, 3.2]);                  // modulo WROOM
    color("Silver") translate([-1.5, esp.y / 2 - 4, esp.z]) cube([6, 8, 3]);           // micro-USB verso la parete
    color("#222") for (y = [1.27, esp.y - 1.27 - 2.54]) translate([3, y - 1.27 + (y > 2 ? 0 : 0), -2.5]) cube([esp.x - 6, 2.54, 2.5]);  // file di pin
}
module breadboard_model() color("WhiteSmoke") translate([bb_at.x + 1.2 + clr_pocket, bb_at.y + 1.2 + clr_pocket, floor_h]) cube([bb.x, bb.y, 8.5]);
module wago_model() color("#d9d9d9") for (x = [22, 44], y = [-56, -38]) translate([x, y, floor_h]) cube([18, 12, 8.5]);

if (part == "all") { color("DimGray") tray(); color("Gray") lid(); }
if (part == "electronics") { color("DimGray") tray(); esp32_model(); breadboard_model(); wago_model(); }
if (part == "tray") tray();
if (part == "lid") translate([0, 0, -tray_h]) lid();

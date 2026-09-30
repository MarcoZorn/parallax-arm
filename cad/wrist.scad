// Polso livellato + pinza a cremagliera simmetrica + culla ESP32-CAM.
// Frame G (quello di questo file): origine sul perno polso W, X avanti, Y laterale (= Y mondo), Z in alto.
// La pinza resta sempre orizzontale grazie ai due parallelogrammi. TCP = centro delle dita = (xp, 0, tcp_z).
//
// Meccanismo: SG90 capovolto sul piano superiore, pignone m1 z32 (r = 16) sotto la squadretta doppia,
// due cremagliere su guide a coda di rondine (come il provino) nella piastra inferiore.
// Cremagliera A davanti al pignone -> dito A (y >= g/2) esce dalla parete anteriore;
// cremagliera B dietro -> dito B (y <= -g/2) esce dalla parete posteriore. Corsa 0..59 mm in ~106° di servo.
//
// Parti (part=...): bracket | housing | base_plate | pinion | jaw | cam_cradle | all
// Stampa senza supporti: bracket e jaw di fianco (part li esporta già ruotati), housing capovolto
// (piano superiore sul piatto), base_plate, pinion e cam_cradle come escono.
// Montaggio: servo nell'housing, pignone sull'albero (vite dal basso), base_plate con 2 viti M3x10,
// poi le due ganasce si infilano di testa nelle code di rondine (A da +y, B da -y) finché ingranano.
include <params.scad>
use <lib/parts.scad>

part = "all";
g = 30;   // apertura per l'anteprima dell'assieme (mm)

m = 1;                         // modulo
zp = 32;                       // denti pignone
rp = m * zp / 2;               // 16: raggio primitivo
xp = 42;                       // asse pignone = x del TCP
zd = 12;                       // faccia superiore del piano superiore
deck_t = 3;
horn_z = zd - (sg_horn_face - sg_tab_z - sg_tab_t);   // faccia squadretta (sotto il piano)
disc_t = 2.4;                  // disco porta-squadretta sopra il pignone
face_w = 6;                    // larghezza di fascia del pignone
gear_top = horn_z - disc_t;
gear_bot = gear_top - face_w;
rack_h = 6;
rack_top = gear_top - 0.3;     // la cremagliera passa sotto il disco (r 17)
rack_bot = rack_top - rack_h;
rack_in = rp - m;              // punta dei denti della cremagliera (dal centro pignone)
rack_out = rp + 1.25 * m + 10;     // faccia esterna cremagliera (27.25)
x_back = 12;                   // retro del piano superiore (flangia della staffa)
dt_top = 8; dt_h = 4;          // coda di rondine: uguale al provino
dt_bot = dt_top + 2 * dt_h / tan(60);
plate_t = dt_h + 1.2;
plate_top = rack_bot;
plate_bot = plate_top - plate_t;
y_half = 36;                   // corsa cremagliere entro +-35
tab = [3.5, 4];                // linguetta dito: altezza z, spessore y
tab_z = rack_bot + 1.3;
stem_x = rack_out;             // il gambo aderisce alla faccia esterna della cremagliera
stem_t = 3.5;
pad = [24, 16];                // dito: lunghezza x (dal centro verso il lato opposto) e altezza z
pad_top = plate_bot - 2;
tcp_z = pad_top - pad[1] / 2;
rack_len = 40;
echo(str("TCP pinza: L3 = ", xp, "  tcp_dz = ", tcp_z, "   (rig.json / docs/03)"));

// ---------------- ingranaggi ----------------
function inv(a) = tan(a) - a * PI / 180;
function invpt(rb, t) = rb * [cos(t) + (t * PI / 180) * sin(t), sin(t) - (t * PI / 180) * cos(t)];
module gear2d(z, m, pa = 20, bl = 0.15) {
    r = m * z / 2; rb = r * cos(pa); ra = r + m; rf = r - 1.25 * m;
    tmax = sqrt(pow(ra / rb, 2) - 1) * 180 / PI;
    half = 90 / z - (bl / 2) / r * 180 / PI + inv(pa) * 180 / PI;   // mezzo spessore angolare al cerchio base
    flank = [for (i = [0:8]) let(t = tmax * i / 8, p = invpt(rb, t)) p];
    union() {
        circle(r = rf, $fn = z * 4);
        for (k = [0:z - 1]) rotate(k * 360 / z) polygon(concat(
            [[rf * cos(-half), rf * sin(-half)]],
            [for (p = flank) [p.x * cos(-half) - p.y * sin(-half), p.x * sin(-half) + p.y * cos(-half)]],
            [for (i = [8:-1:0]) let(p = flank[i]) [p.x * cos(half) + p.y * sin(half), p.x * sin(half) - p.y * cos(half)]],
            [[rf * cos(half), rf * sin(half)]]));
    }
}
// Dentatura di cremagliera lungo Y, denti verso -X, linea primitiva a x = 0.
module rack2d(len, m, pa = 20, bl = 0.15) {
    p = PI * m;
    for (i = [0:ceil(len / p)]) translate([0, i * p - len / 2]) polygon([
        [-m, -p / 4 + m * tan(pa) + bl / 2], [-m, p / 4 - m * tan(pa) - bl / 2],
        [1.25 * m, p / 4 + 1.25 * m * tan(pa) - bl / 2 + 0.01], [1.25 * m, -p / 4 - 1.25 * m * tan(pa) + bl / 2 - 0.01]]);
}

// ---------------- parti ----------------
module pinion() difference() {
    union() {
        linear_extrude(face_w) gear2d(zp, m);
        translate([0, 0, face_w]) cylinder(r = rp + m, h = disc_t, $fn = 96);
    }
    translate([0, 0, face_w + disc_t]) mirror([0, 0, 1]) horn_pocket(clr_pocket, 20);
    translate([0, 0, -1]) cylinder(d = 5.5, h = face_w + disc_t - horn_t - 0.2 - 1.2 + 1);  // testa vite dal basso
}

// Cremagliera nel suo frame: linea primitiva a x=0, dietro (+x) il corpo, sotto la coda di rondine, a +y la linguetta.
module rack() {
    body = rack_out - rp;   // dalla linea primitiva alla faccia esterna
    difference() {
        union() {
            translate([0, 0, 0]) linear_extrude(rack_h) {
                translate([1.25 * m, -rack_len / 2]) square([body - 1.25 * m, rack_len]);
                intersection() { rack2d(rack_len, m); translate([-2, -rack_len / 2]) square([4, rack_len]); }
            }
            // coda di rondine sotto, centrata nel corpo
            // stretta in alto (attacco al corpo), larga in basso: si incastra nella gola della base_plate
            translate([rp + (rack_out - rp) / 2 + 0.6 - rp, rack_len / 2, 0]) rotate([90, 0, 0]) linear_extrude(rack_len)
                translate([0, -dt_h]) offset(delta = -clr_slide) polygon([[-dt_bot / 2, 0], [dt_bot / 2, 0], [dt_top / 2, dt_h], [-dt_top / 2, dt_h]]);
        }
    }
}

// Dito: gambo verticale sulla faccia esterna della cremagliera + paletta che torna verso il centro. Frame: come rack().
module finger() {
    body = rack_out - rp;
    x0 = body + (stem_x - rack_out);   // faccia interna gambo
    // gambo: dalla linguetta fino al fondo della paletta
    translate([x0, rack_len / 2 - tab[1], pad_top - pad[1] - rack_bot]) cube([stem_t, tab[1], rack_h - pad_top + pad[1] + rack_bot]);
    // paletta: da x0+stem_t fino oltre l'asse del pignone (x = -rp - 12 nel frame cremagliera)
    translate([-rp - 12, rack_len / 2 - tab[1], pad_top - pad[1] - rack_bot]) cube([x0 + stem_t + rp + 12, tab[1], pad[1]]);
}

// Posa di cremagliera+dito nel frame G per apertura g: A davanti (+x), B dietro (ruotata di 180°).
// La faccia interna del dito (y = rack_len/2 - tab nel frame cremagliera) va a y = g/2; B è A ruotata di 180°.
module rack_pose(side, g) translate([xp, 0, rack_bot]) rotate(side > 0 ? 0 : 180)
    translate([rp, g / 2 - rack_len / 2 + tab[1], 0]) children();
module jaw() { rack(); finger(); }

// Piano superiore ridotto all'indispensabile: flangia staffa, SG90, culla camera, 2 colonnine verso la piastra.
// Niente pareti: le code di rondine guidano già le cremagliere in tutte le direzioni tranne lo scorrimento.
posts = [[xp, -22], [xp, 22]];     // fuori dal disco del pignone (r 17) e dal corpo del servo
module deck_outline() hull() {
    translate([x_back, -7.5]) square([12, 12]);
    translate([xp - 8, -23.5]) square([16, 36]);
    for (p = posts) translate(p) circle(r = 5);
    translate([xp + 8, -cam.x / 2 - 3]) square([10, cam.x + 6]);
}
module housing() {
    difference() {
        union() {
            translate([0, 0, zd - deck_t]) linear_extrude(deck_t) deck_outline();
            for (p = posts) translate([p.x, p.y, plate_top]) cylinder(d = 7, h = zd - deck_t - plate_top + 0.01);
            translate([x_back, -7, zd - deck_t - 3]) cube([12, 11, 3]);   // rinforzo per i dadi della staffa
        }
        // finestra SG90 capovolto: asse albero in (xp, 0), corpo lungo Y
        translate([xp - sg_body.y / 2 - clr_pocket, -(sg_body.x - sg_shaft_x) - clr_pocket, zd - deck_t - 1])
            cube([sg_body.y + 2 * clr_pocket, sg_body.x + 2 * clr_pocket, deck_t + 2]);
        for (y = [-(sg_body.x - sg_shaft_x) / 2 + sg_shaft_x / 2 - sg_screw_pitch / 2, -(sg_body.x - sg_shaft_x) / 2 + sg_shaft_x / 2 + sg_screw_pitch / 2])
            translate([xp, y, zd - deck_t - 1]) cylinder(d = sg_screw_d - 0.4, h = deck_t + 2, $fn = 16);
        for (p = posts) translate([p.x, p.y, plate_top - 1]) cylinder(d = 2.5, h = 12);   // autofilettanti M3 dal basso
        // viti staffa: 2 x M3 verticali con dado sotto
        for (x = [x_back + 3.5, x_back + 8.5])
            translate([x, -1.5, zd - deck_t - 3 - 1]) { cylinder(d = m3_d + clr_hole, h = 10); rotate(30) hex_pocket(h = 3.6); }
        // viti della culla camera
        for (y = [-cam.x / 2, cam.x / 2]) translate([xp + 13, y, zd - deck_t - 1]) cylinder(d = 2.5, h = deck_t + 2);
    }
}

// Piastra inferiore: due binari a coda di rondine uniti da due traverse sotto le colonnine.
rail_x = rp + (rack_out - rp) / 2 + 0.6;   // centro della gola dal centro pignone
rail_w = dt_bot + 2.4;
module base_plate() {
    difference() {
        union() {
            for (s = [-1, 1]) translate([xp + s * rail_x - rail_w / 2, -y_half - 2.5, plate_bot]) cube([rail_w, 2 * y_half + 5, plate_t]);
            for (p = posts) translate([xp - rail_x, p.y - 4, plate_bot]) cube([2 * rail_x, 8, plate_t]);
        }
        for (s = [-1, 1]) translate([xp + s * rail_x, y_half + 4, plate_top - dt_h]) rotate([90, 0, 0])
            linear_extrude(2 * y_half + 8) { polygon([[-dt_bot / 2, 0], [dt_bot / 2, 0], [dt_top / 2, dt_h], [-dt_top / 2, dt_h]]); translate([-dt_top / 2, dt_h - 0.01]) square([dt_top, 1]); }
        for (p = posts) translate([p.x, p.y, plate_bot - 1]) { cylinder(d = m3_d + clr_hole, h = plate_t + 2); cylinder(d = 6, h = 3.5); }
    }
}

// Staffa: mozzo sul perno W, leva V (piano y_link) verso la biella 2, braccio che si avvita sul piano superiore.
module bracket() {
    difference() {
        union() {
            translate([0, y_bracket[1], 0]) rotate([90, 0, 0]) linear_extrude(y_bracket[1] - y_bracket[0]) {
                circle(r = 7);
                hull() { circle(r = 7); translate([x_back - 7, zd - 4]) square([7, 5]); }   // sovrapposto alla flangia: niente spigoli condivisi
            }
            // flangia sul piano superiore
            translate([x_back - 1, y_bracket[0], zd]) cube([12, y_bracket[1] - y_bracket[0], 4]);
            // leva V
            translate([0, y_link[1], 0]) rotate([90, 0, 0]) linear_extrude(y_link[1] - y_link[0])
                hull() { circle(r = 7); translate([0, lev2_r]) circle(r = 5); }
        }
        translate([0, 10, 0]) rotate([90, 0, 0]) cylinder(d = m3_d + clr_pivot, h = 30);        // W: ruota sulla vite
        translate([0, 10, lev2_r]) rotate([90, 0, 0]) cylinder(d = m3_d + clr_hole, h = 30);   // V
        for (x = [x_back + 3.5, x_back + 8.5]) translate([x, -1.5, zd - 1]) cylinder(d = m3_d + clr_hole, h = 10);
    }
}

// Culla ESP32-CAM (27 x 40.5 x ~4.5 con fotocamera): in piedi sul davanti, inclinata di 25° verso le dita.
cam = [27, 40.5, 1.6];
module cam_cradle() {
    difference() {
        union() {
            translate([xp + 8, -cam.x / 2 - 3, zd]) cube([10, cam.x + 6, 3]);   // piede sul piano
            translate([xp + 13, 0, zd + 3]) rotate([0, 25, 0]) translate([-3, -cam.x / 2 - 3, 0]) difference() {
                cube([6, cam.x + 6, 22]);
                translate([2, 3 - clr_pocket, 4]) cube([cam.z + 2 * clr_pocket, cam.x + 2 * clr_pocket, 30]);   // fessura della scheda
            }
        }
        for (y = [-cam.x / 2, cam.x / 2]) translate([xp + 13, y, zd - 1]) cylinder(d = m3_d + clr_hole, h = 6);
    }
}

module wrist_assembly(g = g, lite = false) {
    color("Silver") bracket();
    color("SteelBlue") housing();
    color("SteelBlue") base_plate();
    color("Orange") translate([xp, 0, gear_bot]) if (lite) cylinder(r = rp + m, h = face_w + disc_t); else pinion();
    for (s = [-1, 1]) color("Gold") rack_pose(s, g) jaw();
    color("DimGray") cam_cradle();
}

if (part == "all") wrist_assembly();
if (part == "bracket") rotate([90, 0, 0]) translate([0, -y_bracket[0], 0]) bracket();
if (part == "housing") mirror([0, 0, 1]) translate([0, 0, -zd]) housing();       // capovolto: piano sul piatto
if (part == "base_plate") translate([0, 0, -plate_bot]) base_plate();
if (part == "pinion") pinion();
if (part == "jaw") rotate([-90, 0, 0]) translate([0, -rack_len / 2, 0]) jaw();
if (part == "cam_cradle") translate([0, 0, -zd]) cam_cradle();
// SG90 capovolto sul piano (visivo): corpo lungo +Y? no, verso -Y come la finestra; albero giù in (xp, 0)
module wrist_servo() multmatrix([[0, 1, 0, xp], [1, 0, 0, 0], [0, 0, -1, zd + sg_tab_z + sg_tab_t], [0, 0, 0, 1]]) sg90_model();

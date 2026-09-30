// Tasche e sedi riusate da tutte le parti.
include <../params.scad>

// Sagoma della squadretta doppia SG90, lungo X, allargata di c per lato.
module horn_outline(c = clr_pocket) {
    reach = horn_len / 2 - horn_tip_d / 2;
    hull() {
        circle(d = horn_hub_d + 2 * c);
        for (s = [-1, 1]) translate([s * reach, 0]) circle(d = horn_tip_d + 2 * c);
    }
}

// Tasca squadretta sulla faccia z=0 + foro vite centrale passante.
module horn_pocket(c = clr_pocket, through = 20) {
    translate([0, 0, -0.01]) linear_extrude(horn_t + 0.2) horn_outline(c);
    translate([0, 0, -1]) cylinder(d = horn_screw_d + clr_hole, h = through);
}

// Sede esagonale per dado, chiave af, allargata di c per lato.
module hex_pocket(af = m3_nut_af, h = m3_nylock_h, c = clr_pocket) {
    cylinder(d = (af + 2 * c) / cos(30), h = h, $fn = 6);
}

// Scritta incisa (profondità 0.6) centrata in p sulla faccia a quota z.
module engrave(p, z, s, size = 3) {
    translate([p[0], p[1], z - 0.6]) linear_extrude(1)
        text(s, size = size, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
}

// Sede a stadio per un piombo a oliva, asse lungo X, centrata; o = offset (parete/coperchio).
module lead_outline(o = 0) offset(r = o) hull()
    for (s = [-1, 1]) translate([s * (lead_pocket[0] - lead_pocket[1]) / 2, 0]) circle(d = lead_pocket[1]);

// SG90 solo visivo (twin/anteprime). Frame servo: fondo a z=0, albero in (0,0) verso +z, corpo lungo X verso -X.
module sg90_model() {
    x0 = -(sg_body.x - sg_shaft_x);
    color("#1f4fa8") {
        translate([x0, -sg_body.y / 2, 0]) cube(sg_body);
        translate([x0 - (sg_tab_len - sg_body.x) / 2, -sg_body.y / 2, sg_tab_z]) cube([sg_tab_len, sg_body.y, sg_tab_t]);
        cylinder(d = sg_boss_d, h = sg_body.z + sg_boss_h);
    }
    color("White") cylinder(d = 4.6, h = sg_horn_face - horn_t);
}

// Percorsi cavi (solo anteprima e misura lunghezze). Frame torretta come assembly.scad.
// Il fascio pinza+camera: servo pinza -> staffa (fascetta sul braccetto) -> faccia esterna piastra L
// (2 fascette nelle asole) -> ansa fuori dal gomito -> canalina del braccio (lato servo) -> spazio tra squadretta
// e guancia sinistra -> asola della guancia -> giù fuori dalla guancia -> asola del pavimento -> base.
include <params.scad>

function u(a) = [cos(a), 0, sin(a)];
function Y(p, y) = [p.x, y, p.z];

// punti del fascio pinza per una posa (th2, phi): y laterale fissato dai piani delle parti
function grip_path(th2, phi, xp = 42, zd = 12) = let(
    O = [0, 0, sh_h], E = O + L1 * u(th2), W = E + L2 * u(phi), ye = y_fore_l[0] - 1.8, ya = y_arm - 1.5)
    [W + [xp, -18, zd + 15], W + [20, -2, zd + 5], W + [4, -2, 6], Y(W + 8 * u(phi + 180), ye),
     Y(E + 55 * u(phi), ye), Y(E + 22 * u(phi), ye), Y(E, y_arm - 6), Y(E + 9 * u(th2 + 180), ya),
     Y(O + 18 * u(th2), ya), [-22, -y_wall + 4, sh_h], [-22, -y_wall - cheek_t - 2, sh_h],
     [-12, -y_wall - cheek_t - 4, 12], [-8, -42, floor_t + 2], [-8, -42, -20]];

// cavo di un servo di guancia: esce dal fondo del corpo (in basso) e scende all'asola del pavimento
function cheek_path(side) = [[0, side * (y_wall + cheek_t + 16), sh_h - (sg_body.x - sg_shaft_x) + 2],
    [-6, side * 43, 20], [-8, side * 42, floor_t + 2], [-8, side * 42, -20]];

function plen(p) = len(p) < 2 ? 0 : [for (i = [0:len(p) - 2]) norm(p[i + 1] - p[i])] * [for (i = [0:len(p) - 2]) 1];

module tube(p, d = 3) for (i = [0:len(p) - 2]) hull() { translate(p[i]) sphere(d = d, $fn = 12); translate(p[i + 1]) sphere(d = d, $fn = 12); }

module cables(th2, phi) {
    color("Red") tube(grip_path(th2, phi), 4);
    color("#202020") { tube(cheek_path(-1)); tube(cheek_path(1)); }
}

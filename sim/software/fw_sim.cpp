// Harness nativo del planner del firmware (motion.cpp compilato così com'è).
// stdin, per scenario:
//   S q0 q1 q2 q3 N        posa iniziale, N tick a 50 Hz
//   M k f t0 t1 t2 t3      al tick k: move (validato come in main.cpp)
//   T k | H k              al tick k: stop | halt (estop)
//   E                      esegue
// stdout: "S" poi una riga per tick "q0 q1 q2 q3 v0 v1 v2 v3 moving", "R k motivo" per i move rifiutati.
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <vector>
#include "motion.h"

struct Ev { int k; char c; float f, t[NJ]; };

int main() {
    Cal cal[NJ];
    cal_default(cal);
    char tag[4];
    float q0[NJ];
    int N = 0;
    std::vector<Ev> ev;
    const float DT = CTRL_MS / 1000.0f;
    while (scanf("%3s", tag) == 1) {
        if (tag[0] == 'S') {
            for (int j = 0; j < NJ; j++) scanf("%f", &q0[j]);
            scanf("%d", &N);
            ev.clear();
        } else if (tag[0] == 'M') {
            Ev e = {};
            e.c = 'M';
            scanf("%d %f %f %f %f %f", &e.k, &e.f, &e.t[0], &e.t[1], &e.t[2], &e.t[3]);
            ev.push_back(e);
        } else if (tag[0] == 'T' || tag[0] == 'H') {
            Ev e = {};
            e.c = tag[0];
            scanf("%d", &e.k);
            ev.push_back(e);
        } else if (tag[0] == 'E') {
            Planner p;
            p.reset(q0);
            puts("S");
            char err[96];
            for (int k = 0; k < N; k++) {
                for (auto& e : ev) {
                    if (e.k != k) continue;
                    if (e.c == 'M') {
                        if (!(e.f > 0 && e.f <= 1)) printf("R %d v\n", k);
                        else if (!check_target(e.t, cal, err, sizeof err)) printf("R %d %s\n", k, err);
                        else p.move(e.t, e.f);
                    } else if (e.c == 'T') p.stop();
                    else p.halt();
                }
                p.step(DT, cal);
                printf("%.9g %.9g %.9g %.9g %.9g %.9g %.9g %.9g %d\n", p.q[0], p.q[1], p.q[2], p.q[3], p.v[0], p.v[1],
                       p.v[2], p.v[3], p.moving() ? 1 : 0);
            }
        }
    }
    return 0;
}

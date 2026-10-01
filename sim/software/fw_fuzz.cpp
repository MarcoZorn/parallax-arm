// Punto 4 (firmware): fuzz di check_target, check_cal, q_to_us/us_to_q e robustezza del Planner
// con input estremi (NaN, inf, enormi, denormali, k=0, min>max, tarature casuali). Esce con 1 se una proprietà cade.
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <random>
#include "motion.h"

static int fails = 0;
static long checks = 0;
#define CHECK(c, ...)                                     \
    do {                                                  \
        checks++;                                         \
        if (!(c) && fails++ < 20) {                       \
            printf("FALLITO %s:%d: ", __FILE__, __LINE__); \
            printf(__VA_ARGS__);                          \
            puts("");                                     \
        }                                                 \
    } while (0)

static std::mt19937 rng(20261001);
static float U(float a, float b) { return std::uniform_real_distribution<float>(a, b)(rng); }
static const float SPECIAL[] = {NAN, INFINITY, -INFINITY, 3.4e38f, -3.4e38f, 1e-45f, -1e-45f, 0.0f, -0.0f, 1e30f, -1e30f, 1e-30f};
static float weird() { return rng() % 3 ? U(-1e4f, 1e4f) : SPECIAL[rng() % (sizeof SPECIAL / sizeof *SPECIAL)]; }

int main() {
    Cal def[NJ];
    cal_default(def);
    char err[96];
    const float DT = CTRL_MS / 1000.0f;

    // check_target: mai accettato un q fuori limiti/vincolo (tolleranza 1e-3) o non finito; err sempre terminato
    long acc = 0;
    for (int i = 0; i < 2000000; i++) {
        float q[NJ];
        for (int j = 0; j < NJ; j++) q[j] = rng() % 4 ? U(def[j].min - 5, def[j].max + 5) : weird();
        size_t n = 1 + rng() % sizeof err;
        memset(err, 'x', sizeof err);
        bool ok = check_target(q, def, err, n);
        CHECK(ok || memchr(err, 0, n), "err non terminato");
        if (!ok) continue;
        acc++;
        for (int j = 0; j < NJ; j++) CHECK(isfinite(q[j]) && q[j] >= def[j].min - 1e-3f && q[j] <= def[j].max + 1e-3f, "accettato q%d=%g", j, q[j]);
        float e = q[1] - q[2];
        CHECK(e >= PAR_MIN - 1e-3f && e <= PAR_MAX + 1e-3f, "accettato e=%g", e);
    }
    printf("check_target: 2e6 casi, %ld accettati\n", acc);

    // check_cal: rifiuta NaN/inf, k=0, |k|<1, ref_us fuori [500,2500], min>=max; non si pronuncia sui valori enormi
    long calOk = 0, calHuge = 0;
    for (int i = 0; i < 500000; i++) {
        Cal c[NJ];
        cal_default(c);
        int j = rng() % NJ;
        float* f = &c[j].ref_us + rng() % 5;
        *f = weird();
        if (rng() % 2) c[j].k = rng() % 2 ? 0 : U(-1.5f, 1.5f);
        bool ok = check_cal(c, err, sizeof err);
        const Cal& x = c[j];
        bool sane = isfinite(x.ref_us) && isfinite(x.k) && isfinite(x.q_ref) && isfinite(x.min) && isfinite(x.max) && x.ref_us >= 500 &&
                    x.ref_us <= 2500 && fabsf(x.k) >= 1 && x.min < x.max;
        CHECK(ok == sane, "check_cal giunto %d: ok=%d atteso=%d", j, ok, sane);
        if (ok) {
            calOk++;
            calHuge += fabsf(x.min) > 1000 || fabsf(x.max) > 1000 || fabsf(x.q_ref) > 1000;
            // q_to_us sempre nel clamp per q finito, anche con taratura estrema ma accettata
            for (int t = 0; t < 8; t++) {
                float q = rng() % 2 ? U(-1e6f, 1e6f) : weird();
                float us = q_to_us(x, q);
                if (isfinite(q)) CHECK(us >= US_MIN && us <= US_MAX, "q_to_us(%g)=%g", q, us);
            }
        }
    }
    printf("check_cal: 5e5 casi, %ld accettati, %ld con valori enormi (|min|,|max| o |q_ref| > 1000) accettati\n", calOk, calHuge);

    // q_to_us / us_to_q: andata e ritorno nel campo utile, NaN in ingresso
    float worst = 0;
    for (int i = 0; i < 1000000; i++) {
        Cal c = {U(500, 2500), (rng() % 2 ? 1 : -1) * U(1, 50), U(-180, 180), 0, 0};
        float us = U(US_MIN, US_MAX), q = us_to_q(c, us), back = q_to_us(c, q);
        worst = fmaxf(worst, fabsf(back - us));
    }
    printf("q_to_us(us_to_q(us)): errore max %.4f us su 1e6 casi\n", worst);
    CHECK(worst < 0.01f, "andata e ritorno %g us", worst);
    printf("q_to_us(NaN) = %g (NaN passa il clamp: oggi irraggiungibile, il planner non produce NaN)\n", q_to_us(def[0], NAN));
    printf("us_to_q(k=0) = %g (solo con taratura non validata)\n", us_to_q(Cal{1500, 0, 0, -90, 90}, 1600));

    // Planner: fattori f estremi, partenze fuori limiti (dopo raw), tarature casuali valide.
    // Proprietà: q sempre finito; dentro limiti e vincolo (+0.01) se ci partiva; mai peggiora se partiva fuori.
    long steps = 0, stalls = 0;
    const float FS[] = {1, 0.5f, 1e-3f, 1e-30f, 1e-45f, 1.0f};
    for (int s = 0; s < 20000; s++) {
        Cal c[NJ];
        cal_default(c);
        if (s % 2)
            for (int j = 0; j < NJ; j++) {  // limiti più stretti, k e verso casuali
                float a = U(def[j].min, def[j].max), b = U(def[j].min, def[j].max);
                c[j].min = fminf(a, b), c[j].max = fmaxf(a, b) + 1;
                c[j].k = (rng() % 2 ? 1 : -1) * U(5, 20);
            }
        float q0[NJ], t[NJ];
        bool inside = rng() % 4 != 0;
        for (int it = 0;; it++) {
            for (int j = 0; j < NJ; j++) q0[j] = inside ? U(c[j].min, c[j].max) : U(def[j].min - 20, def[j].max + 20);
            if (!inside || check_target(q0, c, err, sizeof err) || it > 1000) break;
        }
        int it = 0;
        do
            for (int j = 0; j < NJ; j++) t[j] = U(c[j].min, c[j].max);
        while (!check_target(t, c, err, sizeof err) && ++it < 1000);
        if (it >= 1000) continue;
        bool in0 = check_target(q0, c, err, sizeof err);
        Planner p;
        p.reset(q0);
        float f = FS[rng() % 6];
        p.move(t, f);
        int k = 0, K = f < 1e-2f ? 200 : 3000;
        for (; k < K && p.moving(); k++) {
            if (k == 37 && rng() % 3 == 0) p.stop();
            if (k == 53 && rng() % 3 == 0) p.move(t, 1);
            float qb[NJ];
            memcpy(qb, p.q, sizeof qb);
            p.step(DT, c);
            steps++;
            for (int j = 0; j < NJ; j++) {
                CHECK(isfinite(p.q[j]) && isfinite(p.v[j]), "q/v non finiti (f=%g)", f);
                if (in0) CHECK(p.q[j] >= c[j].min - 0.0101f && p.q[j] <= c[j].max + 0.0101f, "fuori limiti q%d=%g [%g,%g]", j, p.q[j], c[j].min, c[j].max);
                else CHECK(!(p.q[j] < c[j].min - 0.0101f && p.q[j] < qb[j]) && !(p.q[j] > c[j].max + 0.0101f && p.q[j] > qb[j]), "peggiora fuori limiti q%d", j);
            }
            float e = p.q[1] - p.q[2], eb = qb[1] - qb[2];
            if (in0) CHECK(e >= PAR_MIN - 0.0101f && e <= PAR_MAX + 0.0101f, "fuori vincolo e=%g", e);
            else CHECK(!(e < PAR_MIN - 0.0101f && e < eb) && !(e > PAR_MAX + 0.0101f && e > eb), "peggiora fuori vincolo e=%g", e);
        }
        if (f >= 1e-2f && p.moving()) stalls++;
    }
    printf("planner: %ld tick su 2e4 scenari, %ld non arrivati in 60 s con f>=0.01\n", steps, stalls);
    CHECK(stalls == 0, "planner fermo a metà");
    printf("%ld controlli, %d falliti\n", checks, fails);
    return fails ? 1 : 0;
}

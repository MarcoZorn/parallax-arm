// Test nativi della logica di moto: pio test -e native
#include <unity.h>
#include <math.h>
#include <string.h>
#include "motion.h"

static Cal cal[NJ];
static char err[96];
static const float DT = CTRL_MS / 1000.0f;
// Tolleranza sull'accelerazione misurata dalle posizioni: l'ultimo tick si ferma esattamente sul target
// e percorre meno di v*dt, la differenza finita arriva fino a 1.125 * amax.
static const float A_TOL = 1.15f;

void setUp() { cal_default(cal); }
void tearDown() {}

static void test_mapping() {
    TEST_ASSERT_FLOAT_WITHIN(1e-3, 1500, q_to_us(cal[0], 0));
    TEST_ASSERT_FLOAT_WITHIN(1e-3, 1500, q_to_us(cal[1], 90));
    TEST_ASSERT_FLOAT_WITHIN(1e-3, 1500, q_to_us(cal[3], 29.5f));
    TEST_ASSERT_FLOAT_WITHIN(1e-2, 1500 + 11.11f * 45, q_to_us(cal[0], 45));
    TEST_ASSERT_FLOAT_WITHIN(1e-2, 1500 - 19.89f * 10, q_to_us(cal[3], 19.5f));
    TEST_ASSERT_EQUAL_FLOAT(2500, q_to_us(cal[0], 100));  // clamp
    TEST_ASSERT_EQUAL_FLOAT(500, q_to_us(cal[0], -100));
    Cal inv = cal[2];
    inv.k = -inv.k;  // verso invertito
    TEST_ASSERT_FLOAT_WITHIN(1e-2, 1500 - 11.11f * 30, q_to_us(inv, 30));
    TEST_ASSERT_FLOAT_WITHIN(1e-3, 30, us_to_q(inv, q_to_us(inv, 30)));
}

static void test_limits() {
    float ok[NJ] = {0, 90, 0, 30};
    TEST_ASSERT_TRUE(check_target(ok, cal, err, sizeof err));
    float bad_q1[NJ] = {95, 90, 0, 30};
    TEST_ASSERT_FALSE(check_target(bad_q1, cal, err, sizeof err));
    TEST_ASSERT_NOT_NULL(strstr(err, "fuori limiti: q1"));
    float bad_g[NJ] = {0, 90, 0, 60};
    TEST_ASSERT_FALSE(check_target(bad_g, cal, err, sizeof err));
    float bad_phi[NJ] = {0, 90, 72, 30};  // phi oltre 70
    TEST_ASSERT_FALSE(check_target(bad_phi, cal, err, sizeof err));
    TEST_ASSERT_NOT_NULL(strstr(err, "fuori limiti: phi"));
    float bad_nan[NJ] = {0, NAN, 0, 30};
    TEST_ASSERT_FALSE(check_target(bad_nan, cal, err, sizeof err));
}

static void test_constraint() {
    float low[NJ] = {0, 30, 18, 30};  // th2-phi = 12, entrambi nei limiti
    TEST_ASSERT_FALSE(check_target(low, cal, err, sizeof err));
    TEST_ASSERT_EQUAL_STRING("fuori vincolo: th2-phi=12", err);
    float high[NJ] = {0, 150, -5, 30};  // 155
    TEST_ASSERT_FALSE(check_target(high, cal, err, sizeof err));
    TEST_ASSERT_EQUAL_STRING("fuori vincolo: th2-phi=155", err);
    float edge[NJ] = {0, 40, 20, 30};  // 20, al bordo: ammesso
    TEST_ASSERT_TRUE(check_target(edge, cal, err, sizeof err));
    float edge_hi[NJ] = {0, 140, -10, 30};  // 150, al bordo: ammesso
    TEST_ASSERT_TRUE(check_target(edge_hi, cal, err, sizeof err));
}

struct Run {
    int ticks;
    int arrive[NJ];  // tick da cui il giunto sta sul target
    float vpeak[NJ], apeak[NJ];
};

// simula fino a fermo; opzionale retarget al tick `at`
static Run simulate(Planner& p, const float* retarget = nullptr, int at = -1, float f2 = 1) {
    Run r = {};
    float prev[NJ], vprev[NJ];
    memcpy(prev, p.q, sizeof prev);
    memcpy(vprev, p.v, sizeof vprev);  // si può partire in moto (test_stop)
    for (int j = 0; j < NJ; j++) r.arrive[j] = -1;
    for (int k = 1; k < 2000; k++) {
        if (k == at) p.move(retarget, f2);
        p.step(DT, cal);
        for (int j = 0; j < NJ; j++) {
            float v = (p.q[j] - prev[j]) / DT, a = fabsf(v - vprev[j]) / DT;
            if (fabsf(v) > r.vpeak[j]) r.vpeak[j] = fabsf(v);
            if (a > r.apeak[j]) r.apeak[j] = a;
            if (p.q[j] == p.target[j] && r.arrive[j] < 0) r.arrive[j] = k;
            if (p.q[j] != p.target[j]) r.arrive[j] = -1;
            prev[j] = p.q[j], vprev[j] = v;
        }
        float e = p.q[1] - p.q[2];
        TEST_ASSERT_TRUE(e >= PAR_MIN - 1e-3 && e <= PAR_MAX + 1e-3);
        if (!p.moving() && k > at) {
            r.ticks = k;
            return r;
        }
    }
    TEST_FAIL_MESSAGE("il planner non si ferma");
    return r;
}

static void check_run(const Run& r, float f, float a_scale) {
    for (int j = 0; j < NJ; j++) {
        TEST_ASSERT_TRUE_MESSAGE(r.vpeak[j] <= VMAX[j] * f * 1.001f, "vmax superata");
        TEST_ASSERT_TRUE_MESSAGE(r.apeak[j] <= AMAX[j] * a_scale * A_TOL, "amax superata");
    }
}

static void test_planner_sync() {
    const float home[NJ] = {0, 90, 0, 30}, tgt[NJ] = {60, 130, 40, 10};
    for (float f : (const float[]){1.0f, 0.5f, 0.2f}) {
        Planner p;
        p.reset(home);
        p.move(tgt, f);
        Run r = simulate(p);
        for (int j = 0; j < NJ; j++) TEST_ASSERT_EQUAL_FLOAT(tgt[j], p.q[j]);  // esatto
        int lo = r.arrive[0], hi = r.arrive[0];
        for (int j = 1; j < NJ; j++) lo = r.arrive[j] < lo ? r.arrive[j] : lo, hi = r.arrive[j] > hi ? r.arrive[j] : hi;
        TEST_ASSERT_TRUE_MESSAGE(hi - lo <= 1, "i giunti non arrivano insieme");
        // q1 e th2/phi percorrono 60 e 40°: il più lento (q1) deve toccare vmax*f se il moto è lungo abbastanza
        check_run(r, f, f);
        // durata vicina al trapezio ideale del giunto guida (q1: 60°)
        float V = VMAX[0] * f, A = AMAX[0] * f, D = 60;
        float T = D / V + V / A;
        if (V * V / A > D) T = 2 * sqrtf(D / A);
        TEST_ASSERT_FLOAT_WITHIN(0.1f, T, r.ticks * DT);
    }
}

static void test_retarget() {
    const float home[NJ] = {0, 90, 0, 30}, a[NJ] = {80, 150, 60, 55}, b[NJ] = {-70, 40, -30, 5};
    Planner p;
    p.reset(home);
    p.move(a, 1);
    Run r = simulate(p, b, 40, 1);  // a metà moto, a piena velocità verso a
    for (int j = 0; j < NJ; j++) TEST_ASSERT_EQUAL_FLOAT(b[j], p.q[j]);
    check_run(r, 1, 1);  // niente salti: velocità e accelerazione dalle posizioni restano nei limiti
}

static void test_stop() {
    const float home[NJ] = {0, 90, 0, 30}, a[NJ] = {80, 150, 60, 55};
    Planner p;
    p.reset(home);
    p.move(a, 1);
    for (int k = 0; k < 30; k++) p.step(DT, cal);
    p.stop();
    Run r = simulate(p);
    check_run(r, 1, 1);
    TEST_ASSERT_FALSE(p.moving());
    for (int j = 0; j < NJ; j++) TEST_ASSERT_EQUAL_FLOAT(p.q[j], p.target[j]);  // tiene la posizione
    TEST_ASSERT_TRUE(p.q[0] > 0 && p.q[0] < 80);  // fermo prima del target, sulla stessa retta
}

int main() {
    UNITY_BEGIN();
    RUN_TEST(test_mapping);
    RUN_TEST(test_limits);
    RUN_TEST(test_constraint);
    RUN_TEST(test_planner_sync);
    RUN_TEST(test_retarget);
    RUN_TEST(test_stop);
    return UNITY_END();
}

#include "motion.h"
#include <math.h>
#include <stdio.h>

static const char* NAME[NJ] = {"q1", "th2", "phi", "g"};
static const float EPS = 1e-4f;  // unità di giunto: sotto questa soglia il giunto è arrivato
// Tolleranze sui bordi (limiti e vincolo), ben sotto un passo PWM (0.03°). TOL: arrotondamento float,
// senza un target sul bordo (th2-phi = 20 da valori a 0.01) viene rifiutato o il moto lungo il bordo
// si blocca a metà. HARD: margine dell'ultima difesa, oltre i bordi morbidi.
static const float TOL = 0.001f, HARD = 0.01f;
static const float SNAP = 1.2f;  // decelerazione massima dell'arrivo esatto, in AMAX

static float clampf(float x, float lo, float hi) { return x < lo ? lo : x > hi ? hi : x; }

void cal_default(Cal c[NJ]) {
    for (int j = 0; j < NJ; j++) c[j] = {CAL_REF_US[j], CAL_K[j], CAL_Q_REF[j], Q_MIN[j], Q_MAX[j]};
}

float q_to_us(const Cal& c, float q) { return clampf(c.ref_us + c.k * (q - c.q_ref), US_MIN, US_MAX); }

float us_to_q(const Cal& c, float us) { return c.q_ref + (us - c.ref_us) / c.k; }

bool check_target(const float q[NJ], const Cal cal[NJ], char* err, size_t n) {
    for (int j = 0; j < NJ; j++)
        if (!isfinite(q[j]) || q[j] < cal[j].min - TOL || q[j] > cal[j].max + TOL) {
            snprintf(err, n, "fuori limiti: %s=%g [%g, %g]", NAME[j], q[j], cal[j].min, cal[j].max);
            return false;
        }
    float e = q[1] - q[2];
    if (e < PAR_MIN - TOL || e > PAR_MAX + TOL) {
        snprintf(err, n, "fuori vincolo: th2-phi=%g", e);
        return false;
    }
    return true;
}

bool check_cal(const Cal cal[NJ], char* err, size_t n) {
    for (int j = 0; j < NJ; j++) {
        const Cal& c = cal[j];
        bool ok = isfinite(c.ref_us) && isfinite(c.k) && isfinite(c.q_ref) && isfinite(c.min) && isfinite(c.max) &&
                  c.ref_us >= US_MIN && c.ref_us <= US_MAX && fabsf(c.k) >= 1 && c.min < c.max &&
                  c.min >= Q_MIN[j] - 0.001f && c.max <= Q_MAX[j] + 0.001f;  // mai oltre i limiti meccanici (assembly.scad)
        if (!ok) {
            snprintf(err, n, "taratura non valida: giunto %d", j);
            return false;
        }
    }
    return true;
}

void Planner::reset(const float q0[NJ]) {
    for (int j = 0; j < NJ; j++) q[j] = target[j] = q0[j], v[j] = 0;
    stopping = false;
}

void Planner::move(const float tgt[NJ], float f) {
    for (int j = 0; j < NJ; j++) {
        target[j] = tgt[j];
        vmax[j] = VMAX[j] * f;
        amax[j] = AMAX[j] * f;
    }
    stopping = false;
}

void Planner::halt() {
    for (int j = 0; j < NJ; j++) target[j] = q[j], v[j] = 0;
    stopping = false;
}

bool Planner::moving() const {
    if (stopping) return true;
    for (int j = 0; j < NJ; j++)
        if (v[j] != 0 || q[j] != target[j]) return true;
    return false;
}

// velocità massima da cui ci si ferma entro d frenando di A*dt a ogni tick, senza superare d nel tick
static float vstop(float d, float A, float dt) {
    return d <= 0 ? 0 : fminf(A * dt * (sqrtf(0.25f + 2 * d / (A * dt * dt)) - 0.5f), d / dt);
}

void Planner::step(float dt, const Cal cal[NJ]) {
    float d[NJ], v0[NJ];
    for (int j = 0; j < NJ; j++) d[j] = target[j] - q[j], v0[j] = v[j];
    if (stopping) {
        // tutte le velocità scalate dello stesso fattore: la direzione non cambia,
        // il giunto più carico frena ad AMAX pieno
        float T = 0;
        for (int j = 0; j < NJ; j++) T = fmaxf(T, fabsf(v[j]) / AMAX[j]);
        float s = T > dt ? 1 - dt / T : 0;
        for (int j = 0; j < NJ; j++) v[j] *= s;
    } else {
        // Sincronizzazione: limiti per unità di distanza residua, presi dal giunto più lento.
        // vmax_j' = vs*|d_j|, amax_j' = as*|d_j|: da fermo i giunti sono copie in scala dello stesso
        // moto 1D, quindi restano sulla retta e arrivano insieme. Ricalcolati a ogni tick
        // (lungo la retta non cambiano), così un retarget o un overshoot si riassorbono da soli.
        float vs = INFINITY, as = INFINITY;
        for (int j = 0; j < NJ; j++) {
            float ad = fabsf(d[j]);
            if (ad > EPS) vs = fminf(vs, vmax[j] / ad), as = fminf(as, amax[j] / ad);
        }
        for (int j = 0; j < NJ; j++) {
            float ad = fabsf(d[j]);
            float vdes = 0, Aj = AMAX[j];
            if (ad > EPS) {
                Aj = as * ad;
                // velocità massima da cui si ferma esattamente in d togliendo Aj*dt a ogni tick
                float vb = Aj * dt * (sqrtf(0.25f + 2 * ad / (Aj * dt * dt)) - 0.5f);
                vdes = copysignf(fminf(vs * ad, vb), d[j]);
            }
            // accelera con il limite sincronizzato, frena sempre con AMAX pieno
            bool accel = vdes * v[j] >= 0 && fabsf(vdes) > fabsf(v[j]);
            float lim = (accel ? Aj : AMAX[j]) * dt;
            float vn = v[j] + clampf(vdes - v[j], -lim, lim);
            // inversione: oltre lo zero è di nuovo accelerazione, col limite sincronizzato
            v[j] = vn * v[j] < 0 ? copysignf(fminf(fabsf(vn), Aj * dt), vn) : vn;
        }
    }
    // Arrivo esatto, ma solo da velocità di fine profilo: v0 -> d/dt in questo tick e d/dt -> 0 nel
    // prossimo devono costare al più SNAP*AMAX. Dopo un retarget il giunto può arrivare sul target
    // troppo veloce: allora lo supera, frena e torna. Per i bordi morbidi chi arriva vale d/dt.
    bool snap[NJ];
    for (int j = 0; j < NJ; j++) {
        float ad = fabsf(d[j]), dv = SNAP * AMAX[j] * dt;
        snap[j] = !stopping && ((v[j] * d[j] > 0 && fabsf(v[j]) * dt >= ad && ad / dt <= dv && fabsf(v0[j]) - ad / dt <= dv) ||
                                (ad <= EPS && v[j] == 0));
        if (snap[j]) v[j] = d[j] / dt;
    }
    // Bordi morbidi: né un giunto né e = th2 - phi vanno più veloci di quanto serve per fermarsi sul
    // bordo frenando ad AMAX (e: 2*AMAX, lo muovono due giunti). Da fermo verso un target valido non
    // intervengono (il profilo frena già prima); dopo un retarget o uno stop la traiettoria curva e
    // scivola lungo il bordo invece di sbatterci.
    float e0 = q[1] - q[2], ev = v[1] - v[2];
    float evm = vstop(ev > 0 ? PAR_MAX + TOL - e0 : e0 - (PAR_MIN - TOL), 2 * AMAX[1], dt);
    if (fabsf(ev) > evm) {
        float c = copysignf((fabsf(ev) - evm) / 2, ev);
        v[1] -= c, v[2] += c, snap[1] = snap[2] = false;
    }
    for (int j = 0; j < NJ; j++) {
        float vm = vstop(v[j] > 0 ? cal[j].max + TOL - q[j] : q[j] - (cal[j].min - TOL), AMAX[j], dt);
        if (fabsf(v[j]) > vm) v[j] = copysignf(vm, v[j]), snap[j] = false;
    }

    float qn[NJ];
    for (int j = 0; j < NJ; j++) {
        if (snap[j]) qn[j] = target[j], v[j] = 0;
        else qn[j] = q[j] + v[j] * dt;
    }
    // Ultima difesa (arrotondamenti, angoli tra due bordi): si blocca solo il moto che peggiora,
    // così una taratura cambiata o un raw fuori limiti non fanno saltare il giunto.
    for (int j = 0; j < NJ; j++)
        if ((qn[j] < cal[j].min - HARD && qn[j] < q[j]) || (qn[j] > cal[j].max + HARD && qn[j] > q[j])) qn[j] = q[j], v[j] = 0;
    float e1 = qn[1] - qn[2];
    if ((e1 < PAR_MIN - HARD && e1 < e0) || (e1 > PAR_MAX + HARD && e1 > e0)) qn[1] = q[1], qn[2] = q[2], v[1] = v[2] = 0;

    bool still = true;
    for (int j = 0; j < NJ; j++) q[j] = qn[j], still &= v[j] == 0;
    if (stopping && still) halt();
}

#include "motion.h"
#include <math.h>
#include <stdio.h>

static const char* NAME[NJ] = {"q1", "th2", "phi", "g"};
static const float EPS = 1e-4f;  // unità di giunto: sotto questa soglia il giunto è arrivato

static float clampf(float x, float lo, float hi) { return x < lo ? lo : x > hi ? hi : x; }

void cal_default(Cal c[NJ]) {
    for (int j = 0; j < NJ; j++) c[j] = {CAL_REF_US[j], CAL_K[j], CAL_Q_REF[j], Q_MIN[j], Q_MAX[j]};
}

float q_to_us(const Cal& c, float q) { return clampf(c.ref_us + c.k * (q - c.q_ref), US_MIN, US_MAX); }

float us_to_q(const Cal& c, float us) { return c.q_ref + (us - c.ref_us) / c.k; }

bool check_target(const float q[NJ], const Cal cal[NJ], char* err, size_t n) {
    for (int j = 0; j < NJ; j++)
        if (!isfinite(q[j]) || q[j] < cal[j].min || q[j] > cal[j].max) {
            snprintf(err, n, "fuori limiti: %s=%g [%g, %g]", NAME[j], q[j], cal[j].min, cal[j].max);
            return false;
        }
    float e = q[1] - q[2];
    if (e < PAR_MIN || e > PAR_MAX) {
        snprintf(err, n, "fuori vincolo: th2-phi=%g", e);
        return false;
    }
    return true;
}

bool check_cal(const Cal cal[NJ], char* err, size_t n) {
    for (int j = 0; j < NJ; j++) {
        const Cal& c = cal[j];
        bool ok = isfinite(c.ref_us) && isfinite(c.k) && isfinite(c.q_ref) && isfinite(c.min) && isfinite(c.max) &&
                  c.ref_us >= US_MIN && c.ref_us <= US_MAX && fabsf(c.k) >= 1 && c.min < c.max;
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

void Planner::step(float dt, const Cal cal[NJ]) {
    float qn[NJ];
    if (stopping) {
        // tutte le velocità scalate dello stesso fattore: la direzione non cambia,
        // il giunto più carico frena ad AMAX pieno
        float T = 0;
        for (int j = 0; j < NJ; j++) T = fmaxf(T, fabsf(v[j]) / AMAX[j]);
        float s = T > dt ? 1 - dt / T : 0;
        for (int j = 0; j < NJ; j++) v[j] *= s, qn[j] = q[j] + v[j] * dt;
    } else {
        // Sincronizzazione: limiti per unità di distanza residua, presi dal giunto più lento.
        // vmax_j' = vs*|d_j|, amax_j' = as*|d_j|: da fermo i giunti sono copie in scala dello stesso
        // moto 1D, quindi restano sulla retta e arrivano insieme. Ricalcolati a ogni tick
        // (lungo la retta non cambiano), così un retarget o un overshoot si riassorbono da soli.
        float vs = INFINITY, as = INFINITY;
        for (int j = 0; j < NJ; j++) {
            float ad = fabsf(target[j] - q[j]);
            if (ad > EPS) vs = fminf(vs, vmax[j] / ad), as = fminf(as, amax[j] / ad);
        }
        for (int j = 0; j < NJ; j++) {
            float d = target[j] - q[j], ad = fabsf(d);
            float vdes = 0, Aj = AMAX[j];
            if (ad > EPS) {
                Aj = as * ad;
                // velocità massima da cui si ferma esattamente in d togliendo Aj*dt a ogni tick
                float vb = Aj * dt * (sqrtf(0.25f + 2 * ad / (Aj * dt * dt)) - 0.5f);
                vdes = copysignf(fminf(vs * ad, vb), d);
            }
            // accelera con il limite sincronizzato, frena sempre con AMAX pieno
            bool accel = vdes * v[j] >= 0 && fabsf(vdes) > fabsf(v[j]);
            float lim = (accel ? Aj : AMAX[j]) * dt;
            v[j] += clampf(vdes - v[j], -lim, lim);
            if ((v[j] * d > 0 && fabsf(v[j]) * dt >= ad) || (ad <= EPS && v[j] == 0))
                qn[j] = target[j], v[j] = 0;  // arrivo esatto
            else
                qn[j] = q[j] + v[j] * dt;
        }
    }
    // Difesa: mai oltre limiti e vincolo (target validati, ma dopo un retarget la traiettoria è curva).
    // Si blocca solo il moto che peggiora, così una taratura cambiata non fa saltare il giunto.
    // ponytail: il blocco azzera la velocità di colpo; succede solo in casi limite di retarget
    for (int j = 0; j < NJ; j++)
        if ((qn[j] < cal[j].min && qn[j] < q[j]) || (qn[j] > cal[j].max && qn[j] > q[j])) qn[j] = q[j], v[j] = 0;
    float e0 = q[1] - q[2], e1 = qn[1] - qn[2];
    if ((e1 < PAR_MIN && e1 < e0) || (e1 > PAR_MAX && e1 > e0)) qn[1] = q[1], qn[2] = q[2], v[1] = v[2] = 0;

    bool still = true;
    for (int j = 0; j < NJ; j++) q[j] = qn[j], still &= v[j] == 0;
    if (stopping && still) halt();
}

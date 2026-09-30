// Logica pura (niente Arduino): taratura q -> us, validazione target, planner sincronizzato.
// Testata sul PC con `pio test -e native`.
#pragma once
#include <stddef.h>
#include "config.h"

struct Cal {
    float ref_us, k, q_ref, min, max;
};

void cal_default(Cal c[NJ]);
float q_to_us(const Cal& c, float q);   // con clamp a [US_MIN, US_MAX]
float us_to_q(const Cal& c, float us);  // inversa, senza clamp

// false + motivo in err se il target esce dai limiti o dal vincolo del parallelogramma
bool check_target(const float q[NJ], const Cal cal[NJ], char* err, size_t n);
bool check_cal(const Cal cal[NJ], char* err, size_t n);

// Profilo trapezoidale sincronizzato, calcolato online a ogni tick.
// Da fermo tutti i giunti restano proporzionali (retta nello spazio giunti) e arrivano insieme;
// un nuovo target a metà moto riparte da posizione e velocità correnti.
struct Planner {
    float q[NJ] = {}, v[NJ] = {}, target[NJ] = {};
    float vmax[NJ] = {}, amax[NJ] = {};  // limiti del moto corrente, già scalati per f
    bool stopping = false;

    void reset(const float q0[NJ]);                // posa nota, fermo
    void move(const float tgt[NJ], float f);       // f in (0, 1], target già validato
    void stop() { stopping = true; }               // decelera e tiene la posizione
    void halt();                                   // fermo istantaneo (estop, PWM già sganciato)
    bool moving() const;
    void step(float dt, const Cal cal[NJ]);
};

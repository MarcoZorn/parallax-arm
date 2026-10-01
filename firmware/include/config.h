// Costanti del firmware. Contratto: docs/03-protocollo.md, pin: docs/02-cablaggio.md.
// Se cambiano là (o in cad/params.scad), vanno aggiornate qui.
// Niente Arduino.h: lo includono anche i test nativi.
#pragma once

#define FW_VERSION "0.1.0"

constexpr int NJ = 4;  // 0 base q1, 1 spalla th2, 2 gomito phi, 3 pinza g

// ---- PWM servo (LEDC) ----
constexpr int PIN_SERVO[NJ] = {33, 25, 26, 27};  // adiacenti, non strapping, niente impulsi al boot
constexpr int PWM_HZ = 50;
constexpr int PWM_BITS = 16;  // 20000 us / 65536 = 0.31 us per passo
constexpr float PWM_PERIOD_US = 20000;
constexpr float US_MIN = 500, US_MAX = 2500;  // clamp finale del segnale, sempre

// ---- taratura default (us = ref_us + k * (q - q_ref)) ----
constexpr float CAL_REF_US[NJ] = {1500, 1500, 1500, 1500};
constexpr float CAL_K[NJ] = {11.11f, 11.11f, 11.11f, 19.89f};  // SG90 11.11 us/°; pinza pignone r=16 mm -> 19.89 us/mm
constexpr float CAL_Q_REF[NJ] = {0, 90, 0, 29.5f};
constexpr float Q_MIN[NJ] = {-90, 20, -70, 0};  // ° ° ° mm
constexpr float Q_MAX[NJ] = {90, 160, 70, 59};

// ---- vincolo del parallelogramma: PAR_MIN <= th2 - phi <= PAR_MAX ----
constexpr float PAR_MIN = 20, PAR_MAX = 150;

constexpr float HOME_DEFAULT[NJ] = {0, 90, 0, 30};

// ---- moto (scalati dal fattore v del comando, tranne la frenata) ----
constexpr float VMAX[NJ] = {90, 90, 90, 60};      // °/s, pinza mm/s
constexpr float AMAX[NJ] = {180, 180, 180, 120};  // °/s², pinza mm/s²

// enable: un servo agganciato ogni ATTACH_STAGGER_MS, non tutti insieme. Un SG90 che salta alla home
// assorbe ~0.7 A per 150-250 ms (costante meccanica ~60 ms col braccio): 4 insieme fanno 2.4-2.7 A di picco
// e portano i servo sotto 4.0 V con cavi USB sottili. Sfalsati: picco ~1.7 A (sim/electrical/out/results.md).
constexpr int ATTACH_STAGGER_MS = 200;

constexpr int CTRL_MS = 20;   // loop di controllo 50 Hz, uno per frame servo
constexpr int STATE_MS = 50;  // broadcast stato 20 Hz

// ---- rete ----
constexpr unsigned STA_TIMEOUT_MS = 10000;
#define AP_SSID "BRACCIO"
#define AP_PASS "braccio-arm"
#define MDNS_NAME "braccio"

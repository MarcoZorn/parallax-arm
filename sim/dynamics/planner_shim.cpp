// Ponte C per usare il planner VERO del firmware (firmware/src/motion.cpp) da Python via ctypes.
#include "motion.h"

static Cal cal[NJ];
static Planner pl;

extern "C" {
void pl_init(const float* q0) { cal_default(cal); pl.reset(q0); }
void pl_move(const float* tgt, float f) { pl.move(tgt, f); }
void pl_stop() { pl.stop(); }
void pl_step(float dt) { pl.step(dt, cal); }
int pl_moving() { return pl.moving(); }
void pl_get(float* q, float* v) { for (int j = 0; j < NJ; j++) q[j] = pl.q[j], v[j] = pl.v[j]; }
float pl_us(int j, float q) { return q_to_us(cal[j], q); }
int pl_check(const float* q) { char e[80]; return check_target(q, cal, e, sizeof e); }
}

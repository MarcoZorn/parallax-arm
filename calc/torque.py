"""Coppia statica sui giunti — solo SG90, topologia parallela (tipo MeArm).

Spalla e gomito hanno ENTRAMBI il servo sulla torretta, coassiale all'asse spalla.
Il gomito è mosso da manovella + biella a parallelogramma, quindi il servo gomito non viaggia sul braccio.
Per lavoro virtuale (caso peggiore: segmenti orizzontali):
  T_gomito = g * sum(m_i * d_i)              momenti della catena avambraccio attorno al gomito
  T_spalla = g * (m_braccio*L1/2 + M_cat*L1)  la catena pesa sulla spalla solo come massa al gomito
I contrappesi (piombi da pesca) sulla coda della manovella gomito e del braccio compensano la gravità
a ogni angolo: coda e segmento ruotano insieme, quindi entrambi i momenti vanno con lo stesso cos(angolo).

Rilancia dopo ogni modifica: python3 calc/torque.py   (deve coincidere con cad/params.scad)
"""
from math import radians

G = 9.81
KGCM = 0.0980665  # 1 kg*cm in N*m

L1 = 0.080  # spalla -> gomito
L2 = 0.080  # gomito -> perno polso
L3 = 0.045  # perno polso -> centro dita
R_CW_ELBOW = 0.0393  # baricentro dei 4 piombi ad arco r=43 (echo di cad/crank.scad)
R_CW_SHOULDER = 0.030  # raggio contrappeso sulla coda del braccio
LEAD = 0.020  # piombo da pesca a oliva, kg

SG90_T = 1.6  # kg*cm @4.8V dichiarati (i cloni reali 1.2-1.5: da qui SF 2)
SG90_I = 0.75  # A stallo
SF_MIN = 2.0
PAYLOAD_MAX = 0.050


def chain(payload, roll=False):
    """Catena avambraccio: (nome, massa kg, distanza dal gomito m). Stime PLA 20% infill."""
    r = 0.010 if roll else 0.0  # il roll allunga il polso
    c = [
        ("avambraccio PLA", 0.007, L2 / 2),
        ("staffa polso + bielle livellamento", 0.006, L2),
        ("pinza cremagliera + SG90", 0.027, L2 + r + 0.022),
        ("ESP32-CAM + culla", 0.014, L2 + r + 0.015),
        ("payload", payload, L2 + r + L3),
    ]
    if roll:
        c.append(("SG90 roll + staffa", 0.014, L2 + 0.005))
    return c


def moment(items):
    return sum(m * d for _, m, d in items)  # kg*m


def t_elbow(payload, roll, cw=0.0):
    return (moment(chain(payload, roll)) - cw * R_CW_ELBOW) * G / KGCM


def t_shoulder(payload, roll, cw=0.0):
    m_chain = sum(m for _, m, _ in chain(payload, roll)) + 0.004  # + biella motrice (metà)
    return (0.009 * L1 / 2 + m_chain * L1 - cw * R_CW_SHOULDER) * G / KGCM


def cw_needed(t_fn, r_cw, roll):
    """Contrappeso minimo (kg) per SF >= SF_MIN a payload massimo."""
    excess = t_fn(PAYLOAD_MAX, roll) - SG90_T / SF_MIN  # kg*cm oltre il consentito
    return max(0.0, excess * KGCM / G / r_cw)


def report(roll):
    print(f"\n=== {'5 assi (con polso roll)' if roll else '4 assi: base, spalla, gomito, pinza'} ===")
    cw_e = cw_needed(t_elbow, R_CW_ELBOW, roll)
    cw_s = cw_needed(t_shoulder, R_CW_SHOULDER, roll)
    for p in (0.0, 0.030, PAYLOAD_MAX):
        te0, ts0 = t_elbow(p, roll), t_shoulder(p, roll)
        te, ts = t_elbow(p, roll, cw_e), t_shoulder(p, roll, cw_s)
        print(f"payload {p * 1000:3.0f} g | senza contrappeso: gomito {te0:4.2f} (SF {SG90_T / te0:3.1f})"
              f" spalla {ts0:4.2f} (SF {SG90_T / ts0:3.1f}) | con: gomito {te:+5.2f} spalla {ts:+5.2f} kg*cm")
        # anche scarico e sovrabilanciato il servo deve restare entro SF
        assert abs(te) <= SG90_T / SF_MIN + 1e-9 and abs(ts) <= SG90_T / SF_MIN + 1e-9
    print(f"contrappeso gomito  {cw_e * 1000:3.0f} g @ {R_CW_ELBOW * 1000:.0f} mm  (~{cw_e / LEAD:.1f} piombi da 20 g)")
    print(f"contrappeso spalla  {cw_s * 1000:3.0f} g @ {R_CW_SHOULDER * 1000:.0f} mm  (~{cw_s / LEAD:.1f} piombi da 20 g)")
    return cw_e, cw_s


if __name__ == "__main__":
    print(f"L1 {L1 * 1000:.0f} + L2 {L2 * 1000:.0f} + L3 {L3 * 1000:.0f} mm -> sbraccio "
          f"{(L1 + L2 + L3) * 1000:.0f} mm dall'asse spalla. SG90 {SG90_T} kg*cm, SF min {SF_MIN}")
    report(roll=False)
    report(roll=True)

    # Configurazione montata (cad/): 4 piombi ad arco sulla manovella, 2 sulla coda del braccio
    cw_e, cw_s = 4 * LEAD, 2 * LEAD
    print("\n=== montato: 4 assi, 4 piombi (80 g) gomito + 2 (40 g) spalla ===")
    for p in (0.0, 0.030, PAYLOAD_MAX):
        te, ts = t_elbow(p, False, cw_e), t_shoulder(p, False, cw_s)
        print(f"payload {p * 1000:3.0f} g | gomito {te:+5.2f} kg*cm (SF {SG90_T / abs(te):3.1f})"
              f" | spalla {ts:+5.2f} kg*cm (SF {SG90_T / abs(ts):3.1f})")
        assert SG90_T / abs(te) >= 1.9 and SG90_T / abs(ts) >= 1.9

    # Base: asse verticale, nessuna coppia gravitazionale; inerzia con contrappesi, accel. limitata dal firmware
    inertia = moment([(n, m, d) for n, m, d in chain(PAYLOAD_MAX, True)]) * (L2 + L3) + 0.03 * L1**2
    tb = inertia * 10.0 / KGCM
    print(f"\nbase: {tb:4.2f} kg*cm inerziali @10 rad/s^2 (SF {SG90_T / tb:.0f})")
    assert SG90_T / tb >= SF_MIN

    # Pinza: pignone m1 z20 (r=10 mm) tra due cremagliere simmetriche
    r_pin = 0.010
    stroke = 2 * r_pin * radians(170) * 1000  # 170 gradi utili del servo
    f_jaw = SG90_T * KGCM / (2 * r_pin)  # T = 2*F*r
    f_need = PAYLOAD_MAX * G * SF_MIN / (2 * 0.3)  # due dita, mu PLA ~0.3
    print(f"pinza: corsa {stroke:.0f} mm, forza/dito {f_jaw:.1f} N (servono {f_need:.1f} N)")
    assert 55 <= stroke <= 62 and f_jaw >= f_need

    n = 4
    print(f"corrente: stallo cumulativo {n} x {SG90_I} A = {n * SG90_I:.2f} A -> caricatore USB 5V >= 3A")

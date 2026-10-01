"""Coppia statica sui giunti — solo SG90, topologia parallela (tipo MeArm).

Spalla e gomito hanno ENTRAMBI il servo sulla torretta, coassiale all'asse spalla.
Il gomito è mosso da manovella + biella a parallelogramma, quindi il servo gomito non viaggia sul braccio.
Per lavoro virtuale (caso peggiore: segmenti orizzontali):
  T_gomito = g * sum(m_i * d_i)              momenti della catena avambraccio attorno al gomito
  T_spalla = g * (m_braccio*d + M_cat*L1)    la catena pesa sulla spalla solo come massa al gomito
I contrappesi (piombi da pesca 20 g) sulla coda della manovella gomito e del braccio compensano la gravità
a ogni angolo: coda e segmento ruotano insieme, quindi entrambi i momenti vanno con lo stesso cos(angolo).
La pinza è livellata dai parallelogrammi: ruotando phi trasla senza ruotare, quindi pinza, payload e camera
caricano il gomito col braccio L2 (non L2+L3). Il resto del loro momento va al montante fisso G
(verificato con la simulazione MuJoCo in sim/dynamics: coppie a regime uguali al lavoro virtuale).

Masse dai volumi degli STL in cad/stl (PLA 1.24 g/cm3 x 0.6 di riempimento effettivo) + componenti.
Rilancia dopo ogni modifica: python3 calc/torque.py   (quote = cad/params.scad e cad/wrist.scad)
"""
G = 9.81
KGCM = 0.0980665  # 1 kg*cm in N*m

L1 = 0.080  # spalla -> gomito
L2 = 0.080  # gomito -> perno polso
L3 = 0.042  # perno polso -> centro dita (xp in wrist.scad)
LEAD = 0.020  # piombo da pesca a oliva
R_CW_SHOULDER = 0.030  # 4 piombi in fila trasversale sulla coda del braccio
R_CW_ELBOW = {2: 0.0422, 4: 0.0393, 6: 0.0346}  # baricentro dell'arco di piombi, sedi centrali per prime (cad/crank.scad)

SG90_T = 1.6  # kg*cm @4.8V dichiarati (i cloni reali 1.2-1.5: da qui SF 2)
SG90_I = 0.75  # A stallo
SF_MIN = 2.0
PAYLOAD_MAX = 0.050


def chain(payload, cam):
    """Catena avambraccio: (nome, massa kg, braccio di leva rispetto al gomito m). Le parti livellate stanno a L2."""
    c = [
        ("avambraccio (13_forearm)", 0.0090, L2 / 2),
        ("biella livellamento 2 + triangolo", 0.0032, L2 / 2),
        ("viti/dadi/distanziale polso", 0.0045, L2),
        ("pinza stampata + SG90 (15..19)", 0.0373, L2),
        ("payload", payload, L2),
    ]
    if cam:
        c.append(("ESP32-CAM + culla (20)", 0.0131, L2))
    return c


def moment(items):
    return sum(m * d for _, m, d in items)  # kg*m


def t_elbow(payload, cam, n_lead):
    cw = n_lead * LEAD * R_CW_ELBOW[n_lead] if n_lead else 0.0
    return (moment(chain(payload, cam)) - cw) * G / KGCM


def t_shoulder(payload, cam, n_lead):
    m_chain = sum(m for _, m, _ in chain(payload, cam)) + 0.006  # + perno E, biella motrice (metà)
    return (0.0132 * L1 / 2 + m_chain * L1 - n_lead * LEAD * R_CW_SHOULDER) * G / KGCM


def report(cam, n_elbow, n_shoulder=4):
    print(f"\n=== {'con' if cam else 'senza'} ESP32-CAM, {n_elbow} piombi gomito + {n_shoulder} spalla ===")
    sfs = {}
    for p in (0.0, 0.030, PAYLOAD_MAX):
        te, ts = t_elbow(p, cam, n_elbow), t_shoulder(p, cam, n_shoulder)
        sfs[p] = min(SG90_T / abs(te), SG90_T / abs(ts))
        print(f"payload {p * 1000:3.0f} g | gomito {te:+5.2f} kg*cm (SF {SG90_T / abs(te):3.1f})"
              f" | spalla {ts:+5.2f} kg*cm (SF {SG90_T / abs(ts):3.1f})")
    return sfs


if __name__ == "__main__":
    print(f"L1 {L1 * 1000:.0f} + L2 {L2 * 1000:.0f} + L3 {L3 * 1000:.0f} mm -> sbraccio "
          f"{(L1 + L2 + L3) * 1000:.0f} mm dall'asse spalla. SG90 {SG90_T} kg*cm, SF min {SF_MIN}")
    print(f"senza contrappeso, senza camera, 50 g: gomito SF {SG90_T / t_elbow(PAYLOAD_MAX, False, 0):.2f}")

    a = report(cam=False, n_elbow=2)
    b = report(cam=True, n_elbow=2)
    c = report(cam=True, n_elbow=4)

    # Base: asse verticale, nessuna coppia gravitazionale; inerzia a braccio disteso, accel. limitata dal firmware
    inertia = moment(chain(PAYLOAD_MAX, True)) * (L2 + L3) + 0.03 * L1**2
    tb = inertia * 10.0 / KGCM
    friction = 0.3 * 0.30 * G * 0.050 / KGCM  # PLA su PLA, ~300 g sulla corona r=50 mm
    print(f"\nbase: {tb:4.2f} kg*cm inerziali @10 rad/s^2 + {friction:4.2f} attrito corona (SF {SG90_T / (tb + friction):.1f})")

    # Pinza: pignone m1 z32 (r=16 mm) tra due cremagliere simmetriche
    r_pin = 0.016
    stroke = 59
    turn = stroke / 1000 / (2 * r_pin) * 180 / 3.14159265
    f_jaw = SG90_T * KGCM / (2 * r_pin)  # T = 2*F*r
    f_need = PAYLOAD_MAX * G * SF_MIN / (2 * 0.3)  # due dita, mu PLA ~0.3
    print(f"pinza: corsa {stroke} mm in {turn:.0f} gradi, forza/dito {f_jaw:.1f} N (servono {f_need:.1f} N)")

    n = 4
    print(f"corrente: stallo cumulativo {n} x {SG90_I} A = {n * SG90_I:.2f} A -> caricatore USB 5V >= 3A")

    # Punto di progetto (docs/01): 2 piombi sulla manovella + 4 sulla coda del braccio, 50 g anche con la camera.
    # 2 e non 4 sulla manovella: con 4 il gomito è bilanciato a vuoto e gira libero nel gioco (sim/dynamics).
    assert a[PAYLOAD_MAX] >= 2.0, a
    assert b[PAYLOAD_MAX] >= 2.0, b
    assert t_elbow(0.0, False, 2) > 0.1  # il gomito resta caricato sempre dallo stesso lato
    assert SG90_T / (tb + friction) >= SF_MIN
    assert turn <= 170 and f_jaw >= f_need

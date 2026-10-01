// Firmware BRACCIO: 4 SG90 su LEDC, web app da LittleFS, comandi via WebSocket.
// Contratto con la web app: docs/03-protocollo.md.
// Le callback WS girano nel task di AsyncTCP: fanno solo parsing e accodano, il loop esegue.
#include <Arduino.h>
#include <WiFi.h>
#include <ESPmDNS.h>
#include <LittleFS.h>
#include <Preferences.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include "config.h"
#include "motion.h"

#if __has_include("secrets.h")
#include "secrets.h"
#else
#define WIFI_SSID ""  // niente secrets.h: direttamente AP
#define WIFI_PASS ""
#endif

AsyncWebServer server(80);
AsyncWebSocket ws("/ws");
Preferences prefs;

Cal cal[NJ];
float home[NJ];
Planner pl;
bool enabled = false;
bool known = false;  // posa nota: dopo il primo enable il planner parte dall'ultima posa comandata
int attachNext = NJ;  // prossimo servo da agganciare dopo l'enable (NJ: tutti agganciati o nessuno in attesa)
uint32_t tAttach = 0;
const char* netMode = "ap";

enum CmdType : uint8_t { C_MOVE, C_STOP, C_ENABLE, C_RAW, C_CAL_GET, C_CAL_SET, C_CAL_SAVE, C_HOME_SET };
struct Cmd {
    CmdType t;
    uint32_t client;
    float q[NJ], v;  // move: target e fattore; raw: v = us
    int j;           // raw: giunto
    Cal cal[NJ];
};
QueueHandle_t cmdq;
volatile bool estopReq = false;  // estop salta la coda: non deve mai perdersi

// ---- servo ----

static uint32_t duty(float us) { return lroundf(us * (1 << PWM_BITS) / PWM_PERIOD_US); }

static void writeServos() {
    for (int j = 0; j < NJ; j++) ledcWrite(j, duty(q_to_us(cal[j], pl.q[j])));
}

// Aggancio sfalsato: chiamata dal loop, un servo ogni ATTACH_STAGGER_MS per non sommare gli spunti
static void attachStep() {
    if (attachNext >= NJ || millis() - tAttach < ATTACH_STAGGER_MS) return;
    ledcAttachPin(PIN_SERVO[attachNext], attachNext);  // duty già scritto: il primo impulso è quello giusto
    attachNext++;
    tAttach = millis();
}

static void detachServos() {
    for (int j = 0; j < NJ; j++) {
        ledcDetachPin(PIN_SERVO[j]);
        pinMode(PIN_SERVO[j], OUTPUT);  // linea bassa: servo senza impulsi, senza coppia
        digitalWrite(PIN_SERVO[j], LOW);
    }
}

// ---- messaggi in uscita ----

static void send(uint32_t client, JsonDocument& doc) {  // client 0 = tutti
    String s;
    serializeJson(doc, s);
    if (client) ws.text(client, s);
    else ws.textAll(s);
}

static void sendErr(uint32_t client, const char* msg) {
    JsonDocument doc;
    doc["t"] = "err";
    doc["msg"] = msg;
    send(client, doc);
}

static float r2(float x) { return roundf(x * 100) / 100; }

static void sendCal(uint32_t client) {
    JsonDocument doc;
    doc["t"] = "cal";
    JsonArray a = doc["cal"].to<JsonArray>(), h = doc["home"].to<JsonArray>();
    for (int j = 0; j < NJ; j++) {
        JsonObject o = a.add<JsonObject>();
        o["ref_us"] = cal[j].ref_us;
        o["k"] = cal[j].k;
        o["q_ref"] = cal[j].q_ref;
        o["min"] = cal[j].min;
        o["max"] = cal[j].max;
        h.add(r2(home[j]));
    }
    send(client, doc);
}

static void sendState() {
    JsonDocument doc;
    doc["t"] = "state";
    JsonArray q = doc["q"].to<JsonArray>(), t = doc["target"].to<JsonArray>(), us = doc["us"].to<JsonArray>();
    for (int j = 0; j < NJ; j++) {
        q.add(r2(pl.q[j]));
        t.add(r2(pl.target[j]));
        us.add(r2(q_to_us(cal[j], pl.q[j])));
    }
    doc["moving"] = pl.moving();
    doc["enabled"] = enabled;
    send(0, doc);
}

// ---- comandi (eseguiti nel loop) ----

static void estop() {
    attachNext = NJ;
    detachServos();
    enabled = false;
    pl.halt();
}

static void handle(const Cmd& c) {
    char err[80];
    switch (c.t) {
    case C_MOVE:
        if (!enabled) return sendErr(c.client, "disabilitato: manda enable");
        if (attachNext < NJ) return sendErr(c.client, "enable in corso");
        if (!(c.v > 0 && c.v <= 1)) return sendErr(c.client, "v fuori da (0, 1]");
        if (!check_target(c.q, cal, err, sizeof err)) return sendErr(c.client, err);
        pl.move(c.q, c.v);
        break;
    case C_STOP:
        if (enabled) pl.stop();
        break;
    case C_ENABLE:
        if (enabled) return;
        if (!known) pl.reset(home), known = true;
        writeServos();
        attachNext = 0;
        tAttach = millis() - ATTACH_STAGGER_MS;  // il primo subito
        enabled = true;
        break;
    case C_RAW: {
        if (!enabled) return sendErr(c.client, "raw solo con enabled");
        if (attachNext < NJ) return sendErr(c.client, "enable in corso");
        if (c.j < 0 || c.j >= NJ || !isfinite(c.v)) return sendErr(c.client, "raw: giunto o us non validi");
        if (pl.moving()) return sendErr(c.client, "raw: braccio in moto");
        // il giunto va dove dice l'impulso: la posa resta coerente, il prossimo move parte da qui senza salti
        pl.q[c.j] = pl.target[c.j] = us_to_q(cal[c.j], constrain(c.v, US_MIN, US_MAX));
        break;
    }
    case C_CAL_GET:
        sendCal(c.client);
        break;
    case C_CAL_SET:
        if (pl.moving()) return sendErr(c.client, "cal_set: braccio in moto");
        if (!check_cal(c.cal, err, sizeof err)) return sendErr(c.client, err);
        // si tiene l'impulso attuale e si rilegge la posa con la nuova taratura: il servo non si muove
        for (int j = 0; j < NJ; j++) pl.q[j] = pl.target[j] = us_to_q(c.cal[j], q_to_us(cal[j], pl.q[j]));
        memcpy(cal, c.cal, sizeof cal);
        sendCal(0);
        break;
    case C_CAL_SAVE:
        prefs.putBytes("cal", cal, sizeof cal);
        break;
    case C_HOME_SET:
        if (pl.moving()) return sendErr(c.client, "home_set: braccio in moto");
        if (!check_target(pl.q, cal, err, sizeof err)) return sendErr(c.client, err);
        memcpy(home, pl.q, sizeof home);
        prefs.putBytes("home", home, sizeof home);
        sendCal(0);
        break;
    }
}

// ---- WebSocket (task AsyncTCP: solo parsing) ----

static void onWs(AsyncWebSocket*, AsyncWebSocketClient* client, AwsEventType type, void* arg, uint8_t* data, size_t len) {
    uint32_t id = client->id();
    if (type == WS_EVT_CONNECT) {
        char s[64];
        snprintf(s, sizeof s, "{\"t\":\"hello\",\"fw\":\"%s\",\"mode\":\"%s\"}", FW_VERSION, netMode);
        client->text(s);
        return;
    }
    if (type != WS_EVT_DATA) return;
    auto* info = (AwsFrameInfo*)arg;
    if (!info->final || info->index || info->len != len || info->opcode != WS_TEXT) return;  // un frame di testo

    JsonDocument doc;
    if (deserializeJson(doc, data, len)) return sendErr(id, "json non valido");
    const char* t = doc["t"] | "";
    if (!strcmp(t, "estop")) {
        estopReq = true;
        return;
    }
    Cmd c = {};
    c.client = id;
    if (!strcmp(t, "move")) {
        c.t = C_MOVE;
        JsonArray q = doc["q"];
        if (q.size() != NJ) return sendErr(id, "move: servono 4 valori in q");
        for (int j = 0; j < NJ; j++) c.q[j] = q[j] | NAN;
        c.v = doc["v"] | 0.5f;
    } else if (!strcmp(t, "stop")) c.t = C_STOP;
    else if (!strcmp(t, "enable")) c.t = C_ENABLE;
    else if (!strcmp(t, "raw")) {
        c.t = C_RAW;
        c.j = doc["j"] | -1;
        c.v = doc["us"] | NAN;
    } else if (!strcmp(t, "cal_get")) c.t = C_CAL_GET;
    else if (!strcmp(t, "cal_set")) {
        c.t = C_CAL_SET;
        JsonArray a = doc["cal"];
        if (a.size() != NJ) return sendErr(id, "cal_set: servono 4 giunti");
        for (int j = 0; j < NJ; j++)
            c.cal[j] = {a[j]["ref_us"] | NAN, a[j]["k"] | NAN, a[j]["q_ref"] | NAN, a[j]["min"] | NAN, a[j]["max"] | NAN};
    } else if (!strcmp(t, "cal_save")) c.t = C_CAL_SAVE;
    else if (!strcmp(t, "home_set")) c.t = C_HOME_SET;
    else return sendErr(id, "comando sconosciuto");
    if (xQueueSend(cmdq, &c, 0) != pdTRUE) sendErr(id, "coda comandi piena");
}

// ---- rete ----

static void wifiStart() {
    if (strlen(WIFI_SSID)) {
        WiFi.mode(WIFI_STA);
        WiFi.setHostname(MDNS_NAME);
        WiFi.begin(WIFI_SSID, WIFI_PASS);
        for (uint32_t t0 = millis(); WiFi.status() != WL_CONNECTED && millis() - t0 < STA_TIMEOUT_MS;) delay(100);
        if (WiFi.status() == WL_CONNECTED) {
            netMode = "sta";
            return;
        }
        WiFi.disconnect(true);
    }
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASS);  // 192.168.4.1
    netMode = "ap";
}

static String ip() { return strcmp(netMode, "sta") ? WiFi.softAPIP().toString() : WiFi.localIP().toString(); }

void setup() {
    // PWM non agganciato: i pin restano come al boot, bassi grazie ai pull-down da 10k
    Serial.begin(115200);
    for (int j = 0; j < NJ; j++) ledcSetup(j, PWM_HZ, PWM_BITS);

    cal_default(cal);
    memcpy(home, HOME_DEFAULT, sizeof home);
    prefs.begin("braccio");
    Cal saved[NJ];
    char err[80];
    if (prefs.getBytes("cal", saved, sizeof saved) == sizeof saved && check_cal(saved, err, sizeof err))
        memcpy(cal, saved, sizeof cal);
    float h[NJ];
    if (prefs.getBytes("home", h, sizeof h) == sizeof h && check_target(h, cal, err, sizeof err)) memcpy(home, h, sizeof home);
    pl.reset(home);

    cmdq = xQueueCreate(16, sizeof(Cmd));

    wifiStart();
    MDNS.begin(MDNS_NAME);
    MDNS.addService("http", "tcp", 80);
    Serial.printf("BRACCIO %s: %s %s, http://%s.local\n", FW_VERSION, netMode, ip().c_str(), MDNS_NAME);

    if (!LittleFS.begin(false)) Serial.println("LittleFS vuoto o assente: fai uploadfs");
    ws.onEvent(onWs);
    server.addHandler(&ws);
    server.on("/api/info", HTTP_GET, [](AsyncWebServerRequest* req) {
        String s = String("{\"fw\":\"" FW_VERSION "\",\"ip\":\"") + ip() + "\",\"mode\":\"" + netMode + "\"}";
        req->send(200, "application/json", s);
    });
    server.serveStatic("/", LittleFS, "/").setDefaultFile("index.html");  // usa da solo i .gz se presenti
    server.onNotFound([](AsyncWebServerRequest* req) { req->send(404, "text/plain", "404"); });
    server.begin();
}

void loop() {
    static uint32_t tCtl = millis(), tState = millis();
    if (estopReq) estopReq = false, estop();
    Cmd c;
    while (xQueueReceive(cmdq, &c, 0) == pdTRUE) handle(c);
    attachStep();

    uint32_t now = millis();
    if (now - tCtl >= CTRL_MS) {
        tCtl = now - tCtl > 5 * CTRL_MS ? now : tCtl + CTRL_MS;  // se resta indietro non recupera a raffica
        if (enabled) {
            // watchdog: nessun client connesso durante il moto -> frena e tiene la posizione
            if (!ws.count() && pl.moving() && !pl.stopping) pl.stop();
            pl.step(CTRL_MS / 1000.0f, cal);
            writeServos();
        }
    }
    if (now - tState >= STATE_MS) {
        tState = now;
        if (ws.count()) sendState();
        ws.cleanupClients();
    }
    delay(1);
}

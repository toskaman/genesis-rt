/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * genesis_faultinject: on-target guard verification client.
 * Sends a fixed sequence of nominal and faulty commands to genesis_guard
 * over native message passing and checks each reply (decision, reason
 * AND resulting state) against the expected verdict. Order matters:
 * non-latching denials first, latching integrity faults next, then
 * proof that SAFE_STOP holds. Exit 0 only if all match.
 */
#include <stdio.h>
#include <string.h>
#include "genesis_ipc.h"
#include "guard_policy.h"

#ifdef __QNXNTO__
#include <math.h>
#include <stdlib.h>
#include <sys/dispatch.h>
#include <sys/neutrino.h>
#include <time.h>
/* Check vectors derive from the SAME generated header as the guard, so the
 * 9 checks stay valid for every machine: cruise is always nominal, OVER is
 * always over the limit, on AMR and conveyor alike. */
#include "genesis_config_gen.h"

#define FI_CRUISE ((float)(0.4 * GENESIS_MAX_LINEAR_MPS))
#define FI_OVER ((float)(GENESIS_MAX_LINEAR_MPS * 2.0 + 1.0))

static uint64_t now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000u + (uint64_t)ts.tv_nsec / 1000000u;
}

static int failures = 0;

/* One-shot 2 s guard-call timeout, re-armed before every MsgSend so a
 * hung guard fails loudly instead of wedging the verifier (same
 * pattern as the controller; Wave 10 jury A). */
static int arm_ipc_timeout(void) {
    struct sigevent ev;
    uint64_t to = 2000000000ULL;
    memset(&ev, 0, sizeof ev);
    ev.sigev_notify = SIGEV_UNBLOCK;
    return TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_SEND | _NTO_TIMEOUT_REPLY,
                        &ev, &to, NULL);
}
static void check_n(int coid, const char *name, genesis_cmd_t *cmd, size_t send_len,
                    uint32_t want_decision, uint32_t want_reason, uint32_t want_state) {
    genesis_reply_t reply;
    memset(&reply, 0xFF, sizeof reply); /* short replies must not read as ALLOW */
    if (arm_ipc_timeout() != 0) {
        printf("FAIL %-18s TimerTimeout error\n", name);
        failures++;
        return;
    }
    if (MsgSend(coid, cmd, send_len, &reply, sizeof reply) != 0) {
        printf("FAIL %-18s MsgSend error\n", name);
        failures++;
        return;
    }
    int ok = (reply.decision == want_decision && reply.reason == want_reason &&
              reply.state_out == want_state);
    printf("%s %-18s decision=%u reason=%u state=%u (want %u/%u/%u)\n",
           ok ? "PASS" : "FAIL", name, reply.decision, reply.reason,
           reply.state_out, want_decision, want_reason, want_state);
    if (!ok)
        failures++;
}

static void check(int coid, const char *name, genesis_cmd_t *cmd,
                  uint32_t want_decision, uint32_t want_reason, uint32_t want_state) {
    check_n(coid, name, cmd, sizeof *cmd, want_decision, want_reason, want_state);
}

/* Probe mode: send ONE command and print the guard's verdict. With a
 * number, a nominal command at that linear speed; with "estop", a
 * nominal command with the estop wire engaged. Exit 0 when a reply
 * arrives (whatever the verdict -- the caller asserts it), 2 on
 * usage/IPC errors. Used by the two-machine proof and the estop
 * target proof. */
static int run_probe(int coid, const char *arg, uint32_t seq) {
    char *end = NULL;
    double v = 0.5;
    int estop = 0;
    if (strcmp(arg, "estop") == 0) {
        estop = 1;
    } else {
        v = strtod(arg, &end);
        if (end == arg || *end != '\0' || !isfinite(v) || fabs(v) > 1e6) {
            printf("PROBE usage: genesis_faultinject probe <linear_mps|estop>\n");
            return 2;
        }
    }
    genesis_cmd_t cmd;
    memset(&cmd, 0, sizeof cmd);
    cmd.magic = GENESIS_PROTOCOL_MAGIC;
    cmd.version = GENESIS_PROTOCOL_VERSION;
    cmd.req_state = GENESIS_ST_NOMINAL;
    cmd.seq = seq;
    uint64_t now = now_ms();
    cmd.now_ms = (uint32_t)now;
    cmd.deadline_ms = (uint32_t)now + 30u;
    cmd.linear_mps = (float)v;
    cmd.angular_radps = 0.0f;
    cmd.sensor_age_ms = 0;
    cmd.sim_connected = 1;
    cmd.estop_engaged = (uint8_t)estop;
    genesis_reply_t reply;
    memset(&reply, 0xFF, sizeof reply);
    if (arm_ipc_timeout() != 0) {
        printf("PROBE TimerTimeout error\n");
        return 2;
    }
    if (MsgSend(coid, &cmd, sizeof cmd, &reply, sizeof reply) != 0) {
        printf("PROBE MsgSend error\n");
        return 2;
    }
    printf("PROBE linear=%.3f estop=%d decision=%s reason=%s state=%u\n", v,
           estop,
           reply.decision == GENESIS_ALLOW ? "ALLOW" : "DENY",
           genesis_reason_str(reply.reason), reply.state_out);
    return 0;
}

/* State-probe mode (IR v2 transitions): send ONE command with
 * req_state=n at cruise speed and print the guard verdict. Cruise is
 * always nominal, so the verdict isolates the TRANSITION rule:
 * identical magnitude, only the requested state varies. Exit 0 when a
 * reply arrives (whatever the verdict -- the caller asserts it), 2 on
 * usage/IPC errors. */
static int run_state_probe(int coid, const char *arg) {
    if (!(arg[0] >= '0' && arg[0] <= '3' && arg[1] == '\0')) {
        printf("PROBE usage: genesis_faultinject probe state <0..3>\n");
        return 2;
    }
    float v = FI_CRUISE;
    genesis_cmd_t cmd;
    memset(&cmd, 0, sizeof cmd);
    cmd.magic = GENESIS_PROTOCOL_MAGIC;
    cmd.version = GENESIS_PROTOCOL_VERSION;
    cmd.req_state = (uint8_t)(arg[0] - '0');
    cmd.seq = 1;
    uint64_t now = now_ms();
    cmd.now_ms = (uint32_t)now;
    cmd.deadline_ms = (uint32_t)now + 30u;
    cmd.linear_mps = v;
    cmd.angular_radps = 0.0f;
    cmd.sensor_age_ms = 0;
    cmd.sim_connected = 1;
    cmd.estop_engaged = 0;
    genesis_reply_t reply;
    memset(&reply, 0xFF, sizeof reply);
    if (arm_ipc_timeout() != 0) {
        printf("PROBE TimerTimeout error\n");
        return 2;
    }
    if (MsgSend(coid, &cmd, sizeof cmd, &reply, sizeof reply) != 0) {
        printf("PROBE MsgSend error\n");
        return 2;
    }
    printf("PROBE state=%c decision=%s reason=%s state=%u\n", arg[0],
           reply.decision == GENESIS_ALLOW ? "ALLOW" : "DENY",
           genesis_reason_str(reply.reason), reply.state_out);
    return 0;
}

/* Bench mode: N sequential nominal MsgSend round trips, CLOCK_MONOTONIC
 * timestamps. Prints one SAMPLE <us> line per trip plus PERF_DONE.
 * Raw data only (no in-C stats): the host analyzes the samples.
 * Exit 0 on full delivery, 2 on usage/IPC errors. */
static uint64_t now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000u + (uint64_t)ts.tv_nsec;
}

static int run_bench(int coid, const char *arg) {
    char *end = NULL;
    long n = strtol(arg, &end, 10);
    if (end == arg || *end != '\0' || n < 1 || n > 100000) {
        printf("BENCH usage: genesis_faultinject bench <1..100000>\n");
        return 2;
    }
    /* IPC timeline trace (Wave 11 S12): off unless GENESIS_IPC_TRACE=1.
     * Same CLOCK_MONOTONIC as the guard, so SEND/DONE join with the
     * guard's RECV/REPLY by seq on the host. */
    const char *trace_env = getenv("GENESIS_IPC_TRACE");
    int trace = trace_env != NULL && strcmp(trace_env, "1") == 0;
    genesis_cmd_t cmd;
    memset(&cmd, 0, sizeof cmd);
    cmd.magic = GENESIS_PROTOCOL_MAGIC;
    cmd.version = GENESIS_PROTOCOL_VERSION;
    cmd.req_state = GENESIS_ST_NOMINAL;
    cmd.linear_mps = FI_CRUISE;
    cmd.angular_radps = 0.0f;
    cmd.sensor_age_ms = 0;
    cmd.sim_connected = 1;
    for (long i = 0; i < n; i++) {
        cmd.seq = (uint32_t)(i + 1);
        {
            uint64_t now = now_ms();
            cmd.now_ms = (uint32_t)now;
            cmd.deadline_ms = (uint32_t)now + 1000u;
        }
        genesis_reply_t reply;
        uint64_t t0 = now_ns();
        if (trace)
            printf("TRACE SEND seq=%u t=%llu\n", cmd.seq,
                   (unsigned long long)t0);
        if (arm_ipc_timeout() != 0) {
            printf("BENCH TimerTimeout error at trip %ld\n", i);
            return 2;
        }
        int rc = MsgSend(coid, &cmd, sizeof cmd, &reply, sizeof reply);
        uint64_t t1 = now_ns();
        uint64_t dt = t1 - t0;
        if (rc != 0) {
            printf("BENCH MsgSend error at trip %ld\n", i);
            return 2;
        }
        if (trace)
            printf("TRACE DONE seq=%u t=%llu\n", cmd.seq,
                   (unsigned long long)t1);
        printf("SAMPLE %.3f\n", (double)dt / 1000.0);
    }
    printf("PERF_DONE n=%ld\n", n);
    return 0;
}

int main(int argc, char **argv) {
    int coid = name_open(GENESIS_ATTACH_NAME, 0);
    if (coid < 0) {
        printf("FAIL faultinject: guard not found (start genesis_guard first)\n");
        return 2;
    }
    if (argc > 1 && strcmp(argv[1], "probe") == 0) {
        if (argc == 4 && strcmp(argv[2], "state") == 0)
            return run_state_probe(coid, argv[3]);
        if (argc != 3 && argc != 4) {
            printf("PROBE usage: genesis_faultinject probe <linear_mps|estop> [seq]\n");
            return 2;
        }
        uint32_t pseq = 1;
        if (argc == 4) {
            char *send = NULL;
            unsigned long pv = strtoul(argv[3], &send, 10);
            if (send == argv[3] || *send != '\0' || pv == 0 || pv > 0xFFFFFFFFUL) {
                printf("PROBE usage: seq must be 1..4294967295\n");
                return 2;
            }
            pseq = (uint32_t)pv;
        }
        return run_probe(coid, argv[2], pseq);
    }
    if (argc > 1 && strcmp(argv[1], "bench") == 0) {
        if (argc != 3) {
            printf("BENCH usage: genesis_faultinject bench <1..100000>\n");
            return 2;
        }
        return run_bench(coid, argv[2]);
    }
    if (argc > 1) {
        printf("FAIL faultinject: unknown mode '%s'\n", argv[1]);
        return 2;
    }
    uint32_t seq = 0;
    genesis_cmd_t cmd;
    uint64_t t;

    /* 1. nominal: must ALLOW */
    memset(&cmd, 0, sizeof cmd);
    cmd.magic = GENESIS_PROTOCOL_MAGIC;
    cmd.version = GENESIS_PROTOCOL_VERSION;
    cmd.req_state = GENESIS_ST_NOMINAL;
    cmd.seq = ++seq;
    t = now_ms();
    cmd.now_ms = (uint32_t)t;
    cmd.deadline_ms = (uint32_t)t + 30u;
    cmd.linear_mps = FI_CRUISE;
    cmd.sensor_age_ms = 0;
    cmd.sim_connected = 1;
    check(coid, "nominal", &cmd, GENESIS_ALLOW, GENESIS_R_OK, GENESIS_ST_NOMINAL);

    /* 2. over-limit speed: DENY, no latch */
    cmd.seq = ++seq;
    t = now_ms();
    cmd.now_ms = (uint32_t)t;
    cmd.deadline_ms = (uint32_t)t + 30u;
    cmd.linear_mps = FI_OVER;
    check(coid, "over_limit", &cmd, GENESIS_DENY, GENESIS_R_SPEED_OVER_LIMIT,
          GENESIS_ST_NOMINAL);
    cmd.linear_mps = FI_CRUISE;

    /* 3. replayed sequence: DENY. Only ACCEPTED seqs are consumed, so we
     * replay seq 1 (accepted in step 1), not seq 2 (denied in step 2). */
    cmd.seq = 1;
    t = now_ms();
    cmd.now_ms = (uint32_t)t;
    cmd.deadline_ms = (uint32_t)t + 30u;
    check(coid, "replay_seq", &cmd, GENESIS_DENY, GENESIS_R_STALE_SEQ,
          GENESIS_ST_NOMINAL);
    cmd.seq = ++seq;

    /* 4. overdue deadline: DENY */
    t = now_ms();
    cmd.now_ms = (uint32_t)t;
    cmd.deadline_ms = (uint32_t)t - 50u;
    check(coid, "overdue", &cmd, GENESIS_DENY, GENESIS_R_OVERDUE_DEADLINE,
          GENESIS_ST_NOMINAL);
    cmd.seq = ++seq;

    /* 5. unsupported protocol version: DENY + latch SAFE_STOP */
    t = now_ms();
    cmd.now_ms = (uint32_t)t;
    cmd.deadline_ms = (uint32_t)t + 30u;
    cmd.version = 99;
    check(coid, "bad_version", &cmd, GENESIS_DENY, GENESIS_R_BAD_VERSION,
          GENESIS_ST_SAFE_STOP);
    cmd.version = GENESIS_PROTOCOL_VERSION;
    cmd.seq = ++seq;

    /* 6. NaN velocity: DENY MALFORMED (integrity checks precede state) */
    t = now_ms();
    cmd.now_ms = (uint32_t)t;
    cmd.deadline_ms = (uint32_t)t + 30u;
    cmd.linear_mps = NAN;
    check(coid, "nan_linear", &cmd, GENESIS_DENY, GENESIS_R_MALFORMED,
          GENESIS_ST_SAFE_STOP);
    cmd.linear_mps = FI_CRUISE;
    cmd.seq = ++seq;

    /* 7. corrupted magic: DENY + latch SAFE_STOP */
    t = now_ms();
    cmd.now_ms = (uint32_t)t;
    cmd.deadline_ms = (uint32_t)t + 30u;
    cmd.magic = 0xDEADBEEFu;
    check(coid, "bad_magic", &cmd, GENESIS_DENY, GENESIS_R_BAD_MAGIC,
          GENESIS_ST_SAFE_STOP);
    cmd.magic = GENESIS_PROTOCOL_MAGIC;
    cmd.seq = ++seq;

    /* 8. truncated frame: DENY BAD_SIZE (guard sees sender byte count) */
    t = now_ms();
    cmd.now_ms = (uint32_t)t;
    cmd.deadline_ms = (uint32_t)t + 30u;
    check_n(coid, "short_frame", &cmd, sizeof cmd - 4,
            GENESIS_DENY, GENESIS_R_BAD_SIZE, GENESIS_ST_SAFE_STOP);
    cmd.seq = ++seq;

    /* 9. nominal after latch: must stay DENIED (safe stop holds) */
    t = now_ms();
    cmd.now_ms = (uint32_t)t;
    cmd.deadline_ms = (uint32_t)t + 30u;
    check(coid, "locked_nominal", &cmd, GENESIS_DENY, GENESIS_R_BAD_TRANSITION,
          GENESIS_ST_SAFE_STOP);

    printf("faultinject: %s\n", failures == 0 ? "ALL 9 CHECKS PASS" : "FAILURES PRESENT");
    return failures == 0 ? 0 : 1;
}
#else
int main(void) {
    printf("genesis_faultinject host stub: native QNX IPC requires QNX Neutrino.\n");
    return 2;
}
#endif

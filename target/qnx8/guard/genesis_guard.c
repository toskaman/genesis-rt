/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * genesis_guard: policy-enforcing command server.
 * QNX: named channel, MsgReceive/MsgReply loop, monotonic clock checks.
 * Host (non-QNX): informative stub; policy logic is tested through
 * target/qnx8/host_tests/guard_vector instead.
 */
#include <stdio.h>
#include <string.h>
#include "genesis_ipc.h"
#include "guard_policy.h"

#ifdef __QNXNTO__
#include <errno.h>
#include <signal.h>
#include <stdlib.h>
#include <sys/dispatch.h>
#include <sys/neutrino.h>
#include <time.h>
/* Machine-specific limits BAKED IN at build time from the generated
 * header (`genesis-rt generate` output, `-I.` on the compile line).
 * A missing/stale header is a compile error, never a silent default:
 * the guard cannot run with limits from another machine. */
#include "genesis_config_gen.h"

static genesis_limits_t g_limits = {GENESIS_MAX_LINEAR_MPS,
                                    GENESIS_MAX_ANGULAR_RADPS,
                                    GENESIS_FRESHNESS_LIMIT_MS};
static genesis_guard_ctx_t g_ctx = {0, GENESIS_ST_NOMINAL, 0};
static uint64_t g_allows = 0;
static uint64_t g_denies = 0;
static uint32_t g_last_reason = GENESIS_R_OK;
static uint32_t g_ndropped = 0;
static uint64_t g_fwd_ok = 0;
static uint64_t g_fwd_fail = 0;
static int g_dev_coid = -1;

/* Operator reset (Omega2 §3.3): SIGUSR1 arms the policy's one-shot
 * reset latch so the NEXT command may leave SAFE_STOP. The handler
 * only sets a flag (async-signal-safe); the loop arms the latch.
 * Without this wire the latch was dead-on-target: estop latched
 * forever until process restart. Reset = deliberate local-operator
 * action (`kill -s USR1 <guard pid>`); a failed handler install
 * leaves the latch terminal, which is the safe direction. */
static volatile sig_atomic_t g_reset_req = 0;

static void on_sigusr1(int signo) {
    (void)signo;
    g_reset_req = 1;
}

#define GUARD_FWD_TIMEOUT_NS 500000000ULL /* 500 ms: never wedge the loop */

/* Forward one validated command to the virtual device. Best-effort
 * DELIVERY, strict REPORTING: a dead device never flips an ALLOW to a
 * DENY (validation is about the command), but every miss increments
 * nfwd_fail in telemetry. Connection is lazy + self-healing. */
static void forward_to_device(const genesis_cmd_t *cmd, uint32_t state_out) {
    if (g_dev_coid < 0)
        g_dev_coid = name_open(GENESIS_DEVICE_ATTACH_NAME, 0);
    if (g_dev_coid < 0) {
        g_fwd_fail++;
        return;
    }
    genesis_fwd_t fwd;
    fwd.magic = GENESIS_FWD_MAGIC;
    fwd.version = GENESIS_FWD_VERSION;
    fwd.reserved = 0;
    fwd.seq = cmd->seq;
    fwd.linear_mps = cmd->linear_mps;
    fwd.angular_radps = cmd->angular_radps;
    fwd.state_out = state_out;
    genesis_fwd_ack_t ack;
    memset(&ack, 0xFF, sizeof ack);
    struct sigevent ev;
    uint64_t to = GUARD_FWD_TIMEOUT_NS;
    memset(&ev, 0, sizeof ev);
    ev.sigev_notify = SIGEV_UNBLOCK;
    if (TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_SEND | _NTO_TIMEOUT_REPLY,
                     &ev, &to, NULL) == 0 &&
        MsgSend(g_dev_coid, &fwd, sizeof fwd, &ack, sizeof ack) == 0 &&
        ack.applied == 1) {
        g_fwd_ok++;
    } else {
        g_fwd_fail++;
        name_close(g_dev_coid); /* force re-open next time: stale coid? */
        g_dev_coid = -1;
    }
}

static uint64_t trace_now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000u + (uint64_t)ts.tv_nsec;
}

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;
    /* IPC timeline trace (Wave 11 S12): default off. */
    const char *trace_env = getenv("GENESIS_IPC_TRACE");
    int trace = trace_env != NULL && strcmp(trace_env, "1") == 0;
    name_attach_t *attach = name_attach(NULL, GENESIS_ATTACH_NAME, 0);
    if (attach == NULL) {
        fprintf(stderr, "guard: name_attach failed: %s\n", strerror(errno));
        return 1;
    }
    printf("guard: attached as '%s' chid=%d\n", GENESIS_ATTACH_NAME, attach->chid);
    printf("guard: machine=%s limits linear=%.3f angular=%.3f freshness=%ums\n",
           GENESIS_MACHINE_ID, g_limits.max_linear_speed_mps,
           g_limits.max_angular_speed_radps, g_limits.freshness_limit_ms);
    if (signal(SIGUSR1, on_sigusr1) == SIG_ERR)
        fprintf(stderr, "guard: WARNING: SIGUSR1 handler not installed; "
                        "SAFE_STOP latch is terminal this run\n");
    else
        printf("guard: operator reset armed via SIGUSR1\n");
    fflush(stdout);
    for (;;) {
        union {
            genesis_cmd_t cmd;
            genesis_stats_req_t stats;
            unsigned char raw[64];
        } msg;
        struct _msg_info info;
        memset(&msg, 0, sizeof msg);
        memset(&info, 0, sizeof info);
        int rcvid = MsgReceive(attach->chid, &msg, sizeof msg, &info);
        if (rcvid < 0) {
            fprintf(stderr, "guard: MsgReceive failed: %s\n", strerror(errno));
            continue;
        }
        if (rcvid == 0) {
            /* Pulse: never reply, never treat as a command. */
            continue;
        }
        /* The policy sees the SENDER's byte count, never our buffer size:
         * short or overlong frames must hit BAD_SIZE. */
        uint32_t nbytes = (uint32_t)info.msglen;
        if (nbytes == (uint32_t)sizeof(msg.stats) &&
            msg.stats.magic == GENESIS_STATS_MAGIC &&
            msg.stats.version == GENESIS_STATS_VERSION) {
            genesis_stats_reply_t s;
            s.state = g_ctx.state;
            s.last_reason = g_last_reason;
            s.last_seq = g_ctx.last_seq;
            s.ndropped = g_ndropped;
            s.allows = g_allows;
            s.denies = g_denies;
            s.nfwd_ok = g_fwd_ok;
            s.nfwd_fail = g_fwd_fail;
            MsgReply(rcvid, EOK, &s, sizeof s);
            continue;
        }
        if (g_reset_req) {
            g_reset_req = 0;
            g_ctx.reset_armed = 1;
            printf("guard: operator reset armed (SIGUSR1)\n");
            fflush(stdout);
        }
        if (trace)
            printf("TRACE RECV seq=%u t=%llu\n", msg.cmd.seq,
                   (unsigned long long)trace_now_ns());
        genesis_verdict_t v =
            genesis_guard_decide(&msg.cmd, nbytes, &g_ctx, &g_limits);
        g_ctx.state = v.state_out;
        if (v.decision == GENESIS_ALLOW) {
            g_allows++;
            forward_to_device(&msg.cmd, v.state_out);
        } else {
            g_denies++;
            g_last_reason = v.reason;
            if (v.reason == GENESIS_R_BAD_MAGIC || v.reason == GENESIS_R_BAD_VERSION ||
                v.reason == GENESIS_R_BAD_SIZE || v.reason == GENESIS_R_MALFORMED)
                g_ndropped++;
        }
        genesis_reply_t reply;
        reply.decision = v.decision;
        reply.reason = v.reason;
        reply.state_out = v.state_out;
        if (trace) {
            printf("TRACE REPLY seq=%u t=%llu decision=%s\n",
                   msg.cmd.seq,
                   (unsigned long long)trace_now_ns(),
                   v.decision == GENESIS_ALLOW ? "ALLOW" : "DENY");
            fflush(stdout); /* slain, never exits: flush per probe */
        }
        MsgReply(rcvid, EOK, &reply, sizeof reply);
        printf("guard: seq=%u decision=%s reason=%s state=%u\n", msg.cmd.seq,
               v.decision == GENESIS_ALLOW ? "ALLOW" : "DENY",
               genesis_reason_str(v.reason), v.state_out);
        fflush(stdout);
    }
    /* unreachable */
    return 0;
}
#else
int main(void) {
    printf("genesis_guard host stub: native QNX IPC transport requires QNX Neutrino.\n"
           "Policy logic is verified on host via guard_vector; see host_tests/.\n");
    return 2;
}
#endif

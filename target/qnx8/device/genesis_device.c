/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * genesis_device: SIMULATED actuator/sensor endpoint.
 * Receives ONLY guard-forwarded validated commands (GENESIS_FWD_MAGIC)
 * over native message passing, integrates virtual pose, and serves
 * state queries. The controller never talks to this process (no-bypass
 * is enforced by construction and audited: every applied command logs
 * its sender pid). No physical motor support by design (simulation).
 */
#include <stdio.h>
#include <string.h>
#include "genesis_ipc.h"
#include "device_model.h"

#ifdef __QNXNTO__
#include <errno.h>
#include <sys/dispatch.h>
#include <sys/neutrino.h>
#include <time.h>
#include <unistd.h>

static uint64_t mono_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000ull + (uint64_t)ts.tv_nsec / 1000000ull;
}

int main(int argc, char **argv) {
    int belt_mode = argc > 1 && strcmp(argv[1], "belt") == 0;
    if (argc > 1 && !belt_mode) {
        fprintf(stderr, "device: usage: genesis_device [belt]\n");
        return 2;
    }
    name_attach_t *attach =
        name_attach(NULL, GENESIS_DEVICE_ATTACH_NAME, NAME_FLAG_ATTACH_GLOBAL);
    if (attach == NULL) {
        fprintf(stderr, "device: name_attach failed: %s\n", strerror(errno));
        return 1;
    }
    genesis_device_state_t dev;
    genesis_device_state_init(&dev);
    genesis_belt_state_t belt;
    genesis_belt_state_init(&belt);
    printf("device: attached as '%s' (%s mode); awaiting guard-forwarded commands.\n",
           GENESIS_DEVICE_ATTACH_NAME, belt_mode ? "belt" : "pose");
    fflush(stdout);

    uint8_t buf[64];
    for (;;) {
        struct _msg_info info;
        memset(buf, 0, sizeof buf);
        int rcvid = MsgReceive(attach->chid, buf, sizeof buf, &info);
        if (rcvid < 0) {
            if (errno == EINTR)
                continue;
            fprintf(stderr, "device: MsgReceive failed: %s\n", strerror(errno));
            return 1;
        }
        if (rcvid == 0) {
            continue; /* pulse: never replied */
        }
        uint32_t msglen = (uint32_t)info.msglen;
        if (msglen == sizeof(genesis_fwd_t) &&
            ((genesis_fwd_t *)buf)->magic == GENESIS_FWD_MAGIC &&
            ((genesis_fwd_t *)buf)->version == GENESIS_FWD_VERSION) {
            genesis_fwd_t *fwd = (genesis_fwd_t *)buf;
            genesis_fwd_ack_t ack;
            memset(&ack, 0, sizeof ack);
            /* Audit trail: every apply pins its sender pid. In a correct
             * system all of these equal the guard pid (no bypass). */
            if (belt_mode) {
                ack.applied = (uint32_t)genesis_belt_apply(
                    &belt, (double)fwd->linear_mps, fwd->seq, mono_ms());
                printf("device: APPLY seq=%u v=%.3f w=%.3f from_pid=%d applied=%u "
                       "belt_pos=%.3f belt_jammed=%d\n",
                       fwd->seq, (double)fwd->linear_mps,
                       (double)fwd->angular_radps, info.pid, ack.applied,
                       belt.position_m, belt.jammed);
            } else {
                ack.applied = (uint32_t)genesis_device_apply(
                    &dev, (double)fwd->linear_mps, (double)fwd->angular_radps,
                    fwd->seq, mono_ms());
                printf("device: APPLY seq=%u v=%.3f w=%.3f from_pid=%d applied=%u "
                       "x=%.3f theta=%.3f\n",
                       fwd->seq, (double)fwd->linear_mps,
                       (double)fwd->angular_radps, info.pid, ack.applied,
                       dev.x, dev.theta);
            }
            fflush(stdout);
            MsgReply(rcvid, EOK, &ack, sizeof ack);
        } else if (msglen == sizeof(genesis_devstate_req_t) &&
                   ((genesis_devstate_req_t *)buf)->magic ==
                       GENESIS_DEVSTATE_MAGIC &&
                   ((genesis_devstate_req_t *)buf)->version ==
                       GENESIS_DEVSTATE_VERSION) {
            genesis_devstate_reply_t rep;
            if (belt_mode) {
                genesis_belt_watchdog(&belt, mono_ms());
                rep.x = belt.position_m;
                rep.y = 0.0;
                rep.theta = 0.0;
                rep.v = (float)belt.speed_mps;
                rep.w = 0.0f;
                rep.applied = (uint32_t)(belt.applied & 0xFFFFFFFFu);
                rep.last_seq = belt.last_seq;
            } else {
                genesis_device_watchdog(&dev, mono_ms());
                rep.x = dev.x;
                rep.y = dev.y;
                rep.theta = dev.theta;
                rep.v = (float)dev.v;
                rep.w = (float)dev.w;
                rep.applied = (uint32_t)(dev.applied & 0xFFFFFFFFu);
                rep.last_seq = dev.last_seq;
            }
            MsgReply(rcvid, EOK, &rep, sizeof rep);
        } else {
            static uint64_t nbad = 0;
            nbad++;
            fprintf(stderr, "device: rejected malformed frame len=%u from_pid=%d\n",
                    msglen, info.pid);
            MsgError(rcvid, EBADMSG);
        }
    }
    return 0;
}
#else
int main(void) {
    printf("device: virtual endpoint ready (simulation only, no physical I/O).\n"
           "device: host build; logic verified through the device_model harness.\n");
    return 2;
}
#endif

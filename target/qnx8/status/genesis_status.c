/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * genesis_status: read-only QNX resource manager exposing
 * /dev/genesis/status with LIVE guard state + counters queried over
 * native message passing on every read. If the guard is unreachable
 * the file says so explicitly instead of serving stale numbers.
 * QNX-only; host builds produce an informative stub.
 */
#include <stdio.h>
#include <string.h>
#include "genesis_ipc.h"

#ifdef __QNXNTO__
#include <errno.h>
#include <sys/dispatch.h>
#include <sys/iofunc.h>
#include <sys/neutrino.h>
#include <sys/resmgr.h>
#include <time.h>
#include "guard_policy.h"

static resmgr_connect_funcs_t g_connect_funcs;
static resmgr_io_funcs_t g_io_funcs;
static iofunc_attr_t g_attr;

static char g_status[512] = "state=? (no read yet)\n";
static int g_coid = -1;
static int g_dev_coid = -1;

#define STATUS_IPC_TIMEOUT_NS 2000000000ULL /* 2 s */

static void refresh_status(void) {
    if (g_coid < 0)
        g_coid = name_open(GENESIS_ATTACH_NAME, 0);
    if (g_coid < 0) {
        snprintf(g_status, sizeof g_status,
                 "state=? allows=? denies=? last_reason=? (guard unreachable)\n");
        return;
    }
    genesis_stats_req_t req;
    genesis_stats_reply_t rep;
    req.magic = GENESIS_STATS_MAGIC;
    req.version = GENESIS_STATS_VERSION;
    req.reserved = 0;
    memset(&rep, 0xFF, sizeof rep);
    struct sigevent ev;
    uint64_t to = STATUS_IPC_TIMEOUT_NS;
    memset(&ev, 0, sizeof ev);
    ev.sigev_notify = SIGEV_UNBLOCK;
    if (!(TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_SEND | _NTO_TIMEOUT_REPLY,
                       &ev, &to, NULL) == 0 &&
          MsgSend(g_coid, &req, sizeof req, &rep, sizeof rep) == 0)) {
        name_close(g_coid);
        g_coid = -1;
        snprintf(g_status, sizeof g_status,
                 "state=? allows=? denies=? last_reason=? (guard unreachable)\n");
        return;
    }
    int n = snprintf(g_status, sizeof g_status,
                     "state=%u allows=%llu denies=%llu last_reason=%s last_seq=%u dropped=%u fwd_ok=%llu fwd_fail=%llu",
                     rep.state, (unsigned long long)rep.allows,
                     (unsigned long long)rep.denies,
                     genesis_reason_str(rep.last_reason),
                     rep.last_seq, rep.ndropped,
                     (unsigned long long)rep.nfwd_ok,
                     (unsigned long long)rep.nfwd_fail);
    /* Device leg: best effort, honestly labelled. A missing device must
     * never poison the guard numbers above. */
    if (g_dev_coid < 0)
        g_dev_coid = name_open(GENESIS_DEVICE_ATTACH_NAME, 0);
    if (g_dev_coid >= 0) {
        genesis_devstate_req_t dreq;
        genesis_devstate_reply_t drep;
        dreq.magic = GENESIS_DEVSTATE_MAGIC;
        dreq.version = GENESIS_DEVSTATE_VERSION;
        dreq.reserved = 0;
        memset(&drep, 0xFF, sizeof drep);
        memset(&ev, 0, sizeof ev);
        ev.sigev_notify = SIGEV_UNBLOCK;
        if (TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_SEND | _NTO_TIMEOUT_REPLY,
                         &ev, &to, NULL) == 0 &&
            MsgSend(g_dev_coid, &dreq, sizeof dreq, &drep, sizeof drep) == 0) {
            snprintf(g_status + n, sizeof g_status - (size_t)n,
                     " dev_x=%.3f dev_theta=%.3f dev_v=%.3f dev_applied=%u dev_seq=%u\n",
                     drep.x, drep.theta, (double)drep.v,
                     drep.applied, drep.last_seq);
            return;
        }
        name_close(g_dev_coid);
        g_dev_coid = -1;
    }
    snprintf(g_status + n, sizeof g_status - (size_t)n, " (device unreachable)\n");
}

int io_read(resmgr_context_t *ctp, io_read_t *msg, RESMGR_OCB_T *ocb) {
    int status;
    iofunc_ocb_t *o = (iofunc_ocb_t *)ocb; /* default connect funcs: OCBs are iofunc_ocb_t */
    if ((status = iofunc_read_verify(ctp, msg, ocb, NULL)) != EOK)
        return status;
    if ((msg->i.xtype & _IO_XTYPE_MASK) != _IO_XTYPE_NONE)
        return ENOSYS;
    /* Refresh once per read sequence so multi-read cats see one snapshot. */
    if (o->offset == 0)
        refresh_status();
    size_t len = strlen(g_status);
    size_t off = (size_t)o->offset;
    size_t nbytes = 0;
    if (off < len) {
        nbytes = len - off;
        if (nbytes > (size_t)msg->i.nbytes)
            nbytes = (size_t)msg->i.nbytes;
    }
    _IO_SET_READ_NBYTES(ctp, nbytes);
    if (nbytes > 0) {
        MsgReply(ctp->rcvid, (int)nbytes, g_status + off, (int)nbytes);
        o->offset += (off_t)nbytes;
    } else {
        MsgReply(ctp->rcvid, EOK, NULL, 0);
    }
    return _RESMGR_NOREPLY;
}

int main(int argc, char **argv) {
    const char *path = argc > 1 ? argv[1] : "/dev/genesis/status";
    dispatch_t *dpp = dispatch_create();
    if (dpp == NULL) {
        fprintf(stderr, "status: dispatch_create failed\n");
        return 1;
    }
    iofunc_func_init(_RESMGR_CONNECT_NFUNCS, &g_connect_funcs,
                     _RESMGR_IO_NFUNCS, &g_io_funcs);
    g_io_funcs.read = io_read;
    iofunc_attr_init(&g_attr, S_IFREG | 0444, NULL, NULL);
    int id = resmgr_attach(dpp, NULL, path, _FTYPE_ANY, 0,
                           &g_connect_funcs, &g_io_funcs, &g_attr);
    if (id < 0) {
        fprintf(stderr, "status: resmgr_attach(%s) failed: %s\n", path, strerror(errno));
        return 1;
    }
    printf("status: serving %s\n", path);
    dispatch_context_t *ctp = dispatch_context_alloc(dpp);
    if (ctp == NULL) {
        fprintf(stderr, "status: dispatch_context_alloc failed\n");
        return 1;
    }
    while ((ctp = dispatch_block(ctp)) != NULL) {
        dispatch_handler(ctp);
    }
    dispatch_context_free(ctp);
    return 0;
}
#else
int main(void) {
    printf("genesis_status host stub: resource managers require QNX Neutrino.\n");
    return 2;
}
#endif

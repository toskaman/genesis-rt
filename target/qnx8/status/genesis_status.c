/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * genesis_status: read-only QNX resource manager exposing
 * /dev/genesis/status with guard state + counters. QNX-only;
 * host builds produce an informative stub.
 */
#include <stdio.h>

#ifdef __QNXNTO__
#include <errno.h>
#include <string.h>
#include <sys/dispatch.h>
#include <sys/iofunc.h>
#include <sys/resmgr.h>

static resmgr_connect_funcs_t g_connect_funcs;
static resmgr_io_funcs_t g_io_funcs;
static iofunc_attr_t g_attr;

static char g_status[256] = "state=1 allows=0 denies=0\n";

int io_read(resmgr_context_t *ctp, io_read_t *msg, RESMGR_OCB_T *ocb) {
    (void)msg;
    (void)ocb;
    size_t len = strlen(g_status);
    _IO_SET_READ_NBYTES(ctp, len);
    MsgReply(ctp->rcvid, (int)len, g_status, (int)len);
    return _RESMGR_NPARTS(0);
}

int main(void) {
    dispatch_t *dpp = dispatch_create();
    if (dpp == NULL) {
        fprintf(stderr, "status: dispatch_create failed\n");
        return 1;
    }
    iofunc_func_init(_RESMGR_CONNECT_NFUNCS, &g_connect_funcs,
                     _RESMGR_IO_NFUNCS, &g_io_funcs);
    g_io_funcs.read = io_read;
    iofunc_attr_init(&g_attr, S_IFREG | 0444, NULL, NULL);
    int id = resmgr_attach(dpp, NULL, "/dev/genesis/status", _FTYPE_ANY, 0,
                           &g_connect_funcs, &g_io_funcs, &g_attr);
    if (id < 0) {
        fprintf(stderr, "status: resmgr_attach failed: %s\n", strerror(errno));
        return 1;
    }
    printf("status: serving /dev/genesis/status\n");
    dispatch_context_t *ctp = dispatch_block(dpp);
    while (ctp != NULL) {
        dispatch_handler(ctp);
        ctp = dispatch_block(dpp);
    }
    return 0;
}
#else
int main(void) {
    printf("genesis_status host stub: resource managers require QNX Neutrino.\n");
    return 2;
}
#endif

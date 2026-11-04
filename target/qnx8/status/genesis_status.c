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
    int status;
    iofunc_ocb_t *o = (iofunc_ocb_t *)ocb; /* default connect funcs: OCBs are iofunc_ocb_t */
    if ((status = iofunc_read_verify(ctp, msg, ocb, NULL)) != EOK)
        return status;
    if ((msg->i.xtype & _IO_XTYPE_MASK) != _IO_XTYPE_NONE)
        return ENOSYS;
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

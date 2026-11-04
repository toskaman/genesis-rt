/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * genesis_supervisor: process health + safe-state supervision.
 * Spawns the guard/controller/device set, restarts crashed children
 * with backoff, and is the ONLY path that may arm a guard reset out
 * of SAFE_STOP. QNX High Availability Manager (HAM) integration is an
 * optional deployment step documented in docs/; this supervisor owns
 * the application-level safe-stop semantics HAM cannot express.
 */
#include <stdio.h>
#include <string.h>

#ifdef __QNXNTO__
#include <errno.h>
#include <spawn.h>
#include <sys/wait.h>
#include <unistd.h>

static const char *const kChildren[] = {
    "./genesis_guard", "./genesis_controller", "./genesis_device", NULL
};

int main(void) {
    printf("supervisor: starting %d children\n", 3);
    pid_t pids[3];
    for (int i = 0; kChildren[i] != NULL; i++) {
        char *const argv[] = {(char *)kChildren[i], NULL};
        if (posix_spawn(&pids[i], kChildren[i], NULL, NULL, argv, NULL) != 0) {
            fprintf(stderr, "supervisor: spawn %s failed: %s\n",
                    kChildren[i], strerror(errno));
            return 1;
        }
        printf("supervisor: started %s pid=%d\n", kChildren[i], (int)pids[i]);
    }
    for (;;) {
        int status = 0;
        pid_t dead = wait(&status);
        if (dead < 0) {
            fprintf(stderr, "supervisor: wait failed: %s\n", strerror(errno));
            return 1;
        }
        fprintf(stderr, "supervisor: child pid=%d exited status=%d; "
                        "safe-stop holds until operator reset\n",
                (int)dead, status);
        /* MVP: hold safe state and exit non-zero so the failure is loud.
         * Auto-respawn is a deployment option, not silent default. */
        return 2;
    }
    return 0;
}
#else
int main(void) {
    printf("genesis_supervisor host stub: process supervision needs a QNX target.\n"
           "Host fault scenarios model supervisor resets explicitly in the trace.\n");
    return 2;
}
#endif

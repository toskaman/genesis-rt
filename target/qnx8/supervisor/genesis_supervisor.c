/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * genesis_supervisor: process health + safe-state supervision.
 * Spawns the guard/controller/device set, restarts crashed children
 * with backoff (bounded: MAX_RESTARTS per child), and stops the whole
 * set loudly when a child keeps dying. The supervisor never leaves
 * survivors behind on give-up: with no guard there is no validated
 * command path, so the set is halted instead of running unguarded.
 * QNX High Availability Manager (HAM) integration is an optional
 * deployment step documented in docs/; this supervisor owns the
 * application-level safe-stop semantics HAM cannot express.
 * Device binding (Omega2 §3.2): the device is spawned with the
 * guard pid (--guard-pid), pre-pinning its forward channel with no
 * first-sender race. A guard respawn therefore restarts the device
 * as a set (REBIND, no death counted: halt_one reaps the old pid
 * so the main loop never sees it). Controller/device deaths
 * respawn independently; the device keeps its pin because its
 * guard did not change.
 */
#include <stdio.h>
#include <string.h>

#ifdef __QNXNTO__
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <spawn.h>
#include <sys/wait.h>
#include <unistd.h>

#define NCHILD 3
#define MAX_RESTARTS 3

static const char *const kChildren[NCHILD] = {
    "./genesis_guard", "./genesis_controller", "./genesis_device"
};
static const unsigned kBackoffS[MAX_RESTARTS] = {1, 2, 4};
/* One log per child (O_APPEND): children must never share the
 * supervisor's own stdout/stderr. With inherited descriptors, four
 * writers race on one file offset and a child write can land mid-line
 * on a RESPAWN/GIVE_UP audit line, destroying the evidence the matrix
 * asserts (observed natively: "supervisor: RESPA" + guard chatter).
 * Isolated logs keep sup.log a single-writer audit trail. */
static const char *const kChildLogs[NCHILD] = {
    "sup-guard.log", "sup-controller.log", "sup-device.log"
};

static pid_t g_pids[NCHILD] = {-1, -1, -1};
static unsigned g_deaths[NCHILD] = {0, 0, 0};

static int spawn_child(int idx) {
    char *plain[] = {(char *)kChildren[idx], NULL};
    char pidbuf[32];
    char *device[] = {(char *)kChildren[2], (char *)"--guard-pid",
                      pidbuf, NULL};
    char **argv = plain;
    if (idx == 2 && g_pids[0] > 0) {
        snprintf(pidbuf, sizeof pidbuf, "%d", (int)g_pids[0]);
        argv = device;
    }
    pid_t pid = -1;
    posix_spawn_file_actions_t fa;
    int rc = posix_spawn_file_actions_init(&fa);
    if (rc == 0)
        rc = posix_spawn_file_actions_addopen(&fa, STDOUT_FILENO, kChildLogs[idx],
                                              O_WRONLY | O_CREAT | O_APPEND, 0644);
    if (rc == 0)
        rc = posix_spawn_file_actions_adddup2(&fa, STDOUT_FILENO, STDERR_FILENO);
    if (rc == 0)
        rc = posix_spawn(&pid, kChildren[idx], &fa, NULL, argv, NULL);
    posix_spawn_file_actions_destroy(&fa);
    if (rc != 0) {
        fprintf(stderr, "supervisor: spawn %s failed: %s\n",
                kChildren[idx], strerror(rc));
        return -1;
    }
    g_pids[idx] = pid;
    printf("supervisor: started %s pid=%d\n", kChildren[idx], (int)pid);
    fflush(stdout);
    return 0;
}

static int find_child(pid_t pid) {
    for (int i = 0; i < NCHILD; i++)
        if (g_pids[i] == pid)
            return i;
    return -1;
}

/* Stop one child synchronously for supervisor-directed restarts.
 * SIGTERM, bounded wait, SIGKILL, reap: the reaped pid never
 * reaches the main wait() loop, so no death is counted. A stale
 * g_pids entry can only name a process dead for milliseconds
 * (wait() would otherwise have reaped it), so pid reuse between
 * death and this kill is not a practical hazard; ESRCH is harmless. */
static void halt_one(int idx) {
    pid_t pid = g_pids[idx];
    if (pid <= 0)
        return;
    g_pids[idx] = -1;
    kill(pid, SIGTERM);
    for (int i = 0; i < 3; i++) {
        if (waitpid(pid, NULL, WNOHANG) == pid)
            return;
        sleep(1);
    }
    kill(pid, SIGKILL);
    while (waitpid(pid, NULL, 0) < 0 && errno == EINTR)
        ;
}

/* Stop every survivor, then report failure loudly. No orphaned set. */
static void halt_set(void) {
    for (int i = 0; i < NCHILD; i++)
        if (g_pids[i] > 0)
            kill(g_pids[i], SIGTERM);
    sleep(2);
    for (int i = 0; i < NCHILD; i++) {
        if (g_pids[i] > 0 && kill(g_pids[i], 0) == 0)
            kill(g_pids[i], SIGKILL);
        g_pids[i] = -1;
    }
    while (waitpid(-1, NULL, WNOHANG) > 0)
        ;
}

int main(void) {
    printf("supervisor: starting %d children\n", NCHILD);
    for (int i = 0; i < NCHILD; i++) {
        if (spawn_child(i) != 0) {
            halt_set();
            return 1;
        }
    }
    for (;;) {
        int status = 0;
        pid_t dead = wait(&status);
        if (dead < 0) {
            fprintf(stderr, "supervisor: wait failed: %s\n", strerror(errno));
            halt_set();
            return 1;
        }
        int idx = find_child(dead);
        if (idx < 0) {
            fprintf(stderr, "supervisor: reaped unknown pid=%d status=%d\n",
                    (int)dead, status);
            continue;
        }
        g_pids[idx] = -1;
        g_deaths[idx]++;
        if (g_deaths[idx] > MAX_RESTARTS) {
            fprintf(stderr, "supervisor: GIVE_UP %s deaths=%u; "
                            "halting set, safe-stop holds until operator reset\n",
                    kChildren[idx], g_deaths[idx]);
            fflush(stderr);
            halt_set();
            return 2;
        }
        unsigned wait_s = kBackoffS[g_deaths[idx] - 1];
        fprintf(stderr, "supervisor: RESPAWN %s deaths=%u backoff=%us status=%d\n",
                kChildren[idx], g_deaths[idx], wait_s, status);
        fflush(stderr); /* audit lines must survive a SIGTERM before exit */
        sleep(wait_s);
        if (spawn_child(idx) != 0) {
            halt_set();
            return 1;
        }
        if (idx == 0) {
            /* New guard pid: the device pre-pin is stale. Restart
             * the device as a set (REBIND, not RESPAWN: no death
             * counted, old pid reaped above the main loop). */
            halt_one(2);
            if (spawn_child(2) != 0) {
                halt_set();
                return 1;
            }
            fprintf(stderr, "supervisor: REBIND ./genesis_device to "
                            "guard pid=%d (guard respawn)\n",
                    (int)g_pids[0]);
            fflush(stderr);
        }
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

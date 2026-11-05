/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * genesis_cellcheck: on-target cell interlock selftest.
 * Replays the transfer-interlock truth table from the generated cell
 * policy header (genesis_cell_policy.h) plus policy bound checks, and
 * reports per-vector PASS/FAIL. Portable C (no QNX headers) so the same
 * selftest runs on the host toolchain and on the QNX target.
 * Usage: genesis_cellcheck selftest. Exit 0 only if all checks pass.
 */
#include <stdio.h>
#include <string.h>
#include "genesis_cell_policy.h"

struct vector {
    const char *name;
    int phase, fresh, presence, jammed, estop, expect;
};

static const struct vector kVectors[] = {
    /* Mirrors host cell_transfer_allowed() truth table. */
    {"allow_nominal",  GENESIS_CELL_TRANSFERRING, 1, 1, 0, 0, 1},
    {"deny_predock",   GENESIS_CELL_AT_STATION,  1, 1, 0, 0, 0},
    {"deny_enroute",   GENESIS_CELL_ENROUTE,     1, 1, 0, 0, 0},
    {"deny_stale",     GENESIS_CELL_TRANSFERRING, 0, 1, 0, 0, 0},
    {"deny_no_presence", GENESIS_CELL_TRANSFERRING, 1, 0, 0, 0, 0},
    {"deny_jam",       GENESIS_CELL_TRANSFERRING, 1, 1, 1, 0, 0},
    {"deny_estop",     GENESIS_CELL_TRANSFERRING, 1, 1, 0, 1, 0},
    {"deny_complete",  GENESIS_CELL_COMPLETE,    1, 1, 0, 0, 0},
    {"deny_safe",      GENESIS_CELL_SAFE,        1, 1, 0, 0, 0},
};

static int check_id(const char *id)
{
    /* IR ids: [a-z0-9][a-z0-9-_]{0,63}; reject anything else. */
    size_t i, n;
    if (id == NULL)
        return 0;
    n = strlen(id);
    if (n < 1 || n > 64)
        return 0;
    if (!((id[0] >= 'a' && id[0] <= 'z') || (id[0] >= '0' && id[0] <= '9')))
        return 0;
    for (i = 1; i < n; i++) {
        char c = id[i];
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')
              || c == '-' || c == '_'))
            return 0;
    }
    return 1;
}

int main(int argc, char **argv)
{
    size_t i, nvec = sizeof(kVectors) / sizeof(kVectors[0]);
    int passed = 0, total = 0, ok;

    if (argc != 2 || strcmp(argv[1], "selftest") != 0) {
        fprintf(stderr, "usage: genesis_cellcheck selftest\n");
        return 2;
    }
    for (i = 0; i < nvec; i++) {
        const struct vector *v = &kVectors[i];
        int got = genesis_cell_transfer_allowed(v->phase, v->fresh,
                                                v->presence, v->jammed,
                                                v->estop);
        ok = (got == v->expect);
        total++;
        passed += ok;
        printf("CELLCHECK %-16s %s (want %d got %d)\n",
               v->name, ok ? "PASS" : "FAIL", v->expect, got);
    }
    ok = GENESIS_CELL_STATION_X_M > 0.0 && GENESIS_CELL_STATION_X_M <= 12.0;
    total++;
    passed += ok;
    printf("CELLCHECK %-16s %s (station_x=%g)\n",
           "policy_station", ok ? "PASS" : "FAIL",
           (double)GENESIS_CELL_STATION_X_M);
    ok = GENESIS_CELL_TRANSFER_TICKS >= 1 && GENESIS_CELL_TRANSFER_TICKS <= 600;
    total++;
    passed += ok;
    printf("CELLCHECK %-16s %s (ticks=%d)\n",
           "policy_ticks", ok ? "PASS" : "FAIL",
           GENESIS_CELL_TRANSFER_TICKS);
    ok = check_id(GENESIS_CELL_PRESENCE_ID)
        && check_id(GENESIS_CELL_AMR_ACTUATOR)
        && check_id(GENESIS_CELL_BELT_ACTUATOR);
    total++;
    passed += ok;
    printf("CELLCHECK %-16s %s\n", "policy_ids", ok ? "PASS" : "FAIL");
    printf("CELL_POLICY: %s %d/%d\n",
           passed == total ? "PASS" : "FAIL", passed, total);
    return passed == total ? 0 : 1;
}

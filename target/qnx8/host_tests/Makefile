# Host conformance harness build (no QNX SDK needed).
CC ?= cc
CFLAGS = -O1 -Wall -Wextra -I../include -I../common

all: guard_vector

guard_vector: guard_vector.c ../common/guard_policy.c
	$(CC) $(CFLAGS) -o $@ $^

check: guard_vector
	printf 'LIMITS 1.2 1.0 100\n47454E31 1 1 1 0 50 0.5 0.0 1 0 1 0 1\n47454E31 1 1 2 10 60 5.0 0.0 1 0 1 0 1\n' | ./guard_vector

clean:
	rm -f guard_vector guard_vector.exe

.PHONY: all check clean

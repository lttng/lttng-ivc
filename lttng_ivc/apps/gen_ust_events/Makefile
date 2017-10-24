# Copyright (C) 2017  Jonathan Rajotte <jonathan.rajotte-julien@efficios.com>
#
# THIS MATERIAL IS PROVIDED AS IS, WITH ABSOLUTELY NO WARRANTY EXPRESSED
# OR IMPLIED.  ANY USE IS AT YOUR OWN RISK.
#
# Permission is hereby granted to use or copy this program for any
# purpose,  provided the above notices are retained on all copies.
# Permission to modify the code and to distribute modified code is
# granted, provided the above notices are retained, and a notice that
# the code was modified is included with the above copyright notice.

LIBS = -llttng-ust -ldl
LOCAL_CPPFLAGS += -I.

all: app

.PHONY: app

app: gen-ust-events.o tp.o
	$(CC) -o $@ $(LDFLAGS) $(CFLAGS) $^ $(LIBS)

gen-ust-events.o: gen-ust-events.c tp.h
	$(CC) $(CPPFLAGS) $(LOCAL_CPPFLAGS) $(CFLAGS) -c -o $@ $<

tp.o: tp.c
	$(CC) $(CPPFLAGS) $(LOCAL_CPPFLAGS) $(AM_CFLAGS) $(AM_CPPFLAGS) $(CFLAGS) -c -o $@ $<




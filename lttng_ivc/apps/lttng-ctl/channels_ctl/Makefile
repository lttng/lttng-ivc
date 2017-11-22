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

LIBS = -llttng-ctl
LOCAL_CPPFLAGS += -I.

all: app

.PHONY: app

app: app.o
	$(CC) -o $@ $(LDFLAGS) $(CFLAGS) $^ $(LIBS)

app.o: app.c
	$(CC) $(CPPFLAGS) $(LOCAL_CPPFLAGS) $(LTTNG_CPPFLAGS) $(CFLAGS) -c -o $@ $<




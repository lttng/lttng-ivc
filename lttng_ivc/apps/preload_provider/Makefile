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

PROVIDER_LIBS = -llttng-ust -ldl
APP_LIBS = -ldl
LOCAL_CPPFLAGS += -I.

.PHONY: app provider app-enum provider-enum

provider: libtp.so
provider-enum: libtp-enum.so


app: app.o
	$(CC) -o $@ $(LDFLAGS) $(CFLAGS) $^ $(APP_LIBS)

app.o: app.c
	$(CC) $(CPPFLAGS) $(LOCAL_CPPFLAGS) $(CFLAGS) -c -o $@ $<

libtp.so: tp.o
	$(CC) $(CPPFLAGS) $(LOCAL_CPPFLAGS) $(CFLAGS) --shared -o $@ $< $(PROVIDER_LIBS) $(LDFLAGS)

tp.o: tp.c
	$(CC) $(CPPFLAGS) $(LOCAL_CPPFLAGS) $(CFLAGS) -fpic -c -o $@ $<

app-enum: app-enum.o
	$(CC) -o $@ $(LDFLAGS) $(CFLAGS) $^ $(APP_LIBS)

app-enum.o: app.c
	$(CC) $(CPPFLAGS) $(LOCAL_CPPFLAGS) $(CFLAGS) -DIVC_ENUM -c -o $@ $<

libtp-enum.so: tp-enum.o
	$(CC) $(CPPFLAGS) $(LOCAL_CPPFLAGS) $(CFLAGS) --shared -o $@ $< $(PROVIDER_LIBS) $(LDFLAGS)

tp-enum.o: tp.c
	$(CC) $(CPPFLAGS) $(LOCAL_CPPFLAGS) $(CFLAGS) -DIVC_ENUM -fpic -c -o $@ $<



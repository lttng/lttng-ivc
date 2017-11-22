#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <inttypes.h>
#include <lttng/lttng.h>

static enum lttng_domain_type get_domain_type(const char *domain)
{
	if (!strcmp("UST", domain)) {
		return LTTNG_DOMAIN_UST;
	} else if (!strcmp("KERNEL", domain)) {
		return LTTNG_DOMAIN_KERNEL;
	} else {
		printf("Domain not supported\n");
		assert(0);
	}
}

static int process_channel(struct lttng_channel *channel)
{
	int ret;
	uint64_t uint64 = 0;
	int64_t int64 = 0;


	ret = lttng_channel_get_discarded_event_count(channel, &uint64);
	if (ret < 0) {
		ret = 1;
		goto end;
	}
	printf("discarded_event_count: %" PRIu64 "\n", uint64);

	ret = lttng_channel_get_lost_packet_count(channel, &uint64);
	if (ret < 0) {
		ret = 1;
		goto end;
	}
	printf("lost packet: %" PRIu64 "\n", uint64);

#ifdef LTTNG_2_10
	ret = lttng_channel_get_monitor_timer_interval(channel, &uint64);
	if (ret < 0) {
		ret = 1;
		goto end;
	}
	printf("monitor timer interval: %" PRIu64 "\n", uint64);

	ret = lttng_channel_get_blocking_timeout(channel, &int64);
	if (ret < 0) {
		ret = 1;
		goto end;
	}
	printf("blocking timeout: %" PRId64 "\n", int64);

	/* Setter */
	ret = lttng_channel_set_blocking_timeout(channel, 100);
	if (ret < 0) {
		ret = 1;
		goto end;
	}

	ret = lttng_channel_set_monitor_timer_interval(channel, 100);
	if (ret < 0) {
		ret = 1;
		goto end;
	}
#endif /* LTTNG_2_10 */

end:
	return ret;
}

int main(int argc, char **argv)
{
int ret;
bool found;

if (argc < 4) {
printf("missing parameters, session name, channel name, domain type\n");
return 1;
}

const char *session_name = argv[1];
const char *channel_name = argv[2];
const char *domain_str = argv[3];

/* Domain related variables */
enum lttng_domain_type domain_type = LTTNG_DOMAIN_NONE;
struct lttng_domain *domains = NULL;
struct lttng_domain domain;
int domain_index = -1;

/* Channel related variables */
struct lttng_channel *channels = NULL;
int channel_index = -1;

struct lttng_handle *handle = NULL;

/* Find the domain we are interested in */
domain_type = get_domain_type(domain_str);
ret = lttng_list_domains(session_name, &domains);
for (int i = 0; i < ret; i++) {
	if (domains[i].type == domain_type) {
			domain_index = i;
		}
	}

	if (domain_index < 0) {
		printf("domain not found for session %s\n", session_name);
		ret = 1;
		goto end;
	}

	/* Get the handle */

	handle = lttng_create_handle(session_name, &domains[domain_index]);

	/* Find the channel we are interested in */
	ret = lttng_list_channels(handle, &channels);
	for (int i = 0; i < ret; i++) {
		if (!strcmp(channels[i].name, channel_name)) {
			channel_index = i;
		}
	}

	if (channel_index < 0) {
		printf("channel not found for session %s\n", session_name);
		ret = 1;
		goto end;
	}

	ret = process_channel(&channels[channel_index]);

end:
	free(channels);
	free(domains);
	if (handle) {
		lttng_destroy_handle(handle);
	}
	return 0;
}

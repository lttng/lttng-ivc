#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
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

static int process_event(struct lttng_event *event)
{
	int ret = -1;

	/* Exclusion related lttng-ctl call */
	ret = lttng_event_get_exclusion_name_count(event);
	if (ret < 0) {
		ret = 1;
		goto end;
	}
	if (ret > 0) {
		int count = ret;
		for (int i = 0; i < count ; i++) {
			const char *name;
			ret = lttng_event_get_exclusion_name(event, i , &name);
			if (ret) {
				ret = 1;
				goto end;
			}
			printf("exclusion name: %s\n", name);
		}
	}

	/* Filet expression related lttng-ctl call */
	const char *filter_str;
	ret = lttng_event_get_filter_expression(event, &filter_str);
	if (ret) {
		ret = 1;
		goto end;
	}

	printf("filter expression: %s\n", filter_str);
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

	/* Event related variables */
	struct lttng_event *events = NULL;


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

	/* List events */
	ret = lttng_list_events(handle, channel_name, &events);
	if (ret <= 0) {
		printf("No events found for channel %s in session %s\n", channel_name, session_name);
	}

	for (int i = 0; i < ret; i++) {
		ret = process_event(&events[i]);
		if (ret) {
			printf("Error while processing event \n");
			ret = 1;
			goto end;
		}
	}

end:
	free(events);
	free(channels);
	free(domains);
	if (handle) {
		lttng_destroy_handle(handle);
	}
	return 0;
}

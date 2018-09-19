#pragma once

struct pollfd {
	int fd; // The following descriptor being polled.
	short events; // The input event flags
	short revents; // The output event flags
};

typedef uint32_t nfds_t;

#define POLLIN     0x0001
#define POLLPRI    0x0002
#define POLLOUT    0x0004
#define POLLRDNORM 0x0040
#define POLLWRNORM POLLOUT
#define POLLRDBAND 0x0080
#define POLLWRBAND 0x0100

#define POLLERR    0x0008
#define POLLHUP    0x0010
#define POLLNVAL   0x0020

# btkbd: BTstack classic HID keyboard for the Nebulae's Pi 4. Built by tools/btbuild.sh (WSL):
#   make BTSTACK_ROOT=~/btstack            -> btkbd (static, armv7 hard-float, runs with any glibc)
#   make keymap_test CC=gcc                -> native unit test of keymap.c
BTSTACK_ROOT ?= ../../../btstack
CC = arm-linux-gnueabihf-gcc
SRC_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

VPATH = $(SRC_DIR) \
	$(BTSTACK_ROOT)/src $(BTSTACK_ROOT)/src/classic $(BTSTACK_ROOT)/src/ble \
	$(BTSTACK_ROOT)/platform/posix $(BTSTACK_ROOT)/chipset/bcm $(BTSTACK_ROOT)/3rd-party/micro-ecc

CFLAGS = -O2 -g0 -Wall -Wno-unused-parameter -ffile-prefix-map=$(BTSTACK_ROOT)=btstack \
	-ffile-prefix-map=$(SRC_DIR)=btkbd \
	-I$(SRC_DIR) -I$(BTSTACK_ROOT)/src -I$(BTSTACK_ROOT)/src/classic -I$(BTSTACK_ROOT)/src/ble \
	-I$(BTSTACK_ROOT)/platform/posix -I$(BTSTACK_ROOT)/platform/embedded -I$(BTSTACK_ROOT)/chipset/bcm \
	-I$(BTSTACK_ROOT)/3rd-party/micro-ecc -I$(BTSTACK_ROOT)/3rd-party/tinydir \
	-I$(BTSTACK_ROOT)/3rd-party/bluedroid/encoder/include -I$(BTSTACK_ROOT)/3rd-party/bluedroid/decoder/include \
	-I$(BTSTACK_ROOT)/3rd-party/lc3-google/include -I$(BTSTACK_ROOT)/3rd-party/yxml
LDFLAGS = -static -Wl,--build-id=none
LDLIBS = -lpthread -lrt -lm

BTSTACK_SRC = \
	btstack_memory.c btstack_linked_list.c btstack_memory_pool.c btstack_run_loop.c btstack_util.c \
	ad_parser.c hci.c hci_cmd.c hci_dump.c hci_event.c l2cap.c l2cap_signaling.c btstack_tlv.c btstack_ltv_builder.c \
	btstack_ring_buffer.c btstack_hid.c btstack_hid_parser.c \
	sdp_util.c sdp_server.c device_id_server.c hid_device.c btstack_link_key_db_tlv.c \
	hci_transport_h4.c btstack_run_loop_posix.c btstack_tlv_posix.c btstack_uart_posix.c hci_dump_posix_fs.c \
	btstack_chipset_bcm.c
OUR_SRC = main.c keymap.c

OBJ = $(BTSTACK_SRC:.c=.o) $(OUR_SRC:.c=.o)

btkbd: $(OBJ)
	$(CC) $(LDFLAGS) -o $@ $^ $(LDLIBS)

keymap_test: keymap_test.c keymap.c keymap.h
	$(CC) -O2 -Wall -std=c99 -I$(SRC_DIR) -o $@ $(SRC_DIR)keymap_test.c $(SRC_DIR)keymap.c

clean:
	rm -f *.o btkbd keymap_test

.PHONY: clean

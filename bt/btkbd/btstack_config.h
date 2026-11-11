// btstack_config.h for btkbd: classic Bluetooth HID keyboard only, POSIX (Pi 4, Arch Linux ARM)
#ifndef BTSTACK_CONFIG_H
#define BTSTACK_CONFIG_H

// Port related features
#define HAVE_ASSERT
#define HAVE_MALLOC
#define HAVE_POSIX_FILE_IO

// BTstack features
#define ENABLE_CLASSIC
#define ENABLE_LOG_ERROR
#define ENABLE_LOG_INFO
#define ENABLE_PRINTF_TO_LOG

// Buffers
#define HCI_ACL_PAYLOAD_SIZE (1021 + 4)
#define HCI_OUTGOING_PRE_BUFFER_SIZE 4

#define NVM_NUM_LINK_KEYS 4

#endif

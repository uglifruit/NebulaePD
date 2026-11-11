// btkbd: the Nebulae's Pi 4 as a classic Bluetooth keyboard (BTstack, no BlueZ).
//
//   btkbd --probe                  check the Pi 4's Bluetooth, start the controller once, report, power it off
//   btkbd --hello                  keyboard; types a hello line every 10 s while connected (hardware test)
//   btkbd --type                   keyboard; types the lines it reads on stdin (from narrator.py); stops at EOF
// options:
//   --state FILE    write starting / waiting / reconnecting / connected / off / failed: <why>   (atomic)
//   --tlv FILE      pairing store (BTstack TLV); a stored host means "owned": not discoverable, reconnects to it
//   --hook CMD      run (sh) after a new pairing has been stored, e.g. to copy the TLV to the USB stick
//   --watch FILE NAME   stop when FILE (the firmware's bootinstr.txt) names an instrument other than NAME
//   --hcd-dir DIR   also look for the BCM4345C0 firmware (.hcd) here (after the card's firmware folders)
//   --baud N        main UART speed (default 921600 with flow control, else 460800)
//   --name NAME     Bluetooth name (default Nebulae)
//   --pklg FILE     HCI packet log (PacketLogger format) for debugging
//
// Pi 4 port, adapted from BTstack's port/archive/raspi (main.c, btstack_control_raspi.c):
//   - The controller (CYW43455, "BCM4345C0") is on the PL011 UART /dev/ttyAMA0 (GPIO 32/33), H4 transport.
//     The card's device tree muxes only TX/RX; if GPIO 30/31 are found set to CTS/RTS (ALT3, read from
//     /dev/gpiomem) it uses flow control at 921600 baud, else none at 460800 (as Raspberry Pi OS's btuart).
//   - Its power (BT_REG_ON) is a line of the Pi firmware's GPIO expander, set through the firmware mailbox
//     (/dev/vcio, SET_GPIO_STATE, expander line n = GPIO 128 + n). Other lines of that expander switch WiFi, the
//     power LED, a global reset and the SD card power, so the line is never guessed: btkbd uses only the line the
//     device tree names "BT_ON", and refuses to run without exactly one.
//   - Nothing else may own the UART: no serial console on it, no kernel Bluetooth (hci0), no other process.
// Every check runs before any hardware is touched.
#define BTSTACK_FILE__ "btkbd.c"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

#include "btstack_config.h"
#include "btstack.h"
#include "btstack_chipset_bcm.h"
#include "btstack_control.h"
#include "btstack_run_loop_posix.h"
#include "btstack_signal.h"
#include "btstack_tlv_posix.h"
#include "btstack_uart.h"
#include "classic/btstack_link_key_db_tlv.h"
#include "hci_dump_posix_fs.h"
#include "hci_transport_h4.h"
#include "keymap.h"

#define UART_DEVICE "/dev/ttyAMA0"
#define START_TIMEOUT_MS 25000
#define RECONNECT_MS 10000
#define HELLO_MS 10000
#define TYPING_KEYDOWN_MS 18
#define TYPING_DELAY_MS 18
#define REPORT_ID 0x01
#define TLV_TAG_HIDR ((((uint32_t) 'H') << 24) | (((uint32_t) 'I') << 16) | (((uint32_t) 'D') << 8) | 'R')

static enum { MODE_PROBE, MODE_HELLO, MODE_TYPE } mode = MODE_TYPE;
static const char * state_path, * tlv_path, * hook_cmd, * watch_path, * watch_name, * pklg_path;
static const char * extra_hcd_dir;
static const char * bt_name = "Nebulae";
static uint32_t baud_main;   // 0: 921600 with flow control, 460800 without (as Raspberry Pi OS's btuart)
static int check_only;

// --root DIR (tests only): read the device tree, /proc/cmdline, /sys and the firmware folders from DIR
static const char * root = "";
static const char * P(const char * path){
    static char bufs[4][700];
    static int k;
    k = (k + 1) % 4;
    snprintf(bufs[k], sizeof(bufs[k]), "%s%s", root, path);
    return bufs[k];
}

// ---------------------------------------------------------------------------------------------------- state file
static void write_state(const char * fmt, const char * arg){
    if (!state_path) return;
    char tmp[300];
    snprintf(tmp, sizeof(tmp), "%s.tmp", state_path);
    FILE * f = fopen(tmp, "w");
    if (!f) return;
    fprintf(f, fmt, arg ? arg : "");
    fprintf(f, "\n");
    fclose(f);
    rename(tmp, state_path);
}

// --------------------------------------------------------------------------------------------- Pi 4 checks
static int read_file(const char * path, char * buf, int size){
    FILE * f = fopen(path, "rb");
    if (!f) return -1;
    int n = (int) fread(buf, 1, (size_t) size - 1, f);
    fclose(f);
    buf[n < 0 ? 0 : n] = 0;
    return n;
}

// a device-tree string list (NUL-separated) contains s
static int dt_list_has(const char * buf, int n, const char * s){
    for (int i = 0; i < n; i += (int) strlen(buf + i) + 1){
        if (strcmp(buf + i, s) == 0) return 1;
    }
    return 0;
}

static int bt_on_count;
static int bt_on_line = -1;
static char bt_on_node[400];

// find gpio-line-names of the firmware GPIO expander ("raspberrypi,firmware-gpio") and the index of "BT_ON"
static void find_bt_on(const char * dir, int depth){
    if (depth > 5) return;
    char path[600], buf[4096];
    snprintf(path, sizeof(path), "%s/gpio-line-names", dir);
    int n = read_file(path, buf, sizeof(buf));
    if (n > 0){
        char comp[512];
        char cpath[600];
        snprintf(cpath, sizeof(cpath), "%s/compatible", dir);
        int cn = read_file(cpath, comp, sizeof(comp));
        int is_fw = cn > 0 && dt_list_has(comp, cn, "raspberrypi,firmware-gpio");
        int idx = 0;
        for (int i = 0; i < n; i += (int) strlen(buf + i) + 1, idx++){
            if (strcmp(buf + i, "BT_ON") == 0){
                printf("  BT_ON: line %d of %s%s\n", idx, dir, is_fw ? " (firmware GPIO expander)" : " (not the expander)");
                if (is_fw){
                    bt_on_count++;
                    bt_on_line = idx;
                    snprintf(bt_on_node, sizeof(bt_on_node), "%s", dir);
                }
            }
        }
    }
    DIR * d = opendir(dir);
    if (!d) return;
    struct dirent * e;
    while ((e = readdir(d)) != NULL){
        if (e->d_name[0] == '.') continue;
        snprintf(path, sizeof(path), "%s/%s", dir, e->d_name);
        struct stat st;
        if (lstat(path, &st) == 0 && S_ISDIR(st.st_mode)) find_bt_on(path, depth + 1);
    }
    closedir(d);
}

static char hcd_path[600];

static void find_hcd(const char * dir, int * score){
    DIR * d = opendir(dir);
    if (!d) return;
    struct dirent * e;
    while ((e = readdir(d)) != NULL){
        size_t len = strlen(e->d_name);
        if (strncasecmp(e->d_name, "BCM4345C0", 9) != 0 || len < 5) continue;
        if (strcasecmp(e->d_name + len - 4, ".hcd") != 0) continue;
        // prefer the Pi 4 specific file, then the plain BCM4345C0.hcd, then anything else matching
        int s = strstr(e->d_name, "4-model-b") ? 3 : (strcasecmp(e->d_name, "BCM4345C0.hcd") == 0 ? 2 : 1);
        printf("  firmware candidate: %s/%s\n", dir, e->d_name);
        if (s > *score){
            *score = s;
            snprintf(hcd_path, sizeof(hcd_path), "%s/%s", dir, e->d_name);
        }
    }
    closedir(d);
}

// a BCM2711 GPIO's function (0 input, 1 output, 4..7 ALT0..ALT3, 3 ALT4, 2 ALT5), or -1; read-only mapping
static int flow;
static int pin_function(int gpio){
    int fd = open(P("/dev/gpiomem"), O_RDONLY | O_SYNC);
    if (fd < 0) return -1;
    volatile uint32_t * regs = mmap(NULL, 4096, PROT_READ, MAP_SHARED, fd, 0);
    close(fd);
    if (regs == MAP_FAILED) return -1;
    uint32_t fsel = regs[gpio / 10];
    munmap((void *) regs, 4096);
    return (int) ((fsel >> ((gpio % 10) * 3)) & 7);
}

// other processes that have the UART open
static int uart_users(void){
    int users = 0;
    if (root[0]) return 0;   // test root: no processes to scan
    DIR * proc = opendir("/proc");
    if (!proc) return 0;
    struct dirent * p;
    char self[32];
    snprintf(self, sizeof(self), "%d", (int) getpid());
    while ((p = readdir(proc)) != NULL){
        if (p->d_name[0] < '0' || p->d_name[0] > '9' || strcmp(p->d_name, self) == 0) continue;
        char fdd[300];
        snprintf(fdd, sizeof(fdd), "/proc/%s/fd", p->d_name);
        DIR * fds = opendir(fdd);
        if (!fds) continue;
        struct dirent * f;
        while ((f = readdir(fds)) != NULL){
            char link[600], target[300];
            snprintf(link, sizeof(link), "%s/%s", fdd, f->d_name);
            ssize_t n = readlink(link, target, sizeof(target) - 1);
            if (n <= 0) continue;
            target[n] = 0;
            if (strcmp(target, UART_DEVICE) == 0){
                char comm[100] = "?", cpath[300];
                snprintf(cpath, sizeof(cpath), "/proc/%s/comm", p->d_name);
                read_file(cpath, comm, sizeof(comm));
                comm[strcspn(comm, "\n")] = 0;
                printf("  UART in use by pid %s (%s)\n", p->d_name, comm);
                users++;
            }
        }
        closedir(fds);
    }
    closedir(proc);
    return users;
}

// returns NULL when everything is in order, else why not
static const char * pi4_checks(void){
    char buf[4096];
    printf("=== checks\n");
    if (read_file(P("/proc/device-tree/model"), buf, sizeof(buf)) <= 0) return "no /proc/device-tree/model";
    printf("  model: %s\n", buf);
    if (strstr(buf, "Raspberry Pi 4") == NULL) return "not a Raspberry Pi 4";
    if (read_file(P("/proc/cmdline"), buf, sizeof(buf)) > 0){
        buf[strcspn(buf, "\n")] = 0;
        printf("  cmdline: %s\n", buf);
        if (strstr(buf, "ttyAMA0") || strstr(buf, "serial1")) return "a console is on the Bluetooth UART";
    }
    DIR * bt = opendir(P("/sys/class/bluetooth"));
    if (bt){
        struct dirent * e;
        int hci = 0;
        while ((e = readdir(bt)) != NULL) if (e->d_name[0] != '.'){ printf("  kernel Bluetooth: %s\n", e->d_name); hci++; }
        closedir(bt);
        if (hci) return "the kernel already runs Bluetooth on this UART";
    }
    char uart0[200] = "", serial1[200] = "";
    read_file(P("/proc/device-tree/aliases/uart0"), uart0, sizeof(uart0));
    read_file(P("/proc/device-tree/aliases/serial1"), serial1, sizeof(serial1));
    printf("  aliases: uart0=%s serial1=%s\n", uart0, serial1);
    if (!uart0[0] || strcmp(uart0, serial1) != 0) return "serial1 is not the PL011 (Bluetooth is not on uart0)";
    char of[600];
    ssize_t n = readlink(P("/sys/class/tty/ttyAMA0/device/of_node"), of, sizeof(of) - 1);
    if (n <= 0) return "no /dev/ttyAMA0 (or it has no device-tree node)";
    of[n] = 0;
    printf("  ttyAMA0 node: %s\n", of);
    size_t ol = strlen(of), ul = strlen(uart0);
    if (ol < ul || strcmp(of + ol - ul, uart0) != 0) return "/dev/ttyAMA0 is not uart0";
    // uart0's TX/RX must be GPIO 32/33, the Pi 4's lines to the Bluetooth chip (device tree: uart0_pins <32 33>)
    int pins = read_file(P("/proc/device-tree/soc/gpio@7e200000/uart0_pins/brcm,pins"), buf, sizeof(buf));
    int has32 = 0, has33 = 0;
    for (int i = 0; i + 3 < pins; i += 4){
        uint32_t pin = ((uint32_t) (uint8_t) buf[i] << 24) | ((uint32_t) (uint8_t) buf[i + 1] << 16) |
                       ((uint32_t) (uint8_t) buf[i + 2] << 8) | (uint8_t) buf[i + 3];
        printf("  uart0 pin: GPIO %u\n", pin);
        if (pin == 32) has32 = 1;
        if (pin == 33) has33 = 1;
    }
    if (!has32 || !has33) return "uart0 is not on GPIO 32/33 (the Bluetooth chip's lines)";
    // flow control only if GPIO 30/31 are set to uart0's CTS/RTS (ALT3), read-only from /dev/gpiomem
    int f30 = pin_function(30), f31 = pin_function(31);
    flow = (f30 == 7 && f31 == 7);
    printf("  GPIO 30/31 functions: %d/%d (7 = ALT3, CTS/RTS): %s\n", f30, f31,
           flow ? "flow control" : "no flow control");
    if (uart_users()) return "another process has the Bluetooth UART open";
    find_bt_on(P("/proc/device-tree"), 0);
    if (bt_on_count != 1) return bt_on_count ? "more than one BT_ON line" : "no BT_ON line in the device tree";
    if (bt_on_line < 0 || bt_on_line > 7) return "BT_ON is not one of the expander's 8 lines";
    printf("  BT_REG_ON: firmware GPIO %d (expander line %d)\n", 128 + bt_on_line, bt_on_line);
    int score = 0;
    find_hcd(P("/usr/lib/firmware/updates/brcm"), &score);
    find_hcd(P("/usr/lib/firmware/brcm"), &score);
    find_hcd(P("/lib/firmware/brcm"), &score);
    if (extra_hcd_dir) find_hcd(extra_hcd_dir, &score);
    if (!score) return "no BCM4345C0*.hcd Bluetooth firmware found";
    printf("  firmware: %s\n", hcd_path);
    if (access(P("/dev/vcio"), R_OK) != 0) return "no /dev/vcio (firmware mailbox)";
    return NULL;
}

// ------------------------------------------------------------------------- BT_REG_ON via the firmware mailbox
#define IOCTL_RPI_FIRMWARE_PROPERTY _IOWR(100, 0, char *)
#define RPI_FIRMWARE_GET_GPIO_STATE 0x00030041
#define RPI_FIRMWARE_SET_GPIO_STATE 0x00038041
static int vcio_fd = -1;

static int mailbox_gpio(uint32_t tag, int gpio, int value){
    if (vcio_fd < 0) vcio_fd = open("/dev/vcio", O_NONBLOCK);
    if (vcio_fd < 0) return -1;
    uint32_t m[8];
    m[0] = sizeof(m);
    m[1] = 0;            // request
    m[2] = tag;
    m[3] = 8;            // value buffer size
    m[4] = 0;
    m[5] = (uint32_t) gpio;
    m[6] = (uint32_t) value;
    m[7] = 0;            // end tag
    if (ioctl(vcio_fd, IOCTL_RPI_FIRMWARE_PROPERTY, m) == -1) return -1;
    if (m[1] != 0x80000000u) return -1;
    return (int) m[6];
}

static int bt_gpio(void){ return 128 + bt_on_line; }
static void control_init(const void * config){ UNUSED(config); }
static int control_on(void){ log_info("BT_ON high"); mailbox_gpio(RPI_FIRMWARE_SET_GPIO_STATE, bt_gpio(), 1); return 0; }
static int control_off(void){ log_info("BT_ON low"); mailbox_gpio(RPI_FIRMWARE_SET_GPIO_STATE, bt_gpio(), 0); return 0; }
static btstack_control_t control = { control_init, control_on, control_off, NULL, NULL, NULL };

// ----------------------------------------------------------------------------------------------- stack setup
static hci_transport_config_uart_t transport_config = { HCI_TRANSPORT_CONFIG_UART, 115200, 0, 1, NULL, 0 };
static btstack_uart_config_t uart_config;
static btstack_packet_callback_registration_t hci_event_callback_registration;
static btstack_tlv_posix_t tlv_context;
static const btstack_tlv_t * tlv_impl;
static btstack_timer_source_t start_timer, watch_timer, hook_timer, hello_timer, reconnect_timer, exit_timer;
static int working, shutting_down, exit_code;

static void bd_addr_from_serial(bd_addr_t addr){
    // as Raspberry Pi OS's btuart (and BTstack's raspi port): b8:27:eb + the serial's last 3 bytes ^ 0xaa
    char buf[64] = "";
    unsigned int a = 0, b = 0, c = 0;
    read_file("/proc/device-tree/serial-number", buf, sizeof(buf));
    size_t l = strlen(buf);
    if (l >= 6) sscanf(buf + l - 6, "%2x%2x%2x", &a, &b, &c);
    addr[0] = 0xb8; addr[1] = 0x27; addr[2] = 0xeb;
    addr[3] = (uint8_t) (a ^ 0xaa); addr[4] = (uint8_t) (b ^ 0xaa); addr[5] = (uint8_t) (c ^ 0xaa);
}

static void force_exit(btstack_timer_source_t * ts){
    UNUSED(ts);
    control_off();
    printf("exit (forced)\n");
    exit(exit_code);
}

static void shutdown_with(int code, const char * why){
    if (shutting_down) return;
    shutting_down = 1;
    exit_code = code;
    printf("shutting down: %s\n", why);
    fflush(stdout);
    if (code) write_state("failed: %s", why); else write_state("off", NULL);
    btstack_run_loop_set_timer_handler(&exit_timer, force_exit);
    btstack_run_loop_set_timer(&exit_timer, 3000);
    btstack_run_loop_add_timer(&exit_timer);
    hci_power_control(HCI_POWER_OFF);
}

static void on_signal(void){ shutdown_with(0, "signal"); }

static void start_timeout(btstack_timer_source_t * ts){
    UNUSED(ts);
    if (!working){
        if (mode == MODE_PROBE) printf("PROBE FAIL: the controller did not start (no answer on the UART)\n");
        shutdown_with(3, "the Bluetooth controller did not start");
    }
}

static void watch_check(btstack_timer_source_t * ts){
    char buf[512];
    if (read_file(watch_path, buf, sizeof(buf)) > 0){
        char * p = strstr(buf, "instr,");
        if (p){
            p += 6;
            p[strcspn(p, "\r\n")] = 0;
            if (strcmp(p, watch_name) != 0){
                char why[300];
                snprintf(why, sizeof(why), "instrument changed to %s", p);
                shutdown_with(0, why);
                return;
            }
        }
    }
    btstack_run_loop_set_timer(ts, 1000);
    btstack_run_loop_add_timer(ts);
}

static void run_hook(btstack_timer_source_t * ts){
    UNUSED(ts);
    if (!hook_cmd) return;
    printf("pairing stored, running hook\n");
    fflush(stdout);
    int r = system(hook_cmd);
    printf("hook exit %d\n", r);
}

static void schedule_hook(void){
    btstack_run_loop_remove_timer(&hook_timer);
    btstack_run_loop_set_timer_handler(&hook_timer, run_hook);
    btstack_run_loop_set_timer(&hook_timer, 1000);
    btstack_run_loop_add_timer(&hook_timer);
}

// ------------------------------------------------------------------------------------------------- keyboard
// close to USB HID Specification 1.1, Appendix B.1 (as BTstack's hid_keyboard_demo)
static const uint8_t hid_descriptor_keyboard[] = {
    0x05, 0x01, 0x09, 0x06, 0xa1, 0x01, 0x85, REPORT_ID,
    0x75, 0x01, 0x95, 0x08, 0x05, 0x07, 0x19, 0xe0, 0x29, 0xe7, 0x15, 0x00, 0x25, 0x01, 0x81, 0x02,
    0x75, 0x01, 0x95, 0x08, 0x81, 0x03,
    0x95, 0x05, 0x75, 0x01, 0x05, 0x08, 0x19, 0x01, 0x29, 0x05, 0x91, 0x02,
    0x95, 0x01, 0x75, 0x03, 0x91, 0x03,
    0x95, 0x06, 0x75, 0x08, 0x15, 0x00, 0x25, 0xff, 0x05, 0x07, 0x19, 0x00, 0x29, 0xff, 0x81, 0x00,
    0xc0,
};
static uint8_t hid_service_buffer[300];
static uint8_t device_id_sdp_service_buffer[100];
static uint16_t hid_cid;
static bd_addr_t host_addr;
static int bonded, connected, hello_count;
static uint32_t dropped;

static uint8_t send_storage[4096];
static btstack_ring_buffer_t send_buffer;
static btstack_timer_source_t send_timer;
static uint8_t send_modifier, send_keycode;
static int send_active;

static void send_report(uint8_t modifier, uint8_t keycode){
    uint8_t message[] = {0xa1, REPORT_ID, modifier, 0, keycode, 0, 0, 0, 0, 0};
    hid_device_send_interrupt_message(hid_cid, &message[0], sizeof(message));
}

static void trigger_key_up(btstack_timer_source_t * ts){
    UNUSED(ts);
    hid_device_request_can_send_now_event(hid_cid);
}

static void send_next(btstack_timer_source_t * ts){
    for (;;){
        uint8_t c;
        uint32_t n = 0;
        btstack_ring_buffer_read(&send_buffer, &c, 1, &n);
        if (n == 0){ send_active = 0; return; }
        if (neb_keymap(c, &send_keycode, &send_modifier)) break;   // others are skipped
    }
    UNUSED(ts);
    send_active = 1;
    hid_device_request_can_send_now_event(hid_cid);
}

static void queue_text(const char * s, size_t len){
    if (!connected){ dropped += (uint32_t) len; return; }
    for (size_t i = 0; i < len; i++){
        if (btstack_ring_buffer_bytes_free(&send_buffer) == 0){ dropped++; continue; }
        btstack_ring_buffer_write(&send_buffer, (uint8_t *) &s[i], 1);
    }
    if (!send_active) send_next(&send_timer);
}

static void hello_tick(btstack_timer_source_t * ts){
    if (connected){
        char line[100];
        snprintf(line, sizeof(line), "Hello from the Nebulae. This is line %d.\n", ++hello_count);
        queue_text(line, strlen(line));
    }
    btstack_run_loop_set_timer(ts, HELLO_MS);
    btstack_run_loop_add_timer(ts);
}

static btstack_data_source_t stdin_source;
static void stdin_process(btstack_data_source_t * ds, btstack_data_source_callback_type_t type){
    UNUSED(type);
    char buf[512];
    ssize_t n = read(ds->source.fd, buf, sizeof(buf));
    if (n > 0){ queue_text(buf, (size_t) n); return; }
    if (n == 0 || (errno != EAGAIN && errno != EINTR)){
        btstack_run_loop_disable_data_source_callbacks(ds, DATA_SOURCE_CALLBACK_READ);
        btstack_run_loop_remove_data_source(ds);
        shutdown_with(0, "input closed");
    }
}

static void reconnect(btstack_timer_source_t * ts){
    UNUSED(ts);
    if (connected || shutting_down || !bonded) return;
    printf("reconnecting to %s\n", bd_addr_to_str(host_addr));
    write_state("reconnecting", NULL);
    hid_device_connect(host_addr, &hid_cid);
}

static void schedule_reconnect(void){
    btstack_run_loop_remove_timer(&reconnect_timer);
    btstack_run_loop_set_timer_handler(&reconnect_timer, reconnect);
    btstack_run_loop_set_timer(&reconnect_timer, RECONNECT_MS);
    btstack_run_loop_add_timer(&reconnect_timer);
}

static void keyboard_ready(void){
    // a stored host = owned: only that PC may connect again; otherwise discoverable for pairing
    int len = tlv_impl ? tlv_impl->get_tag(&tlv_context, TLV_TAG_HIDR, (uint8_t *) &host_addr, sizeof(bd_addr_t)) : 0;
    bonded = (len == sizeof(bd_addr_t));
    gap_connectable_control(1);
    if (bonded){
        gap_discoverable_control(0);
        printf("paired with %s: reconnecting (not discoverable)\n", bd_addr_to_str(host_addr));
        reconnect(NULL);
    } else {
        gap_discoverable_control(1);
        printf("not paired: discoverable as \"%s\"\n", bt_name);
        write_state("waiting", NULL);
    }
}

static void hid_packet_handler(uint8_t packet_type, uint16_t channel, uint8_t * packet, uint16_t size){
    UNUSED(channel);
    UNUSED(size);
    if (packet_type != HCI_EVENT_PACKET || hci_event_packet_get_type(packet) != HCI_EVENT_HID_META) return;
    uint8_t status;
    switch (hci_event_hid_meta_get_subevent_code(packet)){
        case HID_SUBEVENT_CONNECTION_OPENED:
            status = hid_subevent_connection_opened_get_status(packet);
            if (status != ERROR_CODE_SUCCESS){
                printf("connection failed, status 0x%02x\n", status);
                hid_cid = 0;
                if (bonded) schedule_reconnect();
                return;
            }
            hid_cid = hid_subevent_connection_opened_get_hid_cid(packet);
            hid_subevent_connection_opened_get_bd_addr(packet, host_addr);
            connected = 1;
            printf("connected to %s\n", bd_addr_to_str(host_addr));
            write_state("connected", NULL);
            if (!bonded && tlv_impl){
                tlv_impl->store_tag(&tlv_context, TLV_TAG_HIDR, (const uint8_t *) &host_addr, sizeof(bd_addr_t));
                bonded = 1;
                gap_discoverable_control(0);
                schedule_hook();
            }
            break;
        case HID_SUBEVENT_CONNECTION_CLOSED:
            btstack_run_loop_remove_timer(&send_timer);
            btstack_ring_buffer_reset(&send_buffer);
            send_active = 0;
            connected = 0;
            hid_cid = 0;
            printf("disconnected\n");
            if (!shutting_down){
                write_state(bonded ? "reconnecting" : "waiting", NULL);
                if (bonded) schedule_reconnect();
            }
            break;
        case HID_SUBEVENT_CAN_SEND_NOW:
            if (send_keycode){
                send_report(send_modifier, send_keycode);
                send_keycode = 0;
                send_modifier = 0;
                btstack_run_loop_set_timer_handler(&send_timer, trigger_key_up);
                btstack_run_loop_set_timer(&send_timer, TYPING_KEYDOWN_MS);
            } else {
                send_report(0, 0);
                btstack_run_loop_set_timer_handler(&send_timer, send_next);
                btstack_run_loop_set_timer(&send_timer, TYPING_DELAY_MS);
            }
            btstack_run_loop_add_timer(&send_timer);
            break;
        default:
            break;
    }
}

static void keyboard_setup(void){
    gap_set_class_of_device(0x2540);            // peripheral, keyboard
    gap_set_local_name(bt_name);
    gap_set_default_link_policy_settings(LM_LINK_POLICY_ENABLE_ROLE_SWITCH | LM_LINK_POLICY_ENABLE_SNIFF_MODE);
    gap_set_allow_role_switch(true);
    // Just Works pairing: no PIN for the PC to show or to type
    gap_ssp_set_io_capability(SSP_IO_CAPABILITY_NO_INPUT_NO_OUTPUT);
    gap_ssp_set_authentication_requirement(SSP_IO_AUTHREQ_MITM_PROTECTION_NOT_REQUIRED_GENERAL_BONDING);
    l2cap_init();
    sdp_init();
    memset(hid_service_buffer, 0, sizeof(hid_service_buffer));
    hid_sdp_record_t hid_params = {
        0x2540, 0,          // keyboard, country code 0 (not localised)
        0, 1, 1, 1,         // virtual cable, remote wake, reconnect initiate, normally connectable
        0,                  // no boot protocol
        1600, 3200, 3200,   // host max latency, min timeout, supervision timeout
        hid_descriptor_keyboard, sizeof(hid_descriptor_keyboard),
        "Nebulae storyteller"
    };
    hid_create_sdp_record(hid_service_buffer, sdp_create_service_record_handle(), &hid_params);
    sdp_register_service(hid_service_buffer);
    device_id_create_sdp_record(device_id_sdp_service_buffer, sdp_create_service_record_handle(),
                                DEVICE_ID_VENDOR_ID_SOURCE_BLUETOOTH, BLUETOOTH_COMPANY_ID_BLUEKITCHEN_GMBH, 1, 1);
    sdp_register_service(device_id_sdp_service_buffer);
    hid_device_init(0, sizeof(hid_descriptor_keyboard), hid_descriptor_keyboard);
    hid_device_register_packet_handler(&hid_packet_handler);
    btstack_ring_buffer_init(&send_buffer, send_storage, sizeof(send_storage));
}

// ------------------------------------------------------------------------------------------------ HCI events
static void hci_packet_handler(uint8_t packet_type, uint16_t channel, uint8_t * packet, uint16_t size){
    UNUSED(channel);
    UNUSED(size);
    if (packet_type != HCI_EVENT_PACKET) return;
    bd_addr_t addr;
    switch (hci_event_packet_get_type(packet)){
        case BTSTACK_EVENT_STATE:
            switch (btstack_event_state_get_state(packet)){
                case HCI_STATE_WORKING:
                    if (working) break;
                    working = 1;
                    gap_local_bd_addr(addr);
                    printf("controller running, address %s\n", bd_addr_to_str(addr));
                    if (mode == MODE_PROBE){
                        printf("PROBE OK\n");
                        shutdown_with(0, "probe done");
                        break;
                    }
                    if (tlv_path){
                        tlv_impl = btstack_tlv_posix_init_instance(&tlv_context, tlv_path);
                        btstack_tlv_set_instance(tlv_impl, &tlv_context);
                        hci_set_link_key_db(btstack_link_key_db_tlv_get_instance(tlv_impl, &tlv_context));
                    }
                    keyboard_ready();
                    break;
                case HCI_STATE_OFF:
                    if (!shutting_down) break;
                    if (tlv_impl) btstack_tlv_posix_deinit(&tlv_context);
                    control_off();
                    printf("off; %u characters not typed (not connected or queue full)\n", dropped);
                    fflush(stdout);
                    exit(exit_code);
                    break;
                default:
                    break;
            }
            break;
        case HCI_EVENT_COMMAND_COMPLETE: {
            const uint8_t * r = hci_event_command_complete_get_return_parameters(packet);
            uint16_t op = hci_event_command_complete_get_command_opcode(packet);
            if (op == HCI_OPCODE_HCI_READ_LOCAL_VERSION_INFORMATION && r[0] == 0){
                printf("controller: HCI %u rev 0x%04x, LMP %u subversion 0x%04x, manufacturer 0x%04x\n", r[1],
                       little_endian_read_16(r, 2), r[4], little_endian_read_16(r, 7), little_endian_read_16(r, 5));
            } else if (op == HCI_OPCODE_HCI_READ_LOCAL_NAME && r[0] == 0){
                char name[249];
                memcpy(name, r + 1, 248);
                name[248] = 0;
                printf("controller name: %s\n", name);
            }
            break;
        }
        case HCI_EVENT_PIN_CODE_REQUEST:
            // legacy pairing (hosts without Secure Simple Pairing): PIN 0000
            hci_event_pin_code_request_get_bd_addr(packet, addr);
            gap_pin_code_response(addr, "0000");
            break;
        case HCI_EVENT_USER_CONFIRMATION_REQUEST:
            hci_event_user_confirmation_request_get_bd_addr(packet, addr);
            gap_ssp_confirmation_response(addr);
            break;
        case HCI_EVENT_LINK_KEY_NOTIFICATION:
            printf("link key stored\n");
            schedule_hook();
            break;
        default:
            break;
    }
}

// --------------------------------------------------------------------------------------------------- main
static void usage(void){
    printf("usage: btkbd --probe|--hello|--type [--state F] [--tlv F] [--hook CMD] [--watch F NAME] "
           "[--hcd-dir D] [--baud N] [--name S] [--pklg F] [--check-only] [--root DIR (tests)]\n");
    exit(1);
}

int main(int argc, const char * argv[]){
    setvbuf(stdout, NULL, _IOLBF, 0);
    for (int i = 1; i < argc; i++){
        const char * a = argv[i];
        int more = i + 1 < argc;
        if (!strcmp(a, "--probe")) mode = MODE_PROBE;
        else if (!strcmp(a, "--hello")) mode = MODE_HELLO;
        else if (!strcmp(a, "--type")) mode = MODE_TYPE;
        else if (!strcmp(a, "--state") && more) state_path = argv[++i];
        else if (!strcmp(a, "--tlv") && more) tlv_path = argv[++i];
        else if (!strcmp(a, "--hook") && more) hook_cmd = argv[++i];
        else if (!strcmp(a, "--hcd-dir") && more) extra_hcd_dir = argv[++i];
        else if (!strcmp(a, "--baud") && more) baud_main = (uint32_t) strtoul(argv[++i], NULL, 10);
        else if (!strcmp(a, "--name") && more) bt_name = argv[++i];
        else if (!strcmp(a, "--pklg") && more) pklg_path = argv[++i];
        else if (!strcmp(a, "--watch") && i + 2 < argc){ watch_path = argv[++i]; watch_name = argv[++i]; }
        else if (!strcmp(a, "--root") && more) root = argv[++i];
        else if (!strcmp(a, "--check-only")) check_only = 1;
        else usage();
    }
    printf("btkbd (%s mode)\n", mode == MODE_PROBE ? "probe" : (mode == MODE_HELLO ? "hello" : "type"));
    write_state("starting", NULL);

    const char * why = pi4_checks();
    if (why){
        printf("%s: %s (nothing was switched on)\n", mode == MODE_PROBE ? "PROBE FAIL" : "cannot start", why);
        write_state("failed: %s", why);
        return 2;
    }
    if (!baud_main) baud_main = flow ? 921600 : 460800;
    if (check_only || root[0]){
        printf("CHECKS OK: BT_ON = firmware GPIO %d, %s at %u baud, firmware %s\n", bt_gpio(),
               flow ? "flow control" : "no flow control", baud_main, hcd_path);
        return 0;
    }
    printf("  BT_ON now: %d\n", mailbox_gpio(RPI_FIRMWARE_GET_GPIO_STATE, bt_gpio(), 0));

    btstack_memory_init();
    if (pklg_path){
        hci_dump_posix_fs_open(pklg_path, HCI_DUMP_PACKETLOGGER);
        hci_dump_init(hci_dump_posix_fs_get_instance());
    }
    btstack_run_loop_init(btstack_run_loop_posix_get_instance());

    transport_config.device_name = UART_DEVICE;
    transport_config.baudrate_main = baud_main;
    transport_config.flowcontrol = flow;
    const btstack_chipset_t * chipset = btstack_chipset_bcm_instance();
    chipset->init(&transport_config);
    btstack_chipset_bcm_set_hcd_file_path(hcd_path);

    const btstack_uart_t * uart_driver = btstack_uart_posix_instance();
    uart_config.baudrate = transport_config.baudrate_init;
    uart_config.flowcontrol = transport_config.flowcontrol;
    uart_config.device_name = transport_config.device_name;
    uart_driver->init(&uart_config);

    hci_init(hci_transport_h4_instance_for_uart(uart_driver), (void *) &transport_config);
    bd_addr_t addr;
    bd_addr_from_serial(addr);
    hci_set_bd_addr(addr);
    hci_set_chipset(chipset);
    hci_set_control(&control);
    hci_event_callback_registration.callback = &hci_packet_handler;
    hci_add_event_handler(&hci_event_callback_registration);
    btstack_signal_register_callback(SIGINT, &on_signal);
    btstack_signal_register_callback(SIGTERM, &on_signal);

    if (mode != MODE_PROBE) keyboard_setup();
    if (mode == MODE_HELLO){
        btstack_run_loop_set_timer_handler(&hello_timer, hello_tick);
        btstack_run_loop_set_timer(&hello_timer, HELLO_MS);
        btstack_run_loop_add_timer(&hello_timer);
    }
    if (mode == MODE_TYPE){
        fcntl(0, F_SETFL, fcntl(0, F_GETFL) | O_NONBLOCK);
        btstack_run_loop_set_data_source_fd(&stdin_source, 0);
        btstack_run_loop_set_data_source_handler(&stdin_source, &stdin_process);
        btstack_run_loop_enable_data_source_callbacks(&stdin_source, DATA_SOURCE_CALLBACK_READ);
        btstack_run_loop_add_data_source(&stdin_source);
    }
    if (watch_path){
        btstack_run_loop_set_timer_handler(&watch_timer, watch_check);
        btstack_run_loop_set_timer(&watch_timer, 1000);
        btstack_run_loop_add_timer(&watch_timer);
    }

    // a clean power cycle of the controller, then let BTstack bring it up (firmware download, reset, baud rate)
    control_off();
    usleep(100000);
    printf("=== starting the controller: %s, H4, %u then %u baud, %s, firmware %s\n", UART_DEVICE,
           transport_config.baudrate_init, baud_main, flow ? "flow control" : "no flow control", hcd_path);
    btstack_run_loop_set_timer_handler(&start_timer, start_timeout);
    btstack_run_loop_set_timer(&start_timer, START_TIMEOUT_MS);
    btstack_run_loop_add_timer(&start_timer);
    hci_power_control(HCI_POWER_ON);
    btstack_run_loop_execute();
    return 0;
}

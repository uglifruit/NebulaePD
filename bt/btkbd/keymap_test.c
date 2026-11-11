// keymap_test.c: native unit test of keymap.c (tools/btbuild.sh builds and runs it on the PC).
#include <stdio.h>
#include <string.h>
#include "keymap.h"

static int fails;

static void expect(unsigned char c, int typed, uint8_t key, uint8_t mod){
    uint8_t k = 0xee, m = 0xee;
    int r = neb_keymap(c, &k, &m);
    if (r != typed || (typed && (k != key || m != mod))){
        printf("FAIL %d '%c': got %d key 0x%02x mod %d, want %d key 0x%02x mod %d\n", c, c > 31 ? c : '?', r, k, m,
               typed, key, mod);
        fails++;
    }
}

int main(void){
    int c;
    // letters, digits, Enter, space
    for (c = 'a'; c <= 'z'; c++) expect((unsigned char) c, 1, (uint8_t) (4 + c - 'a'), 0);
    for (c = 'A'; c <= 'Z'; c++) expect((unsigned char) c, 1, (uint8_t) (4 + c - 'A'), NEB_MOD_SHIFT);
    for (c = '1'; c <= '9'; c++) expect((unsigned char) c, 1, (uint8_t) (0x1e + c - '1'), 0);
    expect('0', 1, 0x27, 0);
    expect('\n', 1, 0x28, 0);
    expect(' ', 1, 0x2c, 0);
    // punctuation that types the same on UK and US layouts
    expect('.', 1, 0x37, 0);  expect(',', 1, 0x36, 0);  expect('-', 1, 0x2d, 0);  expect('\'', 1, 0x34, 0);
    expect('!', 1, 0x1e, 2);  expect('%', 1, 0x22, 2);  expect('(', 1, 0x26, 2);  expect(')', 1, 0x27, 2);
    expect(':', 1, 0x33, 2);  expect('?', 1, 0x38, 2);
    // every NEB_SAFE_PUNCT character is typed
    for (const char * p = NEB_SAFE_PUNCT; *p; p++){
        uint8_t k, m;
        if (!neb_keymap((unsigned char) *p, &k, &m)){ printf("FAIL safe '%c' not typed\n", *p); fails++; }
    }
    // everything else is dropped: UK/US differences, control characters, 8-bit
    const char * dropped = "\"@#~\\|`^&*_+={}[]<>/;$\t\r";
    for (const char * p = dropped; *p; p++) expect((unsigned char) *p, 0, 0, 0);
    for (c = 0; c < 32; c++) if (c != '\n') expect((unsigned char) c, 0, 0, 0);
    for (c = 127; c < 256; c++) expect((unsigned char) c, 0, 0, 0);
    // count: exactly 26 + 26 + 10 + Enter + the safe punctuation are typed
    int typed = 0;
    for (c = 0; c < 256; c++){ uint8_t k, m; typed += neb_keymap((unsigned char) c, &k, &m); }
    int want = 26 + 26 + 10 + 1 + (int) strlen(NEB_SAFE_PUNCT);
    if (typed != want){ printf("FAIL %d characters typed, want %d\n", typed, want); fails++; }
    printf(fails ? "keymap: %d FAILED\n" : "keymap: OK (%d checks)\n", fails ? fails : 256);
    return fails ? 1 : 0;
}

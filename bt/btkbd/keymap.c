// keymap.c: ASCII -> USB HID keyboard usage (HID Usage Tables, Keyboard/Keypad page 0x07).
//
// The host (a Windows PC with a UK layout) turns usages back into characters with its own layout, so only
// characters on keys that are identical on UK and US layouts are typed: letters, digits, space, Enter and
// . , ! ? ( ) - : % '   (UK and US differ on " @ # ~ \ | and a few others; those are dropped).
#include "keymap.h"

int neb_keymap(unsigned char c, uint8_t * keycode, uint8_t * modifier){
    *modifier = 0;
    if (c >= 'a' && c <= 'z'){ *keycode = (uint8_t) (0x04 + (c - 'a')); return 1; }
    if (c >= 'A' && c <= 'Z'){ *keycode = (uint8_t) (0x04 + (c - 'A')); *modifier = NEB_MOD_SHIFT; return 1; }
    if (c >= '1' && c <= '9'){ *keycode = (uint8_t) (0x1e + (c - '1')); return 1; }
    switch (c){
        case '0':  *keycode = 0x27; return 1;
        case '\n': *keycode = 0x28; return 1;   // Enter
        case ' ':  *keycode = 0x2c; return 1;
        case '-':  *keycode = 0x2d; return 1;
        case '\'': *keycode = 0x34; return 1;   // UK and US: the key right of ';' (UK Shift gives @, never sent)
        case ',':  *keycode = 0x36; return 1;
        case '.':  *keycode = 0x37; return 1;
        case '!':  *keycode = 0x1e; *modifier = NEB_MOD_SHIFT; return 1;   // Shift 1
        case '%':  *keycode = 0x22; *modifier = NEB_MOD_SHIFT; return 1;   // Shift 5
        case '(':  *keycode = 0x26; *modifier = NEB_MOD_SHIFT; return 1;   // Shift 9
        case ')':  *keycode = 0x27; *modifier = NEB_MOD_SHIFT; return 1;   // Shift 0
        case ':':  *keycode = 0x33; *modifier = NEB_MOD_SHIFT; return 1;   // Shift ;
        case '?':  *keycode = 0x38; *modifier = NEB_MOD_SHIFT; return 1;   // Shift /
        default:   return 0;
    }
}

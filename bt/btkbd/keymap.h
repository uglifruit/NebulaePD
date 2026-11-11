// keymap.h: ASCII -> USB HID keyboard usage, for the characters that type the same on UK and US layouts.
#ifndef NEB_KEYMAP_H
#define NEB_KEYMAP_H

#include <stdint.h>

#define NEB_MOD_SHIFT 0x02   // left Shift in the HID modifier byte

// The characters btkbd types (plus '\n' = Enter). Everything else is dropped.
#define NEB_SAFE_PUNCT " .,!?()-:%'/;=+[]<>*"

// 1 and the keycode/modifier when c is typed, 0 when it is dropped.
int neb_keymap(unsigned char c, uint8_t * keycode, uint8_t * modifier);

#endif

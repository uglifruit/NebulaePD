# Paged instrument selector logic (uf1). Pure logic, no hardware: ui.py drives it and draws the LEDs.
# Python 2 and 3 compatible so it can be unit-tested off the module.
#
# A bank holds up to MAX_FILES instruments in pages of PAGE_SIZE. The five buttons are the five slots of the page:
#   Pitch turn   -> page (clamped at both ends; ui.py sets the detents per page)
#   button press -> load the instrument in that slot, if there is one (ui.py)
PAGE_SIZE = 5
MAX_FILES = 25

LED_CURRENT = 1.0   # the instrument that is running
LED_FILE = 0.3      # another instrument on this page
LED_EMPTY = 0.0


class InstrPager(object):
    def __init__(self, count=0):
        self.count = 0
        self.page = 0
        self.setCount(count)

    def setCount(self, count):
        self.count = max(0, min(int(count), MAX_FILES))
        self.clamp()

    def numPages(self):
        return max(1, (self.count + PAGE_SIZE - 1) // PAGE_SIZE)

    def filesOnPage(self, page=None):
        if page is None:
            page = self.page
        return max(0, min(PAGE_SIZE, self.count - page * PAGE_SIZE))

    def clamp(self):
        if self.page >= self.numPages():
            self.page = self.numPages() - 1
        if self.page < 0:
            self.page = 0

    def turn(self, pages):
        self.page += int(pages)
        self.clamp()

    def showIndex(self, index):
        """Show the page holding `index` (absolute, 0-based). Out of range or None shows page 1."""
        if index is None or index < 0 or index >= self.count:
            self.page = 0
        else:
            self.page = index // PAGE_SIZE
        self.clamp()

    def slotIndex(self, slot):
        """Absolute index of button `slot` (0-4) on this page, or None if that slot is empty."""
        if slot < 0 or slot >= PAGE_SIZE:
            return None
        idx = self.page * PAGE_SIZE + slot
        if idx >= self.count:
            return None
        return idx

    def offset(self):
        return self.page * PAGE_SIZE

    def leds(self, current=None):
        """Brightness for the five slot LEDs (Record, Next, Source, Reset, Freeze order). `current` is the running
        instrument's absolute index in this bank, or None."""
        values = []
        for slot in range(PAGE_SIZE):
            idx = self.slotIndex(slot)
            if idx is None:
                values.append(LED_EMPTY)
            elif idx == current:
                values.append(LED_CURRENT)
            else:
                values.append(LED_FILE)
        return values

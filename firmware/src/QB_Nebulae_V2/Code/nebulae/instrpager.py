# Paged instrument selector logic (uf1). Pure logic, no hardware: ui.py drives it and draws the LEDs.
# Python 2 and 3 compatible so it can be unit-tested off the module.
#
# A bank holds up to MAX_FILES instruments, shown PAGE_SIZE at a time on the five button LEDs:
#   Next press  -> next page (wraps)          Pitch turn -> cursor within the page (clamped)
#   Reset press -> load the instrument under the cursor (ui.py)
PAGE_SIZE = 5
MAX_FILES = 25

LED_CURSOR = 1.0
LED_FILE = 0.3
LED_EMPTY = 0.0


class InstrPager(object):
    def __init__(self, count=0):
        self.count = 0
        self.page = 0
        self.cursor = 0
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
        n = self.filesOnPage()
        if self.cursor > n - 1:
            self.cursor = n - 1
        if self.cursor < 0:
            self.cursor = 0

    def nextPage(self):
        self.page = (self.page + 1) % self.numPages()
        self.clamp()

    def move(self, steps):
        self.cursor += int(steps)
        self.clamp()

    def goto(self, index):
        """Show `index` (absolute, 0-based). Out-of-range or None goes to the first slot."""
        if index is None or index < 0 or index >= self.count:
            self.page = 0
            self.cursor = 0
        else:
            self.page = index // PAGE_SIZE
            self.cursor = index % PAGE_SIZE
        self.clamp()

    def index(self):
        """Absolute index under the cursor, or None if the bank is empty."""
        if self.count == 0:
            return None
        return self.page * PAGE_SIZE + self.cursor

    def offset(self):
        return self.page * PAGE_SIZE

    def leds(self):
        """Brightness for the five slot LEDs (Record, Next, Source, Reset, Freeze order)."""
        n = self.filesOnPage()
        values = []
        for i in range(PAGE_SIZE):
            if i >= n:
                values.append(LED_EMPTY)
            elif i == self.cursor:
                values.append(LED_CURSOR)
            else:
                values.append(LED_FILE)
        return values

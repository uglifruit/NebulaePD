#!/bin/sh
# run.sh: the Nebulae Bluetooth keyboard helper, started by bt_test.instr / bt_storyteller.instr with
#   systemd-run --unit=neb-bt --collect sh /dev/shm/neb_bt/run.sh <test|story>
# Everything runs from RAM (/dev/shm/neb_bt); nothing on the SD card is written. The stick's bt_keyboard/ folder
# holds the programs, the pairing (pairing.tlv) and the logs (probe.txt, log.txt).
#   test   diagnose the chip's power and UART (diag.txt), probe BTstack's start (probe.txt), then be a keyboard
#          that types a hello line every 10 s
#   story  narrator.py + phrases.py (the instrument's events -> data + poetry) piped into the keyboard;
#          a file named hide_data in bt_keyboard/ leaves out the [data] lines
#   save   (btkbd's hook) copy the new pairing to the stick
# It stops when the module loads another instrument (btkbd --watch on the firmware's bootinstr.txt), or when
# systemd stops the unit (the next launch). btkbd then powers the Bluetooth chip off.
M=/mnt/memory
S=$M/bt_keyboard
W=/dev/shm/neb_bt
BOOTINSTR=/home/alarm/QB_Nebulae_V2/Code/config/bootinstr.txt

mounted() { grep -q " $M " /proc/mounts; }

# copy a file to the stick: mount it if needed, unmount it again if this mounted it
to_stick() {
    was=1
    if ! mounted; then was=0; mkdir -p $M; mount /dev/sda1 $M || return 1; fi
    mkdir -p $S && cp "$1" "$S/$2" && sync
    [ $was = 1 ] || umount $M
}

if [ "$1" = save ]; then
    to_stick $W/pairing.tlv pairing.tlv && echo "pairing saved to the stick" >> $W/log.txt
    exit 0
fi

mkdir -p $W
exec >> $W/log.txt 2>&1
echo "=== run.sh $1, uptime $(cut -d ' ' -f 1 /proc/uptime) s"

# the programs and the pairing, from the stick into RAM
if ! mounted; then mkdir -p $M; mount /dev/sda1 $M; fi
for f in btkbd narrator.py phrases.py; do [ -f $S/$f ] && cp $S/$f $W/$f; done
chmod +x $W/btkbd
rm -f $W/pairing.tlv $W/state
[ -f $S/pairing.tlv ] && cp $S/pairing.tlv $W/pairing.tlv && echo "pairing loaded from the stick"

# this instrument's name, as the firmware wrote it before starting it; btkbd stops once it names another
NAME=$(sed -n 's/^instr,//p' $BOOTINSTR | head -n 1)
echo "instrument: $NAME"
KBD="$W/btkbd --state $W/state --tlv $W/pairing.tlv --hook 'sh $W/run.sh save' --hcd-dir $S"
[ -n "$NAME" ] && KBD="$KBD --watch $BOOTINSTR $NAME"

finish() {
    echo "=== run.sh end, uptime $(cut -d ' ' -f 1 /proc/uptime) s"
    # stopped by itself because another instrument is loading: the firmware is copying from the stick right now,
    # so wait before mounting it (when the next bt instrument stops us, it holds the stick mounted already)
    [ -z "$TERMED" ] && sleep 6
    to_stick $W/log.txt log.txt
    [ -f $W/narrator.log ] && to_stick $W/narrator.log narrator.log
}
trap finish EXIT
trap 'TERMED=1; exit 0' TERM INT

case "$1" in
test)
    # the chip's power line and raw UART first (diag.txt), then BTstack's start (probe.txt)
    $W/btkbd --diag > $W/diag.txt 2>&1
    cat $W/diag.txt
    to_stick $W/diag.txt diag.txt
    $W/btkbd --probe --state $W/state > $W/probe.txt 2>&1
    PROBE=$?
    cat $W/probe.txt
    to_stick $W/probe.txt probe.txt
    if [ $PROBE != 0 ]; then
        echo "probe failed ($PROBE): no keyboard"
        exit 0
    fi
    sleep 1
    eval "$KBD --hello"
    ;;
story)
    # bt_storyteller.instr writes the events; narrator.py turns them into lines; btkbd types them
    if ! python2 -m py_compile $W/narrator.py $W/phrases.py; then
        echo "failed: narrator.py or phrases.py does not compile" > $W/state
        echo 4 > $W/state.code
        exit 0
    fi
    DATA=""
    [ -f $S/hide_data ] && DATA="--no-data" && echo "data lines hidden (hide_data on the stick)"
    python2 -u $W/narrator.py --state $W/state --events $W/events --log $W/narrator.log $DATA | eval "$KBD --type"
    ;;
*)
    echo "unknown mode: $1"
    ;;
esac

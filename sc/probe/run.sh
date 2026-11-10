#!/bin/sh
# SuperCollider probe (docs/FIRMWARE.md, Stage 2). Started by 000_sc_probe.instr through systemd-run, so it runs
# outside nebulae.service and survives the app being stopped in stage 2.
# Nothing on the card changes: SuperCollider runs from /tmp (RAM), gone after a reboot. Results go to the stick:
#   neb_scprobe/RESULT.txt   first line OK or FAIL, then the stage flags
#   neb_scprobe/log.txt      everything this script printed
#   neb_scprobe/probe_nrt.wav  the stage 1 render (2 s: 440 Hz sine left, filtered noise right)
# Stage 1 renders offline (scsynth -N, no audio device). Stage 2 stops the Nebulae app for ~20 s, runs jackd and
# plays a short arpeggio live, then starts the app again (also on any failure, through the EXIT trap).
S=/mnt/memory/neb_scprobe
T=/tmp/sc_probe
R=/tmp/sc
mkdir -p "$T/out" /tmp/sc_home
exec > "$T/log.txt" 2>&1
echo "=== start"
date
uptime

finish() {
  echo "=== finish"
  pkill -x sclang
  pkill -x scsynth
  pkill -x jackd
  sleep 1
  pkill -9 -x sclang
  pkill -9 -x scsynth
  pkill -9 -x jackd
  grep -q " /mnt/memory " /proc/mounts || mount /dev/sda1 /mnt/memory
  if [ -n "$NRT_OK" ] && [ -n "$RT_OK" ]; then RESULT=OK; else RESULT=FAIL; fi
  echo "$RESULT"
  printf '%s\nunpack=%s libs=%s nrt=%s rt=%s\n' "$RESULT" "${UNPACK_OK:-no}" "${LIBS_OK:-no}" "${NRT_OK:-no}" \
    "${RT_OK:-no}" > "$S/RESULT.txt"
  cp "$T"/*.txt "$S/" 2>/dev/null
  cp "$T"/out/*.wav "$S/" 2>/dev/null
  sync
  umount /mnt/memory
  if [ -n "$APP_STOPPED" ]; then systemctl start nebulae; fi
}
trap finish EXIT

grep -q " /mnt/memory " /proc/mounts || mount /dev/sda1 /mnt/memory
echo "=== unpack"
rm -rf "$R"
mkdir -p "$R"
tar -xzf "$S/sc_runtime.tgz" -C "$R" && UNPACK_OK=1
cp "$S/probe_nrt.scd" "$S/probe_rt.scd" "$T/"
du -sh "$R"
df -h /tmp

export LD_LIBRARY_PATH="$R/lib"
export PATH="$R/bin:$PATH"
export HOME=/tmp/sc_home
export SC_PLUGIN_PATH="$R/plugins"
export SC_JACK_DEFAULT_OUTPUTS="system:playback_1,system:playback_2"
export SC_JACK_DEFAULT_INPUTS="system:capture_1,system:capture_2"

echo "=== ldd"
ldd "$R/bin/sclang" "$R/bin/scsynth"
if ldd "$R/bin/sclang" "$R/bin/scsynth" | grep -q "not found"; then echo "LIBS_MISSING"; else LIBS_OK=1; fi
echo "=== versions"
timeout 10 scsynth -v
timeout 30 sclang -v

echo "=== stage 1: NRT render"
cd "$T"
timeout 180 sclang -D -l "$R/sclang_conf.yaml" "$T/probe_nrt.scd" < /dev/null
ls -l "$T/out"
if [ -s "$T/out/probe_nrt.wav" ]; then NRT_OK=1; fi

echo "=== stage 2: realtime (the Nebulae app is stopped meanwhile)"
APP_STOPPED=1
systemctl stop nebulae
sleep 2
jackd -R -P75 -dalsa -dhw:0 -p512 -n3 -s -r48000 > "$T/jackd.txt" 2>&1 &
sleep 5
timeout 60 sclang -D -l "$R/sclang_conf.yaml" "$T/probe_rt.scd" < /dev/null > "$T/rt.txt" 2>&1
cat "$T/rt.txt"
if grep -q "SCPROBE: RT done" "$T/rt.txt"; then RT_OK=1; fi
echo "=== jackd"
cat "$T/jackd.txt"

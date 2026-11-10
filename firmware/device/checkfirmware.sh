#!/bin/bash
set -x
# Check if original firmware exists
primarypath=/home/alarm/QB_Nebulae_V2/Code
foundfiles=0
foundc=0
nfoundc=0
fflist=""
nflist=""
filelist='/home/alarm/mandatory_files.txt'

revertfirmware=0

exec 3< $filelist
while read file_a <&3; do
    if [[ -s "$primarypath/${file_a}" ]];then
        foundc=$((foundc + 1))
        fflist="${fflist} ${file_a}"
    else
        nfoundc=$((nfoundc + 1))
        fflist="${nflist} ${file_a}"
    fi
done

exec 3<&-

mount /dev/sda1 /mnt/memory
logfile="/mnt/memory/neb_log.txt"
if [ ! -f $logfile ]; then
    logfile="/home/alarm/temp_log.txt"
    sh $primarypath/scripts/mountfs.sh rw
fi

#echo "List of found files: " "${fflist}" >> $logfile
#echo "List of NOT found files: " "${nflist}" >> $logfile
echo "Number of files in "[$filelist]" found = [${foundc}]" >> $logfile
echo "Number of files in "[$filelist]" NOT found = [${nfoundc}]" >> $logfile

if [ "$nfoundc" -eq "0" ]; then
    echo "No Missing Files." >> $logfile
    echo "Checking For Reversion Request" >> $logfile
    if [ -f /mnt/memory/revert_to_factory_firmware ]; then
        revertfirmware=$((revertfirmware + 1))
        echo "Found Firmware Reversion Request. Deleting Request File" >> $logfile
        rm /mnt/memory/revert_to_factory_firmware
    else
        echo "Unable to find Factory Firmware Reversion Request" >> $logfile
    fi
else
    revertfirmware=$((revertfirmware + 1))
fi

if [ "$revertfirmware" -eq "0" ]; then
    echo "No request to revert to firmware." >> $logfile
    sh $primarypath/scripts/mountfs.sh ro
    umount /dev/sda1
    sh $primarypath/scripts/startup.sh 
else
    sh $primarypath/scripts/mountfs.sh rw
    echo "Reverting to factory firmware." >> $logfile
    rm -rf /home/alarm/QB_Nebulae_V2/
    tar -xvf /home/alarm/neb_factory_fw.zip -C /home/alarm/
    umount /dev/sda1
    sh $primarypath/scripts/mountfs.sh ro
    sudo python2 /home/alarm/QB_Nebulae_V2/Code/nebulae/check_calibration.py force
    sh $primarypath/scripts/startup.sh 
fi
exit

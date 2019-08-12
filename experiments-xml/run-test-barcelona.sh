#!/bin/bash
# barcelona split

version="rp0.3"
netlogo="nohup time /home/paolucci/NetLogo\ 6.0.4/netlogo-headless-2G.sh"

for arg in `ls experiments-xml/split_xml/rp0.30[0-7].xml`; do
   eval "$netlogo --model PROTON-OC.nlogo --setup-file $arg --table $arg.barcelona.csv > $arg.barcelona.out 2>&1 &"	
done

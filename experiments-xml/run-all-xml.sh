#!/bin/bash
# barcelona split

version="rp0.3"
netlogo="/Applications/NetLogo\ 6.0.4/netlogo-headless.sh"

for arg in `ls experiments-xml/split_xml/rp0.30[0-7].xml`; do
   eval "$netlogo --model PROTON-T.nlogo --setup-file $arg --table $arg.csv > $arg.out 2>&1 &"	
done

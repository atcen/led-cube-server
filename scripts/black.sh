#!/bin/bash

CONTROLLERS=(
  192.168.10.241
  192.168.10.233
  192.168.10.207
  192.168.10.208
  192.168.10.215
  192.168.10.204
)

for ip in "${CONTROLLERS[@]}"; do
  {
    start=$(perl -MTime::HiRes=time -e 'printf "%d\n", time()*1000')
    result=$(curl --no-progress-meter -X POST http://$ip/json/state \
      -H "Content-Type: application/json" \
      -d '{"on":true,"bri":0,"seg":[{"fx":0,"col":[[0,0,0]]}]}' 2>&1)
    end=$(perl -MTime::HiRes=time -e 'printf "%d\n", time()*1000')
    echo "$ip: ${result} ($(( end - start ))ms)"
  } &
done
wait

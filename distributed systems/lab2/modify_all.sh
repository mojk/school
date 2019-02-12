#!/usr/bin/env bash
for i in `seq 1 8`; do
curl -d 'entry=t2-'${i} -d 'delete=0' -X 'POST' 'http://10.1.0.'${i}':80/board/0' &
done
for i in `seq 1 7`; do
curl -d 'entry=t2-'${i} -d 'delete=1' -X 'POST' 'http://10.1.0.'${i}':80/board/'${i} &
done

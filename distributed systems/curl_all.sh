#!/usr/bin/env bash
for i in `seq 1 8`; do
curl -d 'entry=t'${i} -X 'POST' 'http://10.1.0.'${i}':80/board' &
done

#!/usr/bin/env bash

# Send a get request to the specified url and store response body ui a variable called body.
function send_request {
	# Reset variables
	unset output
	unset head
	unset header
	unset body
    output=$(curl -si $1) # Store request response
	head=true
	while read -r line; do 
	    if $head; then 
	        if [[ $line = $'\r' ]]; then
	        head=false
	    else
	        header="$header"$'\n'"$line" # Get header from response
	    fi
	    else
	        body="$body"$'\n'"$line" # Get body from response
	    fi
	done < <(echo "$output")
}

function check_entries {
	echo " "
	echo Checking entries

	# Check that all messages are in the same order in each vessel.
	result_string="OK!"
	for j in `seq 0 14`; do
	send_request '10.1.0.1/entry/get/'${j}
	msg=$body
	for i in `seq 2 8`; do
	send_request '10.1.0.'${i}'/entry/get/'${j}
	if [[ $body != $msg ]]
	then
		result_string="Done."
	    echo 'Bad output for [10.1.0.'${i}'/entry/get/'${j}']! Expected:'$msg', Actual:'$body
	fi
	done
	done

	echo $result_string
}

function fetch_random_id {
	unset random_id_components
	send_request '10.1.0.'$(($1+1))'/random_id/get'
	random_id_components=$(echo $body | tr ":" "\n" | tr "}" "\n" | tr " " "\n")
	re='^[0-9]+$'
	for p in $random_id_components
	do
		if [[ $p =~ $re ]] ; then
			random_ids[$1]=$p
		fi
	done
}

echo Starting

sleep 5 # If script is run to early, leader might not have been elected yet. Wait 5 second just to make sure.

random_ids=(0,0,0,0,0,0,0,0)

echo " "
echo Fetching random ids to use for delete/modify

for i in `seq 0 7`; do
	fetch_random_id $i
done

sleep 5

echo " "
echo Posting concurrent messages to each vessel

# Send one message to each vessel
for i in `seq 1 8`; do
	curl -d 'entry=t'${i} -X 'POST' 'http://10.1.0.'${i}':80/board' &
done

sleep 5 # Wait for all messages to be received by all servers.

check_entries

echo " "
echo Posting concurrent messages to the same vessel

# Send one message to each vessel
for i in `seq 1 8`; do
	curl -d 'entry=t'$((8+i)) -X 'POST' 'http://10.1.0.1:80/board' &
done

sleep 5 # Wait for all messages to be received by all servers.

check_entries

echo " "
echo Deleting same message concurrently on all vessels

for i in `seq 1 8`; do
	curl -d 'delete=1' -X 'POST' 'http://10.1.0.'$i':80/board/0/'${random_ids[0]}'/1' &
done

sleep 5 # Wait for the delete to be propagated to all servers.

check_entries

echo " "
echo Modifying same message concurrently on all vessels

for i in `seq 1 8`; do
	curl -d 'delete=0' -d 'entry=modified'$i -X 'POST' 'http://10.1.0.'$i':80/board/1/'${random_ids[0]}'/1' &
done

sleep 5 # Wait for the delete to be propagated to all servers.

check_entries

echo " "
echo Done. Stopping
echo " "

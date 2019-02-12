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
	for j in `seq 0 7`; do
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

echo Starting

sleep 5 # If script is run to early, leader might not have been elected yet. Wait 5 second just to make sure.

echo Posting messages

# Send one message to each vessel
for i in `seq 1 8`; do
curl -d 'entry=t'${i} -X 'POST' 'http://10.1.0.'${i}':80/board' &
done

sleep 12 # Wait for all messages to be received by all servers.

echo " "
echo Checking leader

# Check that all vessels have the same leader
send_request 10.1.0.1/leader/get
leader=$body
result_string="OK!"
for i in `seq 1 8`; do
send_request '10.1.0.'${i}'/leader/get'
if [[ $body != $leader ]]
then
	result_string="Done."
    echo 'Bad output for [10.1.0.'${i}'/leader/get]! Expected:'$leader', Actual:'$body
fi
done

echo $result_string

check_entries

echo " "
echo Modifying messages

# Modify first message on all vessels
for i in `seq 1 8`; do
curl -d 'entry=t'$((i+1)) -d 'delete=0' -X 'POST' 'http://10.1.0.'${i}':80/board/0' &
done

sleep 12 # Wait for all modifications to be received by all servers.

check_entries

echo " "
echo Concurrently deleting and modifying messages

# Modify one message on half of the vessels
for i in `seq 1 4`; do
curl -d 'entry=t'${i} -d 'delete=0' -X 'POST' 'http://10.1.0.'${i}':80/board/1' &
done
# Delete the same message on the other half of the vessels
for i in `seq 5 8`; do
curl -d 'entry=t'${i} -d 'delete=1' -X 'POST' 'http://10.1.0.'${i}':80/board/1' &
done

sleep 12 # Wait for all modifications and deletetions to be received by all servers.

check_entries

echo " "
echo Done. Stopping
echo " "

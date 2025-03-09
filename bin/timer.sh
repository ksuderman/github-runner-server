__START_TIME=

function start_timer() {
	__START_TIME=$SECONDS
}

function end_timer() {
	restore=0
	if [[ $- = *u* ]] ; then
		restore=1
		set +u
	fi
	prompt=""
	if [[ -n $1 ]] ; then
		prompt=$1
	fi
	if [[ $restore = 1 ]] ; then
		set -u
	fi
	elapsed_time=$(( SECONDS - $__START_TIME ))
	seconds=$(( elapsed_time % 60 ))
	echo "$prompt$(( elapsed_time / 60 )):$(printf %02d $seconds)"
}
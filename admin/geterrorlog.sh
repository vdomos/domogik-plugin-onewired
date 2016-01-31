#!/bin/bash

ERROR=$(egrep 'WARNING|ERROR' /var/log/domogik/onewired.log |sort -rnk1,2 | head -10)
if [ -z "$ERROR" ]
then
	echo "Hooray, No error."
else
	echo "$ERROR"
fi

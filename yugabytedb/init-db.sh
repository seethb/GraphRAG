#!/bin/bash

# Start YugabyteDB as a daemon
/home/yugabyte/bin/yugabyted start \
  --base_dir=/home/yugabyte/var \
  --advertise_address=yugabytedb

# Wait for YSQL to be ready
until /home/yugabyte/bin/ysqlsh -h /tmp/.yb.*:5433 -c '\l'; do
  echo "Waiting for YSQL..."
  sleep 3
done

# Check whether we have data in the database already
/home/yugabyte/bin/ysqlsh -h /tmp/.yb.*:5433  -c "SELECT COUNT(*) FROM graph_nodes" -d graphrag

# If we do not, populate the database
if [ $? -ne 0 ]; then
  /home/yugabyte/bin/ysqlsh -h /tmp/.yb.*:5433 --file=/home/yugabyte/init-db.sql
fi

# Don't exit this script so that the container continues to run YugabyteDB
tail -f /dev/null
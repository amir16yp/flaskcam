#!/bin/bash

# Prompt user for username
read -p "Enter username: " username

# Prompt user for password
read -p "Enter password: " -s password
echo

# Prompt user for host
read -p "Enter host: " host

# Prompt user for port
read -p "Enter port: " port

# Start flaskcamera with user input
nohup python3 flaskcamera.py --username $username --password $password --host $host --port $port > output.log &
echo "Flaskcamera has been started."

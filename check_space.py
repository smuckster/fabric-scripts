#!/usr/bin/env python3
#
# Check Space Script
# version 1.0
#

from dateutil import parser
from fabric import Connection
from datetime import datetime, timedelta, timezone
import colored
from colored import stylize
import sys
import re
import argparse
import os
import time

# Import complete list of host names for active clients
from hosts_list import clients

# Get an array containing space usage information for xvda1, in the format [percent_used, amount_used, total_amount, amount_left]
def get_percentage(host):

    percentage = host.sudo("df -h | grep xvda1 | awk '{print $5}'", hide='both').stdout.split('\n')[:-1]
    percentage.append(host.sudo("df -h | grep xvda1 | awk '{print $3}'", hide='both').stdout.split('\n')[:-1][0])
    percentage.append(host.sudo("df -h | grep xvda1 | awk '{print $2}'", hide='both').stdout.split('\n')[:-1][0])
    percentage.append(host.sudo("df -h | grep xvda1 | awk '{print $4}'", hide='both').stdout.split('\n')[:-1][0])
    return percentage

# Checks the expiration date of each SSL certificate supplied and prints a message about it
def check_space(host, host_name, flags=None):

    # Get an array of space information
    percentage = get_percentage(host)

    # Get the IP of this host
    ip = host.host
    # Find the instance that corresponds to this IP, and grab its volume ID
    vol_id = os.popen("aws ec2 describe-instances --filter Name=ip-address,Values='"+ip+"' | grep VolumeId | awk '{print $2}'").read().replace('"', '')
    # Get the current size of this volume and strip the extra chars
    curr_size = os.popen("aws ec2 describe-volumes --volume-ids '"+vol_id+"' | grep Size | awk '{print $2}'").read().strip()[:-1]

    # Create local variables that can be flagged to change function behavior
    no_colors = False
    only_warn = False
    expand_vol = False

    # Check if there are any flags in the flags list (if one was provided)
    if (flags is not None) and (len(flags) > 0):
        for flag in flags:
            if flag == "--no-colors":
                no_colors = True
            elif flag == "--only-warnings":
                only_warn = True
            elif flag == "--expand-vols":
                expand_vol = True

    print("\nSpace Usage: " + host_name)

    if int(percentage[0][:-1]) > 90 or float(percentage[3][:-1]) < 5:
        if no_colors:
            print("+ ", percentage[1]+"/"+percentage[2]+" used, "+percentage[3]+" left ("+percentage[0]+") \tSpace may run out soon. \t*WARNING*")
        else:
            print("+ ", percentage[1]+"/"+percentage[2]+" used, "+percentage[3]+" left ("+percentage[0]+")", stylize("\tSpace may run out soon. \t*WARNING*", colored.fg("orange_1")))
        if expand_vol:
            print("Expanding volume "+vol_id+" to "+str(int(curr_size)+10)+"GB...")
            os.system('aws ec2 modify-volume --size '+str(int(curr_size)+10)+" --volume-id "+vol_id)
            print("Waiting for volume to expand...")
            # Growing the partition and expanding the filesystem will fail if we don't wait long enough.
            # I'm not sure how long this needs to be, but it's somwhere between 5 and 30 seconds
            time.sleep(30)
            os.system('aws cli --size '+str(int(curr_size)+10)+" --volume-id '"+vol_id+"'")
            host.sudo('growpart /dev/xvda 1')
            host.sudo('resize2fs /dev/xvda1')

    elif int(percentage[0][:-1]) == 100:
        if no_colors:
            print("+ ", percentage[1]+"/"+percentage[2]+" used, "+percentage[3]+" left ("+percentage[0]+")\tOut of space!. \t*WARNING*")
        else:
            print("+ ", percentage[1]+"/"+percentage[2]+" used, "+percentage[3]+" left ("+percentage[0]+")", stylize("\tOut of space! \t*WARNING*", colored.fg("red_1")))
        if expand_vol:
            print("Expanding volume "+vol_id+" to "+str(int(curr_size)+10)+"GB...")
            os.system("aws ec2 modify-volume --size "+str(int(curr_size)+10)+" --volume-id "+vol_id)
            print("Waiting for volume to expand...")
            time.sleep(30)
            os.system('aws cli --size '+str(int(curr_size)+10)+" --volume-id '"+vol_id+"'")
            host.sudo('growpart /dev/xvda 1')
            host.sudo('resize2fs /dev/xvda1')
    elif not only_warn:
        print("+ ", percentage[1]+"/"+percentage[2]+" used, "+percentage[3]+" left ("+percentage[0]+")")

# Handle arguments

# Declare global variables
flags = list()
host_args = list()

# Delete the first item in the argument list, which is just the name of the command being run
del sys.argv[0]

# If any arguments were passed, first check to see if they are flags or host names
if len(sys.argv) > 0:
    for arg in sys.argv:
        # If the first character in the argument is a dash, it is a flag, so add it to the array of flags to be passed to the check_ssl() function
        if arg[0] == "-":
            flags.append(arg)
        # Otherwise, append the argument to the host_args list because it is expected to be a host name
        else:
            host_args.append(arg)

# If one of the flags was -h or --help, show help options
        if ("-h" in flags) or ("--help" in flags):
            print("This tool checks the space usage on remote servers, printing the amount used out of the total amount, the amount left, and the percentage used")
            print("It accepts a list of arguments that are host names from your SSH config file.")
            print("If no arguments are provided, this script will output space information for every client.")
            print("\nOptions:\n")
            print("-h or --help: display this message")
            print("--only-warnings: output only warning messages (these will display if space used is greater than 90% or space left is less than 10GB")
            print("--no-color: output will not include text colors. **IMPORTANT** Use this option if you are redirecting the output directly to a log file!")
            print("--expand-vols: this option will actually go ahead and expand the filesystem if space usage is over 90%, or less than 5GB are left. The filesystem will be expanded by 10GB")

# If flags were given but no host name arguments were, run the entire list of clients
        elif (len(host_args) == 0):
            for host in clients:
                c = Connection(host)
                check_space(c, host, flags)

        else:
# For each host name given as an argument, run the check_ssl() function
            for host in host_args:
                c = Connection(host)
                check_space(c, host, flags)

# If no arguments were passed, check all certificates and print output to console
else:
    for host in clients:
        c = Connection(host)
        check_space(c, host)

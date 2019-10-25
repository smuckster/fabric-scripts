#!/usr/bin/env python3
#
# Check SSL Script
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

# Import complete list of host names for active clients
from hosts_list import clients

# Find if cron.php is in the crontab
def get_cron(host):
    try:
        return host.sudo("crontab -l | grep -q cron.php")
    except:
        return False

# Checks if the cron script is in the crontab and displays a message about it
def check_cron(host, host_name, flags=None):

    # Get an array of certificate paths on the server
        is_set_up = get_cron(host)

        # Create local variables that can be flagged to change function behavior
        no_colors = False
        only_warn = False

        # Check if there are any flags in the flags list (if one was provided)
        if (flags is not None) and (len(flags) > 0):
            for flag in flags:
                if flag == "--no-colors":
                    no_colors = True
                elif flag == "--only-warnings":
                    only_warn = True

        print("\nHost: " + host_name)


        if not is_set_up:
            if no_colors == True:
                print("+ Cron is not set up!!\t*WARNING*")
            else:
                print("+ ", stylize("\tCron is not set up!!\t*WARNING*", colored.fg("red")))
        else:
            if only_warn == False:
                if no_colors == True:
                    print("+ \tCron is set up.")
                else:
                    print("+ ", stylize("\tCron is set up.", colored.fg("green")))

# Handle arguments

# Declare global variables
flags = list()
host_args = list()

# Delete the first item in the argument list, which is just the name of the command being run
del sys.argv[0]

# If any arguments were passed, first check to see if they are flags or host names
if len(sys.argv) > 0:
    for arg in sys.argv:
        # If the first character in the argument is a dash, it is a flag, so add it to the array of flags to be passed to the check_cron() function
        if arg[0] == "-":
            flags.append(arg)
        # Otherwise, append the argument to the host_args list because it is expected to be a host name
        else:
            host_args.append(arg)

        # If one of the flags was -h or --help, show help options
        if ("-h" in flags) or ("--help" in flags):
            print("This tool checks the SSL certificate expiration dates on remote servers.")
            print("It accepts a list of arguments that are host names from your SSH config file.")
            print("If no arguments are provided, this script will output cron status for every eClass4Learning client directly to the console.")
            print("\nOptions:\n")
            print("-h or --help: display this message")
            print("--only-warnings: output only warning messages (these will display if certificates have expired or will expire in the next month)")
            print("--no-color: output will not include text colors. **IMPORTANT** Use this option if you are redirecting the output directly to a log file!")

        # If flags were given but no host name arguments were, run the entire list of clients
        elif (len(host_args) == 0):
            for host in clients:
                c = Connection(host)
                check_cron(c, host, flags)

        else:
            # For each host name given as an argument, run the check_ssl() function
            for host in host_args:
                c = Connection(host)
                check_cron(c, host, flags)

# If no arguments were passed, check all certificates and print output to console
else:
    for host in clients:
        c = Connection(host)
        check_cron(c, host)

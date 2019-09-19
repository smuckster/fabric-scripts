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

# Retrieve a list of absolute paths to SSL certificate files by searching the /etc/nginx/sites-enabled directory
def get_certs(host):
	possible_certs = host.sudo("grep -soRE 'ssl_certificate[[:space:]]+[^;]+;.*$' /etc/nginx/sites-enabled | awk '{print $2}' | awk '-F;' '{print $1}'", hide='both').stdout.split('\n')[:-1]
	possible_certs = list(map(lambda i: i.strip(), possible_certs))

	return possible_certs

# Checks the expiration date of each SSL certificate supplied and prints a message about it
def check_ssl(host, host_name, flags=None):

	# Get an array of certificate paths on the server
	certs = get_certs(host)

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

	for cert in certs:
		raw_expdate = str(host.sudo("openssl x509 -enddate -noout -in " + cert + " | awk -F= '{print $2}' | awk '-F ' '{print $1, $2, $4, $3, $5}'", hide='both').stdout)
		raw_expdate = raw_expdate.replace("\n", "")
		raw_expdate = raw_expdate.replace("  ", " ")
		#raw_expdate = "Oct 6 21:33:45 2019 GMT"
		#print(cert, "\n" + raw_expdate)

		# Make sure the certificate has an expiration date (excludes sample certificates built into new servers)
		if raw_expdate != "":
			expdate = parser.parse(raw_expdate)
			one_month_before = timedelta(days=-31)
	

			# If the certificate has expired
			if datetime.now(timezone.utc) > expdate:
				if no_colors == True:
					print("+ ", cert, "\tCertificate expired! Expiration date: " + raw_expdate + "\t*WARNING*")
				else:
					print("+ ", cert, stylize("\tCertificate expired! Expiration date: " + raw_expdate + "\t*WARNING*", colored.fg("red")))
			
			# If the certificate will expire in the next 31 days
			elif datetime.now(timezone.utc) > (expdate + one_month_before):
				if no_colors == True:
					print("+ ", cert, "\tCertificate expires soon! Expiration date: " + raw_expdate + "\t*WARNING*")
				else:
					print("+ ", cert, stylize("\tCertificate expires soon! Expiration date: " + raw_expdate + "\t*WARNING*", colored.fg("orange_1")))
			
			# If the certificate is still active and will not expire soon
			else:
				if only_warn == False:
					if no_colors == True:
						print("+ ", cert, "\tCertificate expires " + raw_expdate)
					else:
						print("+ ", cert, stylize("\tCertificate expires " + raw_expdate, colored.fg("green"))) 
		
		# If the certificate has no expiration date
		else:
			print("+ ", cert, stylize("\tCertificate is not valid.", colored.fg("red")))

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
		print("This tool checks the SSL certificate expiration dates on remote servers.")
		print("It accepts a list of arguments that are host names from your SSH config file.")
		print("If no arguments are provided, this script will output expiration dates for every eClass4Learning client directly to the console.")
		print("\nOptions:\n")
		print("-h or --help: display this message")
		print("--only-warnings: output only warning messages (these will display if certificates have expired or will expire in the next month)")
		print("--no-color: output will not include text colors. **IMPORTANT** Use this option if you are redirecting the output directly to a log file!")

	# If flags were given but no host name arguments were, run the entire list of clients
	elif (len(host_args) == 0):
		for host in clients:
			c = Connection(host)
			check_ssl(c, host, flags)

	else:
		# For each host name given as an argument, run the check_ssl() function
		for host in host_args:
			c = Connection(host)
			check_ssl(c, host, flags)

# If no arguments were passed, check all certificates and print output to console
else:
	for host in clients:
		c = Connection(host)
		check_ssl(c, host)

#!/usr/bin/env python

import socket
import re
import os
import signal
import time
from pprint import pprint
from requests import get
import json
import sys
import traceback
import yaml
from jinja2 import Template
import socket
from sys import stdout
from time import sleep

def exit_gracefully(signum, frame):
	# restore the original signal handler as otherwise evil things will happen
	# in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
	signal.signal(signal.SIGINT, original_sigint)
	main()
	# restore the exit gracefully handler here    
	signal.signal(signal.SIGINT, exit_gracefully)
	
	

def GetControllerIP():
	ip = get('https://api.ipify.org').text
	return ip


def RenderRouterConfiguration():
	script_dir = os.path.dirname(__file__)
	rel_path = "TopologyVariables.yaml"
	abs_file_path = os.path.join(script_dir, rel_path)
	file=open(abs_file_path)
	asbr_vars = yaml.load(file.read())
	asbr_vars['home_directory'] = os.path.dirname(os.path.realpath(__file__))
	asbr_vars['controller_ip'] = GetControllerIP()
	file.close()
	template_open = open("LER_Configs.j2")
	ingress_template = Template(template_open.read())
	template_output = ingress_template.render(asbr_vars)
	script_dir = os.path.dirname(__file__)
	rel_path = "LERs.conf"
	abs_file_path = os.path.join(script_dir, rel_path)
	with open(abs_file_path, "wb") as f:
		f.write(template_output)
	f.close()
	file.close()



if __name__ == "__main__":
	# store the original SIGINT handler
	original_sigint = signal.getsignal(signal.SIGINT)
	signal.signal(signal.SIGINT, exit_gracefully)
	RenderRouterConfiguration()

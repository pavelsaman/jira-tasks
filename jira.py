#!/usr/bin/python

#########################################################################
# Finds all Jira issues in specified projects and in particular states. #
# Jira statuses are projects could be defined in:                       #
# - here in the status                                                  #
# - in files ".statuses" and ".projects"                                #
# - in env variables JIRA_STATUSES and JIRA_PROJECTS                    #
# The statuses and projects are read in this order, going down the list #
# happens only if the previous source returns an empty list/dict of     #
# projects/statuses.                                                    #
# Statuses are a key:value pair on each line of .statuses file or       #
# a key:value pair separated by commas in env variable.                 #
# One projects is on each line of .projects or a you can define a       #
# comma-separated string of projects in env variable.                   #
# Files .statuses and .projects support comments (line starting         #
# with '#'), and lines with only '\n' or '\r\n' are ignored.            #
#########################################################################

from requests.auth import HTTPBasicAuth
from types import MappingProxyType
import requests
import argparse
import sys
import os

##############################################################################################################

EMPTY = ''

# read Jira statuses from a file
def read_statuses_from_file(orig_file_name):
	file_name = orig_file_name.replace('~', os.environ.get("HOME"))
	if not os.path.isfile(file_name):
		return statuses
	with open(file_name, 'r') as reader:
		statuses = reader.read().split('\n')
	statuses = [status for status in statuses if len(status)>0 and status[0] != '#']
	statuses_dict = {}
	for status in statuses:
		key, value = status.split(':')
		statuses_dict[key] = value
	return statuses_dict

# read Jira statuses from env variable
# format: key:value,key1:value1,...keyN:valueN
def read_statuses_from_env(env_var_name):
	statuses = {}
	if not os.getenv(env_var_name):
		return statuses
	for l in os.getenv(env_var_name).split(','):
		key, value = l.split(':')
		statuses[key] = value
	return statuses

# read Jira projects from a file
def read_projects_from_file(orig_file_name):
	file_name = orig_file_name.replace('~', os.environ.get("HOME"))
	if not os.path.isfile(file_name):
		return projects
	with open(file_name, 'r') as reader:
		projects = reader.read().split('\n')
	return [project for project in projects if len(project)>0 and project[0] != '#']

# read Jira projects from env variable
# format: project1,project2,...,projectN
def read_projects_from_env(env_var_name):
	projects = []
	if not os.getenv(env_var_name):
		return projects
	for l in os.getenv(env_var_name).split(','):
		projects.append(l)
	return projects

def requirements():
	if not JIRA_API_KEY:
		print('NO JIRA API KEY present, can\'t proceed.')
		exit(1)
	if not JIRA_USER:
		print('NO JIRA USER present, can\'t proceed.')
		exit(1)
	if not BASE_API_URL:
		print('NO BASE API URL present, can\'t proceed.')
		exit(1)
	if not AUTH:
		print('No auth, can\'t proceed.')
		exit(1)
	if not HEADERS:
		print('No headers specified, can\'t proceed.')
		exit(1)
	if not BROWSE_BASE_URL:
		print('No BROWSE BASE URL specified, can\'t proceed.')
		exit(1)
	if not STATUSES:
		print('No STATUSES, can\'t proceed.')
		exit(1)
	if not PROJECTS:
		print('No PROJECTS, can\'t proceed.')
		exit(1)

# searches
def get_test_tickets(env):	
	query = MappingProxyType({
		'jql': 'project in ({0}) AND status in ("{1}")'.format(','.join(PROJECTS), env)
	})
	response = requests.request("GET", BASE_API_URL + 'search', headers=HEADERS, params=query, auth=AUTH)
	if response.status_code == 200:
		return response.json()
	return None

# pretty prints issues
# adds '!' in front of 'Number of issues: ' if a status_code was != 200
def issues_pretty_print(result_json):
	if result_json is None:
		print('! Number of issues: 0')
	else:
		print('Number of issues: {0}'.format(result_json['total']))	
		for j in result_json['issues']:
			print('{0} : {1} : {2} : {3}'.format(j['key'], BROWSE_BASE_URL + j['key'],
				j['fields']['priority']['id'] ,j['fields']['summary']))
	
def main(args):
	# only prints all Jira statuses to console
	if args.statushelp:
		for k, v in STATUSES.items():
			print(k + ':' + v)
		return 0

	# only prints all Jira priorities to console
	if args.priorityhelp:
		for k, v in PRIORITY.items():
			print(k + ':' + v)
		return 0

	print(','.join(PROJECTS) + '\n')

	if args.status.lower() == 'all': # iterate over all test statuses
		for v in STATUSES.values():
			print('{0}:'.format(v))
			issues_pretty_print(get_test_tickets(v))	

	# create environment list
	envs = args.status.split(',')
	for e in envs:
		e_lower = e.lower()
		if e_lower in STATUSES: # if such a status exists
			print('{0}:'.format(STATUSES[e_lower]))
			issues_pretty_print(get_test_tickets(STATUSES[e_lower]))		

##############################################################################################################

JIRA_USER = os.getenv('JIRA_API_USER') or 'pavel.saman@inveo.cz'
JIRA_API_KEY = os.getenv('JIRA_API_KEY') or None
BASE_API_URL = 'https://inveocz.atlassian.net/rest/api/3/'
BROWSE_BASE_URL = 'https://inveocz.atlassian.net/browse/'
AUTH = HTTPBasicAuth(JIRA_USER, JIRA_API_KEY)
HEADERS = MappingProxyType({
   "Accept": "application/json"
})
STATUSES_FILE_NAME = './.statuses'
PROJECTS_FILE_NAME = './.projects'
STATUSES_ENV_NAME = 'JIRA_STATUSES'
PROJECTS_ENV_NAME = 'JIRA_PROJECTS'
STATUSES = {} or read_statuses_from_file(STATUSES_FILE_NAME) or read_statuses_from_env(STATUSES_ENV_NAME)
PROJECTS = [] or read_projects_from_file(PROJECTS_FILE_NAME) or read_projects_from_env(PROJECTS_ENV_NAME)
PROJECTS = ['"' + i + '"' for i in PROJECTS] # double quotes around project names
PRIORITY = MappingProxyType({
	1: 'Highest',
	2: 'High',
	3: 'Medium',
	4: 'Low',
	5: 'Lowest'
})

##############################################################################################################

if __name__ == '__main__':

	# check requirements
	requirements()

	# arguments
	parser = argparse.ArgumentParser(description='Show Jira tickets in particular states.')
	parser.add_argument("-s", "--status", nargs='?', const='all', type=str,
		help="Comma separated string of states in Jira.")
	parser.add_argument("--statushelp", action='store_true',
		help="Print all Jira statuses.")
	parser.add_argument("--priorityhelp", action='store_true',
		help="Print all Jira priorities.")

	# if no arguments are present
	if len(sys.argv) == 1:
		parser.print_help()
		exit(0)

	# parse arguments
	args = parser.parse_args()

	# start main program
	main(args)

	exit(0)

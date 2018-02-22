import csv
import os
import sys
from datetime import datetime

try:
	import yaml
except ImportError:
	yaml = None

DEBUG = True  # Set this to False before releasing

FACULTY_COLUMN = 2

# Default candidates per election
DEFAULT_FRC_CANDIDATES = 3  # 2 + Abstain
DEFAULT_EXECUTIVE_CANDIDATES = 2  # 1 + Abstain

VALIDATED_STUDENTS_NUM_HEADERS = 3  # Number of header lines to ignore before reading CSV

DEFAULT_CONFIG = {
	'faculty_column': 3,
	'user_column': 2,
	'frc_votes': 2,
	'exec_votes': 1,
	'international_offset': 13,
	'frc_offset': 4,
	'frc_elections': ["Social Sciences", "Humanities", "Health Sciences", "Business"],
	'exec_offset': 15,
	'exec_elections': ["VP Administration", "VP Internal", "VP External", "VP Services", "President"]
}

DEFAULT_OUTPUT_DIR = "compiled_results_{}".format(datetime.now().strftime("%Y%m%d"))

def create_parser():
	# Build argument parser
	parser = argparse.ArgumentParser()
	parser.add_argument('file', help="Validated Results File")
	parser.add_argument('-c', '--config', help="Provide a config file for the program.")
	#parser.add_argument('-r', '--results_file', default="compilation_results_{}.csv".format(datetime.now().strftime("%Y%m%d")))
	parser.add_argument('-d', '--directory', default=DEFAULT_OUTPUT_DIR, help="Write compiled votes into a given directory. Default: {}".format(DEFAULT_OUTPUT_DIR))

	return parser

def debug(msg):
	if DEBUG:
		print("DEBUG " + msg)

def read_config(config_file):
	if config_file is None:
		return DEFAULT_CONFIG

	if yaml is None:
		print("Error: This script requires the package pyyaml to be installed.  Install it via `pip install pyyaml`")
		sys.exit(1)

	with open(config_file, 'r') as f:
		config = yaml.load(f)

	# Populate with default values if not present
	for key, val in DEFAULT_CONFIG.items():
		if key not in config:
			config[key] = val

	return config

def convert_election_name(election):
	# Creates a file friendly name from a human readable

	return election.lower().replace(' ', '_')

def create_election_files(directory, *elections):
	# For each frc and exec candidates structure, create a file

	the_files = {}
	for election_type in elections:
		for election in election_type:
			converted_election = convert_election_name(election)
			the_files[election] = open(os.path.join(directory, converted_election +'.csv'), 'w', newline="")

	return the_files

def close_election_files(election_files):
	# Close all file handlers

	for f in election_files.values():
		try:
			f.close()
		except Exception as exc:
			print("Warning: Cannot close file: {}".format(str(exc)))

def build_election_columns(config):
	# From config file, build a dict of elections and column numbers, for easy refernce while compiling
	
	election_columns = {}

	# Get User and Faculty Columns from config
	election_columns['User'] = config['user_column']-1
	election_columns['Faculty'] = config['faculty_column']-1

	# Find columns for FRC elections
	current_col = config['frc_offset']-1
	for faculty in config['frc_elections']:
		election_columns[faculty] = current_col
		current_col += config['frc_votes']

	# Get International Elections columns
	election_columns['International'] = config['international_offset']-1

	# Get Exec elections columns
	current_col = config['exec_offset']-1

	for exec_role in config['exec_elections']:
		election_columns[exec_role] = current_col
		current_col += 1

	return election_columns

def compile_validated_results(validated_file, config, output_directory):
	# Reads a validated results file and breaks up votes into each election for easy tallying.
	# Writes one set of votes for each election (ie. <output_dir>/humanities.csv)

	print()
	print("Compiling Election Results from {}".format(validated_file))
	print("Output Directory: {}".format(output_directory))
	debug("Config: {}".format(config))

	election_files = create_election_files(output_directory, config['frc_elections'], config['exec_elections'], ["International"])

	election_columns = build_election_columns(config)

	with open(validated_file, 'r') as validated_f:

		[next(validated_f) for i in range(VALIDATED_STUDENTS_NUM_HEADERS)]

		reader = csv.reader(validated_f)

		for row in reader:
			# print(row)
			user = row[election_columns['User']]  # Index-1 to convert to 0-indexing
			faculty = row[election_columns['Faculty']]
			# debug("International: {}".format(row[election_columns['International']-1]))

			if faculty in config['frc_elections']:
				# Find right file and write data to it
				for i in range(config['frc_votes']):
				
					vote = row[election_columns[faculty]+i]

					if vote == '':
						print("Warning: Empty FRC [{}] vote found: {}".format(faculty, user))
					else:
						debug("User: [{}][{}] Vote: [{}]".format(user, faculty, vote))
						election_files[faculty].write(",".join([user, vote])+os.linesep)

			# Compile International FRC Votes
			if row[election_columns['International']-1] == 'Yes':
				for i in range(config['frc_votes']):
					vote = row[election_columns['International']+i]
					if vote == '':
						print("Warning: Empty International Vote found [{}]".format(user))
					else:
						debug("User: [{}][International] Vote: [{}]".format(user, vote))
						election_files['International'].write(",".join([user, vote])+os.linesep)

			# Compile Executive Votes
			for i in range(config['exec_votes']):
				for exec_role in config['exec_elections']:
					vote = row[election_columns[exec_role]+i]

					if vote == '':
						print("Warning: Empty Exec vote [{}] found: {}".format(exec_role, user))
					else:
						debug("User: [{}][{}] Vote: [{}]".format(user, exec_role, vote))
						election_files[exec_role].write(",".join([user, vote])+os.linesep)					

	close_election_files(election_files)


if __name__ == '__main__':
	import argparse

	parser = create_parser()
	opts = parser.parse_args()

	# Read config file
	if opts.config is not None:
		try:
			config = read_config(opts.config)
		except FileNotFoundError:
			print("Error: Config File not found [{}]".format(opts.config))
			sys.exit(1)
		except yaml.scanner.ScannerError as exc:
			print("Error: Scanning Error while reading config file [{}]".format(str(exc)))
			sys.exit(1)

	# Check output directory
	if os.path.isdir(opts.directory):
		print("Warning: Output directory {} exists.  Compiled files will be overwritten.")
	else:
		os.makedirs(opts.directory)

	assert(os.path.exists(opts.directory))

	# Go
	compile_validated_results(opts.file, config, opts.directory)

	print()
	print("Done!")
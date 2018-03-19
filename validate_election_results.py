'''
Validate GSA Election Results from Google Forms with verified student lists provided by university
'''
import os
import sys
import csv
from datetime import datetime

DEFAULT_OUTPUT_DIR = "validation_results_{}".format(datetime.now().strftime('%Y%m%d'))

class InvalidCSVFileError(Exception):
	pass


class StudentListFormat(object):
	# Format specific data for the student list
	EMAIL_HEADER = 5             # The column number of the email value
	FACULTY_HEADER = 0           # The column number of the faculty value
	INTERNATIONAL_HEADER = 6     # The column number of the international value
	INTERNATIONAL_LABEL = 'Visa'  # The label for the international classifier


class ResultsListFormat(object):
	# Format specific data for the form entries 
	EMAIL_HEADER = 1             # The column number of the email value
	FACULTY_HEADER = -1          # The column number of the faculty value
	INTERNATIONAL_HEADER = 2    # The column number of the international value
	INTERNATIONAL_LABEL = 'Yes'  # The label for the international classifier


def create_parser():
	# Generate and return the command line parser
	parser = argparse.ArgumentParser("GSA Elections Validator")
	parser.add_argument('-r', '--results', help="Results CSV file from Google Forms")
	parser.add_argument('-s', '--students', help="Student List CSV file from SGS")
	parser.add_argument(
		'-d', '--destination', 
		default=DEFAULT_OUTPUT_DIR, 
		help="Destination folder to create for all output files.  Default: {}".format(DEFAULT_OUTPUT_DIR)
	)
	return parser

def validate_options(parser, opts):
	# Check argument parser options are valid
	try:
		check_valid_csv_file(opts.results)
	except InvalidCSVFileError as e:
		print("Argument Error: [Results] {}".format(str(e)))
		print()
		parser.print_help()
		sys.exit(1)
	try:
		check_valid_csv_file(opts.students)
	except InvalidCSVFileError as e:
		print("Argument Error: [Students] {}".format(str(e)))
		print()
		parser.print_help()
		sys.exit(1)

	create_destination_folder(opts.destination)

	print("Reading from Student List: {}".format(opts.students))
	print("Reading from Results List: {}".format(opts.results))

def create_destination_folder(dirname):
	# Create destination folder 
	if not os.path.isdir(dirname):
		try:
			os.makedirs(dirname)
		except OSError:
			print("Argumment Error: [Directory] Canot create destination folder: {}".format(dirname))
			sys.exit(1)
	else:
		print("Warning: [Directory] Destination Folder Exists: {}. Results will be overridden.".format(dirname))


def check_valid_csv_file(csv_file):
	# Check CSV File exists
	if csv_file is None:
		raise InvalidCSVFileError("No CSV File Found")

	if not os.path.exists(csv_file):
		raise InvalidCSVFileError("CSV File {} does not exist".format(csv_file))

def read_student_list(filename, comments=None, headers=None):
	# Read student list from a csv file
	#
	# Data saved in following format:
	# 	{
	#		<str> email: [<str> faculty, <bool> international] 
	#	}
	print("Reading Student List: {}".format(filename))
	students = {}
	
	with open(filename, 'r') as f:
		reader = csv.reader(f)

		# Headers 
		if comments is not None:
			try:
				[next(reader) for i in range(int(comments))]
			except ValueError:
				print("Warning: Problem reading header comments [{}] in student file {}".format(comments, filename))

		if headers is not None:
			headers = next(reader)
		
		for row in reader:
			try:
				email = row[StudentListFormat.EMAIL_HEADER].lower()
				faculty = row[StudentListFormat.FACULTY_HEADER].title()
				international = row[StudentListFormat.INTERNATIONAL_HEADER] == StudentListFormat.INTERNATIONAL_LABEL

			except IndexError:
				print("Error: Cannot parse row: {}".format(row))

			else:
				students[email] = [faculty, international]

		print("Read {} lines from student list".format(reader.line_num))

	return students

def results_datetime_str():
	# Format a nice datetime string for the results file
	return "Results From {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def write_results_header(filename, comment_str, header_str=None):
	# Overwrites a given file with initial comments and optional headers
	with open(filename, 'w', newline="") as f:
		f.write("# " + comment_str+os.linesep)
		f.write("# " + results_datetime_str()+os.linesep)
		if header_str is not None:
			f.write(str(header_str)+os.linesep)

def void_student(f, row, reason):
	# Void a student for a given reason, the reason is included in the voided results file
	print("VOIDING STUDENT: [{}] {}".format(reason, row[ResultsListFormat.EMAIL_HEADER]))
	f.write(",".join(row + [reason])+os.linesep)

def validate_student(f, row):
	# Validate a student, write their data to the validated results file
	f.write(",".join(row)+os.linesep)

def validate_results_list(students_list, results_list, destination_dir):
	# Read election results list from csv file
	print("Validating Election Results")

	# Read student list
	students = read_student_list(students_list)

	# Create and set up results files, voided and validated
	voided_file = os.path.join(destination_dir, 'voided_results.csv')
	validated_file = os.path.join(destination_dir, 'validated_results.csv')
	
	summary = {'entries': 0, 'validated': 0, 'voided': 0}  # Statistics counts

	# Read the results file and validate each row
	with open(results_list, 'r') as f:

		reader = csv.reader(f)

		# Get the header string and write them to the results files
		results_header = next(reader) 
		write_results_header(voided_file, 'VOIDED STUDENTS', header_str=",".join(results_header + ['Reason']))	
		write_results_header(validated_file, 'VALIDATED STUDENTS', header_str=",".join(results_header))

		void_f = open(voided_file, 'a', newline="")
		validate_f = open(validated_file, 'a', newline="")

		print("FacultyHeader: {}".format(ResultsListFormat.FACULTY_HEADER))
		print("InternationalHeader: {}".format(ResultsListFormat.INTERNATIONAL_HEADER))

		for row in reader:
			summary['entries'] += 1

			# Extract validation data from row.  
			# Warng about bad formatting in a single row, nope out for any other exception
			try:
				email = row[ResultsListFormat.EMAIL_HEADER].lower()

				if ResultsListFormat.FACULTY_HEADER > 0:
					faculty = row[ResultsListFormat.FACULTY_HEADER].title()
				else:
					faculty = None

				if ResultsListFormat.INTERNATIONAL_HEADER > 0:
					international = row[ResultsListFormat.INTERNATIONAL_HEADER] == ResultsListFormat.INTERNATIONAL_LABEL
				else:
					international = None

			except IndexError:
				print("Error: Bad formatting encountered while reading Results file: {}[{}]".format(results_list, reader.line_num))
				continue
			except Exception:
				print("Error: Unexpected Error encountered while processing row: [{}]{}".format(reader.line_num, row))
				print("Nopeing out...")
				break
				continue

			
			# Compare data against student list
			if email not in students:
				void_student(void_f, row, 'Not in Student List')
				summary['voided'] += 1
			elif faculty is not None:
				if students[email][0].lower() != faculty.lower():
					void_student(void_f, row, "Incorrect Faculty: Expected [{}] Got [{}] ".format(faculty, students[email][0]))
					summary['voided'] += 1

			elif students[email][1] != international:
				void_student(void_f, row, "Incorrect International Status: Expected [{}] Got [{}]".format(international, students[email][1]))
				summary['voided'] += 1
			else:
				validate_student(validate_f, row)
				summary['validated'] += 1

		void_f.close()
		validate_f.close()

	# Print summary
	print("Done!")
	print()
	print("Saved validated entries to: {}".format(validated_file))
	print("Saved voided entries to: {}".format(voided_file))
	print()
	print("Summary")
	print("Num Entries: {}".format(summary['entries']))
	print("Validated Entries: {}".format(summary['validated']))
	print("Voided Entries: {}".format(summary['voided']))


if __name__ == '__main__':
	import argparse
	parser = create_parser()    # Create command line argument parser
	opts = parser.parse_args()  # Parse the command line arguments
	validate_options(parser, opts)      # Check provided argument options are sane

	# Validate results with provided command line options
	validate_results_list(opts.students, opts.results, opts.destination)



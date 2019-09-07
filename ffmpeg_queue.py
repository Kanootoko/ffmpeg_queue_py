'''ffmpeg_queue is a console program which provides queue feature for ffmpeg. It can be used with other applications, if needed.
Version: 2.0.0 [2019.09.07]
Usage:
1. Console arguments.
	"--help" - print this help message and terminate program
	"--ffmpeg_path=<path/to/ffmpeg>" or "-ffpath <path/to/ffmpeg>" - set path to ffmpeg executable
	"--input_formats=<string>" or "-if <string>" or "-fin <string>" - set input format(s)
	    for input pattern. For multiple formats you should use commas. -if=mkv,avi,mp4
	"--output_format=<string>" or "-of <string>" or "-fout <string>" - set output format
	    for output pattern
	"--input_dir=<path/to/dir>" or "-id <path/to/dir>" or "-din <path/to/dir>" - set path to
	    directory with input files
	"--output_dir=<path/to/dir>" or "-od <path/to/dir>" or "-dout <path/to/dir>" - set path to
	    directory for output files (if it doesen't exists, but can be created, it will be)
	"--input_parameters=<string>" or "-ip <string>" - set string which will be put before input file path
	    (it should end with "-i" or else ffmpeg error will occur)
	"--output_parameters=<string>" or "-op <string>" - set string which will be put before output file path
	"--threads=<int>" or "-threads <int>" - change number of ffmpegs running at one time
	"--config_file=<path>" or "-cfg <path>" - load configuration from <path>. By default, script tries to
	    load config file "default.ini" in directory of launching. More information on config files in 2.
	"--shutdown" or "-s" - computer will be shut down after the script is finished
	"--hibernate" or "--hibernation" or "-h" - computer will be hibernated after the script is finished
	"--shutdown_time=<int>" or "-time <int>" - set time which passes from the end of the job to
	    shutdown/hibernation of the PC.
	"--no_user" or "-no_user" - no interface will be shown, only commands passed with command line or configuration file
2. Configuration ini file.
	  Configuration can be loaded at startup point, by passing console parameter "--config_file=<path>" or "-cfg <path>",
	or it can be loaded from user interface by command "load". You can save any configuration by command "save" at UI.
	Also, ini file is easily readable by any text-viewer, after save you can try to change by yourself.
	In some cases, not all of the parameters go to ini file - it happens when they are same to default.
3. Interface.
	  After running program, you get to console interface, where you can see list of commands and how your
	executing string looks like at the moment. You can skip interface step by console command ("--no_user")
	or with parameter in configuration file (no_user = true)
4. Some notes.
	  Script is developed and tested under Windows 10 platform with python 3.7.0.
	Script should work on Linux too, but there were too few tests. And some features which work on Windows are not ported.
	  Data which comes with console parameters practically never tested on correctness. Same with configuration files.
	In other words, you can easily get some exception or program would work incorrectly if you're not careful enough with those.'''
import sys
import os
import subprocess
import time

from enum import Enum, auto as enum_auto

class Shutdown:
	'''Shutdown is the class for easy choice between shutdown, hibernation and nothing.'''
	def __init__(self, type_ = '-', time = 30):
		from re import match, findall
		if isinstance(type_, list):
			type_ = ' '.join(type_)
		m = match('^([Hh](ibernation)?|[Ss](hutdown)?)[^\\d]*(\\d+)( seconds)?$', type_)
		if m is not None:
		    m = findall('(\\w)\\w*[^\\d]*(\\d+)', type_)[0]
		    type_ = m[0]
		    time = m[1]
		if type_ in ('hibernate', 'hibernation', '/h', 'h', 'H'):
			self._type = 'h'
		elif (type_ in ('shutdown', '/s', 's', 'S')):
			self._type = 's'
		else:
			self._type = '-'
		try:
			self._time = int(time)
		except ValueError:
			self._time = 30

	def __str__(self):
		if self._type == 's':
			return f'Shutdown in {self._time} seconds'
		elif self._type == 'h':
			return f'Hibernation in {self._time} seconds'
		else:
			return 'No shutdown is planned'
	def __repr__(self):
		return (self._type + ' ' + self.time) if self._type != '-' else self._type

	@property
	def type(self):
		return self._type

	@type.setter
	def type(self, new_type):
		if new_type in ('h', 'hibernate', 'hibernation', '/h'):
			self._type = 'h'
		elif (new_type in ('s', 'shutdown', '/s')):
			self._type = 's'
		else:
			self._type = '-'

	@property
	def time(self):
		return self._time

	@time.setter
	def time(self, new_time):
		try:
			self._time = int(new_time)
		except ValueError:
			return False

	def execute(self):
		'''Shutdown will be launched as "shutdown /s /t <time>" and can be cancelled as "shutdown /a".
		But hibernation cannot be run like this, to stop the process, the file ".stayon" must be created in directory of script.
		Or Crl+C can be hit as well.'''
		if self._type == '-' or os.path.isfile('.stayon'):
			return
		change_title(str(self))
		if self._type == 'h':
			subprocess.call(('msg', os.getlogin(), f'Computer will be hibernated in {self._time} seconds'))
			print(f'Hibernating in {self._time} seconds after {time.ctime()}')
			print('----- If you wish to stop the process, hit Ctrl + C on keyboard -----')
			try:
				time.sleep(self.time)
			except KeyboardInterrupt:
				print('Hibernation cancelled')
				return
			if os.path.isfile('.stayon'):
				return
			subprocess.call(('shutdown', '/h'))
		else:
			if os.path.isfile('.stayon'):
				return
			subprocess.call(('shutdown', '/s', '/t', str(self._time)))

class Properties:
	'''Properties is the class to hold all the main parameters for script to work.
	It is transferred to other functions and can changed until work is started.'''
	class Prop(Enum):
		'''Prop is the enumeration for parts in params_order variable of Properties.
		They are used in Prpos.props_names for naming.'''
		FFPATH          = enum_auto()
		INPUT_PARAMS    = enum_auto()
		OUTPUT_PARAMS   = enum_auto()
		INPUT_FILENAME  = enum_auto()
		OUTPUT_FILENAME = enum_auto()
		INPUT_DIR       = enum_auto()
		OUTPUT_DIR      = enum_auto()
		TIME            = enum_auto()
	props_names = {
		Prop.FFPATH          : '{ffmpeg_path}',
		Prop.INPUT_PARAMS    : '{input_params}',
		Prop.OUTPUT_PARAMS   : '{output_params}',
		Prop.INPUT_FILENAME  : '{input_filename}',
		Prop.OUTPUT_FILENAME : '{output_filename}',
		Prop.INPUT_DIR       : '{input_dir}',
		Prop.OUTPUT_DIR      : '{output_dir}',
		Prop.TIME            : '{time}'
	}
	def __init__(self):
		props_names = Properties.props_names
		Prop = Properties.Prop
		self.params_order = \
			f'{props_names[Prop.FFPATH]} {props_names[Prop.INPUT_PARAMS]} ' \
			f'"{props_names[Prop.INPUT_DIR]}{os.path.sep}{props_names[Prop.INPUT_FILENAME]}" ' \
			f'{props_names[Prop.OUTPUT_PARAMS]} ' \
			f'"{props_names[Prop.OUTPUT_DIR]}{os.path.sep}{props_names[Prop.OUTPUT_FILENAME]}"'
		self.ffmpeg_path = 'ffmpeg'
		self.input_params = '-i'
		self.output_params = '-c copy'
		self._input_formats = ['avi']
		self.output_format = 'mkv'
		self._input_dir = '.'
		self._output_dir = f'{props_names[Prop.INPUT_DIR]}{os.path.sep}Output {{time}}'
		self._threads = 1
		self._finish = Shutdown()
		self._no_user = False
		self._time = int(time.time())
	@property
	def input_formats(self):
		return self._input_formats
	@input_formats.setter
	def input_formats(self, new_input_formats):
		if isinstance(new_input_formats, str):
			from re import match
			if match('^\\[(.*)*\\]$', new_input_formats) is not None:
				self._input_formats = list(map(lambda x: x[1:-1] if x.startswith("'") and x.endswith("'") else x, new_input_formats[1:-1].split(', ')))
			else:
				self._input_formats = ' '.join(new_input_formats.split(',')).split()
		else:
			self._input_formats = new_input_formats
	@staticmethod # FIXME bug occures when non-static method
	def get_exec_str(self, params_order = None): 
		if params_order == None:
			params_order = self.params_order
		return params_order \
			.replace(Properties.props_names[Properties.Prop.FFPATH], self.ffmpeg_path) \
			.replace(Properties.props_names[Properties.Prop.INPUT_PARAMS], self.input_params) \
			.replace(Properties.props_names[Properties.Prop.INPUT_DIR], self.input_dir) \
			.replace(Properties.props_names[Properties.Prop.INPUT_FILENAME], \
				'<filename>.' + (str(self.input_formats) if len(self.input_formats) > 1 else self.input_formats[0])) \
			.replace(Properties.props_names[Properties.Prop.OUTPUT_PARAMS], self.output_params) \
			.replace(Properties.props_names[Properties.Prop.OUTPUT_DIR], self.output_dir) \
			.replace(Properties.props_names[Properties.Prop.OUTPUT_FILENAME], f'<filename>.{self.output_format}') \
			.replace(Properties.props_names[Properties.Prop.TIME], f'{self._time}')
	@staticmethod # FIXME bug occures when non-static method
	def get_exec_cmd(self, filename: str, params_order = None):
		#(props.ffmpeg_path, *split_quotes(props.input_params), props.input_dir + os.path.sep + fname,
		#	*split_quotes(props.output_params),
		#	props.output_dir + os.path.sep + fname[:fname.rfind('.') + 1] + props.output_format		
		if params_order == None:
			params_order = Properties.get_exec_cmd(self, filename, self.params_order)
		return params_order \
			.replace(Properties.props_names[Properties.Prop.FFPATH], self.ffmpeg_path) \
			.replace(Properties.props_names[Properties.Prop.INPUT_PARAMS], self.input_params) \
			.replace(Properties.props_names[Properties.Prop.INPUT_DIR], self.input_dir) \
			.replace(Properties.props_names[Properties.Prop.INPUT_FILENAME], filename) \
			.replace(Properties.props_names[Properties.Prop.OUTPUT_PARAMS], self.output_params) \
			.replace(Properties.props_names[Properties.Prop.OUTPUT_DIR], self.output_dir) \
			.replace(Properties.props_names[Properties.Prop.OUTPUT_FILENAME], filename[:filename.rfind('.') + 1] + self.output_format) \
			.replace(Properties.props_names[Properties.Prop.TIME], f'{self._time}')
	@property
	def threads(self):
		return self._threads
	@threads.setter
	def threads(self, new_threads):
		try:
			self._threads = int(new_threads)
		except:
			pass
	@property
	def no_user(self):
		return self._no_user
	@no_user.setter
	def no_user(self, new_no_user):
		if isinstance(new_no_user, str):
			self._no_user = True if new_no_user.lower() in ('true', 't', '1', True, 'yes', 'on') else False
		else:
			self._no_user = bool(new_no_user)
	@property
	def input_dir(self):
		return self._input_dir
	@input_dir.setter
	def input_dir(self, new_input_dir: str):
		self._input_dir = '.' if new_input_dir == '' else new_input_dir
	@property
	def output_dir(self):
		return self._output_dir
	@output_dir.setter
	def output_dir(self, new_output_dir: str):
		self._output_dir = \
			f'{Properties.props_names[Properties.Prop.INPUT_DIR]}{os.path.sep}Output {{time}}' \
			if new_output_dir == '' else new_output_dir

	@property
	def finish(self):
		return self._finish
	@finish.setter
	def finish(self, new_finish):
		if isinstance(new_finish, str):
			self._finish = Shutdown(new_finish.split())
		else:
			self._finish = new_finish

def pause():
	'''pause is the function for pausing: propgram will wait for user to press something.
	There should be commands both for Windows and Linux systems.'''
	if os.sys.platform == 'win32':
		subprocess.call('pause', shell=True)
	else: # other cases?
		input('Press enter to continue...')

def change_title(title: str):
	'''change_title is the function that changes current window title.
	It is used for one-threaded mode. Currently works only with Windows.'''
	if os.sys.platform == 'win32':
		subprocess.call(f'title {title}', shell=True)

def split_quotes(string: str):
	'''split_quotes is the function which splits input string like .split(), but quoted fragments
	are joined to one and quotes are deleted.
	Example: 'a b "c d e"' -> ['a', 'b', 'c d e']'''
	string = string.split()
	i = 0
	skip = False
	while i < len(string):
		if string[i].count('"') % 2 != 0 and not skip:
			if i + 1 < len(string):
				string[i] += ' ' + string[i + 1]
				del string[i + 1]
			else:
				skip = True
			continue
		else:
			#if string[i][0] == string[i][-1] == '"':
			#	string[i] = string[i][1:-1]
			string[i] = string[i].replace('"', '')
			i += 1
	return string
	
def save_properties(props: Properties, filename: str):
	'''save_properties is the function for saving configuration in file.
	Takes Properties class and filename to save it in ini-format.'''
	import configparser
	f = open(filename, 'w')
	props_default = Properties()
	saving = configparser.ConfigParser()
	saving.add_section('default')

	savedict = {}
	for key in set(filter(lambda x: not x.startswith('_'), dir(props))):
		if not callable(getattr(props, key)) and \
			str(getattr(props, key)) != str(getattr(props_default, key)):
			savedict[key] = str(getattr(props, key))
	if 'output_dir' in savedict and len(savedict['output_dir'].split()) == 2 and \
	   savedict['output_dir'].split()[0].endswith('Output') and savedict['output_dir'].split()[1].isalnum():
		del savedict['output_dir']
	if len(savedict) == 0:
		print('Output is empty, all the parameters are default', file=sys.stderr)
	saving['default'].update(savedict)
	saving.write(f)
	f.close()
	
def load_properties(props: Properties, filename: str):
	'''load_properties is the function for loading configuration file.
	It changes Properties class given in parameters and filename to load from.
	Can throw ValueError exception if file is not found or there is no [default] section.'''
	import configparser
	loading = configparser.ConfigParser()
	if not os.path.isfile(filename):
		raise ValueError(f'File \'{filename}\' is not found')
	loading.read(filename)
	default_props = Properties()
	if not 'default' in loading.sections():
		raise ValueError('no \'default\' section is found; load is aborted')
	loading = loading['default']
	params = set(filter(lambda x: not x.startswith('_'), dir(props)))
	for param in params:
		if param in loading:
			setattr(props, param, loading[param])
		else:
			setattr(props, param, getattr(default_props, param))

def recode_func(inp):
	'''recode_func is the function which is passed to multiprocessing.Pool and takes job number and job itself,
	and then launches job. Job is simply command, string parameter.'''
	number, job = inp
	print(f'{time.ctime()}: Job {number}: [[{job}]]')
	subprocess.getoutput(job)
	print(f'{time.ctime()}: Job {number} is finished')

def parse_arguments(argv: list, props: Properties):
	'''parse_arguments parses all the arguments and fills Properties from given parameters.'''
	class Variant(Enum):
		'''Variant is the enumeration for the type of previous argument of command-line.
		Some arguments need continuation, they are all enumerated. Others passes under NORMAL.'''
		FFPATH = enum_auto()  # ffmpeg_path
		IF = enum_auto()      # input_formats
		OF = enum_auto()      # output_formats
		ID = enum_auto()      # input_dir
		OD = enum_auto()      # output_dir
		IP = enum_auto()      # input_parameters
		OP = enum_auto()      # output_parameters
		THREADS = enum_auto() # threads
		TIME = enum_auto()    # shutdown_time
		CFG = enum_auto()     # config_file
		NORMAL = enum_auto()  # current argument is not a continue to the last one
	var_map = {
		'-ffpath'  : Variant.FFPATH,
		'-if'      : Variant.IF,
		'-of'      : Variant.OF,
		'-id'      : Variant.ID,
		'-din'     : Variant.ID,
		'-od'      : Variant.OD,
		'-dout'    : Variant.OD,
		'-ip'      : Variant.IP,
		'-op'      : Variant.OP,
		'-threads' : Variant.THREADS,
		'-time'    : Variant.TIME,
		'-cfg'     : Variant.CFG
	}
	last = Variant.NORMAL
	for arg in argv[1:]:
		if last == Variant.NORMAL:
			if arg in var_map:
				last = var_map.get(arg)
				continue
			if arg in ('help', '--help', '-h', '-help', '/h', '/?'):
				print(__doc__)
				return True
			elif arg.startswith('--ffmpeg_path='):
				props.ffmpeg_path = arg.split('=')[1]
			elif arg.startswith('--input_formats='):
				props.input_formats = ' '.join(arg.split('=')[1].split(',')).split()
			elif arg.startswith('--output_format='):
				props.output_format = arg.split('=')[1]
			elif arg.startswith('--input_dir='):
				props.input_dir = arg.split('=')[1]
			elif arg.startswith('--output_dir='):
				props.output_dir = arg.split('=')[1]
			elif arg.startswith('--input_parameters='):
				props.input_params = arg.split('=')[1]
			elif arg.startswith('--output_parameters='):
				props.output_params = arg.split('=')[1]
			elif arg.startswith('--threads='):
				try:
					props.threads = int(arg.split('=')[1])
				except ValueError:
					print(f'Warning: Error with threads parameter: \'{arg}\'')
			elif arg.startswith('--config_file='):
				try:
					load_properties(props, arg.split('=')[1])
				except Exception as exc:
					print(f'Warning: Error occured while loading: \'{exc}\'')
			elif arg in ('--shutdown', '-s'):
				props.finish.change_type('s')
			elif arg in ('--hybernation', '--hibernate', '-h'):
				props.finish.change_type('h')
			elif arg.startswith('--shutdown_time='):
				props.finish.time = arg.split('=')[1]
			elif arg in ('--no_user', '-no_user'):
				props.no_user = True
			else:
				print(f'Warning: Unknown console parameter: \'{arg}\'. Try \'{argv[0]} --help\'')
		elif last == Variant.FFPATH:
			props.ffmpeg_path = arg
		elif last == Variant.IF:
			props.input_formats = ' '.join(arg.split(',')).split()
		elif last == Variant.OF:
			props.output_format = arg
		elif last == Variant.ID:
			props.input_dir = arg
		elif last == Variant.OD:
			props.output_dir = arg
		elif last == Variant.IP:
			props.input_params = arg
		elif last == Variant.OP:
			props.output_params = arg
		elif last == Variant.THREADS:
			try:
				props.threads = int(arg)
			except ValueError:
				print(f'Warning: Error with threads parameter: \'{arg}\'')
		elif last == Variant.TIME:
			props.finish.time = arg
		elif last == Variant.CFG:
			try:
				load_properties(props, arg)
			except Exception as exc:
				print(f'Warning: Error occured while loading file \'{arg}\': \'{exc}\'')
		last = Variant.NORMAL
	if last != Variant.NORMAL:
		print(f'Warning: Input parameters list ends with unpaired pair-parameter: \'-{last.name.lower()}\'')
	return False

def edit_order_menu(props: Properties):
	'''edit_order_menu shows user interface for changing the execution string pattern.'''
	params_order = props.params_order
	while True:
		print()
		print('=' * (os.get_terminal_size().columns // 3))
		print('Now order of parameters is: ')
		print(params_order)
		print('Now execution string looks like this:')
		print(Properties.get_exec_str(props, params_order))
		print('These expressions are avaliable:')
		print(f'\t{Properties.props_names[Properties.Prop.FFPATH]} - path to ffmpeg')
		print(f'\t{Properties.props_names[Properties.Prop.INPUT_PARAMS]} - input parameters ffmpeg')
		print(f'\t{Properties.props_names[Properties.Prop.INPUT_DIR]} - path where input files are located')
		print(f'\t{Properties.props_names[Properties.Prop.INPUT_FILENAME]} - filename of file to be recoded')
		print(f'\t{Properties.props_names[Properties.Prop.OUTPUT_PARAMS]} - output parameters for ffmpeg')
		print(f'\t{Properties.props_names[Properties.Prop.OUTPUT_DIR]} - path for output files')
		print(f'\t{Properties.props_names[Properties.Prop.OUTPUT_FILENAME]} - filename of the output file')
		print(f'\t{Properties.props_names[Properties.Prop.TIME]} - current Epoch time')
		inp = input('\nEnter new pattern ("halt" / "cancel" to abort changes or "accept" to apply them):\n')
		if inp in ('halt', 'cancel', 'abort'):
			return
		elif inp in ('accept', 'apply'):
			props.params_order = params_order
			return
		params_order = inp
		for prop in Properties.props_names.values():
			if not prop in params_order:
				print(f'Warning: property "{prop}" is not used')

def main_menu(props: Properties):
	'''main_menu shows user interface where most of the parameters can be set.
	It returns True if user decided to exit the script, and False when user decided to start the script work'''
	while not props.no_user:
		print('-' * (os.get_terminal_size().columns // 2))
		print('Now order of parameters is:')
		print(props.params_order)
		print('Now execution string looks like this:')
		print(Properties.get_exec_str(props))
		cnt = len(tuple(filter(lambda filename: filename.endswith(tuple(props.input_formats)), os.listdir(props.input_dir))))
		print(f'{cnt} files found')

		print(props.finish) # fixme it's not needed here
		print('List of commands:')
		print('\t"ffpath" / "ffmpeg_path" - change path to ffmpeg executable file', f'[{props.ffmpeg_path}]')
		print('\t"if" / "input_formats" / "input_format" / "fin" - change input format(s)', props.input_formats)
		print('\t"of" / "output_format" / "fout" - change output format', f'[{props.output_format}]')
		print('\t"id" / "input_dir" / "din" - change input directory', f'[{props.input_dir}]')
		print('\t"od" / "output_dir" / "dout" - change output directory', f'[{props.output_dir}]')
		print('\t"ip" / "input_params" / "input_parameters" - change input parameters string', f'[{props.input_params}]')
		print('\t"op" / "output_params" / "output_parameters" - change output parameters string', f'[{props.output_params}]')
		print('\t"threads" - change number of ffmpegs running at one time', f'[{props.threads}]')
		print('\t"s_ty" / "shutdown_type" - chage type of action after finishing ("-" or "shutdown" / "s" or "hibernation" / "h")')
		print('\t"s_ti" / "shutdown_time" - change time between finishing and shutdown/hibernation') # TODO make one "finish" command ^
		print('\t"edit_order" / "order" - change the pattern of execution string')
		print('\t"save <filename>" - save current configuration to <filename> file"')
		print('\t"load <filename>" - load configuration from <filename> file"')
		print('\t"start" / "go" / <empty_string> - start the script')
		print('\t"exit" / "stop" / "quit" - exit the script')

		comm = input('>>> ')
		data = ''
		oneline = tuple(comm.split())
		if len(oneline) > 1:
			data = ' '.join(oneline[1:])
		del oneline
		if comm.startswith(('ffpath', 'ffmpeg_path')):
			while True:
				if data == '':
					data = input('Enter path to ffmpeg executable (or "halt" to cancel): ')
				if (data == 'halt'):
					print('Cancelled')
					break
				elif os.path.isfile(data) or True:
					props.ffmpeg_path = os.path.normpath(data)
					print(f'Accepted, ffmpeg_path changed to \'{props.ffmpeg_path}\'')
					break
				else:
					print(f'Error. Path is not correct \'{data}\'')
					data = ''
		elif comm.startswith(('if', 'inupt_format', 'input_formats', 'fin')):
			while True:
				if data == '':
					data = input('Enter format(s) for input (or "halt" to cancel): ')
				if (data == 'halt'):
					print('Cancelled.')
					break
				elif len(data) > 0:
					props.input_formats = data
					print(f'Accepted, input_formats list is changed to \'{props.input_formats}\'')
					break
				else:
					print('Error: empty string is not acceptable.')
					data = ''
		elif comm.startswith(('of', 'output_format', 'fout')):
			while True:
				if data == '':
					data = input('Enter format for output (or "halt" to cancel): ')
				if (data == 'halt'):
					print('Cancelled.')
					break
				elif len(data) > 0 and len(' '.join(data.split(',')).split()) == 1:
					props.output_format = ' '.join(data.split(',')).split()[0]
					print(f'Accepted, output_format is changed to \'{props.output_format}\'.')
					break
				else:
					print(f'Error. Empty strings or strings contining spaces or commas are not acceptable: \'{data}\'.')
					data = ''
		elif comm.startswith(('id', 'input_dir', 'din')):
			while True:
				if data == '':
					data = input('Enter path to input dirctory (or "halt" to cancel): ')
				if (data == 'halt'):
					print('Cancelled.')
					break
				elif os.path.isdir(data):
					props.input_dir = os.path.normpath(data)
					print(f'Accepted, input_dir path changed to \'{props.input_dir}\'.')
					break
				else:
					print(f'Error. Path is not correct: \'{data}\'.')
					data = ''
		elif comm.startswith(('od', 'output_dir', 'dout')):
			while True:
				if data == '':
					data = input('Enter path to input dirctory (or "halt" to cancel): ')
				if (data == 'halt'):
					print('Cancelled.')
					break
				#elif os.access((os.path.sep).join(os.path.split(os.path.abspath(data))[:-1]), os.W_OK):
				props.output_dir = os.path.normpath(data)
				print(f'Accepted, output_dir path changed to \'{props.output_dir}\'.')
				break
				#else:
				#	print(f'Error. Path is not correct: \'{data}\'.')
				#	data = ''
		elif comm.startswith(('ip', 'input_params', 'input_parameters')):
			if data == '':
				props.input_params = input('Enter a string for input parameters: ')
			else:
				props.input_params = data
			print(f'Accepted, new input parameters string is \'{props.input_params}\'.')
		elif comm.startswith(('op', 'output_params', 'output_parameters')):
			if data == '':
				props.output_params = input('Enter a string for output parameters: ')
			else:
				props.output_params = data
			print(f'Accepted, new output parameters string is \'{props.output_params}\'.')
		elif comm.startswith('threads'):
			while True:
				if data == '':
					data = input('Enter number of threads you need (or "halt" to cancel): ')
				if data == 'halt':
					print('Cancelled')
					break
				try:
					assert(int(data) > 0)
					props.threads = int(data)
					if props.threads > os.cpu_count():
						print(f'Warning: number of threads that you\'ve entered is larger than ' \
							f'your computer\'s number of cpus: {os.cpu_count()}, but {props.threads} threads.')
					print('Accepted')
					break
				except Exception:
					print(f'Error of decoding your "number": \'{data}\'. Try again.')
					data = ''
		elif comm in ('edit_order', 'order'):
			edit_order_menu(props)
		elif comm.startswith('save'):
			if data == '':
				data = input('Enter path to save current configuration: ')
			try:
				save_properties(props, data)
			except Exception as exc:
				print(f'Error occured while saving: \'{exc}\'')
			else:
				print('Save is completed successfully.')
		elif comm.startswith('load'):
			if data == '':
				data = input('Enter path to configuration file to load: ')
			try:
				load_properties(props, data)
			except Exception as exc:
				print(f'Error occured while loading: \'{exc}\'.')
			else:
			    print('Loaded successfully.')
		elif comm.startswith(('s_ty', 'shutdown_type')):
			if data == '':
				props.finish.type = input('Enter "shutdown" / "s" to shut PC down, "hibernate" / "h" to hibernate it, "-" to keep it on.')
			else:
				props.finish.type = data
		elif comm.startswith(('s_ti', 'shutdown_time')):
			if data == '':
				props.finish.time = input('Enter time before shutdown: ')
			else:
				props.finish.time = data
		elif comm == 'help':
			print(__doc__)
			pause()
		elif comm in ('', 'start', 'go'):
			print('Start working.')
			break	
		elif comm in ('exit', 'stop', 'quit'):
			print('Exiting now.')
			return True
		else:
			print(f'Error. unknown command: \'{comm}\'')
		print('\n')
	return False

def main(argv):
	props = Properties()
	try:
		load_properties(props, 'default.ini')
	except:
		pass

	# parsing arguments
	if parse_arguments(argv, props):
		return 0
	# console UI
	if main_menu(props):
		return 0
	# saving
	save_properties(props, 'lastconfig.ini')
	print('Current config has been written to "lastconfig.ini"')
	# working
	files = []
	for fname in os.listdir(props.input_dir):
		if fname.endswith(tuple(props.input_formats)):
			files.append(fname)
	props.output_dir = Properties.get_exec_cmd(props, '', props.output_dir)
	if len(files) > 0 and not os.path.exists(props.output_dir):
		os.mkdir(props.output_dir)
	files = tuple(files)
	if props.threads == 1 and len(files) > 0:
		for i, fname in enumerate(files):
			#command = (props.ffmpeg_path, *split_quotes(props.input_params), props.input_dir + os.path.sep + fname,
			#	*split_quotes(props.output_params),
			#	props.output_dir + os.path.sep + fname[:fname.rfind('.') + 1] + props.output_format
			#)
			command = split_quotes(Properties.get_exec_cmd(props, fname))
			print(' '.join(command))
			#print(props.ffmpeg_path, props.input_params, '"' + props.input_dir + os.path.sep + fname + '"',
			#	*split_quotes(props.output_params),
			#	'"' + props.output_dir + os.path.sep + fname[:fname.rfind('.') + 1] + props.output_format + '"')
			change_title(f'[{i} / {len(files)}] ({fname}), {props.finish}')
			subprocess.call(command)
	elif len(files) > 0:
		import multiprocessing
		if len(files) < props.threads:
			print(f'Setting number of threads from {props.threads} to {len(files)} as number of files to encode')
			props.threads = len(files)
		pool = multiprocessing.Pool(processes = props.threads)
		done = None
		if os.sys.platform == 'win32':
			done = pool.map_async( \
				recode_func, \
				((i, f'start "{fname}" /WAIT ' + \
					Properties.get_exec_cmd(props, fname))
					for i, fname in enumerate(files)
				)
			)
		else:
			done = pool.map_async( \
				recode_func, \
				((i, Properties.get_exec_cmd(props, fname) + ' &')
					for i, fname in enumerate(files)
				)
			)
		try:
			done.get()
		except KeyboardInterrupt:
			pool.terminate() # doesen't work
		#pool.join()
	if os.path.isdir(props.output_dir) and len(os.listdir(props.output_dir)) == 0:
		print('Output folder is empty, it will be deleted')
		os.rmdir(props.output_dir)
	props.finish.execute()
	if not props.no_user:
		pause()

if __name__ == '__main__':
	main(sys.argv)

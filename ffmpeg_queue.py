'''ffmpeg_queue is a console program which provides queue feature for ffmpeg with the same parameters.
It is designed to be flexible and can be used with other applications if needed.
Version: 3.0.0 [2022.07.03]
Usage:
1. Console parameters.
arguments:
    input_directory - path to directory with input files (defaults to the current direcory)
options:
    "--help" - print this help message and terminate program
    "--ffmpeg_path=<path/to/ffmpeg>" or "-ffpath <path/to/ffmpeg>" - set path to ffmpeg executable
    "--input_formats=<string>" or "-if <string>" or "-fin <string>" - set input format(s)
        for input pattern. For multiple values you should use commas. -if=mkv,avi,mp4
    "--output_format=<string>" or "-of <string>" or "-fout <string>" - set output format
        for output pattern
    "--output_dir=<path/to/dir>" or "-od <path/to/dir>" or "-dout <path/to/dir>" - set path to
        directory for output files (if it doesen't exists, but can be created, it will be)
    "--input_parameters=<string>" or "-ip <string>" - set string which will be put before input file path
        (it should end with "-i" or else ffmpeg error will occur)
    "--output_parameters=<string>" or "-op <string>" - set string which will be put before output file path
    "--threads=<int>" or "-threads <int>" - change number of ffmpegs running at one time
    "--config_file=<path>" or "-cfg <path>" - load configuration from <path>. By default, script tries to
        load config file "default.ini" in directory of launching. More information on config files in 2.
    "--after_finish=<string>" or "-f <string>" - set action to perform after finishing work
        (shutdown, hibernate or nothing (-)). Optionally continue with time passing after finish and before action.
        Example: "shutdown 10" - turn system down after 10 seconds.
    "--no_user" or "-no_user" - no interface will be shown, only commands passed with command line or configuration file
2. Configuration ini file.
      Configuration file can be loaded at startup, by passing console parameter "--config_file=<path>" or "-cfg <path>"
    (default value is default.ini, prioritized in input directory, next in executable directory),
    or it can be loaded from user interface by command "load". You can save any configuration by command "save" at UI.
    Also, ini file is easily readable by any text-viewer, after executing "save_all" connamd the file with all fields
    will be saved and you can try to change by yourself.
    "save" command saves only those parameters which are different from default values.
    "load" updates current config, while "load_all" replaces all current parameters with the ones given in
    config or defaults.
3. Interface.
      After running program, you get to console interface, where you can see list of commands and how your
    executing string looks like at the moment. You can skip interface step by console command ("--no_user")
    or with parameter in configuration file (no_user = true)
4. Some notes.
      Script is developed and tested under Manjaro 21.3.1 and Windows 10 platforms with python 3.10.5.
    git Script should work on Linux too, but there were too few tests. And some features which work on Windows are not ported.
      Data which comes with console parameters practically never tested on correctness. Same with configuration files.
    In other words, you can easily get some exception or program would work incorrectly if you're not careful enough with those.'''
import configparser
import os
import shutil
import subprocess
import sys
import time
from enum import Enum
from enum import auto as enum_auto
from typing import Any, Literal

import click


class Shutdown:
    '''Shutdown is the class for easy choice between shutdown, hibernation and nothing.'''
    def __init__(self, method: Literal['-', 's', 'h'] | str = '-', wait_time: int = 30):
        from re import findall, match
        if isinstance(method, list):
            method = ' '.join(method)
        m = match('^(/)?([Hh]|[Ss])[^\\d]*(\\d+)(\\s+s.*)?$', method)
        if m is not None:
            m = findall('(\\w)\\w*[^\\d]*(\\d+)', method)[0]
            method = m[0].lower() # type: ignore
            wait_time = m[1] # type: ignore
        if method.startswith(('hibernate', 'hibernation', '/h', 'h')):
            self.method = 'h'
        elif (method in ('shutdown', '/s', 's', 'S')):
            self.method = 's'
        else:
            self.method = '-'
        try:
            self.wait_time = int(wait_time)
        except ValueError:
            self.wait_time = 30

    def __str__(self) -> str:
        if self.method == 's':
            return f'Shutdown in {self.wait_time} seconds'
        elif self.method == 'h':
            return f'Hibernation in {self.wait_time} seconds'
        else:
            return 'No shutdown is planned'

    def __repr__(self):
        return f'{self.method} {self.wait_time}' if self.method != '-' else '-'

    def execute(self) -> None:
        '''Shutdown will be launched as "shutdown /s /t <time>" and can be cancelled as "shutdown /a".
        But hibernation cannot be run like this, to stop the process, the file ".stayon" must be created in directory of script.
        Or Crl+C can be hit as well.'''
        if self.method == '-' or os.path.isfile('.stayon'):
            os.remove('.stayon')
            return
        change_title(str(self))
        if self.method == 'h':
            if sys.platform == 'win32':
                subprocess.call(('msg', os.getlogin(), f'Computer will be hibernated in {self.time} seconds'))
            else:
                subprocess.call(('notify-send', f'Hibernation in {self.wait_time} seconds', f'System will be hibernated in {self.wait_time}'))
            print(f'Hibernating in {self.wait_time} seconds after {time.ctime()}')
            print('----- If you wish to cancel the process, hit Ctrl + C on keyboard -----')
            try:
                time.sleep(self.wait_time)
            except KeyboardInterrupt:
                print('Hibernation cancelled')
                return
            if os.path.isfile('.stayon'):
                print('Hibernation cancelled')
                os.remove('.stayon')
                return
            if sys.platform == 'win32':
                subprocess.call(('shutdown', '/h'))
            else:
                subprocess.call(('systemctl', 'hibernate'))
        else:
            if os.path.isfile('.stayon'):
                return
            if sys.platform == 'win32':
                subprocess.call(('shutdown', '/s', '/t', str(self.wait_time)))
            else:
                subprocess.call(('shutdown', str(self.wait_time)))

class Properties:
    '''Properties is the class to hold all the main parameters for script to work.
    It is transferred to other functions and can be changed until work is started.'''
    class Prop(Enum):
        '''Prop is the enumeration for parts in base_execution_string variable of Properties.
        They are used in Prpos.props_names for naming.'''
        FFPATH          = enum_auto()
        INPUT_PARAMS    = enum_auto()
        OUTPUT_PARAMS   = enum_auto()
        INPUT_FILENAME  = enum_auto()
        OUTPUT_FILENAME = enum_auto()
        INPUT_DIR       = enum_auto()
        OUTPUT_DIR      = enum_auto()
        TIME            = enum_auto()
        NO_SAVE_CONFIG  = enum_auto()

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

    variable_names: list[str] = ['ffmpeg_path', 'input_params', 'output_params', 'input_formats',
            'output_format', 'input_dir', 'output_dir', 'threads', 'after_finish', 'no_save_config', 'no_user']

    def __init__(self, base_execution_string: str = f'{props_names[Prop.FFPATH]} {props_names[Prop.INPUT_PARAMS]} ' \
                    f'"{props_names[Prop.INPUT_DIR]}{os.path.sep}{props_names[Prop.INPUT_FILENAME]}" ' \
                    f'{props_names[Prop.OUTPUT_PARAMS]} ' \
                    f'"{props_names[Prop.OUTPUT_DIR]}{os.path.sep}{props_names[Prop.OUTPUT_FILENAME]}"',
            ffmpeg_path: str = 'ffmpeg', input_params: str = '-i', output_params: str = '-c copy',
            input_formats: list[str] = ['avi'], output_format: str = 'mkv',
            input_dir: str = '.', output_dir: str | None = None, threads: int = 1, after_finish: Shutdown = Shutdown(),
            no_save_config: bool = False, no_user: bool = False, output_commands: bool = False):
        props_names = Properties.props_names
        Prop = Properties.Prop
        self.base_execution_string = base_execution_string
        self.ffmpeg_path = ffmpeg_path
        self.input_params = input_params
        self.output_params = output_params
        self.input_formats = input_formats
        self.output_format = output_format
        self.input_dir = input_dir
        if output_dir is None:
            output_dir = os.path.join(f'{props_names[Prop.INPUT_DIR]}', 'Output {time}')
        self.output_dir = output_dir
        self.threads = threads
        self.after_finish = after_finish
        self.no_save_config = no_save_config
        self.no_user = no_user
        self.output_commands = output_commands
        self.time = int(time.time())

    def get_exec_cmd(self, filename: str | None = None, base_execution_string: str | None = None) -> str:
        if filename is None:
            filename = f'<filename>.{str(self.input_formats) if len(self.input_formats) > 1 else self.input_formats[0]}'
        if base_execution_string is None:
            base_execution_string = Properties.get_exec_cmd(self, filename, self.base_execution_string)
        return base_execution_string \
            .replace(Properties.props_names[Properties.Prop.FFPATH], self.ffmpeg_path) \
            .replace(Properties.props_names[Properties.Prop.INPUT_PARAMS], self.input_params) \
            .replace(Properties.props_names[Properties.Prop.INPUT_DIR], self.input_dir) \
            .replace(Properties.props_names[Properties.Prop.INPUT_FILENAME], filename) \
            .replace(Properties.props_names[Properties.Prop.OUTPUT_PARAMS], self.output_params) \
            .replace(Properties.props_names[Properties.Prop.OUTPUT_DIR], self.output_dir) \
            .replace(Properties.props_names[Properties.Prop.OUTPUT_FILENAME],
                    filename[:filename.rfind('.') + 1] + self.output_format if not filename.startswith('<filename>') \
                            else f'<filename>.{self.output_format}') \
            .replace(Properties.props_names[Properties.Prop.TIME], f'{self.time}')

    def set_input_formats(self, new_input_formats: str | list[str]) -> None:
        if isinstance(new_input_formats, str):
            new_input_formats = new_input_formats.strip().strip('[]')
            self.input_formats = [x.strip().strip('\'"') for x in new_input_formats.split(', ')]
        else:
            self.input_formats = new_input_formats

    def set_no_user(self, new_no_user: bool | str) -> None:
        '''set_no_user is a setter method for no_user'''
        if isinstance(new_no_user, str):
            self.no_user = True if new_no_user.lower() in ('true', 't', '1', 'yes', 'on') else False
        else:
            self.no_user = bool(new_no_user)

    def set_output_dir(self, new_output_dir: str) -> None:
        '''set_output_dir is a setter method for output_dir'''
        self.output_dir = \
            os.path.join(f'{Properties.props_names[Properties.Prop.INPUT_DIR]}', 'Output {time}') \
                    if new_output_dir == '' else new_output_dir

    def set_finish(self, new_finish: Shutdown | str) -> None:
        '''set_finish is a setter method for finish'''
        if isinstance(new_finish, str):
            self.after_finish = Shutdown(new_finish)
        else:
            self.after_finish = new_finish

    def save(self, filename: str, save_defaults: bool = False) -> None:
        '''save is a method for saving configuration in file.
        Takes filename to save it in ini-format, if `save_deufaults` is set to True,
        writes values even if they have default state - otherwise skips them.'''
        saving = configparser.ConfigParser()
        saving.add_section('default')

        savedict: dict[str, Any] = {}
        for key in Properties.variable_names:
            if save_defaults or str(getattr(self, key)) != str(getattr(properties_default, key)):
                savedict[key] = str(getattr(self, key))
        if len(savedict) == 0:
            print('Output is empty, all the parameters are default', file=sys.stderr)
        saving['default'].update(savedict)
        with open(filename, 'w', encoding='utf-8') as f:
            saving.write(f)
        
    def load(self, filename: str, restore_defaults_if_missing: bool = False):
        '''load is a method for loading properties from configuration file.
        It updates current properties if `restore_defaults_if_missing` is set to False (default)
        and replaces every value to default and then do update otherwise.
        Can throw ValueError exception if file is not found or there is no [default] section.'''
        if restore_defaults_if_missing:
            for key in Properties.variable_names:
                setattr(self, key, getattr(properties_default, key))

        loading = configparser.ConfigParser()
        if not os.path.isfile(filename):
            raise ValueError(f'File "{filename}" is not found')
        loading.read(filename)
        if not 'default' in loading.sections():
            raise ValueError('no "default" section is found; load is aborted')
        section = loading['default']
        for key in Properties.variable_names:
            if key in section:
                if key == 'no_user':
                    self.set_no_user(section[key])
                elif key == 'finish':
                    self.set_finish(section[key])
                elif key == 'output_dir':
                    self.set_output_dir(section[key])
                elif key == 'input_formats':
                    self.set_input_formats(section[key])
                else:
                    setattr(self, key, section[key])

    def update(self, other: 'Properties', update_only_defaults: bool = False, no_update_to_defaults: bool = True) -> None:
        '''update is a method for updating current Properties with the values of other Properties.
        If `update_only_defaults` is set to True, then only default values in `self` will be updated.
        If `no_update_to_defaults` is set, no fields which are default in other Properties will not be updated.'''
        for key in Properties.variable_names:
            if (not update_only_defaults or getattr(self, key) == getattr(properties_default, key)) \
                and (not no_update_to_defaults or getattr(other, key) != getattr(properties_default, key)):
                setattr(self, key, getattr(other, key))

properties_default = Properties()

def pause() -> None:
    '''pause is a function for pausing: propgram will wait for user to press something.
    There should be commands both for Windows and Linux systems.'''
    if sys.platform == 'win32':
        subprocess.call('pause', shell=True)
    else: # other cases?
        input('Press enter to continue...')

def change_title(title: str) -> None:
    '''change_title is a function that changes current window title.
    It is used for one-threaded mode. Currently works only with Windows.'''
    if sys.platform == 'win32':
        subprocess.call(f'title {title}', shell=True)

def str_change_title(title: str) -> str:
    '''str_change_title is a function that returns a title changing command.
    It is used for one-threaded mode. Currently works only with Windows.'''
    if sys.platform == 'win32':
        return f'title {title}'

def split_quotes(string: str) -> list[str]:
    '''split_quotes is a function which splits input string like .split(), but quoted fragments
    are joined to one and quotes are deleted.
    Example: 'a b "c d e"' -> ['a', 'b', 'c d e']'''
    parts = string.split()
    i = 0
    skip = False
    while i < len(parts):
        if parts[i].count('"') % 2 != 0 and not skip:
            if i + 1 < len(parts):
                parts[i] += ' ' + parts[i + 1]
                del parts[i + 1]
            else:
                skip = True
            continue
        else:
            parts[i] = parts[i].replace('"', '')
            i += 1
    return parts
    
def recode_func(number: int, job: str) -> str:
    '''recode_func is a function which is passed to multiprocessing.Pool and takes job number and job itself,
    and then launches job. Job is simply command, string parameter.'''
    print(f'{time.ctime()}: Job {number}: [[{job}]]')
    res = subprocess.getoutput(job)
    print(f'{time.ctime()}: Job {number} is finished')
    return res

def edit_order_menu(props: Properties) -> None:
    '''edit_order_menu shows user interface for changing the execution string pattern.'''
    base_execution_string = props.base_execution_string
    while True:
        print('',
                '=' * (os.get_terminal_size().columns // 3),
                'Now order of parameters is: ',
                base_execution_string,
                'Now execution string looks like this:',
                props.get_exec_cmd(base_execution_string=base_execution_string),
                'These expressions are avaliable:',
                f'\t{Properties.props_names[Properties.Prop.FFPATH]} - path to ffmpeg',
                f'\t{Properties.props_names[Properties.Prop.INPUT_PARAMS]} - input parameters ffmpeg',
                f'\t{Properties.props_names[Properties.Prop.INPUT_DIR]} - path where input files are located',
                f'\t{Properties.props_names[Properties.Prop.INPUT_FILENAME]} - filename of file to be recoded',
                f'\t{Properties.props_names[Properties.Prop.OUTPUT_PARAMS]} - output parameters for ffmpeg',
                f'\t{Properties.props_names[Properties.Prop.OUTPUT_DIR]} - path for output files',
                f'\t{Properties.props_names[Properties.Prop.OUTPUT_FILENAME]} - filename of the output file',
                f'\t{Properties.props_names[Properties.Prop.TIME]} - current Epoch time',
                sep='\n'
        )
        inp = input('\nEnter new pattern ("halt" / "cancel" to abort changes or "accept" to apply them):\n')
        if inp in ('halt', 'cancel', 'abort'):
            return
        elif inp in ('accept', 'apply'):
            props.base_execution_string = base_execution_string
            return
        base_execution_string = inp
        for prop in Properties.props_names.values():
            if not prop in base_execution_string:
                print(f'Warning: property "{prop}" is not used')

def main_menu(props: Properties) -> None:
    '''main_menu shows user interface where most of the parameters can be set.
    It returns True if user decided to exit the script, and False when user decided to start the script work'''
    while not props.no_user:
        cnt = len(tuple(filter(lambda filename: filename.endswith(tuple(props.input_formats)), os.listdir(props.input_dir))))
        print('-' * (os.get_terminal_size().columns // 2),
                'Current base execution string:',
                props.base_execution_string,
                'After filling the templates execution string will look like this:',
                props.get_exec_cmd(),
                f'{cnt} files found',
                'List of commands:',
                f'\t"ffpath" / "ffmpeg_path" - change path to ffmpeg executable file [{props.ffmpeg_path}]',
                f'\t"if" / "input_formats" / "input_format" / "fin" - change input format(s) [{", ".join(props.input_formats)}]',
                f'\t"of" / "output_format" / "fout" - change output format [{props.output_format}]',
                f'\t"id" / "input_dir" / "din" - change input directory [{props.input_dir}]',
                f'\t"od" / "output_dir" / "dout" - change output directory [{props.output_dir}]',
                f'\t"ip" / "input_params" / "input_parameters" - change input parameters string [{props.input_params}]',
                f'\t"op" / "output_params" / "output_parameters" - change output parameters string [{props.output_params}]',
                f'\t"threads" - change number of ffmpegs running at one time [{props.threads}]',
                '\t"af" / "after_finish" - chage type of action after finishing ("-" or "shutdown" / "s" or "hibernation" / "h")'
                    f'\n\t\twith optional wait time in seconds [{props.after_finish}]',
                f'\t"output_commands" - toggle output commands mode instead of launching them [{"on" if props.output_commands else "off"}]',
                '\t"edit_order" / "order" - change the pattern of execution string',
                '\t"save <filename>" / "save_all <filename>" - save current configuration to <filename> file"',
                '\t"load <filename>" / "load_all <filename>" - load configuration from <filename> file"',
                '\t"start" / "go" / <empty_string> - start the script',
                '\t"exit" / "stop" / "quit" / "q" - exit the script',
                sep='\n'
        )

        full_command = input('>>> ')
        line = full_command.split()
        comm = line[0]
        data = ' '.join(line[1:]) if len(line) > 0 else ''
        del line
        if comm in ('ffpath', 'ffmpeg_path'):
            while True:
                if data == '':
                    data = input('Enter path to ffmpeg executable (or "halt" to cancel): ')
                if (data == 'halt'):
                    print('Cancelled')
                    break
                else:
                    props.ffmpeg_path = os.path.normpath(data)
                    if shutil.which(data) is not None:
                        print(f'Accepted, ffmpeg_path changed to "{props.ffmpeg_path}"')
                    else:
                        print(f'Path may be incorrect "{data}".')
                    break
        elif comm in ('if', 'inupt_format', 'input_formats', 'fin'):
            while True:
                if data == '':
                    data = input('Enter format(s) for input (or "halt" to cancel): ')
                if (data == 'halt'):
                    print('Cancelled.')
                    break
                elif len(data) > 0:
                    props.set_input_formats(data)
                    print(f'Accepted, input_formats list is changed to "{props.input_formats}"')
                    break
                else:
                    print('Error: empty string is not acceptable.')
                    data = ''
        elif comm in ('of', 'output_format', 'fout'):
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
                    print(f'Error. Empty strings or strings contining spaces or commas are not acceptable: "{data}".')
                    data = ''
        elif comm in ('id', 'input_dir', 'din'):
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
                    print(f'Error. Path is not correct: "{data}".')
                    data = ''
        elif comm in ('od', 'output_dir', 'dout'):
            while True:
                if data == '':
                    data = input('Enter path to input dirctory (or "halt" to cancel): ')
                if (data == 'halt'):
                    print('Cancelled.')
                    break
                props.output_dir = os.path.normpath(data)
                print(f'Accepted, output_dir path changed to "{props.output_dir}".')
                break
        elif comm in ('ip', 'input_params', 'input_parameters'):
            if data == '':
                props.input_params = input('Enter a string for input parameters: ')
            else:
                props.input_params = data
            print(f'Accepted, new input parameters string is "{props.input_params}".')
        elif comm in ('op', 'output_params', 'output_parameters'):
            if data == '':
                props.output_params = input('Enter a string for output parameters: ')
            else:
                props.output_params = data
            print(f'Accepted, new output parameters string is "{props.output_params}".')
        elif comm == 'threads':
            while True:
                if data == '':
                    data = input('Enter number of threads you need (or "halt" to cancel): ')
                if data == 'halt':
                    print('Cancelled')
                    break
                try:
                    assert(int(data) > 0)
                    props.threads = int(data)
                    if props.threads > (os.cpu_count() or 1):
                        print(f'Warning: number of threads that you\'ve entered is larger than ' \
                            f'your computer\'s number of cpus: {os.cpu_count() or 1}, but {props.threads} threads.')
                    print('Accepted')
                    break
                except Exception:
                    print(f'Error of decoding your "number": "{data}". Try again.')
                    data = ''
        elif comm in ('edit_order', 'order'):
            edit_order_menu(props)
        elif comm == 'output_commands':
            props.output_commands = not props.output_commands
            print('Toggled output_commands parameter')
        elif comm in ('save', 'save_all', 'saveall'):
            if data == '':
                data = input('Enter path to save current configuration: ')
            try:
                props.save(data, 'all' in comm)
            except Exception as exc:
                print(f'Error occured while saving: "{exc}".')
            else:
                print('Save is completed successfully.')
        elif comm in ('load', 'load_all', 'loadall'):
            if data == '':
                data = input('Enter path to configuration file to load: ')
            try:
                props.load(data, 'all' in comm)
            except Exception as exc:
                print(f'Error occured while loading: "{exc}".')
            else:
                print('Loaded successfully.')
        elif comm in ('af', 'after_finish '):
            if data == '':
                props.after_finish = Shutdown(input(
                        'Enter "shutdown" / "s" to shut PC down, "hibernate" / "h" to hibernate it, "-" to keep it on.'
                        ' Optionally, proceed with waiting time in seconds before action would happen (default value is 30)'))
            else:
                props.after_finish = Shutdown(data)
        elif comm == 'help':
            print(__doc__)
            pause()
        elif comm in ('', 'start', 'go'):
            print('Start working.')
            break
        elif comm in ('exit', 'stop', 'quit', 'q', '\\q'):
            print('Exiting now.')
        else:
            print(f'Error. unknown command: "{full_command}"')
        print('\n')

def parse_formats(formats_str: str) -> list[str]:
    return list(map(str.strip, formats_str.split(',')))

@click.command('ffmpeg_queue')
@click.option('-ffpath', '--ffmpeg_path', envvar='FFMPEG_PATH', type=str, default=properties_default.ffmpeg_path,
        show_default=True, show_envvar=True, help='Path to ffmpeg executable')
@click.option('-if', '--input_formats', type=parse_formats, default=','.join(properties_default.input_formats),
        show_default=True, help='Input formats list separated by comma')
@click.option('-of', '--output_format', type=str, default=properties_default.output_format, show_default=True,
        help='Output format')
@click.option('-od', '-dout', '--output_directory', type=str, default=None, show_default='Output {current_time_epoch}',
        help='Name of the output directory. Will be created if does not exists')
@click.option('-ip', '--input_parameters', type=str, default=properties_default.input_params, show_default=True,
        help='ffmpeg input file parameters')
@click.option('-op', '--output_parameters', type=str, default=properties_default.output_params, show_default=True,
        help='ffmpeg output file parameters')
@click.option('-t', '--threads', type=int, default=properties_default.threads, show_default=True,
        help='Number of parllel jobs (useful for codecs which cannot consume all cpu resources)')
@click.option('-af', '--after_finish', type=Shutdown, default=str(properties_default.after_finish),
        show_default='No shutdown / hibernation [-]',
        help='Action to perform after the recoding is complete (shutdown or hibernate) and optional timeout. Example: "shutdown 30"')
@click.option('-nu', '--no_user', is_flag=True, help='Wait for no actions from user')
@click.option('-nc', '--no_save_config', is_flag=True, help='Skip saving lastconfig.ini')
@click.option('-c', '--output_commands', is_flag=True, help='Output encoding commands instead of launching them')
@click.option('-cfg', '--config_file', type=click.Path(True, True, readable=True), default=None, show_default='default.ini',
        help='Path to ini file to load configuration from (loads firstly, then updates with CLI parameters)')
@click.option('-bes', '--base_execution_string', type=str, default=properties_default.base_execution_string,
        show_default=True, help='Base execution command string template')
@click.argument('input_directory', type=click.Path(True, dir_okay=True), default=properties_default.input_dir)
def prepare_params(ffmpeg_path: str, input_formats: list[str], output_format: str, input_directory: str, output_directory: str | None,
        input_parameters: str, output_parameters: str, threads: int, after_finish: Shutdown, no_user: bool, no_save_config: bool,
        output_commands: bool, config_file: str | None, base_execution_string) -> Properties:
    '''Launches commands generated by filling the template of `base_execution_string` with other values to the files with
    the given list of formats in the input directory'''
    if config_file is None:
        if 'default.ini' in os.listdir():
            config_file = 'default.ini'
        if 'default.ini' in os.listdir(input_directory):
            config_file = os.path.join(input_directory, 'default.ini')
    elif config_file in ('', '-'):
        config_file = None
    
    props = Properties()
    if config_file is not None:
        try:
            props.load(config_file)
        except Exception as ex:
            print(f'Exception occured while reading config: {ex}\n{ex!r}\nExiting')
            exit(1)
    props.update(Properties(base_execution_string, ffmpeg_path, input_parameters, output_parameters,
            input_formats, output_format, input_directory, output_directory, threads, after_finish, no_save_config, no_user, output_commands))

    if not os.path.isdir(props.input_directory):
        if no_user:
            print(f'Error: input_directory ("{input_directory}") is not a folder, exiting')
            exit(1)
        else:
            print(f'Error: input directory ("{input_directory}") is not a folder.')

    if shutil.which(props.ffmpeg_path) is None:
        print(f'Warning: current ffmpeg path may be invalid: "{props.ffmpeg_path}"')

    if not props.no_user:
        # console UI
        main_menu(props)
            
    return props

def prepare_commands(props: Properties) -> list[str]:
    if not props.no_save_config:
        props.save('lastconfig.ini')
        print('Current config has been written to "lastconfig.ini"')

    # working
    files = [fname for fname in sorted(os.listdir(props.input_dir)) if fname.endswith(tuple(props.input_formats))]
    props.output_dir = props.get_exec_cmd('', props.output_dir)

    if len(files) == 0:
        print('No files to recode found, exiting')
        if not props.no_user:
            pause()
        exit()
    return [props.get_exec_cmd(fname) for fname in files]

def execute_commands(commands: list[str], props: Properties) -> None:
    if not os.path.exists(props.output_dir):
        os.mkdir(props.output_dir)
    if props.threads == 1:
        for i, command in enumerate(commands, 1):
            print(f'Executing {command}')
            command_splitted = split_quotes(command)
            change_title(f'[{i} / {len(commands)}] ({command}), {props.after_finish}')
            if subprocess.call(command_splitted) != 0 and not props.no_user:
                print('Seems that some error has happened. Waiting 10 seconds')
                time.sleep(10)
    else:
        import multiprocessing
        if len(commands) < props.threads:
            print(f'Setting number of threads from {props.threads} to {len(commands)} as number of files to recode')
            props.threads = len(commands)
        pool = multiprocessing.Pool(props.threads)
        pool.starmap( \
            recode_func, \
            ((i, (f'start "{i} / {len(commands)} ({command})" /WAIT {command}' \
                    if sys.platform == 'win32' else f'{command} &'))
                for i, command in enumerate(commands, 1)
            )
        )
        pool.close()
        try:
            pool.join()
        except KeyboardInterrupt:
            pool.terminate()

    if os.path.isdir(props.output_dir) and len(os.listdir(props.output_dir)) == 0:
        print('Output folder is empty, it will be deleted')
        os.rmdir(props.output_dir)
    props.after_finish.execute()
    if not props.no_user:
        pause()

def output_commands(commands: list[str], props: Properties) -> None:
    if not os.path.exists(props.output_dir):
        print ('mkdir "{props.output_dir}"')
    for i, command in enumerate(commands, 1):
        print(str_change_title(f'[{i} / {len(commands)}] ({command}), {props.after_finish}'))
        print(command)

if __name__ == '__main__':
    if os.path.isfile('.env'):
        with open('.env', 'r') as f:
            for name, value in (tuple((line[len('export '):] if line.startswith('export ') else line).strip().split('=')) \
                        for line in f.readlines() if not line.startswith('#') and line != ''):
                if name not in os.environ:
                    print(f'Getting "{name}"={value} from .env file')
                    os.environ[name] = value

    props = prepare_params()
    commands = prepare_commands(props)
    if not props.output_commands:
        execute_commands(commands, props)
    else:
        output_commands(commands, props)


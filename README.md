h1 ffmpeg_queue  
It's the script which helps you launch ffmpeg on list of files, given the same parameters. It's useful when you have many episodes of series downloaded for example, and you want to recode them all with the same parameters to reduce size or some other reason.  
h3 Usage:  

1. Console arguments.  
    * `--help` - print help message and terminate program  
    * `--ffmpeg_path=<path/to/ffmpeg>` or `-ffpath <path/to/ffmpeg>` - set path to ffmpeg executable  
    * `--input_formats=<string>` or `-if <string>` or `-fin <string>` - set input format(s) for input pattern. For multiple formats you should use commas. `-if=mkv,avi,mp4`  
    * `--output_format=<string>` or `-of <string>` or `-fout <string>` - set output format for output pattern  
    * `--input_dir=<path/to/dir>` or `-id <path/to/dir>` or `-din <path/to/dir>` - set path to directory with input files  
    * `--output_dir=<path/to/dir>` or `-od <path/to/dir>` or `-dout <path/to/dir>` - set path to directory for output files (if it doesen't exists, but can be created, it will be)  
    * `--input_parameters=<string>` or `-ip <string>` - set string which will be put before input file path  (it should end with `-i` or else ffmpeg error will occur)  
    * `--output_parameters=<string>` or `-op <string>` - set string which will be put before output file path  
    * `--threads=<int>` or `-threads <int>` - change number of ffmpegs running at one time  
    * `--config_file=<path>` or `-cfg <path>` - load configuration from `<path>`. By default, script tries to  load config file "default.ini" in directory of launching. More information on config files in 2.  
    * `--shutdown` or `-s` - computer will be shut down after the script is finished  
    * `--hibernate` or `--hibernation` or `-h` - computer will be hibernated after the script is finished  
    * `--shutdown_time=<int>` or `-time <int>` - set time which passes from the end of the job to  shutdown/hibernation of the PC.  
    * `--no_user` or `-no_user` - no interface will be shown, only commands passed with command line or configuration file  
2. Configuration ini file.  
    Configuration can be loaded at startup point, by passing console parameter `config_file=<path>` or `-cfg <path>`, or it can be loaded from user interface by command `load`. You can save any configuration by command `save` at UI.  
    Also, ini file is easily readable by any text-viewer, after save you can try to change by yourself.  
    In some cases, not all of the parameters go to ini file - it happens when they are same to default.  
3. Interface.  
    After running program, you get to console interface, where you can see list of commands and how your executing string looks like at the moment. You can skip interface step by console command (`--no_user`) or with parameter in configuration file (no_user = true)  
4. Some notes.  
    Script is developed and tested (a little bit) under Windows 10 platform with python 3.7.0.  
    Script should work on Linux too, but there were too few tests. And some features which work on Windows are not ported.  
    Data which comes with console parameters practically never tested on correctness. Same with configuration files. In other words, you can easily get some exception or program would work incorrectly if you're not careful enough with those.

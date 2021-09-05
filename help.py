from pathlib import Path
from typing import List, Tuple
import subprocess
import sys
import re
from shutil import get_terminal_size


settings = {
    'compilers': {
        '.cpp': 'g++',
        '.c++': 'g++',
        '.c': 'gcc'
    },
    'compiler_args': {
        'g++': [
            '-Wall',
            '-pedantic',
            '-std=c++11',
            '-Ofast'
        ]
    },
    'linker_args': [
        '-lm',
        '-lncurses'
    ],
    'excludes': [
        'oldCode/',
        'colors.cpp',
        'test_graphics.cpp'
    ],
    'verbose': False
}


def get_all_with_ending(ending: str, root: Path, exclude: List[str] = []) -> List[Path]:
    
    all_files = filter(lambda x: not any(x.match(glob) for glob in exclude), root.rglob('*.' + ending))

    # def recurse(path: Path):
    #     ls = []
    #     for p in path.iterdir():
    #         if p.is_dir():
    #             ls += recurse(p)
    #         elif p.suffix == '.' + ending:
    #             ls.append(p)
    #     return ls
    # return recurse(root)
    return list(all_files)


def print_if_something(s: str, always: bool = False):
    s = s.strip()
    if s:
        if always:
            print(s)
        else:
            print_if_verbose(s)


def print_if_verbose(*args, **kwargs):
    if settings['verbose']:
        print(*args, **kwargs)


def get_local_dependencies(path: Path) -> List[Path]:
    with path.open() as f:
        includes = re.findall(r'^[ \t]*#[ \t]*include[ \t]*"([^"]*)"', f.read(), flags=re.MULTILINE)
    return [path.parent / Path(p) for p in includes]


def compile(path: Path) -> Tuple[Path, bool]:
    '''
    Returns object file and if it recompiled or not
    '''
    compiler = settings['compilers'].get(path.suffix)
    if compiler:
        compiler_args = settings['compiler_args'].get(compiler, [])

        pre_abs = path
        path = path.absolute()
        obj_file = path.with_suffix('.o')

        if obj_file.exists() and obj_file.stat().st_mtime > path.stat().st_mtime:
            last_compiled = obj_file.stat().st_mtime
            headers = get_local_dependencies(path)
            if all(h.exists() and last_compiled > h.stat().st_mtime for h in headers):
                print_if_verbose(f'Skipping recompilation for {pre_abs}')
                return obj_file, False

        args = [compiler, '-c'] + compiler_args + ['-o', str(obj_file), str(path)]
        print_if_verbose(' '.join(args))
        result = subprocess.run(args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        print_if_something(result.stdout.decode())
        print_if_something(result.stderr.decode())
        result.check_returncode()

        return obj_file, True
    else:
        raise ValueError(f'No compiler found for suffix: "{path.suffix}"')
            

def final_compile(main_path: Path, all_objects: List[Path]) -> str:
    compiler = settings['compilers'].get(main_path.suffix)
    if compiler:
        linker_args = settings['linker_args']

        all_objects = [str(p.absolute()) for p in all_objects]

        executable = main_path.with_suffix('')
        args = [compiler, '-o', str(executable)] + all_objects + linker_args
        print_if_verbose(' '.join(args))
        result = subprocess.run(args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        print_if_something(result.stdout.decode())
        print_if_something(result.stderr.decode(), always=True)
        result.check_returncode()

        return executable
    else:
        raise ValueError(f'No compiler found for suffix: "{main_path.suffix}"')


def main(exclude_args: List[str]):
    root = Path('.')  #.absolute()
    print_if_verbose('root:', root.absolute())

    all_files = get_all_with_ending('cpp', root, exclude=exclude_args)

    main = root / 'main.cpp'

    if not main.exists():
        print('Error: Could not find main.cpp')
        return

    for i in all_files:
        print_if_verbose(str(i))
    print_if_verbose()

    if not settings['verbose']:
        bar = ProgressBar(len(all_files) + 1)  # +1 for final creation of the executable
        
        bar.update_progress_bar(init=True)
        update_progress_bar = bar.update_progress_bar
    else:
        def update_progress_bar(obj=None):
            return obj

    try:
        obj_files, did_recompile = zip(*(update_progress_bar(compile(p)) for p in all_files))

        if any(did_recompile):
            exe = final_compile(main, obj_files)  
        else:
            print_if_verbose(f'Skipping creating the executable since nothing was recompiled')
        update_progress_bar()

    except subprocess.CalledProcessError:
        print('Something went wrong... :(')
        return
    
    if not settings['verbose']:
        print()


class ProgressBar:

    def __init__(self, compile_count: int) -> None:
        self.files_done: int = 0
        self.cols, _ = get_terminal_size()
        self.cols: int = self.cols - 4 - 8
        self.compile_count: int = compile_count
        self.cols_per_file: float = self.cols / compile_count
    
    def update_progress_bar(self, *args, init: bool = False):
        if not init:
            self.files_done += 1
        should_be = int(self.cols_per_file * self.files_done)
        print(f'\r{self.files_done:3}/{self.compile_count:3} [', should_be * '=', '>', (self.cols - should_be) * ' ', sep='', end=']', flush=True)

        return args[0] if len(args) == 1 else args


def clean():
    root = Path('.')  #.absolute()
    all_files = get_all_with_ending('o', root, exclude=exclude_args)
    main = root / 'main'

    all_files.append(main)

    print_if_verbose('Removing:')
    for f in all_files:
        if f.exists():
            print_if_verbose('\t' + str(f))
            f.unlink()




if __name__ == '__main__':
    exclude_args = sys.argv[1:]
    if '--verbose' in exclude_args:
        exclude_args.remove('--verbose')
        settings['verbose'] = True

    if '--clean' in exclude_args:
        clean()
    else:
        exclude_args += settings['excludes']
        exclude_args = [arg + '*' if arg.endswith('/') else arg for arg in exclude_args]
        main(exclude_args)
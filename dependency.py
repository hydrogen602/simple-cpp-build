from pathlib import Path
from typing import Dict, List, Set, Type
import re


class DependencyTree:

    __visited_dependencies: Dict[Path, 'DependencyTree'] = {}

    def __new__(cls: Type['DependencyTree'], file: Path) -> 'DependencyTree':
        if file in cls.__visited_dependencies:
            return cls.__visited_dependencies[file]
        else:
            obj = super().__new__(cls)
            cls.__visited_dependencies[file] = obj
            return obj

    def __init__(self, file: Path) -> None:
        self.file: Path = file

        with self.file.open() as f:
            includes = re.findall(r'^[ \t]*#[ \t]*include[ \t]*"([^"]*)"', f.read(), flags=re.MULTILINE)

        self.dependencies: List[DependencyTree] = [DependencyTree(self.file.parent / Path(p)) for p in includes]

    def was_updated_after(self, time: float) -> bool:
        if self.file.stat().st_mtime > time:
            return True
        else:
            return any(e.was_updated_after(time) for e in self.dependencies)

    def print(self, depth: int = 0):
        if depth > 20:
            raise Exception('Max depth exceeded for dependencies')
        
        preMain = '  ' * depth + ('- ' * (depth > 0))
        print(f'{preMain}{self.file}')

        for e in self.dependencies:
            e.print(depth+1)
        

# def get_local_dependencies(path: Path) -> List[Path]:
#     with path.open() as f:
#         includes = re.findall(r'^[ \t]*#[ \t]*include[ \t]*"([^"]*)"', f.read(), flags=re.MULTILINE)
#     return [path.parent / Path(p) for p in includes]


# def print_dep(file: Path, depth: int = 0, seen_dependencies: Set[Path] = set()):
#     ls = get_local_dependencies(file)
#     preMain = '  ' * (depth) + ('- ' * (depth > 0))
#     print(f'{preMain}{file}')
#     twice = seen_dependencies.intersection(ls)
#     if twice:
#         raise Exception(f'Circular dependency detected: {twice}')

#     for e in ls:
#         print_dep(e, depth+1, seen_dependencies.union((e,)))
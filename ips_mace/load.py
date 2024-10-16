import ase.io as aio
import ase
import zntrack
import pathlib


class LoadDataFile(zntrack.Node):
    path: str|pathlib.Path = zntrack.deps_path()

    def run(self):
        pass

    @property
    def frames(self) -> list[ase.Atoms]:
        format = pathlib.Path(self.path).suffix[1:]
        if format == 'xyz':
            format = "extxyz"
        with self.state.fs.open(self.path, 'r') as f:
            return list(aio.iread(f, format=format))
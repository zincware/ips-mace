"""MACE model module."""
import zntrack
import ase.io
import sys
import yaml
import pathlib
import subprocess
import pandas as pd
import json

def execute(cmd, **kwargs):
    """Execute a command and yield the output line by line.

    Adapted from https://stackoverflow.com/a/4417735/10504481
    """
    popen = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, universal_newlines=True, **kwargs
    )
    yield from iter(popen.stdout.readline, "")
    popen.stdout.close()
    if return_code := popen.wait():
        raise subprocess.CalledProcessError(return_code, cmd)


class MACE(zntrack.Node):
    data: list[ase.Atoms] = zntrack.deps()
    config: str = zntrack.params_path()

    model_dir: pathlib.Path = zntrack.outs_path(zntrack.nwd / "model")
    training_config: pathlib.Path = zntrack.outs_path(zntrack.nwd / "training_config.yaml")

    history: pd.DataFrame = zntrack.plots(autosave=True, x="epoch", y=["loss", "mae_e_per_atom"])

    def write_test_file(self):
        test_file = self.model_dir / "test_data.xyz"
        ase.io.write(test_file, self.data)
    
    def write_train_file(self):
        train_file = self.model_dir / "train_data.xyz"
        ase.io.write(train_file, self.data)

    def write_config_file(self):
        self.history = pd.DataFrame()
        with open(self.config, "r") as f:
            config = yaml.safe_load(f)

            # model: "MACE" ?

        config["model_dir"] = (self.model_dir / "model").as_posix()
        config["log_dir"] = (self.model_dir / "log").as_posix()
        config["checkpoints_dir"] = (self.model_dir / "checkpoint").as_posix()
        config["results_dir"] =( self.model_dir / "results").as_posix()
        config["train_file"] = (self.model_dir / "train_data.xyz").as_posix()
        config["test_file"] = (self.model_dir / "test_data.xyz").as_posix()

        with open(self.training_config, "w") as f:
            yaml.dump(config, f)



    def run(self):
        # from mace.cli.run_train import main as mace_run_train_main
        self.model_dir.mkdir(parents=True, exist_ok=True)


        self.write_test_file()
        self.write_train_file()
        self.write_config_file()

        for content in execute(["mace_run_train", "--config", self.training_config.as_posix()]):
            print(content, end="")
            for file in (self.model_dir / "results").glob("*.*"):
                data = []
                with open(file, 'r') as file:
                    for line in file:
                        record = json.loads(line)  # parse the JSON object
                        if record["mode"] == "eval":
                            data.append(record)
                self.history = pd.DataFrame(data).set_index("epoch")
                break
            _ = self.history # trigger autosave



# import json
# import logging
# import pathlib
# import subprocess

# import pandas as pd
# import torch
# import yaml
# import zntrack
# from mace.calculators import MACECalculator

# from ipsuite.models import MLModel
# from ipsuite.static_data import STATIC_PATH

# log = logging.getLogger(__name__)


# def execute(cmd, **kwargs):
#     """Execute a command and yield the output line by line.

#     Adapted from https://stackoverflow.com/a/4417735/10504481
#     """
#     popen = subprocess.Popen(
#         cmd, stdout=subprocess.PIPE, universal_newlines=True, **kwargs
#     )
#     yield from iter(popen.stdout.readline, "")
#     popen.stdout.close()
#     if return_code := popen.wait():  # finally a use for walrus operator
#         raise subprocess.CalledProcessError(return_code, cmd)


# class MACE(MLModel):
#     """MACE model."""

#     train_data_file: pathlib.Path = zntrack.outs_path(zntrack.nwd / "train-data.extxyz")

#     test_data = zntrack.deps()
#     test_data_file: pathlib.Path = zntrack.outs_path(zntrack.nwd / "test-data.extxyz")
#     model_dir: pathlib.Path = zntrack.outs_path(zntrack.nwd / "model")

#     config: str = zntrack.params_path("mace.yaml")
#     device: str = zntrack.meta.Text(None)

#     training: pathlib.Path = zntrack.plots_path(
#         zntrack.nwd / "training.csv",
#         template=STATIC_PATH / "y_log.json",
#         x="epoch",
#         y=["loss", "rmse_e_per_atom", "rmse_f"],
#     )

#     _module_ = "ips_mace"

#     def _post_load_(self) -> None:
#         if self.device is None:
#             self.device = "cuda" if torch.cuda.is_available() else "cpu"

#     @classmethod
#     def generate_config_file(self, file: str = "mace.yaml"):
#         example = {
#             "amsgrad": True,
#             "batch_size": 5,
#             "ema": True,
#             "ema_decay": 0.99,
#             "hidden_irreps": "128x0e + 128x1o",
#             "max_num_epochs": 1000,
#             "num_cutoff_basis": 5,
#             "num_interactions": 2,
#             "num_radial_basis": 8,
#             "r_max": 5.0,
#             "seed": 42,
#             "start_swa": 1200,
#             "swa": True,
#             "E0s": "average",
#         }
#         pathlib.Path(file).write_text(yaml.safe_dump(example))

#     def run(self):
#         """Train a MACE model."""
#         self.model_dir.mkdir(parents=True, exist_ok=True)
#         cmd = ["mace_run_train"]
#         cmd.append("--name=MACE_model")
#         cmd.append(f"--train_file={self.train_data_file.resolve().as_posix()}")
#         cmd.append("--valid_fraction=0.05")
#         cmd.append(f"--test_file={self.test_data_file.resolve().as_posix()}")
#         cmd.append(f"--device={self.device}")

#         config = yaml.safe_load(pathlib.Path(self.config).read_text())
#         for key, val in config.items():
#             if val is True:
#                 cmd.append(f"--{key}")
#             elif val is False:
#                 pass
#             else:
#                 cmd.append(f"--{key}={val}")

#         self.write_data_to_file(file=self.train_data_file, atoms_list=self.data)
#         self.write_data_to_file(file=self.test_data_file, atoms_list=self.test_data)

#         log.debug(f"Running: {cmd}")

#         for path in execute(cmd, cwd=self.model_dir):
#             print(path, end="")
#             file = list((self.model_dir / "results").glob("*.*"))
#             if len(file) == 1:
#                 data = []

#                 with file[0].open() as f:
#                     for line in f.readlines():
#                         value = json.loads(line)
#                         if value["mode"] == "eval":
#                             data.append(value)

#                 pd.DataFrame(data).set_index("epoch").to_csv(self.training)

#     def get_calculator(self, device=None, **kwargs):
#         """Return the ASE calculator."""
#         import unittest.mock

#         with self.state.fs.open(self.config) as f:
#             config = yaml.safe_load(f)
#             default_dtype = config.get("default_dtype", "float64")

#         if self.state.fs.exists(self.model_dir / "MACE_model_swa.model"):
#             model_name = "MACE_model_swa.model"
#         else:
#             model_name = "MACE_model.model"

#         with unittest.mock.patch(
#             "torch.serialization._open_file_like", self.state.fs.open
#         ):
#             return MACECalculator(
#                 model_paths=self.model_dir / model_name,
#                 device=device or self.device,
#                 default_dtype=default_dtype,
#             )

import os
import subprocess
from abc import ABC, abstractmethod


class Installer(ABC):
    @staticmethod
    def clone_openvr(clone_dir: str) -> None:
        """Clone the OpenVR repository."""

        if not os.path.exists(os.path.join(clone_dir, "openvr")):
            subprocess.run(
                [
                    "git",
                    "clone",
                    "-b",
                    "v1.0.17",
                    "git@github.com:ValveSoftware/openvr.git",
                    os.path.join(clone_dir, "openvr"),
                ],
                check=True,
            )

    @staticmethod
    def clone_pymol(clone_dir: str, version: str) -> None:
        """Clone the PyMOL repository."""

        if not os.path.exists(os.path.join(clone_dir, "pymol-open-source")):
            subprocess.run(
                [
                    "git",
                    "clone",
                    "-b",
                    version,
                    "git@github.com:schrodinger/pymol-open-source.git",
                    os.path.join(clone_dir, "pymol-open-source"),
                ],
                check=True,
            )

    @staticmethod
    def install_pymol(
        clone_dir: str, version: str, env_name: str, use_openvr: bool
    ) -> None:
        """Clone, build and install PyMOL."""

        Installer.clone_pymol(clone_dir, version)
        subprocess.run(
            [
                "conda",
                "run",
                "-n",
                env_name,
                "pip",
                "install",
                "--config-settings",
                f"openvr={use_openvr}",
                os.path.join(clone_dir, "pymol-open-source"),
            ],
            check=True,
        )

    @staticmethod
    @abstractmethod
    def get_env_file(wizard_root: str) -> str:
        pass

    @staticmethod
    @abstractmethod
    def install_openvr(clone_dir: str, conda_base_path: str, env_name: str) -> None:
        pass

    @staticmethod
    @abstractmethod
    def get_pymol_dir(conda_prefix: str, python_version: str) -> str:
        pass

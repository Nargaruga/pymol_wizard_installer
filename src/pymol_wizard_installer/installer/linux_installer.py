import os
import shutil
import subprocess
from typing import override

from pymol_wizard_installer.installer.base_installer import Installer


class LinuxInstaller(Installer):
    @staticmethod
    @override
    def get_env_file(wizard_root: str) -> str:
        """Get the Conda environment file for the wizard."""

        envs_dir = os.path.join(wizard_root, "envs")

        default_env = os.path.join(envs_dir, "environment.yaml")
        linux_env = os.path.join(envs_dir, "linux_environment.yaml")

        if os.path.exists(default_env):
            return default_env
        elif os.path.exists(linux_env):
            return linux_env
        else:
            raise FileNotFoundError(
                f"Neither {default_env} nor {linux_env} exist. Please check the installation files."
            )

    @staticmethod
    @override
    def install_openvr(clone_dir: str, conda_base_path: str, env_name: str) -> None:
        """Clone, build and install OpenVR."""

        Installer.clone_openvr(clone_dir)
        env_dir = os.path.join(conda_base_path, "envs", env_name)

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

        subprocess.run(
            [
                "conda",
                "run",
                "-n",
                env_name,
                "cmake",
                "-S",
                ".",
                "-B",
                "build",
                "-DCMAKE_BUILD_TYPE=Release",
            ],
            cwd=os.path.join(clone_dir, "openvr"),
            check=True,
        )

        subprocess.run(
            [
                "conda",
                "run",
                "-n",
                env_name,
                "cmake",
                "--build",
                "build",
                "--config",
                "Release",
            ],
            cwd=os.path.join(clone_dir, "openvr"),
            check=True,
        )

        subprocess.run(
            ["conda", "run", "-n", env_name, "sudo", "make", "install"],
            cwd=os.path.join(clone_dir, "openvr", "build"),
            check=True,
        )

        # Copy the openvr.h header
        shutil.copy(
            os.path.join(clone_dir, "openvr", "headers", "openvr.h"),
            os.path.join(env_dir, "include"),
        )

    @staticmethod
    @override
    def get_pymol_dir(conda_prefix: str, python_version: str) -> str:
        return os.path.join(
            conda_prefix,
            "lib",
            f"python{python_version}",
            "site-packages",
            "pymol",
        )

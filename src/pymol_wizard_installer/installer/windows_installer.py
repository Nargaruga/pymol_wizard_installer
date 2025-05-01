import os
import shutil
import subprocess
from typing import override

from pymol_wizard_installer.installer.base_installer import Installer


class WindowsInstaller(Installer):
    @staticmethod
    @override
    def get_env_file(wizard_root: str) -> str:
        """Get the Conda environment file for the wizard."""

        envs_dir = os.path.join(wizard_root, "envs")

        default_env = os.path.join(envs_dir, "environment.yaml")
        windows = os.path.join(envs_dir, "windows_environment.yaml")

        if os.path.exists(default_env):
            return default_env
        elif os.path.exists(windows):
            return windows
        else:
            raise FileNotFoundError(
                f"Neither {default_env} nor {windows} exist. Please check the installation files."
            )

    @staticmethod
    @override
    def install_openvr(clone_dir: str, conda_base_path: str, env_name: str) -> None:
        """Clone, build and install OpenVR."""

        Installer.clone_openvr(clone_dir)
        env_dir = os.path.join(conda_base_path, "envs", env_name)

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
                f"-DCMAKE_INSTALL_PREFIX={env_dir}",
                "-DBUILD_SHARED=1",
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
                "--target",
                "install",
            ],
            cwd=os.path.join(clone_dir, "openvr"),
            check=True,
        )

        # Rename the .lib file
        shutil.move(
            os.path.join(
                env_dir,
                "Lib",
                "openvr_api64.lib",
            ),
            os.path.join(
                env_dir,
                "Lib",
                "openvr_api.lib",
            ),
        )

        # Move the .dll to the right directory
        shutil.move(
            os.path.join(
                env_dir,
                "Lib",
                "openvr_api64.dll",
            ),
            os.path.join(
                env_dir,
                "Library",
                "bin",
                "openvr_api64.dll",
            ),
        )

        # Copy the openvr.h header
        shutil.copy(
            os.path.join(clone_dir, "openvr", "headers", "openvr.h"),
            os.path.join(env_dir, "include"),
        )

    @staticmethod
    @override
    def get_pymol_dir(conda_prefix: str, _: str) -> str:
        return os.path.join(
            conda_prefix,
            "Lib",
            "site-packages",
            "pymol",
        )

import os
import sys
from pathlib import Path
import subprocess
import re
import fileinput
import yaml
import toml

from pymol_wizard_installer.wizard_metadata import WizardMetadata


def read_wizard_metadata(installation_data):
    stream = open(Path(installation_data), "r")
    raw_data = yaml.safe_load(stream)

    return raw_data


def remove_line(file, pattern_to_remove):
    with fileinput.FileInput(file, inplace=True, backup=".bak") as file:
        for line in file:
            if not pattern_to_remove.search(line):
                print(line, end="")


def get_package_name_from_toml(package_root):
    """Reads the package name from pyproject.toml."""

    toml_path = os.path.join(package_root, "pyproject.toml")
    if not os.path.exists(toml_path):
        print(f"Error: pyproject.toml not found in {package_root}")
        return None

    try:
        with open(toml_path, "r") as f:
            data = toml.load(f)
            if "project" in data and "name" in data["project"]:
                return data["project"]["name"]
            else:
                print("Error: 'project.name' not found in pyproject.toml")
                return None
    except toml.TomlDecodeError as e:
        print(f"Error decoding pyproject.toml: {e}")
        return None
    except FileNotFoundError:
        print(f"Error: pyproject.toml not found at {toml_path}")
        return None

def uninstall_package(package_name):
    """Uninstalls a Python package using pip."""

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", package_name])
        print(f"Successfully uninstalled {package_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error uninstalling {package_name}: {e}")

def main():
    if len(sys.argv) < 2:
        print("Please provide the path to the wizard's root directory.")
        exit(1)

    raw_wizard_metadata = read_wizard_metadata(
        os.path.join(sys.argv[1], "metadata.yaml")
    )
    wizard_config = WizardMetadata(
        raw_wizard_metadata["name"],
        raw_wizard_metadata["menu_entry"],
        raw_wizard_metadata["default_env"],
        raw_wizard_metadata["use_vr"],
        raw_wizard_metadata["python_version"],
        raw_wizard_metadata["pymol_version"],
        raw_wizard_metadata["openvr_version"],
        raw_wizard_metadata["pre_script"],
        raw_wizard_metadata["post_script"],
    )

    if len(sys.argv) > 2:
        env_name = sys.argv[2]
    else:
        env_name = None

    if env_name is None:
        print(
            f'The conda environment used in the installation was not recorded. Please enter the name of the environment, or leave empty for default ("{wizard_config.default_env}"):'
        )
        try:
            env_name = input().strip()
            if not env_name:
                env_name = wizard_config.default_env
        except KeyboardInterrupt:
            print("Aborted by user.")
            exit(0)

    try:
        conda_base_path = str(
            subprocess.check_output("conda info --base", shell=True), "utf-8"
        ).strip()
    except subprocess.CalledProcessError:
        print("Failed to retrieve conda base path.")
        exit(1)

    prefix = os.path.join(conda_base_path, "envs", env_name)
    if prefix is None:
        print("Something went wrong. Please check the conda environment name.")
        exit(1)

    print("Uninstalling package...")
    uninstall_package(get_package_name_from_toml(sys.argv[1]))

    print("Removing files...")
    if os.name == "nt":
        pymol_dir = os.path.join(
            prefix,
            "Lib",
            "site-packages",
            "pymol",
        )
    else:
        pymol_dir = os.path.join(
            prefix,
            "lib",
            f"python{wizard_config.python_version}",
            "site-packages",
            "pymol",
        )

    installed_wizard_dir = os.path.join(pymol_dir, "wizard")
    try:
        os.remove(os.path.join(installed_wizard_dir, f"{wizard_config.name}.py"))
    except FileNotFoundError:
        print("No files to delete.")
        pass

    print("Removing menu entries...")
    if wizard_config.use_vr:
        openvr_wizard_file = os.path.join(pymol_dir, "wizard", "openvr.py")
        openvr_entry = (
            f"[1, '{wizard_config.menu_entry}', 'wizard {wizard_config.name}'],\n"
        )
        openvr_entry_pattern = re.compile(
            openvr_entry.replace("[", r"\[").replace("]", r"\]")
        )
        remove_line(openvr_wizard_file, openvr_entry_pattern)

    gui_file = os.path.join(pymol_dir, "_gui.py")
    external_entry = (
        f"('command', '{wizard_config.menu_entry}', 'wizard {wizard_config.name}'),\n"
    )
    external_entry_pattern = re.compile(
        external_entry.replace("(", r"\(").replace(")", r"\)")
    )
    remove_line(gui_file, external_entry_pattern)

    print(
        f"Successfully uninstalled wizard {wizard_config.name} from environment {env_name}."
    )


if __name__ == "__main__":
    main()

import os
import sys
from pathlib import Path
import subprocess
import re
import fileinput
import yaml
import toml
import argparse

from pymol_wizard_installer.wizard_metadata import WizardMetadata


def parse_wizard_metadata(metadata_file):
    """Parse the wizard metadata file."""

    stream = open(Path(metadata_file), "r")
    raw_metadata = yaml.safe_load(stream)

    return WizardMetadata(
        raw_metadata["name"],
        raw_metadata["menu_entry"],
        raw_metadata["default_env"],
        raw_metadata["python_version"],
        raw_metadata["pymol_version"],
        raw_metadata["openvr_version"],
        raw_metadata["pre_script"],
        raw_metadata["post_script"],
    )


def remove_line(file, pattern_to_remove):
    print(f"Processing file: {file}")
    with fileinput.FileInput(file, inplace=True, backup=".bak") as opened_file:
        for line in opened_file:
            if not pattern_to_remove.search(line):
                sys.stdout.write(line)


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


def uninstall_package(package_name, env_name):
    """Uninstalls a Python package using pip."""

    try:
        subprocess.run(
            ["conda", "run", "-n", env_name, "pip", "uninstall", "-y", package_name],
            shell=True,
        )
        print(f"Successfully uninstalled {package_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error uninstalling {package_name}: {e}")


def parse_args():
    """Parse and return command line arguments."""

    parser = argparse.ArgumentParser(
        prog="uninstall_wizard", description="Uninstall a PyMOL wizard."
    )
    parser.add_argument(
        "wizard_root",
        type=str,
        help="Path to the wizard's root directory.",
    )

    parser.add_argument(
        "--env_name",
        type=str,
        help="Name of the conda environment to uninstall from.",
    )

    return parser.parse_args()


def main():
    args = parse_args()
    wizard_metadata = parse_wizard_metadata(
        os.path.join(args.wizard_root, "metadata.yaml")
    )

    if args.env_name:
        env_name = args.env_name
        print(f"Using recorded environment name: {env_name}.")
    else:
        print(
            f'The conda environment used in the installation was not recorded. Please enter the name of the environment, or leave empty for default ("{wizard_metadata.default_env}"):'
        )
        try:
            env_name = input().strip()
            if not env_name:
                env_name = wizard_metadata.default_env
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
    uninstall_package(get_package_name_from_toml(args.wizard_root), args.env_name)

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
            f"python{wizard_metadata.python_version}",
            "site-packages",
            "pymol",
        )

    installed_wizard_dir = os.path.join(pymol_dir, "wizard")
    try:
        os.remove(os.path.join(installed_wizard_dir, f"{wizard_metadata.name}.py"))
    except FileNotFoundError:
        print("No files to delete.")
        pass

    print("Removing menu entries...")
    openvr_wizard_file = os.path.join(pymol_dir, "wizard", "openvr.py")
    openvr_entry = (
        f"[1, '{wizard_metadata.menu_entry}', 'wizard {wizard_metadata.name}'],\n"
    )
    openvr_entry_pattern = re.compile(
        openvr_entry.replace("[", r"\[").replace("]", r"\]")
    )
    remove_line(openvr_wizard_file, openvr_entry_pattern)

    gui_file = os.path.join(pymol_dir, "_gui.py")
    external_entry = f"('command', '{wizard_metadata.menu_entry}', 'wizard {wizard_metadata.name}'),\n"
    external_entry_pattern = re.compile(
        external_entry.replace("(", r"\(").replace(")", r"\)")
    )
    remove_line(gui_file, external_entry_pattern)

    print(
        f"Successfully uninstalled wizard {wizard_metadata.name} from environment {env_name}."
    )


if __name__ == "__main__":
    main()

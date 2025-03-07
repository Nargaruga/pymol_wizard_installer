import os
import sys
from pathlib import Path
import subprocess
import shutil
import re
import fileinput
import yaml

from wizard_metadata import WizardMetadata


def read_installation_data(installation_data):
    stream = open(Path(installation_data), "r")
    raw_data = yaml.safe_load(stream)

    return raw_data


def remove_line(file, pattern_to_remove):
    with fileinput.FileInput(file, inplace=True, backup=".bak") as file:
        for line in file:
            if not pattern_to_remove.search(line):
                print(line, end="")


def main():
    args = sys.argv[1:]
    if len(args) < 1:
        print("Missing mandatory argument: wizard installation data file.")
        exit(1)

    raw_installation_data = read_installation_data(args[0])
    wizard_config_raw = raw_installation_data["config"]
    wizard_config = WizardMetadata(
        wizard_config_raw["name"],
        wizard_config_raw["menu_entry"],
        wizard_config_raw["default_env"],
        wizard_config_raw["root_dir"],
        wizard_config_raw["use_vr"],
        wizard_config_raw["python_version"],
        wizard_config_raw["pymol_version"],
        wizard_config_raw["openvr_version"],
    )
    env_name = raw_installation_data["env_name"]

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

    print("Done! Note that the conda environment was not removed.")

    if __name__ == "__main__":
        main()

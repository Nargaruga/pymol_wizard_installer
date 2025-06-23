import os
import sys
from pathlib import Path
import subprocess
import shutil
import re
import stat
import yaml
import argparse

from pymol_wizard_installer.wizard_metadata import WizardMetadata


if os.name == "nt":
    from pymol_wizard_installer.installer.windows_installer import (
        WindowsInstaller as Installer,
    )
elif os.name == "posix":
    from pymol_wizard_installer.installer.linux_installer import (
        LinuxInstaller as Installer,
    )
else:
    raise RuntimeError("Unsupported operating system.")


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


def get_answer(prompt, default=""):
    """Prompt the user and return the answer."""

    try:
        answer = input(prompt).strip().lower() or default
    except KeyboardInterrupt:
        print("Aborted by user.")
        exit(0)

    return answer


def env_exists(env_name):
    """Check if a conda environment exists."""
    try:
        subprocess.run(
            f"conda list --name {env_name}",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            shell=True,
        ).check_returncode()
    except subprocess.CalledProcessError:
        return False
    return True


def overwrite_env(env_name, wizard_root, current_env):
    """Overwrite an existing conda environment."""

    print(f"Overwriting existing environment {env_name}.")
    if env_name == current_env:
        print(
            "Cannot overwrite an active environment. Please deactivate it before retrying."
        )
        exit(1)
    try:
        subprocess.run(
            [
                "conda",
                "env",
                "remove",
                "--name",
                env_name,
                "--yes",
            ],
            check=True,
        )

        subprocess.run(
            [
                "conda",
                "env",
                "create",
                "--name",
                env_name,
                "--file",
                Installer.get_env_file(wizard_root),
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Something went wrong while overwriting the environment: {e}")
        exit(1)


def reuse_env(env_name, wizard_root):
    """Reuse existing conda environment."""

    print(f"Using existing environment {env_name}.")
    subprocess.run(
        [
            "conda",
            "env",
            "update",
            "--name",
            env_name,
            "--file",
            Installer.get_env_file(wizard_root),
        ],
        check=True,
    )


def create_env(env_name, wizard_root, current_env, answer=""):
    """Create a conda environment."""

    if env_exists(env_name):
        while answer not in ["o", "u", "a"]:
            try:
                print(
                    f"Environment {env_name} already exists. Do you wish to overwrite it, use it or abort? (o/u/A)"
                )
                answer = input().strip().lower() or "a"
            except KeyboardInterrupt:
                print("Aborted by user.")
                exit(0)

        if answer == "o":
            overwrite_env(env_name, wizard_root, current_env)
        elif answer == "u":
            reuse_env(env_name, wizard_root)
        elif answer == "a":
            print("Aborted by user.")
            exit(0)
        else:
            print(
                "Invalid input. Please enter 'o' (overwrite), 'u' (use) or 'a' (abort)."
            )
    else:
        print(f"Creating new environment {env_name}.")
        subprocess.run(
            f"conda env create --name {env_name} -f {Installer.get_env_file(wizard_root)}",
            check=True,
            shell=True,
        )


def is_pymol_installed(env_name: str) -> bool:
    """Check if PyMOL is installed in the conda environment."""

    try:
        subprocess.run(
            ["conda", "run", "--name", env_name, "python", "-c", "import pymol"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def run_aux_script(script_path, wizard_root, conda_env):
    """Run a pre/post installation script."""

    try:
        subprocess.run(
            [
                "conda",
                "run",
                "--no-capture-output",
                "--name",
                conda_env,
                "python",
                script_path,
                wizard_root,
                conda_env,
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Failed to run auxiliary installation script: {e}")
        exit(1)


def install_package(conda_env: str, wizard_root: str):
    """Install the wizard package in the conda environment."""

    print(f"Installing package in the {conda_env} environment...")
    try:
        subprocess.run(
            [
                "conda",
                "run",
                "--name",
                conda_env,
                "pip",
                "install",
                wizard_root,
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Failed to install package: {e}")
        exit(1)


def copy_files(installed_wizard_dir: str, wizard_root: str, wizard_name: str):
    """Copy the wizard files to the PyMOL installation directory."""

    print(f"Copying the {wizard_name} wizard to {installed_wizard_dir}...")
    try:
        shutil.copy(
            os.path.join(wizard_root, f"{wizard_name}.py"),
            os.path.join(installed_wizard_dir, f"{wizard_name}.py"),
        )
    except shutil.Error as e:
        print(f"Failed to copy files: {e}")
        exit(1)


def add_line_after(file, to_insert, pattern_to_insert, target_pattern):
    """Adds a line to the file after the specified point. If the line is already present, the file is unchanged."""

    with open(file, "r") as f:
        contents = f.read()

    if re.search(pattern_to_insert, contents):
        print(f"Entry already exists in {file}, skipping...")
        return

    target = target_pattern.search(contents)
    if target is None:
        print(f"Could not find target in {file}")
        return

    target_end = target.end()

    contents = contents[:target_end] + f"{to_insert}" + contents[target_end:]

    with open(file, "w") as f:
        f.write(contents)


def add_external_gui_entry(pymol_dir: str, menu_entry: str, wizard_name: str):
    """Add an entry to the external GUI's Wizard menu."""

    print("Adding external GUI entry...")
    gui_file = os.path.join(pymol_dir, "_gui.py")
    external_entry = f'\n("command", "{menu_entry}", "wizard {wizard_name}"),'
    external_entry_pattern = re.compile(
        external_entry.replace("(", r"\(").replace(")", r"\)").replace('"', r'["\']')
    )
    external_target_pattern = re.compile(
        r'\(\s*["\']menu["\'],\s*["\']Wizard["\'],\s*\['
    )
    add_line_after(
        gui_file, external_entry, external_entry_pattern, external_target_pattern
    )


def add_internal_gui_entry(
    installed_wizard_dir: str, menu_entry: str, wizard_name: str
):
    """Add an entry to the internal GUI's Wizard menu."""

    print("Adding internal GUI entry...")
    openvr_wizard = os.path.join(installed_wizard_dir, "openvr.py")
    openvr_entry = f'\n[1, "{menu_entry}", "wizard {wizard_name}"],'
    openvr_entry_pattern = re.compile(
        openvr_entry.replace("[", r"\[").replace("]", r"\]").replace('"', r'["\']')
    )
    openvr_target_pattern = re.compile(r'\[2, ["\']Wizard Menu["\'], ["\']["\']\],')
    add_line_after(
        openvr_wizard, openvr_entry, openvr_entry_pattern, openvr_target_pattern
    )


def parse_args():
    """Parse and return command line arguments."""

    parser = argparse.ArgumentParser(
        prog="install_wizard", description="Automate PyMOL wizard installation."
    )
    parser.add_argument(
        "wizard_root",
        type=str,
        help="Path to the wizard's root directory.",
    )

    parser.add_argument(
        "--env_name",
        type=str,
        help="Name of the conda environment to create or use.",
    )

    parser.add_argument(
        "--fast",
        action="store_true",
    )

    return parser.parse_args()


def fast_installation(target_env, prefix, wizard_root, wizard_metadata):
    print("Quick installation mode enabled.")
    install_package(target_env, wizard_root)

    pymol_dir = Installer.get_pymol_dir(prefix, wizard_metadata.python_version)
    installed_wizard_dir = os.path.join(pymol_dir, "wizard")
    copy_files(installed_wizard_dir, wizard_root, wizard_metadata.name)


def full_installation(
    target_env, prefix, conda_base_path, wizard_root, wizard_metadata
):
    pymol_dir = Installer.get_pymol_dir(prefix, wizard_metadata.python_version)
    if is_pymol_installed(target_env):
        print("PyMOL is already installed, skipping...")
    else:
        install_pymol_ans = get_answer(
            f"PyMOL is not installed in the {target_env} environment. Do you wish to install it? (Y/n)",
            "y",
        )
        if install_pymol_ans == "y":
            clone_dir_path = os.path.join(".", "tmp")
            Path(clone_dir_path).mkdir(parents=True, exist_ok=True)

            openvr_support_ans = get_answer(
                "Do you wish to enable OpenVR support? (Y/n)", "y"
            )
            if openvr_support_ans == "y":
                Installer.install_openvr(clone_dir_path, conda_base_path, target_env)
                use_openvr = True
            else:
                use_openvr = False

            Installer.install_pymol(
                clone_dir_path,
                wizard_metadata.pymol_version,
                target_env,
                use_openvr,
            )

    if wizard_metadata.pre_script:
        print(
            f"Running pre-installation script for the {wizard_metadata.name} wizard..."
        )
        run_aux_script(
            os.path.join(wizard_root, wizard_metadata.pre_script),
            wizard_root,
            target_env,
        )

    install_package(target_env, wizard_root)
    installed_wizard_dir = os.path.join(pymol_dir, "wizard")
    copy_files(installed_wizard_dir, wizard_root, wizard_metadata.name)
    add_external_gui_entry(pymol_dir, wizard_metadata.menu_entry, wizard_metadata.name)
    add_internal_gui_entry(
        installed_wizard_dir, wizard_metadata.menu_entry, wizard_metadata.name
    )

    print(f"The {wizard_metadata.name} wizard has been successfully installed.")

    if wizard_metadata.post_script:
        print(
            f"Running post-installation script for the {wizard_metadata.name} wizard..."
        )
        run_aux_script(
            os.path.join(wizard_root, wizard_metadata.post_script),
            wizard_root,
            target_env,
        )

    def remove_readonly(func, path, _):
        """Clear the readonly bit and remove the file."""

        os.chmod(path, stat.S_IWRITE)
        func(path)

    if os.path.exists(os.path.join(wizard_root, "tmp")):
        delete_files_ans = get_answer(
            "Do you wish to clear the installation files? (y/N)", "n"
        )
        if delete_files_ans == "y":
            try:
                shutil.rmtree(os.path.join(wizard_root, "tmp"), onerror=remove_readonly)
                print("Files removed.")
            except FileNotFoundError:
                print("No files to remove.")
                pass
        else:
            print(
                f"Installation files are kept in {os.path.join(wizard_root, 'tmp')}, if you want to manually delete them."
            )


def main():
    args = parse_args()

    wizard_root = os.path.abspath(args.wizard_root)
    wizard_metadata = parse_wizard_metadata(os.path.join(wizard_root, "metadata.yaml"))

    current_env = os.environ.get("CONDA_DEFAULT_ENV")
    if current_env is None:
        print("Could not detect conda environment. Is conda installed?")
        exit(1)

    try:
        conda_base_path = str(
            subprocess.check_output("conda info --base", shell=True), "utf-8"
        ).strip()
    except subprocess.CalledProcessError:
        print("Failed to retrieve conda base path.")
        exit(1)

    if args.env_name:
        target_env = args.env_name
        print(f"Using provided environment name: {target_env}.")
    else:
        target_env = current_env
        print(f"Using current environment: {target_env}.")

    prefix = os.path.join(conda_base_path, "envs", target_env)
    if prefix is None:
        print(f"Environment {target_env} does not exist.")
        exit(1)

    if args.fast:
        fast_installation(target_env, prefix, wizard_root, wizard_metadata)
    else:
        if target_env != current_env:
            create_env(target_env, wizard_root, current_env, "u")
        else:
            create_new_env_ans = get_answer(
                f"You are currently about to install the {wizard_metadata.name} wizard in the {current_env} environment. Do you wish to create a new conda environment instead? (Y/n)",
                "y",
            )

            if create_new_env_ans == "y":
                target_env = get_answer(
                    f"Please enter the name of the new environment ({wizard_metadata.default_env}):",
                    wizard_metadata.default_env,
                )

                create_env(target_env, wizard_root, current_env)
            else:
                print(f"Using existing environment {current_env}.")

        full_installation(
            target_env, prefix, conda_base_path, wizard_root, wizard_metadata
        )

    print(
        f"Remember to activate the {target_env} conda environment before running PyMOL."
    )


if __name__ == "__main__":
    main()

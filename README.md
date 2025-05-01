# PyMOL Wizard Installer <!-- omit in toc -->
Tool for installing PyMOL wizards in Conda environments. The installation process optionally includes building PyMOL from source with optional VR support, based on the wizard's requirements.

For a wizard to be installable, it must adhere to the structure described in the [Making your Wizard Installable](#making-your-wizard-installable) section.

## Table of Contents <!-- omit in toc -->
- [Setup](#setup)
- [Installing a Wizard](#installing-a-wizard)
- [Uninstalling a Wizard](#uninstalling-a-wizard)
- [Making your Wizard Installable](#making-your-wizard-installable)
  - [The Main Wizard File](#the-main-wizard-file)
  - [Conda Environments](#conda-environments)
  - [Wizard Metadata File](#wizard-metadata-file)
  - [Package Installation](#package-installation)

## Additional Dependencies
Installing wizards with OpenVR support requires CMake (major version <=3) and a C++ compiler.

## Setup
- install [miniconda](https://www.anaconda.com/docs/getting-started/miniconda/main);
- clone this repository;
- run `pip install <PATH>` where `<PATH>` is the path to the repository's root.

After installation, two command line tools are made available: `install_wizard` and `uninstall_wizard`.

## Installing a Wizard
To install a wizard, run
```
install_wizard <PATH> [ENV_NAME]
```
where
- `<PATH>`: path to the wizard's root directory;
- `[ENV_NAME]`: (optional) name of the Conda environment to install the wizard in.

## Uninstalling a Wizard
To uninstall a wizard, run
```
uninstall_wizard <PATH> [ENV_NAME]
```
where
- `<PATH>`: path to the wizard's root directory;
- `[ENV_NAME]`: (optional) name of the Conda environment you want to remove the wizard from.

## Making your Wizard Installable
This section is for developers who want to make their wizard installable with this tool. The required structure is as follows:
```
.
├── envs
│   ├── linux_environment.yaml
│   ├── windows_environment.yaml
│   └── environment.yaml
├── metadata.yaml
├── <WIZARD_NAME>.py
├── pyproject.toml
├── MANIFEST.in
└── src
    └── <PACKAGE_NAME>
```
where
- `<WIZARD_NAME>`: the name that PyMOL will use to identify the wizard. You will be able to run the wizard by writing `wizard <WIZARD_NAME>` in the PyMOL console;
- `<PACKAGE_NAME>`: the name of the Python package to be installed, if any.

### The Main Wizard File
The `<WIZARD_NAME>.py` file must contain a class which extends `Wizard` from the `pymol.wizard` module.

### Conda Environments
The `envs` directory must contain either a generic `environment.yaml` file or two platform specific `linux_environment.yaml` and `windows_environment.yaml`. The installer will automatically use the correct one based on the underlying platform.

### Wizard Metadata File
The `metadata.yaml` file contains additional information about the wizard, such as the required PyMOL version, the text of the menu entries, etc. It also allows you to specify the path to custom Python scripts that the installer must run either before or after the installation of the wizard. Refer to the `example_metadata.yaml` file present in this repository for an example.

### Package Installation
If you want to avoid putting all of your wizard's code in the `<WIZARD_NAME>.py` file, you must include a `src` directory with a Python package. Since the package needs to be installable, you must also include a `pyproject.toml` file in the wizard's root directory and an optional `MANIFEST.in` file to specify any additional files that must be included in the package itself.

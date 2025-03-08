class WizardMetadata:
    name: str
    menu_entry: str
    default_env: str
    use_vr: bool
    python_version: str
    pymol_version: str
    openvr_version: str
    extra_dirs: str
    pre_script: str
    post_script: str

    def __init__(
        self,
        name,
        menu_entry,
        default_env,
        use_vr,
        python_version,
        pymol_version,
        openvr_version,
        extra_dirs,
        pre_script,
        post_script,
    ):
        self.name = name
        self.menu_entry = menu_entry
        self.default_env = default_env
        self.use_vr = use_vr
        self.python_version = python_version
        self.pymol_version = pymol_version
        self.openvr_version = openvr_version
        self.extra_dirs = extra_dirs
        self.pre_script = pre_script
        self.post_script = post_script

# © 2024–2026 Evolver Transformation, Inc. All rights reserved.
# This software and all associated documentation (the "Software") are the exclusive, confidential, and proprietary property of Evolver Transformation, Inc.
# Any unauthorized use—including but not limited to copying, distribution, modification, reverse engineering, or repurposing of this Software, in whole or in part—is a direct violation of intellectual property law and will be pursued to the fullest extent permitted under applicable law.
# This restriction applies unequivocally to all individuals and entities, including former employees, contractors, partners, and affiliates.
# Continued possession or use of this Software after termination of any relationship with Evolver Transformation, Inc. is strictly forbidden and may result in legal action.

"""Deprecated shim — import from ``cmdline`` directly.

.. deprecated::
    This module is a compatibility shim. All symbols now live in
    ``aria/packages/cmdline/``. Update your imports::

        # old
        from common.commandline import cmd, optarg, ...

        # new
        from cmdline import cmd, optarg, ...
"""

import warnings

warnings.warn(
    "common.commandline is a deprecated shim. "
    "Import from 'cmdline' instead: `from cmdline import ...`",
    DeprecationWarning,
    stacklevel=2,
)

from cmdline import (  # noqa: F401, E402
    CommandGroup,
    cmd,
    cmd_group,
    cmd_section,
    cmds,
    configure_cli_logging,
    create_parser,
    normalize_command_group_subcommand,
    optarg,
    verbose,
    _group_flat_aliases,
)

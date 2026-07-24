# -*- coding: utf-8 -*-
"""Shared launch options for the web tools' throwaway browsers.

The desktop tools launch a persistent context with ``--start-maximized`` and
``no_viewport`` so a watchable run fills the operator's screen (see
``finder_core.build_launch_kwargs``). The web path launches a *non*-persistent
browser instead, so it needs the same two settings applied across the
launch/context split — otherwise a headed run draws the page into Playwright's
default 1280x720 viewport and leaves the rest of the window blank.

Headless runs keep the fixed viewport: ``no_viewport`` there would fall back to
Chrome's 800x600 default and cut off the wide Aztek tables.
"""
from __future__ import annotations


def launch_kwargs(headed: bool) -> dict:
    """kwargs for ``chromium.launch``."""
    kwargs: dict = {'headless': not headed}
    if headed:
        kwargs['args'] = ['--start-maximized']
    return kwargs


def context_kwargs(headed: bool, **extra) -> dict:
    """kwargs for ``browser.new_context``, sized to the real window when headed."""
    kwargs = dict(extra)
    if headed:
        kwargs['no_viewport'] = True
    return kwargs

# -*- coding: utf-8 -*-
"""GUI-free core ของ Item Finder — ห้าม import tkinter (ใช้ร่วมทั้ง desktop และ web backend)."""
from dataclasses import dataclass, field, asdict

_CONFIG_KEYS = ('game', 'url', 'multi', 'deep', 'web', 'img', 'qty_val',
                'trade', 'drill', 'crit_val', 'batch', 'headless', 'read_desc')


@dataclass(frozen=True)
class SearchConfig:
    game: str
    url: str
    multi: list
    deep: bool = False
    web: str = 'any'
    img: str = 'any'
    qty_val: str = ''
    trade: str = 'any'
    drill: str = 'any'
    crit_val: str = ''
    batch: int = 10
    headless: bool = False
    read_desc: bool = False

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: d[k] for k in _CONFIG_KEYS if k in d})

    def as_dict(self):
        return {k: getattr(self, k) for k in _CONFIG_KEYS}


def build_launch_kwargs(*, headless, user_data_dir, chrome_exe=None):
    """kwargs สำหรับ launch_persistent_context — ให้ตรงกับที่ _auto/_open_login เคย inline ไว้."""
    kw = dict(user_data_dir=user_data_dir, headless=headless,
              args=['--start-maximized'], no_viewport=True)
    if chrome_exe:
        kw['executable_path'] = chrome_exe
    return kw

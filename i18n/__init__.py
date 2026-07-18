import bpy

from . import (
    de_DE,
    en_US,
    es_ES,
    fr_FR,
    it_IT,
    ja_jp,
    ko_KR,
    pl_PL,
    pt_BR,
    ru_RU,
    vi_VN,
    zh_CN,
    zh_TW,
)


CONTEXT = "yl_cameraref"


def _with_addon_context(translations):
    return {(CONTEXT, message): text for (_, message), text in translations.items()}


TRANSLATIONS = {
    "de_DE": _with_addon_context(de_DE.TRANSLATIONS),
    "en_US": _with_addon_context(en_US.TRANSLATIONS),
    "es": _with_addon_context(es_ES.TRANSLATIONS),
    "fr_FR": _with_addon_context(fr_FR.TRANSLATIONS),
    "it_IT": _with_addon_context(it_IT.TRANSLATIONS),
    "ja_JP": _with_addon_context(ja_jp.TRANSLATIONS),
    "ko_KR": _with_addon_context(ko_KR.TRANSLATIONS),
    "pl_PL": _with_addon_context(pl_PL.TRANSLATIONS),
    "pt_BR": _with_addon_context(pt_BR.TRANSLATIONS),
    "ru_RU": _with_addon_context(ru_RU.TRANSLATIONS),
    "vi_VN": _with_addon_context(vi_VN.TRANSLATIONS),
    "zh_HANS": _with_addon_context(zh_CN.TRANSLATIONS),
    "zh_HANT": _with_addon_context(zh_TW.TRANSLATIONS),
}


def tr_report(message, **values):
    translated = bpy.app.translations.pgettext_rpt(message, msgctxt=CONTEXT)
    return translated.format(**values) if values else translated


def tr_iface(message, **values):
    translated = bpy.app.translations.pgettext_iface(message, msgctxt=CONTEXT)
    return translated.format(**values) if values else translated


def register():
    bpy.app.translations.register(__package__, TRANSLATIONS)


def unregister():
    bpy.app.translations.unregister(__package__)

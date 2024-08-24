from pathlib import Path
import gettext as _gettext


_DOMAIN = 'beanbot'

gettext = _gettext.gettext


def init_locale():
    """Initialize the locale translation."""
    from . import config
    locale_dir = Path(__file__).parent.parent / 'locale'
    language = config.get('language')
    if language is not None:
        # Use custom translation
        translation = _gettext.translation(_DOMAIN, locale_dir, [language], fallback=True)
        global gettext
        gettext = translation.gettext
    else:
        # Use default translation, and load locale from env
        _gettext.bindtextdomain(_DOMAIN, locale_dir)
        _gettext.textdomain(_DOMAIN)
    

import argparse
import gettext
import pathlib
import conf
import logging
from bean_utils.bean import init_bean_manager


def _init_locale():
    locale_dir = pathlib.Path(__file__).parent / 'locale'
    gettext.bindtextdomain('beanbot', locale_dir)
    gettext.textdomain('beanbot')


if __name__ == "__main__":
    # Init logging
    logging.basicConfig(level=logging.INFO)
    # logging.getLogger().addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(prog='beanbot',
                                     description='Bot to translate text into beancount transaction')
    subparser = parser.add_subparsers(title='sub command', dest='command')

    telegram_parser = subparser.add_parser("telegram")
    telegram_parser.add_argument('-c', nargs="?", type=str, default="config.yaml", help="config file path")
    mattermost_parser = subparser.add_parser("mattermost")
    mattermost_parser.add_argument('-c', nargs="?", type=str, default="config.yaml", help="config file path")

    args = parser.parse_args()
    if args.command is not None:
        conf.load_config(args.c)
        # Init i18n
        conf.set_locale()
        _init_locale()
        init_bean_manager()

    if args.command == "telegram":
        from bots.telegram_bot import run_bot
        run_bot()
    elif args.command == "mattermost":
        from bots.mmbot import run_bot
        run_bot()
    else:
        parser.print_help()

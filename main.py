import argparse
import conf
from bean_utils import bean


def init_bot(config_path):
    conf.load_config(config_path)
    # Init i18n
    conf.init_locale()
    # Init logging
    conf.init_logging()
    # Init beancount manager
    bean.init_bean_manager()


def parse_args():
    parser = argparse.ArgumentParser(prog='beanbot',
                                     description='Bot to translate text into beancount transaction')
    subparser = parser.add_subparsers(title='sub command', required=True, dest='command')

    telegram_parser = subparser.add_parser("telegram")
    telegram_parser.add_argument('-c', nargs="?", type=str, default="config.yaml", help="config file path")
    mattermost_parser = subparser.add_parser("mattermost")
    mattermost_parser.add_argument('-c', nargs="?", type=str, default="config.yaml", help="config file path")

    return parser.parse_args()


def main():
    args = parse_args()
    init_bot(args.c)

    if args.command == "telegram":
        from bots.telegram_bot import run_bot
    elif args.command == "mattermost":
        from bots.mattermost_bot import run_bot
    run_bot()


if __name__ == "__main__":
    main()

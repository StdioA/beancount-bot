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
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="beanbot",
        description="Bot to translate text into beancount transaction",
    )
    subparsers = parser.add_subparsers(title="sub command", required=True, dest="command")

    telegram_parser = subparsers.add_parser("telegram")
    mattermost_parser = subparsers.add_parser("mattermost")
    web_parser = subparsers.add_parser("web")

    for p in [telegram_parser, mattermost_parser, web_parser]:
        p.add_argument("-c", type=str, default="config.yaml", help="config file path")

    return parser.parse_args()


def main():
    args = parse_args()
    init_bot(args.c)

    if args.command == "telegram":
        from bots.telegram_bot import run_bot
    elif args.command == "mattermost":
        from bots.mattermost_bot import run_bot
    elif args.command == "web":
        from bots.web_bot import run_bot
    run_bot()


if __name__ == "__main__":
    main()

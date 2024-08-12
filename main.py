import argparse
import conf


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='beanbot',
                                     description='Bot to translate text into beancount transaction')
    subparser = parser.add_subparsers(title='sub command', dest='command')

    telegram_parser = subparser.add_parser("telegram")
    telegram_parser.add_argument('-c', nargs="?", type=str, default="config.yaml", help="config file path")
    mattermost_parser = subparser.add_parser("mattermost")
    mattermost_parser.add_argument('-c', nargs="?", type=str, default="config.yaml", help="config file path")

    args = parser.parse_args()
    if args.command == "telegram":
        conf.load_config(args.c)
        from bots.telegram_bot import run_bot
        run_bot()
    elif args.command == "mattermost":
        conf.load_config(args.c)
        from bots.mmbot import run_bot
        run_bot()
    else:
        parser.print_help()

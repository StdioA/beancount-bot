
LANGUAGES := en zh_CN zh_TW fr_FR ja_JP ko_KR de_DE es_ES

gentranslations:
	xgettext -d beanbot -o locale/beanbot.pot **/*.py
	for lang in $(LANGUAGES); do \
		mkdir -p locale/$$lang/LC_MESSAGES; \
		if [ -f locale/$$lang/LC_MESSAGES/beanbot.po ]; then \
			msgmerge --update locale/$$lang/LC_MESSAGES/beanbot.po locale/beanbot.pot; \
		else \
			msginit -i locale/beanbot.pot -o locale/$$lang/LC_MESSAGES/beanbot.po -l $$lang; \
		fi; \
	done

compiletranslations:
	for lang in $(LANGUAGES); do \
		msgfmt -o locale/$$lang/LC_MESSAGES/beanbot.mo locale/$$lang/LC_MESSAGES/beanbot.po; \
	done
